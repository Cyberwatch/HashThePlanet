"""
The main module for HashThePlanet
"""
# standard imports
import argparse
from contextlib import contextmanager
from csv import reader
import os
import sys

# third party imports
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# project imports
from sql.db_connector import DbConnector, Base
from resources.git_resource import GitResource

logger.remove()

HASHTHEPLANET_VERSION = "HashThePlanet 0.0.0"

class HashThePlanet():
    """
    The HashThePlanet class
    """
    def __init__(self, output_file, input_file):
        """
        Initialisation requires an output filename and an input filename (csv).
        """
        self._output_file = output_file
        self._input_file = input_file
        self._database = DbConnector()

        self._engine = create_engine(f"sqlite:///{self._output_file}")

        if not os.path.exists(self._output_file):
            Base.metadata.create_all(self._engine)

        self._git_resource = GitResource(self._database)

        self._session = sessionmaker(self._engine)

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

    def compute_hashs(self):
        """
        Computes all hashs.
        """
        try:
            with open(self._input_file, "r", encoding="utf-8", newline="") as file_descriptor:
                logger.info(f"Start reading {self._input_file}")
                csv_reader = reader(file_descriptor)

                for row in csv_reader:
                    if not row:
                        logger.warning("Input file contains an empty line")
                    else:
                        url = row[0]
                        self._git_resource.clone_checkout_and_compute_hashs(self.session_scope, url)

            logger.info("Computing done")

        except OSError as error:
            logger.error(f"Error: {error}")

def main():
    """
    The main function, which is the entry point of the program.
    It stores arguments provided by the user and launches hash computing.
    """

    parser = argparse.ArgumentParser(description="HashThePlanet-0.0.0")

    parser.add_argument(
        "-o", "--output",
        default="dist/collected_data.db",
        help="Output file name"
    )

    parser.add_argument(
        "--input",
        default="src/tech_list.csv",
        help="Input file (csv) with git repository urls"
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
    logger.debug("Start computing hashs")
    hashtheplanet.compute_hashs()
    logger.debug("Retrieving computed hashs")
    hashtheplanet.show_all_hashs()
    hashtheplanet.close()
