"""
Unit tests for version utility functions.
"""
from hashtheplanet.utils.version_utils import (
    parse_version,
    sort_versions,
    collect_all_versions,
    compress_to_ranges,
    expand_ranges,
)


class TestParseVersion:
    """Unit tests for parse_version."""

    def test_simple_semver(self):
        """Standard semver components are compared numerically."""
        assert parse_version("1.2.3") < parse_version("1.2.4")
        assert parse_version("1.2.3") < parse_version("1.3.0")
        assert parse_version("1.9.0") < parse_version("1.10.0")

    def test_v_prefix(self):
        """A leading v/V is ignored."""
        assert parse_version("v1.2.3") == parse_version("1.2.3")
        assert parse_version("V1.0") == parse_version("1.0")

    def test_prerelease_ordering(self):
        """Pre-release labels are ordered alpha < beta < rc."""
        assert parse_version("1.0.0-alpha1") < parse_version("1.0.0-beta1")
        assert parse_version("1.0.0-beta1") < parse_version("1.0.0-rc1")
        assert parse_version("1.0.0-alpha1") < parse_version("1.0.0-alpha2")

    def test_prerelease_before_release(self):
        """alpha/beta/rc sort before the matching release version."""
        assert parse_version("1.0.0-alpha1") < parse_version("1.0.0")
        assert parse_version("1.0.0-rc1") < parse_version("1.0.0")

    def test_magento_patch_versions(self):
        """Magento -pN patch levels sort after pre-releases."""
        assert parse_version("2.4.8-p1") < parse_version("2.4.8-p2")
        assert parse_version("2.4.8-beta1") < parse_version("2.4.8-p1")

    def test_drupal_style(self):
        """Drupal style pre-releases sort before the release."""
        assert parse_version("10.0.0-alpha1") < parse_version("10.0.0")
        assert parse_version("10.0.0") < parse_version("10.0.1")

    def test_underscore_separator(self):
        """Joomla uses underscores: "2.5.0_RC1", "2.5.0_beta1"."""
        assert parse_version("2.5.0_beta1") < parse_version("2.5.0_RC1")

    def test_four_segment_versions(self):
        """Versions with four numeric segments are ordered correctly."""
        assert parse_version("1.5.1.1") < parse_version("1.5.1.2")
        assert parse_version("1.5.1.3") < parse_version("1.5.2")


class TestSortVersions:
    """Unit tests for sort_versions."""

    def test_basic_sort(self):
        """A plain list of versions is sorted ascending."""
        versions = ["1.2", "1.0", "1.1", "2.0"]
        assert sort_versions(versions) == ["1.0", "1.1", "1.2", "2.0"]

    def test_mixed_with_prerelease(self):
        """Pre-releases are interleaved before their release."""
        versions = ["1.0.0", "1.0.0-alpha1", "1.0.0-rc1", "1.0.0-beta1"]
        result = sort_versions(versions)
        assert result == ["1.0.0-alpha1", "1.0.0-beta1", "1.0.0-rc1", "1.0.0"]

    def test_wordpress_versions(self):
        """Patch numbers are compared numerically, not lexically."""
        versions = ["2.0.10", "2.0.2", "2.0.1", "2.0"]
        result = sort_versions(versions)
        assert result == ["2.0", "2.0.1", "2.0.2", "2.0.10"]

    def test_magento_alpha_versions(self):
        """Alpha numbers are compared numerically, not lexically."""
        versions = ["0.1.0-alpha100", "0.1.0-alpha89", "0.1.0-alpha90"]
        result = sort_versions(versions)
        assert result == ["0.1.0-alpha89", "0.1.0-alpha90", "0.1.0-alpha100"]

    def test_v_prefix_mixed(self):
        """Tags with and without a v prefix sort together."""
        versions = ["v4.3.5", "4.3.6", "v4.3.4"]
        result = sort_versions(versions)
        assert result == ["v4.3.4", "v4.3.5", "4.3.6"]


class TestCollectAllVersions:
    """Unit tests for collect_all_versions."""

    def test_collects_and_sorts(self):
        """All versions across files and hashes are collected and sorted."""
        tech_data = {
            "file1.css": {"hash1": ["1.2", "1.0"], "hash2": ["2.0"]},
            "file2.js": {"hash3": ["1.1", "1.0"]},
        }
        result = collect_all_versions(tech_data)
        assert result == ["1.0", "1.1", "1.2", "2.0"]

    def test_deduplicates(self):
        """A version present in several files appears only once."""
        tech_data = {
            "file1": {"h1": ["1.0", "1.1"]},
            "file2": {"h2": ["1.0", "1.2"]},
        }
        result = collect_all_versions(tech_data)
        assert result == ["1.0", "1.1", "1.2"]


