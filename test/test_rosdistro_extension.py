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

"""Lyrical extends jetty through the committed caches (REP-2015).

Runs only with a rosdistro library that parses distribution file version 3
(the KmoM88 fork). With the stock library every test here is skipped, so the
regular CI job stays green. Reads only committed files; no network.
"""

import gzip
import os
import unittest

import yaml
from rosdistro import get_cached_distribution, get_index
from rosdistro.dependency_walker import DependencyWalker
from rosdistro.distribution_file import DistributionFile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSDISTRO_DIR = os.path.join(REPO_ROOT, 'rosdistro')
INDEX_URL = 'file://' + os.path.join(ROSDISTRO_DIR, 'index-v4.yaml')

DEPENDENCY_TYPES = [
    'buildtool', 'buildtool_export', 'build', 'build_export', 'run', 'test']

# Packages nothing in jetty depends on besides themselves: the metapackage,
# gz-launch, and gz-sim itself.
NOT_A_GZ_SIM_DEPENDENCY = {'gz-jetty', 'gz-launch', 'gz-sim'}


def fork_available():
    try:
        DistributionFile('probe', {
            'type': 'distribution', 'version': 3,
            'repositories': {}, 'release_platforms': {}})
    except AssertionError:
        return False
    return True


def embedded_distribution_file(cache_path):
    with open(cache_path) as f:
        data = yaml.safe_load(f)['distribution_file']
    return data[0] if isinstance(data, list) else data


@unittest.skipUnless(fork_available(), 'needs a rosdistro that parses distribution v3')
class TestLyricalExtendsJetty(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.index = get_index(INDEX_URL)
        cls.jetty = get_cached_distribution(cls.index, 'jetty')
        cls.lyrical = get_cached_distribution(cls.index, 'lyrical')
        cls.jetty_packages = set(cls.jetty.release_packages)

    def test_index_lists_lyrical(self):
        self.assertIn('lyrical', self.index.distributions)

    def test_lyrical_distribution_is_pinned_to_a_commit(self):
        url = self.index.distributions['lyrical']['distribution'][0]
        self.assertRegex(
            url,
            r'^https://raw\.githubusercontent\.com/KmoM88/ros-rosdistro/'
            r'[0-9a-f]{12,40}/lyrical/distribution\.yaml$')

    def test_cache_embeds_the_extension(self):
        dist_file = embedded_distribution_file(
            os.path.join(ROSDISTRO_DIR, 'lyrical-cache.yaml'))
        self.assertEqual(3, dist_file['version'])
        self.assertEqual(1, len(dist_file['extends']))
        self.assertEqual('jetty', dist_file['extends'][0]['distro_name'])
        self.assertEqual(
            'source_rebuild', dist_file['extends'][0]['extension_method'])

    def test_lyrical_resolves_every_jetty_package(self):
        missing = self.jetty_packages - set(self.lyrical.release_packages)
        self.assertFalse(missing, 'not merged from jetty: %s' % sorted(missing))

    def test_gz_sim_dependencies_walk_through_the_extension(self):
        expected = self.jetty_packages - NOT_A_GZ_SIM_DEPENDENCY
        got = DependencyWalker(self.lyrical).get_recursive_depends(
            'gz-sim', DEPENDENCY_TYPES, ros_packages_only=True)
        self.assertEqual(expected, got)

    def test_gz_sim_release_tag_matches_jetty(self):
        def tag(distribution):
            package = distribution.release_packages['gz-sim']
            repo = distribution.repositories[package.repository_name]
            return repo.release_repository.get_release_tag('gz-sim')
        self.assertEqual(tag(self.jetty), tag(self.lyrical))
        self.assertRegex(tag(self.lyrical), r'^gz-sim10_\d+\.\d+\.\d+$')

    def test_compressed_cache_matches_the_plain_cache(self):
        base = os.path.join(ROSDISTRO_DIR, 'lyrical-cache.yaml')
        with open(base, 'rb') as f:
            plain = f.read()
        with gzip.open(base + '.gz', 'rb') as f:
            self.assertEqual(plain, f.read())


if __name__ == '__main__':
    unittest.main()
