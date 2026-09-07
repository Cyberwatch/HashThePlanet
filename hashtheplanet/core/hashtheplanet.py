"""
The main module for HashThePlanet
"""
# standard imports
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from json import JSONDecodeError
import os
import sys

# third party imports
from loguru import logger

# project imports
from hashtheplanet.builders.json_builder import JsonBuilder
from hashtheplanet.config.config import Config
from hashtheplanet.utils.hash_utils import calculate_git_hash

HASHTHEPLANET_VERSION = "HashThePlanet 1.0.0"


class HashThePlanet():
    """
    The HashThePlanet class
    """
    def __init__(self, input_file: str, json_dir: str = "dist",
                 cache_dir: str = None, max_workers: int = 4,
                 discrimination_threshold: float = 0.05):
        """
        Initialisation requires an input filename (json) and an output directory.
        """
        self._input_file = input_file
        self._json_dir = json_dir
        self._cache_dir = cache_dir
        self._max_workers = max_workers
        self._discrimination_threshold = discrimination_threshold
        self._config = Config()

    def _compute_single_target(self, resource_name: str, target: str, builder: JsonBuilder):
        """
        Compute hashes for a single target (used for parallel execution).
        """
        from importlib import import_module

        resource_path = f"{resource_name}_resource"
        resource_class_name = f"{resource_name.title()}Resource"

        try:
            module = import_module("hashtheplanet.resources." + resource_path)
        except ImportError:
            logger.error(f"[!] Could not find module {resource_path}")
            return

        resource_instance = getattr(module, resource_class_name)()

        kwargs = {"builder": builder}
        if resource_name == "git" and self._cache_dir:
            kwargs["cache_dir"] = self._cache_dir

        resource_instance.compute_hashes(target, **kwargs)

    def compute_hashs(self):
        """
        Computes all hashes and outputs JSON files.
        """
        try:
            self._config.parse(self._input_file)
        except (OSError, JSONDecodeError) as error:
            logger.error(f"Error: {error}")
            sys.exit(1)

        builder = JsonBuilder()

        # Load existing JSON files for incremental updates
        if os.path.isdir(self._json_dir):
            builder.load_json(self._json_dir)
            logger.info(f"Loaded existing data from {self._json_dir}")

        futures = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            for resource_name in self._config.get_used_resources():
                targets = self._config.get_targets(resource_name)
                for target in targets:
                    target_builder = JsonBuilder()
                    future = executor.submit(
                        self._compute_single_target,
                        resource_name, target, target_builder
                    )
                    futures.append((future, target_builder, target))

            for future, target_builder, target in futures:
                try:
                    future.result()
                    builder.merge(target_builder)
                    logger.info(f"Merged results for {target}")
                except Exception as error:
                    logger.error(f"Error processing {target}: {error}")

        if self._discrimination_threshold > 0:
            builder.filter_low_discrimination_files(self._discrimination_threshold)

        builder.save_json(self._json_dir)
        logger.info(f"JSON files saved to {self._json_dir}")
        logger.info("Computing done")

    def find_hash(self, file_hash: str):
        """
        Search for a hash in the generated JSON files.
        """
        builder = JsonBuilder()
        builder.load_json(self._json_dir)

        for technology in builder.get_technologies():
            data = builder.get_technology_data(technology)
            for file_path, hash_dict in data.items():
                if file_hash in hash_dict:
                    versions = hash_dict[file_hash]
                    logger.success(f"Found: technology={technology}, file={file_path}, versions={versions}")
                    return (technology, versions)

        logger.info(f"Hash {file_hash} not found")
        return (None, None)


def main():
    """
    The main function, which is the entry point of the program.
    It stores arguments provided by the user and launches hash computing.
    """
    logger.remove()
    parser = argparse.ArgumentParser(description="HashThePlanet-1.0.0")

    parser.add_argument(
        "-i", "--input",
        default="src/tech_list.json",
        help="Input file (json) with resources targets"
    )

    parser.add_argument(
        "--json-dir",
        default="dist",
        help="Output directory for JSON hash files"
    )

    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Directory to cache bare git repositories for incremental updates"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for processing repositories"
    )

    parser.add_argument(
        "--discrimination-threshold",
        type=float,
        default=0.05,
        help="Remove files with discrimination score below this threshold (0 to disable, default: 0.05)"
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
        help="Search for a file hash in the generated JSON files"
    )

    parser.add_argument(
        "-f", "--file",
        default=None,
        help="Compute git hash of a file and search for it"
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
    hashtheplanet = HashThePlanet(
        args.input,
        json_dir=args.json_dir,
        cache_dir=args.cache_dir,
        max_workers=args.workers,
        discrimination_threshold=args.discrimination_threshold,
    )

    if args.file is not None:
        readable_hash = calculate_git_hash(args.file)
        if readable_hash is None:
            return
        hashtheplanet.find_hash(readable_hash)
        return
    if args.hash is not None:
        hashtheplanet.find_hash(args.hash)
        return

    logger.debug("Start computing hashs")
    hashtheplanet.compute_hashs()
