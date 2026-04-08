"""
This module builds hash dictionaries in memory and exports them as JSON files.
"""
import json
import os
from collections import defaultdict
from typing import Dict, List


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
        for technology, tech_data in other._data.items():
            if technology not in self._data:
                self._data[technology] = defaultdict(lambda: defaultdict(list))
            for file_path, hash_dict in tech_data.items():
                for hash_value, versions in hash_dict.items():
                    self._data[technology][file_path][hash_value].extend(versions)

    def save_json(self, output_dir: str):
        """
        Save one JSON file per technology in the output directory.
        Format: {file_path: {hash: [versions]}}
        """
        os.makedirs(output_dir, exist_ok=True)

        for technology, tech_data in self._data.items():
            output_path = os.path.join(output_dir, f"{technology.lower()}_hash_files.json")
            serializable = {
                fp: dict(hashes) for fp, hashes in tech_data.items()
            }
            with open(output_path, "w", encoding="utf-8") as file_fp:
                json.dump(serializable, file_fp, indent=4)

    def load_json(self, output_dir: str):
        """
        Load existing JSON files from the output directory to support incremental updates.
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

            for file_path, hash_dict in data.items():
                for hash_value, versions in hash_dict.items():
                    self._data[technology][file_path][hash_value].extend(versions)
