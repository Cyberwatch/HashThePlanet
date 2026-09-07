# HashThePlanet

HashThePlanet generates fingerprint hash files for common web technologies (CMS, JavaScript libraries).
It computes the native Git blob SHA1 hash of every static file (JS, CSS, TXT, HTML...) across all tagged versions of a repository, and outputs JSON files that can be used by tools like [Wapiti](https://github.com/wapiti-scanner/wapiti) to identify the version of a deployed web application.

## Supported technologies

**Git repositories:**
- WordPress
- Drupal
- Joomla
- Magento 2
- PrestaShop
- SPIP
- Silex

**npm packages:**
- jQuery
- Underscore

Technologies are configured in [`src/tech_list.json`](src/tech_list.json).

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
make install
```

Requires Python >= 3.14 and `git` installed on the system.

## Usage

### Generate hash files

```bash
hashtheplanet --input src/tech_list.json --json-dir dist/
```

This produces one JSON file per technology in `dist/` (e.g. `wordpress_hash_files.json`, `drupal_hash_files.json`).

### Faster with caching and parallelism

```bash
hashtheplanet --input src/tech_list.json --json-dir dist/ --cache-dir .git-cache --workers 4
```

- `--cache-dir` stores bare git repositories locally. On subsequent runs, only new tags are fetched instead of cloning the entire repository.
- `--workers` sets the number of parallel threads (default: 4).
- Existing JSON files in `--json-dir` are loaded and merged with new results, enabling incremental updates.

### Pruning non-discriminating files

Most static files never change across a long run of releases, so their hash cannot narrow down a
version. Each file is scored:

```
score = number of distinct hashes / size of the largest version group
```

A file with many hashes and small version groups is discriminating (high score); a file with a
single hash shared by 200 versions is not (score 0.005). Files scoring below
`--discrimination-threshold` are dropped (default: `0.05`, use `0` to disable).

On the current technology set this removes 25-54% of the files and 23% of the total output size,
while only two versions across all technologies (`drupal 8.1.0-rc1` and `wordpress 5.4.1`) lose the
ability to be pinpointed exactly. No version loses coverage entirely. Raise the threshold for a
smaller database, lower it to keep more candidate files to probe.

### Look up a hash

```bash
# Search by hash value
hashtheplanet --hash abc123def --json-dir dist/

# Compute the git hash of a local file and search for it
hashtheplanet --file path/to/style.css --json-dir dist/
```

### All options

```
usage: hashtheplanet [-h] [-i INPUT] [--json-dir JSON_DIR] [--cache-dir CACHE_DIR]
                     [--workers WORKERS] [--discrimination-threshold DISCRIMINATION_THRESHOLD]
                     [--color] [-v {DEBUG,INFO,WARNING}] [--hash HASH] [-f FILE] [--version]

options:
  -i, --input                    Input file (json) with resources targets
  --json-dir                     Output directory for JSON hash files (default: dist)
  --cache-dir                    Directory to cache bare git repositories
  --workers                      Number of parallel workers (default: 4)
  --discrimination-threshold     Remove files with a discrimination score below this
                                 threshold (0 to disable, default: 0.05)
  --color                        Colorize output
  -v, --verbose                  Set verbosity level
  --hash                         Search for a file hash in the generated JSON files
  -f, --file                     Compute git hash of a file and search for it
  --version                      Show program's version number and exit
```

## Output format

Each JSON file uses format version 2, which stores version **ranges** instead of exhaustive
version lists:

```json
{
    "_meta": {
        "format_version": 2,
        "sorted_versions": ["1.5", "1.5.1", "...", "4.5.23", "4.5.24", "...", "4.5.33", "..."]
    },
    "files": {
        "wp-admin/css/about.min.css": {
            "7dca9b7fd6334608de4d196b761898faec68a22e": ["4.5-4.5.23"],
            "bd003058c2c8e8fa9537d4079be424285170665f": ["4.5.24-4.5.33"]
        },
        "wp-includes/js/jquery/jquery.min.js": {
            "a1b2c3d4...": ["5.0", "5.0.1"]
        }
    }
}
```

- `_meta.sorted_versions` is the ordered list of every version known for this technology. It is the
  reference for range boundaries.
- `files` maps `file_path -> { git_blob_sha1: [ranges] }`. Each entry is either a single version
  (`"5.0"`) or an inclusive range (`"4.5-4.5.23"`) covering every consecutive entry of
  `sorted_versions` between the two bounds.

A range is only emitted for versions that are *adjacent in `sorted_versions`*, so expanding a range
never invents a version that was not observed.

Version ordering handles the tagging schemes used by the supported projects: `v` prefixes
(`v4.3.4`), pre-releases (`10.0.0-alpha1` < `10.0.0-beta1` < `10.0.0-rc1` < `10.0.0`), Magento patch
levels (`2.4.8-p1`), Joomla underscores (`2.5.0_RC1`) and four-segment versions (`1.5.1.1`).
Numeric segments are compared as integers, so `2.0.10` sorts after `2.0.2`.

Compared to a flat `{ file_path: { git_blob_sha1: [versions] } }` mapping, this cuts the total
output from 190 MB to 40 MB (-79% uncompressed, -20% once gzipped) at the cost of an expansion step
when loading.

### Reading the files

Consumers must expand the ranges before matching. `hashtheplanet.utils.version_utils` exposes the
helpers used internally:

```python
from hashtheplanet.utils.version_utils import expand_ranges

sorted_versions = data["_meta"]["sorted_versions"]
versions = expand_ranges(["4.5-4.5.23"], sorted_versions)
```

Since version ranges appeared in format 2, always check `_meta.format_version` before parsing. A
file without a `_meta` key is a legacy release using the flat mapping above; `load_json` still reads
both, which keeps incremental updates working across the format change.

## Development

```bash
# Run tests
make test

# Run linter
make lint

# Clean generated files
make clean
```

## CI/CD

The [release workflow](.github/workflows/db-release.yml) runs weekly and:
1. Restores cached bare git repositories
2. Downloads previous JSON files from the latest release
3. Generates updated hash files incrementally
4. Publishes them as GitHub release assets

## License

GPL-2.0
