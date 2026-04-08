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

Requires Python >= 3.10 and `git` installed on the system.

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

### Look up a hash

```bash
# Search by hash value
hashtheplanet --hash abc123def --json-dir dist/

# Compute the git hash of a local file and search for it
hashtheplanet --file path/to/style.css --json-dir dist/
```

### All options

```
usage: hashtheplanet [-h] [-i INPUT] [--json-dir JSON_DIR]
                     [--cache-dir CACHE_DIR] [--workers WORKERS]
                     [--color] [-v {DEBUG,INFO,WARNING}]
                     [--hash HASH] [-f FILE] [--version]

options:
  -i, --input          Input file (json) with resources targets
  --json-dir           Output directory for JSON hash files (default: dist)
  --cache-dir          Directory to cache bare git repositories
  --workers            Number of parallel workers (default: 4)
  --color              Colorize output
  -v, --verbose        Set verbosity level
  --hash               Search for a file hash in the generated JSON files
  -f, --file           Compute git hash of a file and search for it
  --version            Show program's version number and exit
```

## Output format

Each JSON file follows the format expected by Wapiti:

```json
{
    "wp-admin/css/about.min.css": {
        "7dca9b7fd6334608de4d196b761898faec68a22e": ["4.5", "4.5.1", "4.5.10"],
        "bd003058c2c8e8fa9537d4079be424285170665f": ["4.5.24", "4.5.25"]
    },
    "wp-includes/js/jquery/jquery.min.js": {
        "a1b2c3d4...": ["5.0", "5.0.1"]
    }
}
```

Structure: `{ file_path: { git_blob_sha1: [versions] } }`

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
