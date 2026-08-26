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

## Using it

```python
from rosdistro import get_index, get_cached_distribution

index = get_index(
    'https://raw.githubusercontent.com/gazebo-tooling/gazebodistro/master/rosdistro/index-v4.yaml')
distribution = get_cached_distribution(index, 'jetty')
print(sorted(distribution.release_packages))
```

How a ROS distribution would consume this is an open question. No accepted REP
defines a mechanism for one distribution to extend another, and `rosdistro`
implements none today. What is settled is the format: this is a plain REP-143
distribution file behind a REP-153 index, so anything reading it through the
API above works as it stands, and any mechanism agreed on later has a standard
index to point at.

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
- `release_platforms` lists `noble` only. Jetty is present in the `resolute` apt
  dist but incomplete there: the rendering, GUI, sensors, sim and launch
  packages have not been built yet.
