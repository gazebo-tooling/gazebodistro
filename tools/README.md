# Gazebo Collection Tools

This directory contains helper tools for working with Gazebo collection YAML files.

## get_package_version.py

A Python script that extracts package versions from Gazebo collection YAML files.

### Requirements

- Python 3.x
- PyYAML library

Install PyYAML if not already available:
```bash
pip install PyYAML
```

### Usage

#### Direct Python usage:

```bash
# Single collection file with single package
python3 get_package_version.py --collection-files <collection_file> --libs <package_name>

# Multiple collection files with multiple packages
python3 get_package_version.py --collection-files <collection_file1> <collection_file2> ... --libs <package1> <package2> ...
```

#### Using the shell wrapper:

```bash
./get_package_version.sh <collection_file> <package_name>
```

### Examples

```bash
# Get gz-common version from jetty collection
python3 get_package_version.py --collection-files collection-jetty.yaml --libs gz-common
# Output: gz-common6

# Get gz-sim versions from multiple collections (unique versions, alphabetically sorted)
python3 get_package_version.py --collection-files collection-harmonic.yaml collection-ionic.yaml collection-jetty.yaml --libs gz-sim
# Output: gz-sim8 gz-sim9 main

# Get multiple package versions from multiple collections
python3 get_package_version.py --collection-files collection-harmonic.yaml collection-ionic.yaml --libs gz-sim gz-common
# Output: gz-common5 gz-common6 gz-sim8 gz-sim9

# Get versions for multiple packages across several collections
python3 get_package_version.py --collection-files collection-garden.yaml collection-harmonic.yaml collection-ionic.yaml --libs gz-common sdformat gz-sim
# Output: gz-common5 gz-common6 gz-sim7 gz-sim8 gz-sim9 sdformat13 sdformat14 sdformat15
```

### Command Line Arguments

The script now uses argparse and requires explicit arguments:

- `--collection-files`: One or more collection YAML files to search (required)
- `--libs`: One or more package names to look up (required)

### Features

- **Exact matching**: Looks for exact package name matches first
- **Main version resolution**: When a package version is "main", automatically finds the corresponding versioned YAML file (e.g., gz-sim10.yaml) and returns the filename as the version
- **Format conversions**:
  - Converts `sdf*` versions to `sdformat*` (e.g., `sdf15` → `sdformat15`)
  - Converts `ign-*` versions to `ignition-*` (e.g., `ign-gazebo6` → `ignition-gazebo6`)
- **Alphabetical sorting**: All output versions are sorted alphabetically
- **Deduplication**: Duplicate versions across collections are automatically removed
- **Flexible paths**: Accepts both absolute and relative paths to collection files
- **Error handling**: Provides helpful error messages for missing files or packages
- **Flexible paths**: Accepts both absolute and relative paths to collection files

### Error Cases

If a package is not found:
```bash
python3 get_package_version.py collection-jetty.yaml nonexistent-package
# Error: Package 'nonexistent-package' not found in collection.
# Available packages: gz-cmake, gz-common, gz-fuel-tools, gz-sim, ...
```

If multiple partial matches are found:
```bash
python3 get_package_version.py collection-jetty.yaml gz
# Multiple packages found matching 'gz':
#   - gz-cmake: gz-cmake4
#   - gz-common: gz-common6
#   - gz-fuel-tools: gz-fuel-tools10
#   ...
```
