# Gazebo distro repo #

This repo gz_cmake_projecttains a list of files defining the Open Robotics dependencies (ignition robotics packages, sdformat, gazebo) for each major version of the Open Robotics software.

It is designed to work with the [vcstool](https://github.com/dirk-thomas/vcstool)

## Testing Changes Locally

To test any changes you make to repo files:

Run `yamllint` on all files:

```
pip install yamllint
yamllint *.yaml
```

Run `nosetest` suite on changed files:

```
pip install PyYAML argparse nose coverage unidiff PyGithub

nosetests -s
```




