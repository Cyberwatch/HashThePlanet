"""
Utility functions for sorting versions and compressing/expanding version ranges.
"""
import re
from typing import Dict, List


def parse_version(version_str: str) -> tuple:
    """
    Parse a version string into a comparable tuple for sorting.
    Handles: "1.2.3", "v4.9.26", "7.x-1.0", "10.0.0-alpha1", "2.5.0_RC1", etc.

    Strategy: strip leading 'v'/'V', split on [.\\-_], each segment becomes
    (0, int_value) for numeric or (1, str_value) for alpha.
    Pre-release labels sort before release: alpha < beta < rc < (release).
    """
    version_str = re.sub(r'^[vV]', '', version_str)
    segments = re.split(r'[.\-_]', version_str)

    # We build a list of (type, ...) tuples.
    # Numeric: (1, n)  -- sorts after pre-release (0, ...)
    # Pre-release: (0, order, label, num) -- sorts before numeric and release sentinel
    # At the end, we insert a release sentinel (0, MAX) after each numeric-to-end boundary
    # so that "1.0.0" > "1.0.0-alpha1".
    #
    # Approach: split into numeric prefix + optional pre-release suffix.
    # Numeric-only versions get a high-sorting tail sentinel.
    numeric_parts = []
    prerelease_parts = []
    in_prerelease = False

    for seg in segments:
        if not seg:
            continue
        if seg.isdigit() and not in_prerelease:
            numeric_parts.append(int(seg))
        else:
            in_prerelease = True
            match = re.match(r'^([a-zA-Z]+)(\d+)$', seg)
            if match:
                label = match.group(1).lower()
                num = int(match.group(2))
                prerelease_parts.append((_prerelease_order(label), label, num))
            elif seg.isdigit():
                prerelease_parts.append((99, '', int(seg)))
            else:
                label = seg.lower()
                prerelease_parts.append((_prerelease_order(label), label, 0))

    # Build final key: numeric parts as a tuple, then pre-release indicator.
    # No pre-release: (numeric_tuple, (MAX,)) -- sorts after any pre-release
    # With pre-release: (numeric_tuple, prerelease_tuple)
    num_key = tuple(numeric_parts)
    if prerelease_parts:
        pre_key = tuple(prerelease_parts)
    else:
        # Release: sorts after all pre-release labels (max order = 99)
        pre_key = ((999,),)

    return (num_key, pre_key)


def _prerelease_order(label: str) -> int:
    """
    Returns an ordering value for pre-release labels.
    Lower values sort first. Release (no label) sorts last.
    """
    order = {
        'alpha': 0,
        'a': 0,
        'beta': 1,
        'b': 1,
        'rc': 2,
        'dev': -1,
        'p': 3,       # patch (Magento uses -p1, -p2)
    }
    return order.get(label, 2)


def sort_versions(versions) -> List[str]:
    """Sort a collection of version strings using parse_version as key."""
    return sorted(versions, key=parse_version)


def collect_all_versions(tech_data: Dict[str, Dict[str, List[str]]]) -> List[str]:
    """
    Collect and return the globally sorted list of all unique versions
    present across all files/hashes for a technology.
    """
    all_versions = set()
    for hash_dict in tech_data.values():
        for versions in hash_dict.values():
            all_versions.update(versions)
    return sort_versions(all_versions)


def compress_to_ranges(versions: List[str], sorted_all_versions: List[str]) -> List[str]:
    """
    Given a subset of versions and the globally sorted version list,
    return a list of range strings where contiguous versions are compressed.

    Contiguous means consecutive in sorted_all_versions.
    Example: ["1.0", "1.1", "1.2", "1.5"] with global ["1.0","1.1","1.2","1.3","1.4","1.5"]
             returns: ["1.0-1.2", "1.5"]
    """
    if not versions:
        return []

    version_to_index = {v: i for i, v in enumerate(sorted_all_versions)}
    indices = sorted(version_to_index[v] for v in versions if v in version_to_index)

    if not indices:
        return list(versions)

    ranges = []
    start = indices[0]
    end = indices[0]

    for i in range(1, len(indices)):
        if indices[i] == end + 1:
            end = indices[i]
        else:
            ranges.append(_format_range(start, end, sorted_all_versions))
            start = indices[i]
            end = indices[i]

    ranges.append(_format_range(start, end, sorted_all_versions))
    return ranges


def _format_range(start_idx: int, end_idx: int, sorted_all_versions: List[str]) -> str:
    """Format a contiguous range as 'start-end' or just 'version' if single."""
    if start_idx == end_idx:
        return sorted_all_versions[start_idx]
    return f"{sorted_all_versions[start_idx]}-{sorted_all_versions[end_idx]}"


def expand_ranges(range_list: List[str], sorted_all_versions: List[str]) -> List[str]:
    """
    Inverse of compress_to_ranges. Expands "1.0-1.3" back to individual versions
    using the global sorted version list.
    """
    if not range_list:
        return []

    version_to_index = {v: i for i, v in enumerate(sorted_all_versions)}
    result = []

    for item in range_list:
        if '-' in item:
            # Could be a range "1.0-1.3" or a version with hyphen "10.0.0-alpha1"
            # Try to split as range first: find a split point where both parts are known versions
            expanded = _try_expand_range(item, version_to_index, sorted_all_versions)
            if expanded is not None:
                result.extend(expanded)
            else:
                # It's a single version containing a hyphen
                result.append(item)
        else:
            result.append(item)

    return result


def _try_expand_range(item: str, version_to_index: dict,
                      sorted_all_versions: List[str]) -> list:
    """
    Try to interpret item as a "start-end" range.
    We try all possible split positions of '-' and pick the one where
    both parts are known versions and start <= end.
    Returns expanded list or None if not a range.
    """
    # Find all positions of '-' in the string
    positions = [i for i, c in enumerate(item) if c == '-']

    for pos in positions:
        start_str = item[:pos]
        end_str = item[pos + 1:]
        if start_str in version_to_index and end_str in version_to_index:
            start_idx = version_to_index[start_str]
            end_idx = version_to_index[end_str]
            if start_idx <= end_idx:
                return sorted_all_versions[start_idx:end_idx + 1]

    return None
