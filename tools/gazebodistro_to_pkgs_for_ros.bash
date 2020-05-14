if [[ ${#} -ne 1 ]]; then
    echo "Usage: ${0} <distro_yaml_file>"
    exit -1
fi

GAZEBO_DISTRO=${1}

remove_string_dups()
{
    local string=${1}

    sed 's/ /\n/g' <<< $string | sort | uniq | tr '\n' ' '
}

echo
echo "This tool reads a gazebodistro file and look in the system for"
echo "all available pkgs corresponding to that distro file"
echo

BRANCH_NAMES=$(grep version: ${GAZEBO_DISTRO} | awk '{ print $2 }')
# Get packages from gazebodistro file. Some assumptions and ros- filter
total_pkgs=
for branch in ${BRANCH_NAMES}; do
    pkg_name=${branch/ign-/ignition-}
    pkg_name=${pkg_name/sdf/sdformat}
    echo " 1. Getting packages using: ${pkg_name}"
    # assume here than when foo1 fails search for foo
    pkgs=$(apt-cache search ${pkg_name} | awk '{ print $1 }' | grep -v '^ros-') || pkgs=$(apt-cache search ${pkg_name/1/} | awk '{ print $1 }' | grep -v '^ros-')
    total_pkgs="${total_pkgs} ${pkgs}"
done

echo

# Get all packages listed as dependencies
all_deps_pkgs=
for pkg in $(echo ${total_pkgs} | sort | uniq); do
    echo " 2. Get dependencies of: ${pkg}"
    new_pkgs=$(apt-rdepends ${pkg} 2>/dev/null | grep Depends: | awk '{ print $2 }' | sort | uniq)
    all_deps_pkgs="${all_deps_pkgs} ${new_pkgs}"
done

all_deps_pkgs=$(remove_string_dups "${all_deps_pkgs}")
echo

for new_pkg in ${all_deps_pkgs}; do
    mad_output=$(apt-cache madison ${new_pkg})
    # skip purely virtual
    [[ ${mad_output} == "" ]] && continue
    if [[ -z  $(grep 'packages.ros.org\|archive.ubuntu.com' <<< ${mad_output}) ]]; then
	echo " 3. Found missing package ${new_pkg}"
	osrf_pkgs="${osrf_pkgs} ${new_pkg}"
    fi
done

osrf_pkgs=$(remove_string_dups "${osrf_pkgs}")
echo

echo "LIST OF PACKAGES:"
echo "${osrf_pkgs}"
