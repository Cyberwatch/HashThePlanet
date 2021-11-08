"""
This module handles Git resources to generate hashs.
"""
#standard imports
import glob
import hashlib
import os
import tempfile

# third party imports
from git import Git, Repo, GitCommandError
from loguru import logger

# project imports
from sql.db_connector import DbConnector

EXTENSION = ["txt", "css", "js"]

class GitResource():
    """
    This class implements methods to generate hashs from Git resources.
    """
    def __init__(self, database: DbConnector):
        """
        Initialisation requires a DbConnector object.
        """
        self._database = database

    @staticmethod
    def clone_repository(technology, url, path):
        """
        This method tries to clone the repository from the provided url.
        """
        logger.debug(f"Cloning repository {url} ...")
        Git(path).clone(url)
        repository = Repo(f"{path}/{technology}")
        return repository

    @staticmethod
    def get_tags(repository: Repo):
        """
        This method returns the list of tags sorted by commit date.
        """
        return sorted(repository.tags, key=lambda tag: tag.commit.committed_datetime)

    @staticmethod
    def get_hash(file):
        """
        This method computes the hash of the provided file and returns it.
        """
        try:
            with open(file, 'rb') as file_descriptor:
                file_bytes = file_descriptor.read() # read entire file as bytes
                readable_hash = hashlib.sha256(file_bytes).hexdigest()
                return readable_hash
        except OSError as error:
            logger.error(f"Error with file {file} : {error}")
        return None

    def checkout_and_compute(self, session, directory, repository: Repo, tag):
        """
        This method checkout the provided tag of the repository,
        stores files information in the database and computes the hashs.
        """
        repository.git.checkout(f"tags/{tag}")
        technology = directory.split('/')[-1]

        for root, _, _ in os.walk(directory):
            for ext in EXTENSION:
                for file_name in glob.glob(f"{root}/**/*.{ext}", recursive = True):
                    index = file_name.find(technology)
                    path = file_name[index:].lstrip(technology)

                    logger.debug(f"Current tag : {tag}")

                    self._database.insert_file(session, technology, path)

                    path_to_file = f"{directory}{path}"
                    logger.debug(f"Path to file : {path_to_file}")
                    hash_value = self.get_hash(path_to_file)
                    logger.debug(f"Hash value : {hash_value}")

                    self._database.insert_or_update_hash(session, hash_value, technology, tag)

    def clone_checkout_and_compute_hashs(self, session_scope, url):
        """
        This method clones the repository from url, retrieves and stores tags in the database,
        then checkout each tag, sotres files information in the database and computes the hashs.
        """
        technology = url.split('.git')[0].split('/')[-1]
        with tempfile.TemporaryDirectory() as tmp_dir_name:

            try:
                repository = self.clone_repository(technology, url, tmp_dir_name)
            except GitCommandError as error:
                logger.warning(f"Error while cloning repository on {url}: {error}")
                return

            logger.debug("Retrieving tags ...")
            path = f"{tmp_dir_name}/{technology}"
            git_tags = self.get_tags(repository)
            logger.debug(f"Git tags : {git_tags}")

            logger.debug(f"Inserting tags for {technology} ...")
            with session_scope() as session:
                self._database.insert_versions(session, technology, git_tags)

            logger.debug(f"Retrieving tags from database for {technology}")
            with session_scope() as session:
                tags = self._database.get_versions(session, technology)
                logger.debug(f"Database tags : {tags}")

                for tag in tags:
                    logger.debug(f"Checkout and compute hashs for tag {tag} ...")
                    self.checkout_and_compute(
                        session, path, repository, tag.version)
