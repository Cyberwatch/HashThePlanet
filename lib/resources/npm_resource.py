"""
This module handles npm resources to generate hashs.
"""
#standard imports
import hashlib
import tarfile
import tempfile
from typing import List
import requests

# third party imports
from loguru import logger
from bs4 import BeautifulSoup

# project imports
from sql.db_connector import DbConnector
from resources.resource import Resource

class NpmResource(Resource):
    name = "npm"

    """
    This class implements methods to generate hashs from npm resources.
    """
    def __init__(self, database: DbConnector):
        """
        Initialisation requires a DbConnector object.
        """
        self._database = database

    def get_hash_from_bytes(self, file_bytes):
        """
        This method computes the hash of the provided file and returns it.
        """
        try:
            readable_hash = hashlib.sha256(file_bytes).hexdigest()
            return readable_hash
        except OSError as error:
            print(f"Error with file: {error}")
        return None

    def retrieve_versions(self, npm_module_name: str) -> List[str]:
        """
        This method retrieves an npm module's versions.
        """
        page = requests.get(f"https://www.npmjs.com/package/{npm_module_name}?activeTab=versions")
        soup = BeautifulSoup(page.content, "html.parser")
        versions = []

        table = soup.find('div', attrs={'id':'tabpanel-versions'})
        table_body_version_elements = list(list(table.children)[0])
        table_body_version_history = None

        # The length is equal to 6 when there is a checkbox asking if we want to show deprecated versions
        if len(table_body_version_elements) == 6:
            table_body_version_history = table_body_version_elements[5]
        else:
            table_body_version_history = table_body_version_elements[4]

        rows = table_body_version_history.find_all("li")

        for row in list(rows):
            version = row.find("a")
            if version is None:
                continue
            versions.append(version.get_text())
        return versions

    def save_tar_to_disk(self, file_path: str, npm_module_name: str, version: str):
        """
        This method downloads a tar file containing the specific version of an npm module.
        """
        r = requests.get(
            f"https://registry.npmjs.org/{npm_module_name}/-/{npm_module_name}-{version}.tgz",
            allow_redirects=True
        )
        with open(file_path, 'wb') as file_fd:
            file_fd.write(r.content)

    def extract_hashes_from_tar(self, file_path: str) -> List[str]:
        """
        This method returns all hashes of all files contained in a tar file.
        """
        files = []

        with tarfile.open(file_path) as tar:
            for file in tar.getmembers():
                f = tar.extractfile(file)

                files.append((file.path, self.get_hash_from_bytes(f.read())))
        return files

    def compute_hashes(self, session_scope, npm_module_name: str):
        """
        This method downloads all versions of an npm module and stores all the versions
        with theirs associated files & hashes to the database.
        """
        versions = self.retrieve_versions(npm_module_name)
        files_info = {}

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            for version in versions:
                logger.debug(f"Downloading {npm_module_name}-v{version} ...")
                file_path = f"{tmp_dir_name}/{npm_module_name}-{version}.tgz"

                self.save_tar_to_disk(file_path, npm_module_name, version)
                files_info[version] = self.extract_hashes_from_tar(file_path)

        with session_scope() as session:
            self._database.insert_tags(session, npm_module_name, versions)
            for version, files in files_info.items():
                for (file_path, file_hash) in files:

                    self._database.insert_file(session, npm_module_name, file_path)
                    self._database.insert_or_update_hash(session, file_hash, npm_module_name, version)
