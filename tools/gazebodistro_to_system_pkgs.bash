if [[ ${#} -ne 1 ]]; then
    echo "Usage: ${0} <distro_yaml_file>"
    exit -1
fi

GAZEBO_DISTRO=${1}

echo
echo "This tool reads a gazebodistro file and look in the system for"
echo "all available pkgs corresponding to that distro file"
echo

BRANCH_NAMES=$(grep version: ${GAZEBO_DISTRO} | awk '{ print $2 }')
total_pkgs=
for branch in ${BRANCH_NAMES}; do
    pkg_name=${branch/ign-/ignition-}
    pkg_name=${pkg_name/sdf/sdformat}
    echo " Searching: ${pkg_name}"
    pkgs=$(apt-cache search ${pkg_name} | awk '{ print $1 }')
    total_pkgs="${total_pkgs} ${pkgs}"
done

echo 
echo ${total_pkgs}
