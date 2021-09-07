"""
Create new file system manifest file based on
custom-disk/casper/filesystem.manifest.
Also change the os-release description.
This need to modify outside of chroot environment.
"""

import os
import subprocess
import re

from utilities.logger import create_logger
from utilities.util import run_cmd

logger = create_logger(__name__)

def modify_release_description(custom_root_directory):
    logger.info("Update the release descriptions")
    desc = get_os_release(custom_root_directory)
    description = "%s Customized image" % desc

    file_path = os.path.join(custom_root_directory, 'etc', 'lsb-release')
    if os.path.isfile(file_path) and not os.path.islink(file_path):
        update_release_description(file_path, 'DISTRIB_DESCRIPTION', description)

    file_path = os.path.join(custom_root_directory, 'etc', 'os-release')
    if os.path.isfile(file_path) and not os.path.islink(file_path):
        update_release_description(file_path, 'PREETY_NAME', description)

    file_path = os.path.join(custom_root_directory, 'usr', 'lib', 'os-release')
    if os.path.isfile(file_path) and not os.path.islink(file_path):
        update_release_description(file_path, 'PREETY_NAME', description)


def update_release_description(target_file_path, key, value):
    value = value.replace('"', '')

    logger.info("Update release description in %s", target_file_path)
    logger.debug("key %s", key)
    logger.debug("value %s", value)

    lines = []
    with open(target_file_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.startswith(key):
            line = '%s="%s"' % (key, value)
        new_lines.append(line.strip())

    target_file_name = os.path.basename(target_file_path)
    temp_file_path = os.path.join(os.path.sep, 'tmp', target_file_name)

    with open(temp_file_path, 'w') as f:
        for line in new_lines:
            f.write(line + os.linesep)

    cmd = "mv %s %s" % (temp_file_path, target_file_path)
    ret = subprocess.run(cmd, shell=True)

    return ret.returncode


def get_os_release(custom_root_directory):
    file_path = os.path.join(custom_root_directory, 'etc', 'os-release')
    logger.info("Get OS release in %s", file_path)
    key = 'PRETTY_NAME'
    os_name = ''


    lines = []
    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith(key):
            line = line.replace('"', '')
            os_name = "".join(re.findall(rf"{key}=(.*)", line))
            break

    return os_name


def create_filesystem_manifest(custom_root_directory, custom_disk_directory):
    logger.info("Create file system manifest")
    file_path = os.path.join(custom_disk_directory, 'casper', 'filesystem.manifest')
    logger.info("Write file system manifest to %s", file_path)

    dpkg_database_directory = os.path.join(custom_root_directory, 'var', 'lib', 'dpkg')
    cmd = "dpkg-query --show --admindir=%s" % dpkg_database_directory
    ret, output = run_cmd(cmd)

    installed_packages = output.splitlines()
    packages_count = len(installed_packages)

    with open(file_path, 'w') as f:
        for line in installed_packages:
            f.write('%s\n' % line)
