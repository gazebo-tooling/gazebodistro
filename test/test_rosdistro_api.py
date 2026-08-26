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

"""The committed index and cache load through the stock rosdistro API.

Reads only committed files; no network.
"""

import gzip
import os
import unittest

from catkin_pkg.package import parse_package_string
from rosdistro import get_cached_distribution, get_index

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(REPO_ROOT, 'rosdistro', 'index-v4.yaml')
INDEX_URL = 'file://' + INDEX_PATH

EXPECTED_PACKAGES = {
    'gz-cmake',
    'gz-common',
    'gz-fuel_tools',
    'gz-gui',
    'gz-jetty',
    'gz-launch',
    'gz-math',
    'gz-msgs',
    'gz-physics',
    'gz-plugin',
    'gz-rendering',
    'gz-sensors',
    'gz-sim',
    'gz-tools2',
    'gz-transport',
    'gz-utils',
    'sdformat',
}


class TestRosdistroApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.index = get_index(INDEX_URL)

    def test_index_lists_jetty(self):
        self.assertIn('jetty', self.index.distributions)

    def test_cached_distribution_has_every_package(self):
        distribution = get_cached_distribution(self.index, 'jetty')
        self.assertEqual(
            EXPECTED_PACKAGES, set(distribution.release_packages))

    def test_every_manifest_parses(self):
        distribution = get_cached_distribution(self.index, 'jetty')
        for name in sorted(distribution.release_packages):
            package_xml = distribution.get_release_package_xml(name)
            self.assertIsNotNone(package_xml, '%s has no manifest' % name)
            package = parse_package_string(package_xml)
            self.assertEqual(name, package.name)

    def test_manifest_versions_match_the_release_version(self):
        """The cache must hold the released version, not the branch tip.

        gz-sensors is the live example: its branch is ahead of its release.
        """
        distribution = get_cached_distribution(self.index, 'jetty')
        for repo_name, repo in sorted(distribution.repositories.items()):
            release = repo.release_repository
            if release is None or release.version is None:
                continue
            upstream = release.version.split('-')[0]
            for name in release.package_names:
                package = parse_package_string(
                    distribution.get_release_package_xml(name))
                self.assertEqual(
                    upstream, package.version,
                    '%s: cached manifest is %s but the release is %s'
                    % (name, package.version, upstream))

    def test_compressed_cache_matches_the_plain_cache(self):
        """index-v4.yaml points consumers at the .gz, but CI can only diff the
        plain .yaml, so nothing else joins the two files."""
        base = os.path.join(REPO_ROOT, 'rosdistro', 'jetty-cache.yaml')
        with open(base, 'rb') as f:
            plain = f.read()
        with gzip.open(base + '.gz', 'rb') as f:
            self.assertEqual(plain, f.read())


if __name__ == '__main__':
    unittest.main()
