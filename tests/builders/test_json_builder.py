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


def test_save_and_load_json():
    builder = JsonBuilder()
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash1", "4.5")
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash1", "4.5.1")
    builder.add_entry("wordpress", "wp-admin/css/about.css", "hash2", "4.6")
    builder.add_entry("drupal", "core/misc/ajax.js", "hash3", "8.0")

    with tempfile.TemporaryDirectory() as tmp_dir:
        builder.save_json(tmp_dir)

        # Verify files were created
        assert os.path.exists(os.path.join(tmp_dir, "wordpress_hash_files.json"))
        assert os.path.exists(os.path.join(tmp_dir, "drupal_hash_files.json"))

        # Verify content format matches Wapiti expectations
        with open(os.path.join(tmp_dir, "wordpress_hash_files.json")) as f:
            wp_data = json.load(f)

        assert wp_data["wp-admin/css/about.css"]["hash1"] == ["4.5", "4.5.1"]
        assert wp_data["wp-admin/css/about.css"]["hash2"] == ["4.6"]

        # Test loading back
        builder2 = JsonBuilder()
        builder2.load_json(tmp_dir)

        data = builder2.get_technology_data("wordpress")
        assert data["wp-admin/css/about.css"]["hash1"] == ["4.5", "4.5.1"]


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
        with open(os.path.join(tmp_dir, "wordpress_hash_files.json")) as f:
            data = json.load(f)

        assert data["a.css"]["h1"] == ["1.0", "1.1"]
        assert data["b.css"]["h2"] == ["1.0"]
