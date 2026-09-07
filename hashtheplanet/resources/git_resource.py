"""
This module handles Git resources to generate hashes.
"""
# standard imports
import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Optional, Set, Tuple

# third party imports
from loguru import logger

# project imports
from hashtheplanet.resources.resource import Resource
from hashtheplanet.config.extensions_list import EXCLUDED_FILE_PATTERN

# types
FilePath = str
BlobHash = str
TagName = str
FileHash = str
FileMetadata = Tuple[FilePath, TagName, FileHash]

# SHA1 of an empty blob in git
EMPTY_BLOB_SHA1 = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


class GitResource(Resource):
    """
    This class implements methods to generate hashes from Git resources.
    """
    name = "git"

    def __init__(self):
        # Temporary clone directory, only used when no cache_dir is provided.
        self._tmp_dir: Optional[str] = None

    @staticmethod
    def clone_or_fetch(url: str, path: str):
        """
        Clone the repository if it doesn't exist, otherwise fetch new tags.
        """
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, "objects")):
            logger.debug(f"Fetching updates for {url} ...")
            subprocess.check_call(
                ['git', 'fetch', '--tags', '--force', 'origin'],
                cwd=path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            logger.debug(f"Cloning repository {url} ...")
            subprocess.check_call(
                ['git', 'clone', '--bare', url, path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    @staticmethod
    def get_tags(repo_path: str) -> List[str]:
        """
        Retrieve all tag names from a bare repository.
        """
        output = subprocess.check_output(
            ['git', 'tag', '-l'],
            cwd=repo_path
        ).decode('utf-8', errors='replace')
        return [tag.strip() for tag in output.splitlines() if tag.strip()]

    @staticmethod
    def ls_tree(repo_path: str, tag_name: str) -> List[Tuple[FilePath, BlobHash]]:
        """
        Get all (file_path, blob_sha1) pairs for a given tag using git ls-tree -r.
        This is much faster than traversing the tree with GitPython.
        """
        try:
            output = subprocess.check_output(
                ['git', 'ls-tree', '-r', tag_name],
                cwd=repo_path,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='replace')
        except subprocess.CalledProcessError:
            logger.warning(f"Failed to list tree for tag {tag_name}")
            return []

        files = []
        for line in output.splitlines():
            if not line:
                continue
            # Format: "<mode> <type> <sha1>\t<path>"
            try:
                meta, file_path = line.split('\t', 1)
                parts = meta.split(' ')
                blob_sha1 = parts[2]
            except (ValueError, IndexError):
                continue

            # Skip empty blobs
            if blob_sha1 == EMPTY_BLOB_SHA1:
                continue

            # Skip excluded file patterns
            if re.search(EXCLUDED_FILE_PATTERN, file_path):
                continue

            files.append((file_path, blob_sha1))

        return files

    def _get_blob_hashes(self, repo_path: str, tags: List[str],
                         skip_tags: Optional[Set[str]] = None) -> List[FileMetadata]:
        """
        Retrieve all (file_path, tag_name, blob_sha1) for all tags.
        Uses git ls-tree -r for each tag (single subprocess call per tag).
        """
        files: List[FileMetadata] = []
        skip = skip_tags or set()

        for tag_name in tags:
            if tag_name in skip:
                continue

            for file_path, blob_sha1 in self.ls_tree(repo_path, tag_name):
                files.append((file_path, tag_name, blob_sha1))

        return files

    def compute_hashes(self, target: str, cache_dir: str = None, builder=None, **kwargs):
        """
        Clone/fetch the repository, retrieve tags, compute hashes, and store them in the builder.
        """
        technology = target.split('.git')[0].split('/')[-1]

        if cache_dir:
            repo_path = os.path.join(cache_dir, technology + ".git")
        else:
            repo_path = None

        try:
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
                self.clone_or_fetch(target, repo_path)
            else:
                self._tmp_dir = tempfile.mkdtemp()
                repo_path = self._tmp_dir
                subprocess.check_call(
                    ['git', 'clone', '--bare', target, repo_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except subprocess.CalledProcessError as error:
            logger.warning(f"Error while cloning repository on {target}: {error}")
            return

        logger.info("Retrieving tags ...")
        tags = self.get_tags(repo_path)

        logger.info(f"Retrieving the hashes from the Git repository ({len(tags)} tags)...")
        files = self._get_blob_hashes(repo_path, tags)

        logger.info("== DONE ! ==")

        if builder is not None:
            logger.info("Saving hashes to JSON builder ...")
            entries = [(file_path, file_hash, tag_name) for file_path, tag_name, file_hash in files]
            builder.add_entries_bulk(technology, entries)

        # Clean up temp dir if we created one
        if not cache_dir and self._tmp_dir:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
            self._tmp_dir = None
