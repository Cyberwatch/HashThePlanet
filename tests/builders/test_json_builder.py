"""
Unit tests for JsonBuilder class.
"""
import json
import os
import tempfile

from hashtheplanet.builders.json_builder import JsonBuilder


def test_add_entry():
    builder = JsonBuilder()
    builder.add_entry("WordPress", "wp-admin/css/about.css", "hash1", "4.5")
    builder.add_entry("WordPress", "wp-admin/css/about.css", "hash1", "4.5.1")
    builder.add_entry("WordPress", "wp-admin/css/about.css", "hash2", "4.6")

    data = builder.get_technology_data("WordPress")
    assert "wp-admin/css/about.css" in data
    assert data["wp-admin/css/about.css"]["hash1"] == ["4.5", "4.5.1"]
    assert data["wp-admin/css/about.css"]["hash2"] == ["4.6"]


def test_add_entries_bulk():
    builder = JsonBuilder()
    entries = [
        ("LICENSE", "hash1", "1.0"),
        ("LICENSE", "hash1", "1.1"),
        ("app.js", "hash2", "1.0"),
    ]
    builder.add_entries_bulk("drupal", entries)

    data = builder.get_technology_data("drupal")
    assert data["LICENSE"]["hash1"] == ["1.0", "1.1"]
    assert data["app.js"]["hash2"] == ["1.0"]


def test_get_technologies():
    builder = JsonBuilder()
    builder.add_entry("WordPress", "a.css", "h1", "1.0")
    builder.add_entry("Drupal", "b.css", "h2", "1.0")

    techs = builder.get_technologies()
    assert set(techs) == {"WordPress", "Drupal"}


def test_get_technology_data_empty():
    builder = JsonBuilder()
    data = builder.get_technology_data("nonexistent")
    assert data == {}


def test_merge():
    builder1 = JsonBuilder()
    builder1.add_entry("WordPress", "a.css", "h1", "1.0")

    builder2 = JsonBuilder()
    builder2.add_entry("WordPress", "a.css", "h1", "1.1")
    builder2.add_entry("WordPress", "b.css", "h2", "1.0")

    builder1.merge(builder2)

    data = builder1.get_technology_data("WordPress")
    assert data["a.css"]["h1"] == ["1.0", "1.1"]
    assert data["b.css"]["h2"] == ["1.0"]


def test_merge_different_technologies():
    builder1 = JsonBuilder()
    builder1.add_entry("WordPress", "a.css", "h1", "1.0")

    builder2 = JsonBuilder()
    builder2.add_entry("Drupal", "b.css", "h2", "1.0")

    builder1.merge(builder2)

    assert set(builder1.get_technologies()) == {"WordPress", "Drupal"}


def test_save_json_v2_format():
    """Verify that save_json writes the v2 format with _meta and ranges."""
    builder = JsonBuilder()
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash1", "4.5")
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash1", "4.5.1")
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash1", "4.6")
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash2", "5.0")

    with tempfile.TemporaryDirectory() as tmp_dir:
        builder.save_json(tmp_dir)

        with open(os.path.join(tmp_dir, "wordpress_hash_files.json")) as f:
            raw = json.load(f)

        # Check v2 structure
        assert "_meta" in raw
        assert raw["_meta"]["format_version"] == 2
        assert "sorted_versions" in raw["_meta"]
        assert "files" in raw

        # Versions should be sorted
        assert raw["_meta"]["sorted_versions"] == ["4.5", "4.5.1", "4.6", "5.0"]

        # Contiguous versions should be compressed to ranges
        file_data = raw["files"]["wp-admin/css/about.css"]
        assert file_data["hash1"] == ["4.5-4.6"]
        assert file_data["hash2"] == ["5.0"]


def test_save_and_load_roundtrip():
    """Test that save then load preserves data."""
    builder = JsonBuilder()
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash1", "4.5")
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash1", "4.5.1")
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash2", "4.6")
    builder.add_entry("drupal", "core/misc/ajax.js", "hash3", "8.0")

    with tempfile.TemporaryDirectory() as tmp_dir:
        builder.save_json(tmp_dir)

        assert os.path.exists(os.path.join(tmp_dir, "wordpress_hash_files.json"))
        assert os.path.exists(os.path.join(tmp_dir, "drupal_hash_files.json"))

        # Load back
        builder2 = JsonBuilder()
        builder2.load_json(tmp_dir)

        wp_data = builder2.get_technology_data("wordpress")
        assert sorted(wp_data["wp-admin/css/about.css"]["hash1"]) == ["4.5", "4.5.1"]
        assert wp_data["wp-admin/css/about.css"]["hash2"] == ["4.6"]

        drupal_data = builder2.get_technology_data("drupal")
        assert drupal_data["core/misc/ajax.js"]["hash3"] == ["8.0"]


