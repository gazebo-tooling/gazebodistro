import yaml
import argparse
from pathlib import Path
import difflib
import sys


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""\
Script to update version/branch of a library used in all downstream libraries.
For example, this can be used to change the version of gz-cmake from 'main'
to 'gz-cmake4' in all downstream libraries that use gz-cmake.
    """)
    parser.add_argument('library', help="Versionless name of library. Example 'gz-cmake'")
    parser.add_argument('from_version', help="Branch name of library. Example 'main'")
    parser.add_argument('to_version', help="Branch name of library. Exampe 'gz-cmake4'")
    args = parser.parse_args()

    # Search in current directory
    path = Path(__file__).parent
    files = set(f.resolve() for f in path.glob("*.yaml"))
    changes = {}
    for file in files:
        found_match = False
        old = open(file, "r").read()
        conf = yaml.safe_load(old)
        matching_repo = conf["repositories"].get(args.library)
        if matching_repo and matching_repo["version"] == args.from_version:
            matching_repo["version"] = args.to_version
            new = yaml.dump(conf, sort_keys=False, explicit_start=True)
            changes[file.name] = (old, new)

    print("The following change will be applied")
    for file, (old, new) in changes.items():
        diff = difflib.unified_diff(old.splitlines(keepends=True),
                                    new.splitlines(keepends=True), fromfile=file)
        sys.stdout.writelines(diff)

    choice = input("Do you want to proceed [Y/n]")
    if choice in 'Yy':
        for file, (_, new) in changes.items():
            with open(file, "w") as f:
                f.write(new)
