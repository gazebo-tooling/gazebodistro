#!/usr/bin/env python3
# Author: github.com/methylDragon

"""
Clone gazebodistro; and from the yaml files in the repo, calculate information about the LATEST
version of downstream packages, including:

    - Generating valid bump phases via topological ordering, so downstream packages will always be
    merged AFTER upstream ones

    - Generating a list of all downstream, (explicit) dependants of any participant libraries

Note
====
Does not produce an optimal topological ordering (some elements in neighbouring waves might be
able to be merged), but certainly produces a valid, sound ordering!
"""

import tempfile
import yaml
import os
import re

from collections import defaultdict
from pprint import pprint


# TOPO SORT UTILS ==============================================================================
class Graph:
    def __init__(self, vertex_count):
        self.graph = defaultdict(list)  # Adjacency List
        self.V_num = vertex_count

    def add_edge(self,u,v):
        self.graph[u].append(v)


def assignlevel(graph, v, level):
    """
    Get topological level of vertex.

    Uses heuristic of longest directed path length. Highest level is first in topological order!
    Source: https://stackoverflow.com/questions/3420685
    """
    if v not in level:
        if v not in graph or not graph[v]:
            level[v] = 1
        else:
            level[v] = max(assignlevel(graph, w, level) + 1 for w in graph[v])
    return level[v]


# BUSINESS LOGIC ===================================================================================
def main(tmp_path, targets, gazebodistro_repo):
    # CLONE GAZEBODISTRO ===========================================================================
    os.chdir(tmp_path)
    os.system(f"git clone {gazebodistro_repo}")  # sys call to avoid using non-native git py libs
    os.chdir("gazebodistro")

    # PARSE YAMLS ==================================================================================
    files = [f for f in os.listdir() if os.path.isfile(f)]

    # Get library names and corresponding versions from file-list
    lib_re = re.compile("(\D*)(\d+).yaml")
    lib_tuples = [
        (f_re.group(1), int(f_re.group(2)))
        for f in files
        if (f_re := lib_re.match(f))
    ]

    assert lib_tuples, ("No yaml files found! "
                        "Make sure this runs in gazebodistro or clones it properly!")

    # Abuse sorting to get max lib versions
    lib_tuples.sort()
    max_libs_dict = {lib: "".join((os.path.curdir, "/", lib, str(ver), ".yaml"))
                     for lib, ver in lib_tuples}


    # OBTAIN DEPENDANTS ============================================================================
    dependant_dict = {target: [] for target in targets}

    for target in targets:
        for lib, filename in max_libs_dict.items():
            with open(filename, "r") as f:
                try:
                    conf = yaml.safe_load(f)
                except yaml.YAMLError as exc:
                    print(exc)
                    continue

            if target in conf['repositories'].keys():
                dependant_dict[target].append(lib)

    dependants = set()  # Union of all dependants of all target libraries
    for dependant_list in dependant_dict.values():
        dependants.update(dependant_list)

    # EXECUTE TOPO SORT ============================================================================
    g = Graph(len(dependants))

    # This dict stores the DOWNSTREAM dependants of each library!
    # Deps of deps and targets
    extended_dependant_dict = {parent_dep: [] for parent_dep in dependants}

    for dep in dependants:
        for lib, filename in max_libs_dict.items():
            with open(filename, "r") as f:
                try:
                    conf = yaml.safe_load(f)
                except yaml.YAMLError as exc:
                    print(exc)
                    continue

            if dep in conf['repositories'].keys():
                if lib == dep:
                    continue
                extended_dependant_dict[dep].append(lib)

    print("\n=== EXPLICIT DEPENDANTS ===")
    print("All dict values are dependants of their keys!\n")

    pprint(extended_dependant_dict)

    for lib, dependant_list in extended_dependant_dict.items():
        for dependant in dependant_list:
            if lib == dependant:
                continue
            g.add_edge(lib, dependant)

    l = {}  # Vertex level dict
    for v in g.graph:
        assignlevel(g.graph, v, l)

    topo_groups = [(level, lib) for lib, level in l.items()]
    topo_groups.sort()
    topo_groups.reverse()

    # OUT ==========================================================================================
    # The level number of a vertex is the max length of path in the dependency tree starting from it
    # Merging PRs from highest level downwards should fix most if not all dependency issues
    #
    # Vertices on the same level can be merged together
    #
    # Note: This ordering might not be the most efficient, but it will be safe
    #   E.g. Merging top level vertices from separate branches would work, but this strategy
    #   doesn't account for that
    topo_group_dict = defaultdict(list)

    print("\n=== TOPOLOGICALLY ORDERED MERGE WAVES ===")
    print("(Merge from highest number to lowest number!)\n")

    for level, lib in topo_groups:
        topo_group_dict[level].append(lib)

    assert topo_group_dict, ("No topological tree generatable! "
                             "Either your targets have no dependencies, "
                             "or gazebodistro wasn't cloned properly!")

    for level, libs in topo_group_dict.items():
        print(level, libs)


if __name__ == "__main__":
    import argparse
    import textwrap

    desc = ("""
    Clone gazebodistro; and from the yaml files in the repo, calculate information about the LATEST
    version of downstream packages, including:

        - Generating valid bump phases via topological ordering, so downstream packages will always be
        merged AFTER upstream ones

        - Generating a list of all downstream, (explicit) dependants of any participant libraries
    """)

    parser = argparse.ArgumentParser(description=textwrap.dedent(desc), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('targets', type=str,
                        help="Semicolon delimited bump targets (e.g. 'ign-cmake;ign-tools', using quotes!!)")
    parser.add_argument('--repo', dest='repo', type=str,
                        default="https://github.com/ignition-tooling/gazebodistro.git",
                        help="Target distro repo (default: 'ignition-tooling/gazebodistro')")

    args = parser.parse_args()

    # PARAMS ===========================================================================================
    with tempfile.TemporaryDirectory() as tmp_path:
        stripped_targets = [target.strip() for target in args.targets.split(";")]
        print("PARSING TARGETS:", stripped_targets)

        main(tmp_path, stripped_targets, args.repo)