def test_load_legacy_format():
    """Test that legacy format (without _meta) still loads correctly."""
    legacy_data = {
        "wp-admin/css/about.css": {
            "hash1": ["4.5", "4.5.1"],
            "hash2": ["4.6"],
        }
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        filepath = os.path.join(tmp_dir, "wordpress_hash_files.json")
        with open(filepath, "w") as f:
            json.dump(legacy_data, f)

        builder = JsonBuilder()
        builder.load_json(tmp_dir)

        data = builder.get_technology_data("wordpress")
        assert data["wp-admin/css/about.css"]["hash1"] == ["4.5", "4.5.1"]
        assert data["wp-admin/css/about.css"]["hash2"] == ["4.6"]


def test_load_json_nonexistent_dir():
    builder = JsonBuilder()
    builder.load_json("/nonexistent/path")
    assert builder.get_technologies() == []


def test_incremental_update():
    """Test that loading existing data and adding new data produces merged results."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # First run
        builder1 = JsonBuilder()
        builder1.add_entry("wordpress", "a.css", "h1", "1.0")
        builder1.save_json(tmp_dir)

        # Second run (incremental)
        builder2 = JsonBuilder()
        builder2.load_json(tmp_dir)
        builder2.add_entry("wordpress", "a.css", "h1", "1.1")
        builder2.add_entry("wordpress", "b.css", "h2", "1.0")
        builder2.save_json(tmp_dir)

        # Verify merged results
        builder3 = JsonBuilder()
        builder3.load_json(tmp_dir)

        data = builder3.get_technology_data("wordpress")
        assert sorted(data["a.css"]["h1"]) == ["1.0", "1.1"]
        assert data["b.css"]["h2"] == ["1.0"]


def test_discrimination_score():
    """Score is the hash count divided by the largest version group."""
    builder = JsonBuilder()
    # High discrimination: 3 hashes, max group = 2
    builder.add_entry("wp", "good.css", "h1", "1.0")
    builder.add_entry("wp", "good.css", "h1", "1.1")
    builder.add_entry("wp", "good.css", "h2", "2.0")
    builder.add_entry("wp", "good.css", "h3", "3.0")

    # Low discrimination: 1 hash, 100 versions
    for i in range(100):
        builder.add_entry("wp", "bad.css", "h_same", f"{i}.0")

    scores = builder.compute_discrimination_scores("wp")
    assert scores["good.css"] == 3 / 2  # 1.5
    assert scores["bad.css"] == 1 / 100  # 0.01


def test_filter_low_discrimination():
    """Files scoring below the threshold are dropped."""
    builder = JsonBuilder()

    # Discriminating file: 3 hashes, max group = 1
    builder.add_entry("wp", "good.css", "h1", "1.0")
    builder.add_entry("wp", "good.css", "h2", "2.0")
    builder.add_entry("wp", "good.css", "h3", "3.0")

    # Non-discriminating file: 1 hash, 50 versions
    for i in range(50):
        builder.add_entry("wp", "bad.css", "h_same", f"{i}.0")

    builder.filter_low_discrimination_files(threshold=0.05)

    data = builder.get_technology_data("wp")
    assert "good.css" in data
    assert "bad.css" not in data


def test_filter_preserves_good_files():
    """Files scoring above the threshold are kept."""
    builder = JsonBuilder()

    # All files are discriminating
    builder.add_entry("wp", "a.css", "h1", "1.0")
    builder.add_entry("wp", "a.css", "h2", "2.0")
    builder.add_entry("wp", "b.css", "h3", "1.0")
    builder.add_entry("wp", "b.css", "h4", "2.0")

    builder.filter_low_discrimination_files(threshold=0.05)

    data = builder.get_technology_data("wp")
    assert "a.css" in data
    assert "b.css" in data


def test_save_deduplicates_versions():
    """Test that duplicate versions are deduplicated on save."""
    builder = JsonBuilder()
    builder.add_entry("wp", "a.css", "h1", "1.0")
    builder.add_entry("wp", "a.css", "h1", "1.0")  # duplicate
    builder.add_entry("wp", "a.css", "h1", "1.1")

    with tempfile.TemporaryDirectory() as tmp_dir:
        builder.save_json(tmp_dir)

        builder2 = JsonBuilder()
        builder2.load_json(tmp_dir)

        data = builder2.get_technology_data("wp")
        assert sorted(data["a.css"]["h1"]) == ["1.0", "1.1"]
