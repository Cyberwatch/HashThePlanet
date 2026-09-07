"""
This module handles npm resources to generate hashes.
"""
#standard imports
import re
import tarfile
import tempfile
from typing import Dict, List, Set, Tuple
import json

# third party imports
from loguru import logger
import requests

# project imports
from hashtheplanet.utils.hash_utils import hash_bytes
from hashtheplanet.resources.resource import Resource
from hashtheplanet.config.extensions_list import EXCLUDED_FILE_PATTERN

# types
FileHash = str
FilePath = str
VersionName = str
FileMetadata = Tuple[FilePath, FileHash]

class NpmResource(Resource):
    """
    This class implements methods to generate hashes from npm resources.
    """
    name = "npm"

    @staticmethod
    def retrieve_versions(npm_module_name: str) -> Set[VersionName]:
        """
        This method retrieves npm module versions.
        """
        page = requests.get(f"https://registry.npmjs.org/{npm_module_name}", timeout=10)
        return set(json.loads(page.content)["versions"])

    @staticmethod
    def save_tar_to_disk(file_path: str, npm_module_name: str, version: str):
        """
        This method downloads a tar file containing the specific version of an npm module.
        """
        request = requests.get(
            f"https://registry.npmjs.org/{npm_module_name}/-/{npm_module_name}-{version}.tgz",
            allow_redirects=True,
            timeout=10
        )
        with open(file_path, 'wb') as file_fd:
            file_fd.write(request.content)

    @staticmethod
    def extract_hashes_from_tar(file_path: str) -> List[FileMetadata]:
        """
        This method returns all hashes of all files contained in a tar file.
        """
        files = []

        with tarfile.open(file_path) as tar:
            for member in tar.getmembers():
                file = tar.extractfile(member)

                if file is None:
                    continue
                files.append((member.path, hash_bytes(file.read())))
        return files

    def compute_hashes(self, target: str, builder=None, **kwargs):
        """
        This method downloads all versions of an npm module and stores all the versions with their
        associated files and hashes in the JsonBuilder.
        """
        versions = self.retrieve_versions(target)
        files_info: Dict[VersionName, List[FileMetadata]] = {}

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            for version in versions:
                logger.debug(f"Downloading {target}-v{version} ...")
                file_path = f"{tmp_dir_name}/{target}-{version}.tgz"

                self.save_tar_to_disk(file_path, target, version)
                files_info[version] = self.extract_hashes_from_tar(file_path)

        if builder is not None:
            entries = []
            for version, files in files_info.items():
                for (file_path, file_hash) in files:
                    match_ext = re.search(EXCLUDED_FILE_PATTERN, file_path)
                    if not match_ext:
                        entries.append((file_path, file_hash, version))
            builder.add_entries_bulk(target, entries)
