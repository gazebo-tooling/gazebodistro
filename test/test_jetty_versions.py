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

"""Every release.version matches what packages.osrfoundation.org ships.

Needs network. Skips (never fails) when the apt repository is unreachable, so
offline runs stay green.
"""

import gzip
import io
import os
import unittest
import urllib.error
import urllib.request

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_PATH = os.path.join(REPO_ROOT, 'rosdistro', 'jetty', 'distribution.yaml')

PACKAGES_URL = (
    'https://packages.osrfoundation.org/gazebo/ubuntu-stable/dists/noble/'
    'main/binary-amd64/Packages.gz')

# distribution.yaml repository name -> binary package name in the apt repository
APT_PACKAGE = {
    'gz-cmake': 'gz-jetty-cmake',
    'gz-common': 'gz-jetty-common',
    'gz-fuel-tools': 'gz-jetty-fuel-tools',
    'gz-gui': 'gz-jetty-gui',
    'gz-jetty': 'gz-jetty',
    'gz-launch': 'gz-jetty-launch',
    'gz-math': 'gz-jetty-math',
    'gz-msgs': 'gz-jetty-msgs',
    'gz-physics': 'gz-jetty-physics',
    'gz-plugin': 'gz-jetty-plugin',
    'gz-rendering': 'gz-jetty-rendering',
    'gz-sensors': 'gz-jetty-sensors',
    'gz-sim': 'gz-jetty-sim',
    'gz-tools': 'gz-jetty-tools',
    'gz-transport': 'gz-jetty-transport',
    'gz-utils': 'gz-jetty-utils',
    'sdformat': 'gz-jetty-sdformat',
}


def fetch_noble_versions():
    """Return {binary package name: version} from the noble Packages index.

    The trailing '~noble' suffix is stripped so the value is comparable with
    release.version in the distribution file.
    """
    with urllib.request.urlopen(PACKAGES_URL, timeout=60) as response:
        raw = gzip.GzipFile(fileobj=io.BytesIO(response.read())).read()
    versions = {}
    name = None
    for line in raw.decode('utf-8', 'replace').splitlines():
        if line.startswith('Package: '):
            name = line[len('Package: '):].strip()
        elif line.startswith('Version: ') and name is not None:
            version = line[len('Version: '):].strip()
            versions.setdefault(name, version.split('~')[0])
            name = None
    return versions


class TestJettyVersionsMatchApt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.apt_versions = fetch_noble_versions()
        except (urllib.error.URLError, OSError) as exc:
            raise unittest.SkipTest(
                'packages.osrfoundation.org unreachable: %s' % exc)
        with open(DIST_PATH) as f:
            cls.repositories = yaml.safe_load(f)['repositories']

    def test_every_repository_has_a_release_version(self):
        for repo in sorted(self.repositories):
            release = self.repositories[repo].get('release') or {}
            self.assertTrue(
                release.get('version'),
                '%s has no release.version' % repo)

    def test_release_version_matches_apt(self):
        for repo in sorted(self.repositories):
            apt_name = APT_PACKAGE.get(repo)
            self.assertIsNotNone(
                apt_name, 'no APT_PACKAGE mapping for %s' % repo)
            expected = self.apt_versions.get(apt_name)
            self.assertIsNotNone(
                expected,
                '%s not found in the noble Packages index' % apt_name)
            actual = (self.repositories[repo].get('release') or {}).get('version')
            self.assertEqual(
                expected, actual,
                '%s: distribution.yaml says %s, apt ships %s'
                % (repo, actual, expected))

    def test_release_tag_uses_upstream_version(self):
        """The Debian revision must not leak into the release tag."""
        for repo in sorted(self.repositories):
            release = self.repositories[repo].get('release') or {}
            tag = (release.get('tags') or {}).get('release', '')
            self.assertIn(
                '{upstream_version}', tag,
                '%s release tag %r must use {upstream_version}, not {version}'
                % (repo, tag))


if __name__ == '__main__':
    unittest.main()
