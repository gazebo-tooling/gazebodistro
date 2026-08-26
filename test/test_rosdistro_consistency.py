#!/usr/bin/env python3

# Copyright (c) 2026, Open Source Robotics Foundation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import unittest

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSDISTRO_DIR = os.path.join(REPO_ROOT, 'rosdistro')


def find_rosdistro_distributions():
    """Return (distro_name, distribution.yaml path) for each rosdistro distro."""
    distributions = []
    if not os.path.isdir(ROSDISTRO_DIR):
        return distributions
    for name in sorted(os.listdir(ROSDISTRO_DIR)):
        path = os.path.join(ROSDISTRO_DIR, name, 'distribution.yaml')
        if os.path.isfile(path):
            distributions.append((name, path))
    return distributions


class TestRosdistroMirrorsCollection(unittest.TestCase):
    """rosdistro/<distro>/distribution.yaml stays in sync with collection-<distro>.yaml.

    The two files differ in kind. collection-*.yaml is a vcstool source-build
    manifest; distribution.yaml describes the released set, which additionally
    contains metapackages that have nothing to build from source. So the
    distribution is required to be a superset, and every extra repository must
    be genuinely released.
    """

    def test_distribution_has_valid_header(self):
        for distro, dist_path in find_rosdistro_distributions():
            with open(dist_path) as f:
                distribution = yaml.safe_load(f)
            self.assertEqual(distribution.get('type'), 'distribution', dist_path)
            self.assertEqual(distribution.get('version'), 2, dist_path)

    def test_distribution_covers_collection(self):
        distributions = find_rosdistro_distributions()
        self.assertTrue(
            distributions,
            'no rosdistro/<distro>/distribution.yaml files found under %s' % ROSDISTRO_DIR)

        for distro, dist_path in distributions:
            collection_path = os.path.join(REPO_ROOT, 'collection-%s.yaml' % distro)
            self.assertTrue(
                os.path.isfile(collection_path),
                'rosdistro/%s/distribution.yaml has no matching collection-%s.yaml' % (distro, distro))

            with open(collection_path) as f:
                collection_repos = yaml.safe_load(f)['repositories']
            with open(dist_path) as f:
                distribution_repos = yaml.safe_load(f)['repositories']

            missing = sorted(set(collection_repos) - set(distribution_repos))
            self.assertFalse(
                missing,
                'rosdistro/%s/distribution.yaml is missing repositories present '
                'in collection-%s.yaml: %s' % (distro, distro, missing))

            for repo, collection_entry in collection_repos.items():
                source = distribution_repos[repo].get('source')
                self.assertIsNotNone(
                    source,
                    'rosdistro/%s/distribution.yaml: %s has no source entry' % (distro, repo))
                for key in ('type', 'url', 'version'):
                    self.assertEqual(
                        collection_entry.get(key), source.get(key),
                        'rosdistro/%s/distribution.yaml: %s source %s differs '
                        'from collection-%s.yaml' % (distro, repo, key, distro))

    def test_extra_repositories_are_released(self):
        """A repository absent from the collection must carry a release version."""
        for distro, dist_path in find_rosdistro_distributions():
            collection_path = os.path.join(REPO_ROOT, 'collection-%s.yaml' % distro)
            with open(collection_path) as f:
                collection_repos = yaml.safe_load(f)['repositories']
            with open(dist_path) as f:
                distribution_repos = yaml.safe_load(f)['repositories']

            for repo in sorted(set(distribution_repos) - set(collection_repos)):
                release = distribution_repos[repo].get('release') or {}
                self.assertTrue(
                    release.get('version'),
                    'rosdistro/%s/distribution.yaml: %s is not in collection-%s.yaml '
                    'and has no release version, so it is neither built from source '
                    'nor released' % (distro, repo, distro))


if __name__ == '__main__':
    unittest.main()
