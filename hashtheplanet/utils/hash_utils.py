"""
Utility functions for computing file hashes.
"""
import hashlib
import subprocess

from loguru import logger


def hash_bytes(data: bytes) -> str:
    """
    Computes the SHA256 hash of the provided data and returns it.
    """
    return hashlib.sha256(data).hexdigest()


def calculate_git_hash(file_path: str) -> str:
    """
    Computes the Git SHA1 hash (blob hash) of the provided file using git hash-object.
    """
    try:
        result = subprocess.check_output(
            ['git', 'hash-object', file_path],
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        return result
    except (OSError, subprocess.CalledProcessError) as error:
        logger.error(f"Error with file {file_path} : {error}")
    return None
