#!/usr/bin/env python3
"""
Helper tool to extract package versions from Gazebo collection YAML files.

Usage:
    python3 get_package_version.py --collection-files <collection_file1> [collection_file2 ...] --libs <package1> [package2 ...]

Example:
    python3 get_package_version.py --collection-files collection-harmonic.yaml collection-ionic.yaml --libs gz-sim gz-common
    # Output: gz-common5 gz-common6 gz-sim8 gz-sim9
"""

import sys
import yaml
import os
import argparse
from pathlib import Path


def load_collection_yaml(file_path):
    """Load and parse a collection YAML file."""
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: Collection file '{file_path}' not found.", file=sys.stderr)
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}", file=sys.stderr)
        return None


def get_package_version(collection_data, package_name):
    """Extract the version of a package from collection data."""
    if not collection_data:
        return None

    repositories = collection_data.get('repositories', {})

    # Look for exact match first
    if package_name in repositories:
        version = repositories[package_name].get('version')
        version = version.replace('sdf', 'sdformat', 1) if version.startswith('sdf') else version
        version = version.replace('ign-', 'ignition-', 1) if version.startswith('ign-') else version

        # If version is "main", search for the actual version in package-specific YAML files
        if version == "main":
            version = find_main_version_from_yaml_files(package_name)

        return version

    return None


def find_main_version_from_yaml_files(package_name):
    """Find the actual version number from package-specific YAML files when version is 'main'."""
    # Get the repository root directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Search for YAML files that start with package_name
    pattern = f"{package_name}*.yaml"
    matching_files = list(repo_root.glob(pattern))

    for yaml_file in matching_files:
        try:
            collection_data = load_collection_yaml(yaml_file)
            if collection_data and 'repositories' in collection_data:
                repositories = collection_data['repositories']
                if package_name in repositories:
                    file_version = repositories[package_name].get('version')
                    if file_version == "main":
                        # Extract version from filename (e.g., "gz-sim10" from "gz-sim10.yaml")
                        filename_without_ext = yaml_file.stem
                        return filename_without_ext
        except Exception:
            # Skip files that can't be parsed
            continue

    # If no matching file found, return "main" as fallback
    return "main"


def find_package_version_in_collections(collection_files, package_names):
    """Find package versions from all collection files for multiple packages."""
    results = []

    for collection_file in collection_files:
        collection_data = load_collection_yaml(collection_file)
        if collection_data:
            # Extract collection name from file path
            if isinstance(collection_file, Path):
                collection_name = collection_file.stem.replace("collection-", "")
            else:
                collection_name = Path(collection_file).stem.replace("collection-", "")

            # Get versions for all requested packages
            package_versions = []
            for package_name in package_names:
                version = get_package_version(collection_data, package_name)
                if version:
                    package_versions.append(version)

            if package_versions:
                results.append((collection_name, package_versions))

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Extract package versions from Gazebo collection YAML files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 get_package_version.py --collection-files collection-jetty.yaml --libs gz-common
  python3 get_package_version.py --collection-files collection-harmonic.yaml collection-ionic.yaml --libs gz-sim gz-common
  python3 get_package_version.py --collection-files collection-*.yaml --libs sdformat
        '''
    )

    parser.add_argument(
        '--collection-files',
        nargs='+',
        required=True,
        help='One or more collection YAML files to search'
    )

    parser.add_argument(
        '--libs',
        nargs='+',
        required=True,
        help='One or more package names to look up'
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Resolve file paths
    resolved_files = []
    for collection_file in args.collection_files:
        if not os.path.isabs(collection_file):
            collection_path = repo_root / collection_file
            if collection_path.exists():
                resolved_files.append(collection_path)
            else:
                resolved_files.append(collection_file)  # Keep original if not found in repo_root
        else:
            resolved_files.append(Path(collection_file))

    # Handle single file case differently from multiple files
    if len(resolved_files) == 1 and len(args.libs) == 1:
        # Single file, single package - original simple output format
        collection_file = str(resolved_files[0])
        package_name = args.libs[0]

        collection_data = load_collection_yaml(collection_file)
        if not collection_data:
            sys.exit(1)

        version = get_package_version(collection_data, package_name)
        if version:
            print(version)
        else:
            available_packages = list(collection_data.get('repositories', {}).keys())
            print(f"Package '{package_name}' not found in collection.", file=sys.stderr)
            print(f"Available packages: {', '.join(available_packages)}", file=sys.stderr)
            sys.exit(1)

    else:
        # Multiple files or packages - output all versions in single line
        all_versions = set()  # Use set to avoid duplicates

        results = find_package_version_in_collections(resolved_files, args.libs)

        if results:
            for collection_name, package_versions in results:
                all_versions.update(package_versions)

            # Sort versions alphabetically and print in single line
            sorted_versions = sorted(all_versions)
            print(" ".join(sorted_versions))
        else:
            print(f"None of the packages {args.libs} found in any of the specified collections.", file=sys.stderr)
            print(f"Searched collections: {[Path(f).name for f in resolved_files]}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
