"""
The main module for HashThePlanet
"""

import argparse
import sys

from loguru import logger

logger.remove()

HASHTHEPLANET_VERSION = "HashThePlanet 0.0.0"

class HashThePlanet():
    """
    The HashThePlanet class
    """

    @staticmethod
    def show_all_hashs():
        """
        Prints out all known hashs
        """
        # TODO: change code here
        logger.info("No hash to display")

    @staticmethod
    def compute_hashs():
        """
        Computes all hashs
        """
        # TODO: change code here
        logger.info("Computing done")

def main():
    """
    The main function, which is the entry point of the program.
    It stores arguments provided by the user and launches hash computing.
    """

    parser = argparse.ArgumentParser(description="HashThePlanet-0.0.0")

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
    hashtheplanet = HashThePlanet()
    logger.debug("Start computing hashs")
    hashtheplanet.compute_hashs()
    logger.debug("Retieving computed hashs")
    hashtheplanet.show_all_hashs()
