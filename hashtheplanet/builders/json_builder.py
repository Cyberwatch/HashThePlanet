"""
This module builds hash dictionaries in memory and exports them as JSON files.
"""
import json
import os
from collections import defaultdict
from typing import Dict, List

from loguru import logger

from hashtheplanet.utils.version_utils import (
    collect_all_versions,
    compress_to_ranges,
    expand_ranges,
)

FORMAT_VERSION = 2


class JsonBuilder:
    """
    Builds the hash data structure in memory:
    {file_path: {hash: [versions]}} per technology.
    """
    def __init__(self):
        # {technology: {file_path: {hash: [versions]}}}
        self._data: Dict[str, Dict[str, Dict[str, List[str]]]] = {}

    def add_entry(self, technology: str, file_path: str, hash_value: str, version: str):
        """
        Add a single hash entry for a technology/file/version.
        """
        if technology not in self._data:
            self._data[technology] = defaultdict(lambda: defaultdict(list))

        self._data[technology][file_path][hash_value].append(version)

    def add_entries_bulk(self, technology: str, entries: List[tuple]):
        """
        Add multiple (file_path, hash_value, version) entries for a technology.
        More efficient than calling add_entry in a loop.
        """
        if technology not in self._data:
            self._data[technology] = defaultdict(lambda: defaultdict(list))

        tech_data = self._data[technology]
        for file_path, hash_value, version in entries:
            tech_data[file_path][hash_value].append(version)

    def get_technologies(self) -> List[str]:
        """Returns the list of technologies that have been added."""
        return list(self._data.keys())

    def get_technology_data(self, technology: str) -> Dict[str, Dict[str, List[str]]]:
        """Returns the hash data for a specific technology."""
        return dict(self._data.get(technology, {}))

    def merge(self, other: "JsonBuilder"):
        """Merge another JsonBuilder's data into this one."""
        for technology in other.get_technologies():
            if technology not in self._data:
                self._data[technology] = defaultdict(lambda: defaultdict(list))
            for file_path, hash_dict in other.get_technology_data(technology).items():
                for hash_value, versions in hash_dict.items():
                    self._data[technology][file_path][hash_value].extend(versions)

    def compute_discrimination_scores(self, technology: str) -> Dict[str, float]:
        """
        For each file_path in the technology, compute a discrimination score:
          score = num_distinct_hashes / max(len(version_list) for each hash)

        Higher score = more discriminating file (many hashes, small version groups).
        Lower score = less useful file (few hashes, large version groups).
        """
        tech_data = self._data.get(technology, {})
        scores = {}
        for file_path, hash_dict in tech_data.items():
            num_hashes = len(hash_dict)
            max_group_size = max((len(v) for v in hash_dict.values()), default=0)
            scores[file_path] = num_hashes / max_group_size if max_group_size > 0 else 0
        return scores

    def filter_low_discrimination_files(self, threshold: float = 0.05):
        """
        Remove files with discrimination score below threshold, for all technologies.
        """
        for technology in list(self._data.keys()):
            scores = self.compute_discrimination_scores(technology)
            to_remove = [fp for fp, score in scores.items() if score < threshold]
            if to_remove:
                for fp in to_remove:
                    del self._data[technology][fp]
                logger.info(
                    f"{technology}: removed {len(to_remove)} low-discrimination files "
                    f"(threshold={threshold}), {len(self._data[technology])} files remaining"
                )

    def save_json(self, output_dir: str):
        """
        Save one JSON file per technology in the output directory.
        Format v2: {_meta: {format_version, sorted_versions}, files: {file_path: {hash: [ranges]}}}
        """
        os.makedirs(output_dir, exist_ok=True)

        for technology, tech_data in self._data.items():
            output_path = os.path.join(output_dir, f"{technology.lower()}_hash_files.json")

            sorted_versions = collect_all_versions(tech_data)

            files_data = {}
            for fp, hashes in tech_data.items():
                files_data[fp] = {}
                for hash_value, versions in hashes.items():
                    deduped = list(dict.fromkeys(versions))
                    files_data[fp][hash_value] = compress_to_ranges(deduped, sorted_versions)

            output = {
                "_meta": {
                    "format_version": FORMAT_VERSION,
                    "sorted_versions": sorted_versions,
                },
                "files": files_data,
            }

            with open(output_path, "w", encoding="utf-8") as file_fp:
                # Compact separators: these files are consumed by tools, not read by hand,
                # and the whitespace of indent=4 is ~40% of the total size.
                json.dump(output, file_fp, separators=(",", ":"))

    def load_json(self, output_dir: str):
        """
        Load existing JSON files from the output directory to support incremental updates.
        Supports both v2 format (with ranges) and legacy format.
        """
        if not os.path.isdir(output_dir):
            return

        for filename in os.listdir(output_dir):
            if not filename.endswith("_hash_files.json"):
                continue

            technology = filename.replace("_hash_files.json", "")
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "r", encoding="utf-8") as file_fp:
                data = json.load(file_fp)

            if technology not in self._data:
                self._data[technology] = defaultdict(lambda: defaultdict(list))

            if "_meta" in data and "files" in data:
                # v2 format: expand ranges back to full version lists
                sorted_versions = data["_meta"]["sorted_versions"]
                for file_path, hash_dict in data["files"].items():
                    for hash_value, range_list in hash_dict.items():
                        versions = expand_ranges(range_list, sorted_versions)
                        self._data[technology][file_path][hash_value].extend(versions)
            else:
                # Legacy format: direct version lists
                for file_path, hash_dict in data.items():
                    for hash_value, versions in hash_dict.items():
                        self._data[technology][file_path][hash_value].extend(versions)