class TestCompressToRanges:
    """Unit tests for compress_to_ranges."""

    def test_contiguous_versions(self):
        """A fully contiguous set collapses into a single range."""
        all_versions = ["1.0", "1.1", "1.2", "1.3", "1.4"]
        versions = ["1.0", "1.1", "1.2", "1.3", "1.4"]
        result = compress_to_ranges(versions, all_versions)
        assert result == ["1.0-1.4"]

    def test_gap_in_middle(self):
        """A gap splits the output into several entries."""
        all_versions = ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5"]
        versions = ["1.0", "1.1", "1.2", "1.5"]
        result = compress_to_ranges(versions, all_versions)
        assert result == ["1.0-1.2", "1.5"]

    def test_single_version(self):
        """A lone version is emitted as-is, without a range separator."""
        all_versions = ["1.0", "1.1", "1.2"]
        versions = ["1.1"]
        result = compress_to_ranges(versions, all_versions)
        assert result == ["1.1"]

    def test_all_isolated(self):
        """Non-adjacent versions are never merged."""
        all_versions = ["1.0", "1.1", "1.2", "1.3", "1.4"]
        versions = ["1.0", "1.2", "1.4"]
        result = compress_to_ranges(versions, all_versions)
        assert result == ["1.0", "1.2", "1.4"]

    def test_empty(self):
        """An empty input yields an empty output."""
        assert not compress_to_ranges([], ["1.0"])

    def test_multiple_ranges(self):
        """Contiguity follows the global index, not the version numbers."""
        all_versions = ["1.0", "1.1", "1.2", "2.0", "2.1", "3.0"]
        versions = ["1.0", "1.1", "1.2", "2.0", "2.1", "3.0"]
        result = compress_to_ranges(versions, all_versions)
        assert result == ["1.0-3.0"]

    def test_preserves_order(self):
        """Output is ordered by global index whatever the input order."""
        all_versions = ["1.0", "1.1", "1.2", "2.0", "2.1"]
        versions = ["2.0", "2.1", "1.0"]
        result = compress_to_ranges(versions, all_versions)
        assert result == ["1.0", "2.0-2.1"]


class TestExpandRanges:
    """Unit tests for expand_ranges."""

    def test_expand_single_range(self):
        """A range is expanded to every version it covers."""
        all_versions = ["1.0", "1.1", "1.2", "1.3"]
        result = expand_ranges(["1.0-1.3"], all_versions)
        assert result == ["1.0", "1.1", "1.2", "1.3"]

    def test_expand_single_version(self):
        """A lone version is returned unchanged."""
        all_versions = ["1.0", "1.1", "1.2"]
        result = expand_ranges(["1.1"], all_versions)
        assert result == ["1.1"]

    def test_expand_mixed(self):
        """Ranges and lone versions can be mixed in the same list."""
        all_versions = ["1.0", "1.1", "1.2", "2.0", "2.1"]
        result = expand_ranges(["1.0-1.2", "2.1"], all_versions)
        assert result == ["1.0", "1.1", "1.2", "2.1"]

    def test_version_with_hyphen_not_range(self):
        """A hyphenated version is not mistaken for a range."""
        all_versions = ["10.0.0-alpha1", "10.0.0-alpha2", "10.0.0"]
        result = expand_ranges(["10.0.0-alpha1"], all_versions)
        assert result == ["10.0.0-alpha1"]

    def test_range_of_hyphenated_versions(self):
        """A range whose bounds contain hyphens roundtrips correctly."""
        all_versions = ["10.0.0-alpha1", "10.0.0-alpha2", "10.0.0-beta1", "10.0.0"]
        # Range from alpha1 to alpha2
        compressed = compress_to_ranges(
            ["10.0.0-alpha1", "10.0.0-alpha2"], all_versions
        )
        result = expand_ranges(compressed, all_versions)
        assert result == ["10.0.0-alpha1", "10.0.0-alpha2"]

    def test_empty(self):
        """An empty input yields an empty output."""
        assert not expand_ranges([], ["1.0"])


class TestRoundtrip:
    """Compression followed by expansion must preserve the version set."""

    def test_roundtrip_simple(self):
        """A set with a gap survives a compress/expand roundtrip."""
        all_versions = ["1.0", "1.1", "1.2", "1.3", "2.0", "2.1"]
        versions = ["1.0", "1.1", "1.2", "2.1"]
        compressed = compress_to_ranges(versions, all_versions)
        expanded = expand_ranges(compressed, all_versions)
        assert sorted(expanded) == sorted(versions)

    def test_roundtrip_with_prerelease(self):
        """Pre-release versions survive a compress/expand roundtrip."""
        all_versions = sort_versions([
            "1.0.0-alpha1", "1.0.0-alpha2", "1.0.0-beta1",
            "1.0.0-rc1", "1.0.0", "1.0.1"
        ])
        versions = ["1.0.0-alpha1", "1.0.0-alpha2", "1.0.0-beta1"]
        compressed = compress_to_ranges(versions, all_versions)
        expanded = expand_ranges(compressed, all_versions)
        assert sorted(expanded) == sorted(versions)

    def test_roundtrip_all_versions(self):
        """The full version list collapses to one range and expands back."""
        all_versions = ["1.0", "1.1", "1.2", "1.3"]
        compressed = compress_to_ranges(all_versions, all_versions)
        assert compressed == ["1.0-1.3"]
        expanded = expand_ranges(compressed, all_versions)
        assert expanded == all_versions
