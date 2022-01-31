"""
The main module for HashThePlanet
"""
# standard imports
import argparse
from json import JSONDecodeError
import os
import sys
from contextlib import contextmanager
from typing import List, Tuple

# third party imports
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# project imports
from hashtheplanet.config.config import Config
from hashtheplanet.executor.executor import Executor
from hashtheplanet.sql.db_connector import Base, DbConnector, Hash

HASHTHEPLANET_VERSION = "HashThePlanet 0.0.0"

class HashThePlanet():
    """
    The HashThePlanet class
    """
    def __init__(self, output_file: str, input_file: str):
        """
        Initialisation requires an output filename and an input filename (csv).
        """
        self._output_file = output_file
        self._input_file = input_file
        self._engine = create_engine(f"sqlite:///{self._output_file}")

        if not os.path.exists(self._output_file):
            Base.metadata.create_all(self._engine)

        self._session = sessionmaker(self._engine)

        self._database = DbConnector()
        self._config = Config()
        self._executor = Executor(self._database, self.session_scope)

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope around a series of operations.
        """
        session = self._session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """
        Close the connections with the database.
        """
        self._engine.dispose()

    def show_all_hashs(self):
        """
        Prints out all known hashs.
        """
        with self.session_scope() as session:
            hashs = self._database.get_all_hashs(session)
            if hashs:
                for hash_value in hashs:
                    logger.success(hash_value)
            else:
                logger.info("No hash to display")

    def find_hash(self, file_hash):
        """
        Finds the associated technology to a hash.
        """
        with self.session_scope() as session:
            logger.success(f"Found: {self._database.find_hash(session, file_hash)}")

    def compute_hashs(self):
        """
        Computes all hashs.
        """
        try:
            self._config.parse(self._input_file)

            for resource_name in self._config.get_used_resources():
                targets = self._config.get_targets(resource_name)

                for target in targets:
                    self._executor.execute(resource_name, target)

            logger.info("Computing done")

        except (OSError, JSONDecodeError) as error:
            logger.error(f"Error: {error}")
            sys.exit(1)

    def analyze_file(self, file_path: str) -> Tuple[str, dict]:
        """
        Analyze a file and returns its technology and its versions
        """
        file_hash = Hash.hash_file(file_path)

        if file_hash is None:
            return (None, None)
        return self.analyze_hash(file_hash)

    def analyze_str(self, str_data: str) -> Tuple[str, dict]:
        """
        Analyze a string and returns its technology and its versions
        """
        if str_data is None:
            return (None, None)

        file_hash = Hash.hash_bytes(str_data.encode("utf-8"))
        return self.analyze_hash(file_hash)

    def analyze_hash(self, file_hash: str) -> Tuple[str, dict]:
        """
        Analyze a hash and returns its technology and its versions
        """
        if file_hash is None:
            return (None, None)
        with self.session_scope() as session:
            return self._database.find_hash(session, file_hash)

    def get_static_files(self) -> List[str]:
        """
        Returns all stored static files from the database
        """
        with self.session_scope() as session:
            return self._database.get_static_files(session)

    def get_versions(self, technology: str) -> List[str]:
        """
        Returns all stored versions for a technology
        """
        with self.session_scope() as session:
            return self._database.get_versions(session, technology)

def main():
    """
    The main function, which is the entry point of the program.
    It stores arguments provided by the user and launches hash computing.
    """
    logger.remove()
    parser = argparse.ArgumentParser(description="HashThePlanet-0.0.0")

    parser.add_argument(
        "-o", "--output",
        default="dist/collected_data.db",
        help="Output file name"
    )

    parser.add_argument(
        "-i", "--input",
        default="src/tech_list.json",
        help="Input file (json) with resources targets"
    )

    parser.add_argument(
        "--color",
        action="store_true",
        help="Colorize output"
    )

    parser.add_argument(
        "-v", "--verbose",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
        help="Set verbosity level"
    )

    parser.add_argument(
        "--hash",
        default=None,
        help="File hash"
    )

    parser.add_argument(
        "-f", "--file",
        default=None,
        help="File path"
    )

    parser.add_argument(
        "--version",
        action="version",
        help="Show program's version number and exit",
        version=HASHTHEPLANET_VERSION
    )

    args = parser.parse_args()

    if args.color:
        logger.add(sys.stdout, format="<lvl>{message}</lvl>", level=args.verbose)
    else:
        logger.add(sys.stdout, colorize=False, format="{message}", level=args.verbose)

    logger.info("#### HashThePlanet ####")
    hashtheplanet = HashThePlanet(args.output, args.input)

    if args.file is not None:
        readable_hash = Hash.hash_file(args.file)
        if readable_hash is None:
            return
        hashtheplanet.find_hash(readable_hash)
        return
    if args.hash is not None:
        hashtheplanet.find_hash(args.hash)
        return

    logger.debug("Start computing hashs")
    hashtheplanet.compute_hashs()
    logger.debug("Retrieving computed hashs")
    hashtheplanet.show_all_hashs()
    hashtheplanet.close()
