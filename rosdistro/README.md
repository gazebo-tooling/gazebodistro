# Gazebo rosdistro index

A [REP-143](http://ros.org/reps/rep-0143.html) distribution file and
[REP-153](http://ros.org/reps/rep-0153.html) index describing Gazebo releases in
the format ROS tooling understands.

## Layout

| Path | Purpose |
|---|---|
| `index-v4.yaml` | The index. Canonical URL is this file on `master`. |
| `jetty/distribution.yaml` | Gazebo Jetty: every repository in the collection plus the `gz-jetty` metapackage, pinned to shipped versions. |
| `jetty-cache.yaml` | Generated cache. The reviewable, diffable copy. |
| `jetty-cache.yaml.gz` | Generated cache. What `index-v4.yaml` points at. |
| `lyrical-cache.yaml` | Generated cache for ROS 2 Lyrical extending Jetty (REP-2015 test). Reviewable copy. |
| `lyrical-cache.yaml.gz` | Same, what `index-v4.yaml` points at. |

## Using it

```python
from rosdistro import get_index, get_cached_distribution

index = get_index(
    'https://raw.githubusercontent.com/gazebo-tooling/gazebodistro/master/rosdistro/index-v4.yaml')
distribution = get_cached_distribution(index, 'jetty')
print(sorted(distribution.release_packages))
```

## Lyrical extends Jetty (REP-2015 test)

`index-v4.yaml` also lists `lyrical`, whose distribution file is the
[KmoM88 fork of ros/rosdistro](https://github.com/KmoM88/ros-rosdistro/tree/feature/rep-2015-jetty-extension)
pinned to a commit. That file is REP-2015 distribution version 3 and carries
`extends: [{distro_name: jetty, extension_method: source_rebuild}]`. Reading it
needs the matching
[rosdistro library fork](https://github.com/KmoM88/rosdistro/tree/feature/rep-2015-v3-parser);
the stock library rejects version 3.

The fork merges the parent through the cache path only when the child's
cache embeds a version-3 distribution file, and it looks for the parent in
the same index. Both caches therefore live here, and `lyrical-cache.yaml.gz`
is rebuilt from the official lyrical cache plus the pinned file:

```bash
cd rosdistro
uv venv .venv-fork && uv pip install --python .venv-fork/bin/python \
    'rosdistro @ git+https://github.com/KmoM88/rosdistro@436f5429fc1e' PyYAML catkin_pkg
curl -sSL http://repo.ros2.org/rosdistro_cache/lyrical-cache.yaml.gz -o lyrical-cache.yaml.gz
.venv-fork/bin/python -m rosdistro.cli.rosdistro_build_cache index-v4.yaml lyrical
```

Seeding from the official cache means only manifests whose release entry
differs between the pinned fork file and the seed are refetched (116
non-Gazebo packages on 2026-09-03); the embedded distribution file is
replaced. `test/test_rosdistro_extension.py` checks the result and is
skipped under the stock library.

## Regenerating the cache

Required after any change to a `distribution.yaml`. CI fails otherwise.

```bash
cd rosdistro
python3 -m rosdistro.cli.rosdistro_build_cache --preclean index-v4.yaml jetty
```

Needs `python3-rosdistro`. The command writes into the current working
directory, hence the `cd`. Commit both output files. `--preclean` rebuilds
every entry from the git tags rather than reusing the committed cache, which is
what CI does and how a `tags.release` prefix naming a tag that does not exist
gets caught.

## Adding a repository

Five edits, in this order. Miss one of the last four and it surfaces as a bare
assertion failure in the test suite.

1. `collection-jetty.yaml`, in the repository root, so the source build picks
   the repository up.
2. `rosdistro/jetty/distribution.yaml`: a `source:` entry, and a `release:`
   block whose `tags.release` uses `{upstream_version}` and whose `version` is
   the exact Debian version apt ships.
3. `APT_PACKAGE` in `test/test_jetty_versions.py`: the distribution file's
   repository name mapped to its binary package name in the apt repository.
4. `EXPECTED_PACKAGES` in `test/test_rosdistro_api.py`: every package the
   repository releases, which is not always the repository name.
5. Regenerate the cache and commit both cache files.

## Conventions

- `source.version` is the stable branch; `release.version` is the exact Debian
  version shipped for Ubuntu Noble on `packages.osrfoundation.org`.
- `tags.release` uses `{upstream_version}`, never `{version}`, so the Debian
  revision stays out of the tag: `5.1.1-2` resolves to `gz-cmake5_5.1.1`.
- `release.url` points at the **source** repository. Gazebo's
  `gazebo-release/*-release` repositories hold Debian templates on branches and
  carry no tags, so they cannot serve manifests to `rosdistro_build_cache`. This
  changes once releases are bloomed.
- `gz-fuel-tools` and `gz-tools` need an explicit `packages:` list — their
  package names are `gz-fuel_tools` and `gz-tools2`.
- `release_platforms` lists `noble` and `resolute`. Every Jetty package is
  published for both; `release.version` tracks noble, and resolute's Debian
  revisions may differ.
