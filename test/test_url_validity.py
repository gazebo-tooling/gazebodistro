#!/usr/bin/env python3

# Copyright (c) 2021, Open Source Robotics Foundation
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

from io import StringIO
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import unidiff
import yaml
from yaml.composer import Composer
from yaml.constructor import Constructor

UPSTREAM_NAME = 'unittest_upstream_comparision'
DIFF_BRANCH = 'master'
DIFF_REPO = 'https://github.com/gazebo-tooling/gazebodistro.git'

def check_git_branch_exists(url, branch_name):
    cmd = ('git ls-remote %s refs/heads/*' % url).split()
    try:
        branch_list = subprocess.check_output(cmd).decode('utf-8')
    except subprocess.CalledProcessError as ex:
        return (False, 'subprocess call %s failed: %s' % (cmd, ex))

    if 'refs/heads/%s' % branch_name in branch_list:
        return (True, '')
    return (False, 'No branch found matching %s' % branch_name)

def detect_lines(diffstr):
    """Take a diff string and return a dict of
    files with line numbers changed"""
    resultant_lines = {}
    # diffstr is already decoded
    io = StringIO(diffstr)
    udiff = unidiff.PatchSet(io)
    for file in udiff:
        target_lines = []
        # if file.path in TARGET_FILES:
        for hunk in file:
            target_lines += range(hunk.target_start,
                                  hunk.target_start + hunk.target_length)
        resultant_lines[file.path] = target_lines
    return resultant_lines

def load_yaml_with_lines(filename):
    d = open(filename).read()
    loader = yaml.Loader(d)

    def compose_node(parent, index):
        # the line number where the previous token has ended (plus empty lines)
        line = loader.line
        node = Composer.compose_node(loader, parent, index)
        node.__line__ = line + 1
        return node

    construct_mapping = loader.construct_mapping

    def custom_construct_mapping(node, deep=False):
        mapping = construct_mapping(node, deep=deep)
        mapping['__line__'] = node.__line__
        return mapping
    loader.compose_node = compose_node
    loader.construct_mapping = custom_construct_mapping
    data = loader.get_single_data()

    return data

def isolate_yaml_snippets_from_line_numbers(yaml_dict, line_numbers):
    changed_repos = {}

    for dl in line_numbers:
        match = None
        for name, values in yaml_dict.items():
            if name == '__line__':
                continue
            if not isinstance(values, dict):
                print("not a dict %s %s" % (name, values))
                continue
            # print("comparing to repo %s values %s" % (name, values))
            if values['__line__'] <= dl:
                if match and match['__line__'] > values['__line__']:
                    continue
                match = values
                match['repo'] = name
        if match:
            changed_repos[match['repo']] = match
    return changed_repos

def main():
    detected_errors = []

    # See if UPSTREAM_NAME remote is available and use it as it's expected to be setup by CI
    # Otherwise fall back to origin/master
    try:
        cmd = ('git config --get remote.%s.url' % UPSTREAM_NAME).split()
        try:
            remote_url = subprocess.check_output(cmd).decode('utf-8').strip()
            # Remote exists
            # Check url
            if remote_url != DIFF_REPO:
                detected_errors.append('%s remote url [%s] is different than %s' % (UPSTREAM_NAME, remote_url, DIFF_REPO))
                return detected_errors

            target_branch = '%s/%s' % (UPSTREAM_NAME, DIFF_BRANCH)
        except subprocess.CalledProcessError:
            # No remote so fall back to origin/master
            print('WARNING: No remote %s detected, falling back to origin master. Make sure it is up to date.' % UPSTREAM_NAME)
            target_branch = 'origin/master'

        cmd = ('git diff --unified=0 %s' % target_branch).split()
        diff = subprocess.check_output(cmd).decode('utf-8')
    except subprocess.CalledProcessError as ex:
        detected_errors.append('%s' % ex)
        return detected_errors

    diffed_lines = detect_lines(diff)

    for path, lines in diffed_lines.items():
        # Skip anything that isn't YAML
        if path.find('.yaml') < 0:
            continue

        # Skip anything in the github subdirectory
        if path.find('.github') >= 0:
            continue

        directory = os.path.join(os.path.dirname(__file__), '..')
        fullpath = os.path.abspath(os.path.join(directory, path))

        data = load_yaml_with_lines(fullpath)
        repos = data['repositories']
        changed_repos = isolate_yaml_snippets_from_line_numbers(repos, lines)

        for ((n, r), line) in zip(changed_repos.items(), lines):
            (branch_exists, message) = check_git_branch_exists(r['url'], r['version'])

            if not branch_exists:
                # https://docs.github.com/en/actions/learn-github-actions/workflow-commands-for-github-actions#setting-an-error-message
                val = f"::error file={path},line={line},title=Invalid Repo::{message}"
                detected_errors.extend([val])
    return detected_errors


class TestUrlValidity(unittest.TestCase):

    def test_function(self):
        detected_errors = main()

        for error in detected_errors:
            print(error)

        self.assertFalse(detected_errors)

if __name__ == "__main__":
    detected_errors = main()
    if not detected_errors:
        sys.exit(0)
    sys.exit(1)
