"""
This module handles Git resources to generate hashs.
"""
# standard imports
import os
import subprocess
import tempfile
from stat import S_ISDIR, S_ISREG
from typing import List, Tuple

# third party imports
from git import GitCommandError, Repo
from git.diff import Diff, DiffIndex
from git.objects.commit import Commit
from git.refs.tag import Tag
from loguru import logger

# project imports
from hashtheplanet.sql.db_connector import Hash, Version as VersionTable
from hashtheplanet.resources.resource import Resource

# types
FilePath = str
BlobHash = str
TagName = str
FileHash = str
GitFileMetadata = Tuple[FilePath, TagName, BlobHash]
FileMetadata = Tuple[FilePath, TagName, FileHash]

class GitResource(Resource):
    """
    This class implements methods to generate hashs from Git resources.
    """
    name = "git"

    @staticmethod
    def clone_repository(url, path) -> Repo:
        """
        This method tries to clone the repository from the provided url.
        """
        logger.debug(f"Cloning repository {url} ...")
        return Repo.clone_from(url, path, bare=True)

    @staticmethod
    def get_all_files_from_commit(commit: Commit) -> List[Tuple[FilePath, BlobHash]]:
        """
        This method retrieves all files with their blob hash in a commit.
        """
        file_list = []

        for blob in commit.tree.traverse():
            if S_ISDIR(blob.mode):
                continue
            file_list.append((blob.path, blob.hexsha))
        return file_list

    @staticmethod
    def _hash_files(
        files: List[GitFileMetadata],
        repo_dir_path: str
    ) -> List[FileMetadata]:
        """
        This method calculates the SHA256 hashes of input files.
        To do so, it reads first the content by using the file blob hash with the command `git cat-file -p [blob hash]`,
        then it calculates the hash.
        """
        files_info: List[Tuple[FilePath, TagName, FilePath]] = []
        current_dir = os.getcwd()
        os.chdir(repo_dir_path)

        for (file_path, tag_name, blob_hash) in files:
            try:
                # We need to use a subprocess and not the GitPython library
                # because when we execute "git cat-file -p [blob]" with it, it always removes the \n from the last line.
                # Because of that when we calculate the hash of a file, it may change if it has originally a \n or not.
                # (https://github.com/gitpython-developers/GitPython/blob/main/git/cmd.py#L947)
                file_content = subprocess.check_output(
                    ['git', 'cat-file', '-p', blob_hash],
                    shell=False,
                )
                if len(file_content) == 0:
                    continue
                file_hash = Hash.hash_bytes(file_content)
                files_info.append((file_path, tag_name, file_hash))
            except (ValueError, subprocess.CalledProcessError) as exception:
                logger.error(exception)
        os.chdir(current_dir)
        return files_info

    @staticmethod
    def _get_changes_between_two_tags(tag_a: Tag, tag_b: Tag) -> List[GitFileMetadata]:
        """
        This method fetches all changes (modification & creation) between two tags,
        and returns a list of changes containing:
        - the file path
        - the associated tag name
        - the associated blob hash
        """
        files: List[GitFileMetadata] = []

        commit_a = tag_a.commit
        commit_b = tag_b.commit
        commit_diff: DiffIndex = commit_a.diff(commit_b)

        for diff in commit_diff:
            diff: Diff = diff

            if diff.a_blob and S_ISREG(diff.a_blob.mode):
                files.append((diff.a_blob.path, tag_b.name, diff.a_blob.hexsha))
            elif diff.b_blob and S_ISREG(diff.b_blob.mode):
                files.append((diff.b_blob.path, tag_b.name, diff.b_blob.hexsha))
        return files

    def _get_diff_files(self, tags: List[Tag]) -> List[GitFileMetadata]:
        """
        This method retrieves all changes between a list of tags and returns them.
        """
        logger.info("Retrieving diff of all tags ...")

        files: List[GitFileMetadata] = []

        # This line makes couples with the n + 1 element. Example: (A,B), (B,C), ...
        for (tag_a, tag_b) in zip(tags[:-1], tags[1:]):
            files += self._get_changes_between_two_tags(tag_a, tag_b)
        return files

    def _get_tag_files(self, tag: Tag) -> List[GitFileMetadata]:
        """
        This method retrieves all files with their tag name and their blob hash in a tag.
        """
        files: List[GitFileMetadata] = []

        for (file_path, blob_hash) in self.get_all_files_from_commit(tag.commit):
            files.append((file_path, tag.name, blob_hash))
        return files

    @staticmethod
    def _get_diff_versions(first_version: str, last_version: str, tags: List[Tag]) -> List[str]:
        """
        This method retrieves all tags between two tags.
        """
        tag_names = list(map(lambda tag: tag.name, tags))
        return tag_names[tag_names.index(first_version):tag_names.index(last_version)]

    def _save_hashes(
        self,
        session_scope,
        files_info: List[FileMetadata],
        tags: List[Tag],
        technology: str
    ):
        """
        This method saves all files with their hash & their versions to the database.
        """
        with session_scope() as session:
            file_record = {}

            self._database.insert_versions(session, technology, tags)
            for (file_path, tag_name, file_hash) in files_info:
                (last_version, last_hash) = file_record.get(file_path) or (None, None)

                self._database.insert_file(session, technology, file_path)

                if last_version is not None:
                    # We retrieve all the versions between the last version of the file and this one
                    # and then we add them to the last hash
                    versions = self._get_diff_versions(last_version, tag_name, tags)
                    self._database.insert_or_update_hash(session, last_hash, technology, versions)

                self._database.insert_or_update_hash(session, file_hash, technology, [tag_name])
                file_record[file_path] = (tag_name, file_hash)

    @staticmethod
    def _filter_stored_tags(stored_versions: List[VersionTable], found_tags: List[Tag]) -> List[Tag]:
        """
        This function will compare the stored tags (the tags in the htp database)
        and the tags found in the git repository, then after it keeps only the non stored tags.
        """
        result = []

        if len(stored_versions) == len(found_tags):
            return []
        for found_tag_idx, found_tag in enumerate(found_tags):
            last_found_tag_idx = found_tag_idx - 1

            if found_tag_idx >= len(stored_versions) or found_tag.name != stored_versions[found_tag_idx]:

                # this verification permits to know if it's the first to be added,
                # and if it's the case, then we add the one before to permits to make a diff
                if last_found_tag_idx >= 0 and not result:
                    result.append(found_tags[last_found_tag_idx])
                result.append(found_tag)
        return result

    def compute_hashes(self, session_scope, target: str):
        """
        This method clones the repository from url, retrieves tags, compares each tags to retrieve only modified files,
        computes their hashes and then stores the tags & files information in the database.
        """
        technology = target.split('.git')[0].split('/')[-1]
        tags: List[Tag] = []
        files: List[GitFileMetadata] = []

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            try:
                repo = self.clone_repository(target, tmp_dir_name)
            except GitCommandError as error:
                logger.warning(f"Error while cloning repository on {target}: {error}")
                return

            logger.info("Retrieving tags ...")
            tags = repo.tags.copy()

            with session_scope() as session:
                stored_tags = self._database.get_versions(session, technology)

                if not stored_tags:
                    logger.info("Retrieving files from the first tag ...")
                    files += self._get_tag_files(tags[0])

                logger.info("Filtering the tags ...")
                tags = self._filter_stored_tags(stored_tags, tags)

            logger.info("Retrieving only modified files between the tags ...")
            files += self._get_diff_files(tags)

            logger.info("Generating hashes ...")
            files_info = self._hash_files(files, tmp_dir_name)

        logger.info("Saving hashes ...")
        self._save_hashes(session_scope, files_info, tags, technology)
