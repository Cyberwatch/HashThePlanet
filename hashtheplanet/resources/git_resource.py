"""
This module handles Git resources to generate hashs.
"""
# standard imports
import os
import re
import subprocess
import tempfile
from stat import S_ISDIR
from typing import List, Tuple

# third party imports
from git import GitCommandError, Repo
from git.objects.commit import Commit
from git.refs.tag import Tag
from loguru import logger

# project imports
from hashtheplanet.sql.db_connector import Hash
from hashtheplanet.resources.resource import Resource
from hashtheplanet.config.extensions_list import EXCLUDED_FILE_PATTERN

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
            match_ext = re.search(EXCLUDED_FILE_PATTERN, blob.path)
            if not match_ext:
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


    def _get_blob_hashes(self, tags : List[Tag]) -> List[FileMetadata]:

        files: List[GitFileMetadata] = []

        for tag in tags:
            tag_name = tag.name
            commit = tag.commit

            for item in commit.tree.traverse():
                if item.type == 'blob':
                    file_path = item.path
                    file_hash = item.hexsha
                    match_ext = re.search(EXCLUDED_FILE_PATTERN, file_path)
                    if not match_ext:
                        files.append((file_path, tag_name, file_hash))

        return files

    def _save_hashes(
        self,
        session_scope,
        files_info: List[FileMetadata],
        technology: str
    ):
        """
        This method saves all files with their hash & their versions to the database.
        """
        with session_scope() as session:
            file_record = {}

            for (file_path, tag_name, file_hash) in files_info:

                self._database.insert_or_update_hash(session, file_path, file_hash, technology, [tag_name])
                file_record[file_path] = (tag_name, file_hash)

    def compute_hashes(self, session_scope, target: str):
        """
        This method clones the repository from url, retrieves tags, retrieve the hashes, and then stores the tags
        & files information in the database.
        """
        technology = target.split('.git')[0].split('/')[-1]
        files: List[GitFileMetadata] = []

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            try:
                repo = self.clone_repository(target, tmp_dir_name)
            except GitCommandError as error:
                logger.warning(f"Error while cloning repository on {target}: {error}")
                return

            logger.info("Retrieving tags ...")
            tags = repo.tags.copy()

            logger.info("Retrieving the hashes from the Git repository...")
            files += self._get_blob_hashes(tags)

            logger.info("== DONE ! ==")

        logger.info("Saving hashes ...")
        self._save_hashes(session_scope, files, technology)
