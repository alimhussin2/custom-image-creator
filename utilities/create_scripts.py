"""
This script will generate a entrypoint.sh file in entrypoint.d.
The entrypoint.sh contain the steps to install the kernel overlay and 
userspace packages as follows
1. Download and install kernel overlay
2. Add PPA to /etc/apt/sources.list
3. Install userspace packages using apt
"""

import os
import subprocess

from utilities.logger import create_logger
from utilities.file_ops import make_directory, copy_to
from utilities.constant import *
from utilities.util import get_proxy, set_apt_proxy

logger = create_logger(__name__)

def do_script(target_directory, packages_list, kernel_urls, kernel_version, proxy_path=None):
    """
    Wrapper function for generate install packages, kernel scripts
    """
    create_install_packages_script(packages_list, target_directory, proxy_path)
    create_install_kernel_script(kernel_urls, target_directory, kernel_version, proxy_path)
    create_entrypoint_script(target_directory)


def add_sources_list(target_directory, sources_list):
    #cmd = "deb {link} {version} main multiverse"

    logger.info("Create Script to update sources.list")
    target_directory = os.path.join(target_directory, ENTRYPOINT_DIRECTORY)
    logger.info("Target directory is %s", target_directory)
    make_directory(target_directory)
    srcslists_script = os.path.join(target_directory, SCRIPT_SOURCESLIST)

    with open(srcslists_script, "w") as p:
        p.write("#!/bin/bash\n")
        p.write("\ncat << EOF >> /etc/apt/sources.list\n")
        # open and append the to source list
        for source in sources_list:
            p.write("%s\n" % source)
            logger.info("Add %s to sources.list", source)
        p.write("EOF\n")
        p.write("\napt-get update")
        p.write("\n")

    # change the permission of the script to 0755
    os.chmod(srcslists_script, 0o755)


def create_install_packages_script(packages_list, target_directory, proxy_path=None):
    """
    Generate a script for installing packages in
    <target_directory>/entrypoint.d/packages.sh
    """
    logger.info("Create packages list to be installed")
    custom_root_directory = os.path.join(target_directory, "custom-root")
    target_directory = os.path.join(target_directory, ENTRYPOINT_DIRECTORY)
    logger.info("Target directory is %s", target_directory)
    make_directory(target_directory)
    packages_script = os.path.join(target_directory, SCRIPT_PACKAGES)
    is_proxy, proxy = get_proxy(proxy_path)

    if is_proxy:
        set_apt_proxy(proxy_path, custom_root_directory)

    with open(packages_script, "w") as p:
        p.write("#!/bin/bash\n")
        if is_proxy:
            p.write("\n%s\n" % proxy)

        p.write("\napt-get update")
        for package in packages_list:
            cmd = "apt-get install -y %s" % package
            logger.debug("cmd: %s", cmd)
            p.write("\n%s" % cmd)

        p.write("\n")

    # change the permission of the script to 0755
    os.chmod(packages_script, 0o755)


def create_install_kernel_script(urls, target_directory, kernel_version, proxy_path=None):
    """
    Generate a script for installing kernel overlay in
    <target_directory>/entrypoint.d/install_kernel.sh
    """
    logger.info("Create kernel overlay installation script")
    target_directory = os.path.join(target_directory, ENTRYPOINT_DIRECTORY)
    make_directory(target_directory)
    kernel_script = os.path.join(target_directory, SCRIPT_KERNEL)
    logger.info("Kernel installation script in %s", kernel_script)
    rel_entry_path = os.path.join(ROOT_USER_DIRECTORY, ENTRYPOINT_DIRECTORY)

    if not urls:
        return None

    with open(kernel_script, "w") as k:
        k.write("#!/bin/bash\n")
        # Download kernel overlay for given url
        # proxy might be needed as it download from internal server
        is_proxy, proxy = get_proxy(proxy_path)
        if is_proxy:
            k.write("\n%s\n" % proxy)

        for url in urls:
            #TODO: check if the it url. Else copy the existing files to target_directory
            if url.startswith('http'):
                cmd = ("wget --no-check-certificate --directory-prefix={dest_directory} {url}").format(
                        dest_directory=rel_entry_path,
                        url=url)
                k.write("\n%s" % cmd)
                logger.debug("Add command %s" % cmd)
            else:
                # TODO: check the destination directory
                file_path = os.path.join(target_directory, os.path.basename(url))
                copy_to(url, file_path)
            
        # installing the kernel
        cmd = ("dpkg -i {rel_entry_path}/linux-*{kernel_version}*.deb").format(
                rel_entry_path=rel_entry_path,
                kernel_version=kernel_version)
        k.write("\n\n%s\n" % cmd)
        logger.debug("Add command %s" % cmd)

    # change the permission of the script to 0755
    os.chmod(kernel_script, 0o755)


def create_entrypoint_script(target_directory):
    """
    Create a wrapper script for installing kernel overlay,
    packages
    """
    logger.info("Create entrypoint script")
    target_directory = os.path.join(target_directory, ENTRYPOINT_DIRECTORY)
    make_directory(target_directory)
    entrypoint_script = os.path.join(target_directory, SCRIPT_ENTRYPOINT)
    logger.info("Entrypoint script in %s", entrypoint_script)

    srcslist_script = os.path.join(target_directory, SCRIPT_SOURCESLIST)
    kernel_script = os.path.join(target_directory, SCRIPT_KERNEL)
    packages_script = os.path.join(target_directory, SCRIPT_PACKAGES)

    # Relative directory in container or chroot
    rel_entry_path = os.path.join(ROOT_USER_DIRECTORY, ENTRYPOINT_DIRECTORY)
    rel_srcslist_script = os.path.join(rel_entry_path, SCRIPT_SOURCESLIST)
    rel_kernel_script = os.path.join(rel_entry_path, SCRIPT_KERNEL)
    rel_packages_script = os.path.join(rel_entry_path, SCRIPT_PACKAGES)

    with open(entrypoint_script, "w") as e:
        e.write("#!/bin/bash\n")

        # Add sourceslist script
        if os.path.exists(srcslist_script):
            e.write("\nbash %s" % rel_srcslist_script)
            logger.debug("Add updatesrcslist.sh script")

        # Add install kernel script
        if os.path.exists(kernel_script):
            e.write("\nbash %s" % rel_kernel_script)
            logger.debug("Add install_kernel.sh script")
        # Add install packages script
        if os.path.exists(packages_script):
            e.write("\nbash %s" % rel_packages_script)
            logger.debug("Add install_packages.sh script")

        e.write("\n")
    
    # change the permission of the script to 0755
    os.chmod(entrypoint_script, 0o755)
