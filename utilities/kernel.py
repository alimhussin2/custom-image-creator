#!/usr/bin/python3

"""
Do some operation on the kernel.
Need to find how many kernels are installed in the
rootfs. Then need to select the default boot kernel
and set the grub.conf.
"""

import os
import subprocess
import shutil
import re

from utilities import logger
from utilities.extract import get_casper_directory
from utilities.constant import VMLINUZ, INITRD, SYMLINK_VMLINUZ, SYMLINK_INITRD
from utilities.file_ops import get_directory_file_list, copy_to

logger = logger.create_logger(__name__)

def get_vmlinuz_list(custom_disk_directory, custom_root_directory):
    """
    Search the vmlinuz from the following directories:
    1. custom-root/boot/vmlinuz-*; initrd.img-*
    2. source-disk/casper/vmlinuz.efi; initrd.lz

    If there is a new kernel is installed in the image, there might be
    multiple kernel detected.
    Return: the the list of full path of vmlinuz
    """
    vmlinuz_list = []
    # search vmlinuz in custom root directory
    boot_directory = os.path.join(custom_root_directory, 'boot')
    vmlinuz_list = get_directory_file_list(VMLINUZ, boot_directory)

    # search vmlinuz in custom disk directory
    casper_directory = os.path.join(custom_disk_directory, 'casper')
    vmlinuz_list += get_directory_file_list(VMLINUZ, casper_directory)

    return vmlinuz_list


def get_initrd_list(custom_disk_directory, custom_root_directory):
    """
    Search the vmlinuz from the following directories:
    1. custom-root/boot/initrd.img-*
    2. source-disk/casper/initrd.lz
    Return: the list of full path of initrd
    """
    initrd_list = []
    # search initrd in custom root directory
    boot_directory = os.path.join(custom_root_directory, 'boot')
    initrd_list = get_directory_file_list(INITRD, boot_directory)

    # search vmlinuz in custom disk directory
    casper_directory = os.path.join(custom_disk_directory, 'casper')
    initrd_list += get_directory_file_list(INITRD, casper_directory)

    return initrd_list



def get_kernel_initrd(custom_disk_directory, custom_root_directory, kernel_version):
    """
    Get selected kernel based on kernel_version
    and return path to vmlinuz and initrd
    """
    # get a list of vmlinuz and initrd from boot_directory
    boot_directory = os.path.join(custom_root_directory, 'boot')
    vmlinuz_list = get_directory_file_list(VMLINUZ, boot_directory)
    initrd_list = get_directory_file_list(INITRD, boot_directory)

    kernel_path = {}
    vmlinuz_path = os.path.join(custom_disk_directory, 'casper', 'vmlinuz')
    initrd_path = os.path.join(custom_disk_directory, 'casper', 'initrd')

    for vmlinuz in vmlinuz_list:
        if kernel_version in vmlinuz:
            vmlinuz_path = vmlinuz
            break
    
    for initrd in initrd_list:
        if kernel_version in initrd:
            initrd_path = initrd
            break

    logger.info("Selected kernel %s", vmlinuz_path)
    logger.info("Select initrd %s", initrd_path)
    kernel_path = {
            "vmlinuz": vmlinuz_path,
            "initrd": initrd_path
            }

    return kernel_path

def select_kernel_initrd(boot_directory, kernel_version):
    """
    Select kernel from boot directory as default kernel
    """
    # get a list of kernel and initrd from boot directory and make a symlink
    vmlinuz_list = get_directory_file_list(VMLINUZ, boot_directory)
    initrd_list = get_directory_file_list(INITRD, boot_directory)

    for vmlinuz in vmlinuz_list:
        if kernel_version in vmlinuz:
            logger.info("Select kernel %s", vmlinuz)
            # create a symlink to vmlinuz
            src = os.path.basename(vmlinuz)
            dst = os.path.join(os.path.dirname(vmlinuz), SYMLINK_VMLINUZ)
            logger.debug("src %s", src)
            logger.debug("dst %s", dst)
            #if os.path.exists(dst) and os.path.islink(dst):
            if os.path.islink(dst):
                logger.info("unlink %s", dst)
                os.unlink(dst)
            os.symlink(src, dst)

    for initrd in initrd_list:
        if kernel_version in initrd:
            logger.info("Select initrd %s", initrd)
            # create a symlink to initrd
            src = os.path.basename(initrd)
            dst = os.path.join(os.path.dirname(initrd), SYMLINK_INITRD)
            logger.debug("src %s", src)
            logger.debug("dst %s", dst)
            if os.path.islink(dst):
                os.unlink(dst)
            os.symlink(src, dst)


def get_version_from_file_name(file_path):
    logger.info("Get version from file name %s", file_path)
    version = re.search(r'\d[\d\.-]*\d', file_path)
    version = version.group(0) if version else None
    logger.info("Version %s", version)


def get_version_from_file_type(file_path):
    logger.info("Get version name from file type %s", file_path)
    cmd = "file %s" % file_path
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    version = None
    version_info = re.search(r'(\d+\.\d+\.\d+(?:-\d+))', output)
    if version_info:
        version = version_info.group(1)
        logger.info("Version %s", version)

    return version

def copy_kernel(custom_disk_directory, custom_root_directory, boot_directory):
    kernel_list = get_vmlinuz_list(custom_disk_directory, custom_root_directory)
    for kernel in kernel_list:
        # copy all kernel to boot directory
        #TODO: rename the file with vmlinuz because there is a symlink with 'vmlinuz'
        vmlinuz = os.path.basename(kernel)
        if vmlinuz == VMLINUZ:
            # rename the casper/vmlinuz to vmlinuz-<version>
            version_name = get_version_from_file_type(kernel)
            if version_name:
                vmlinuz = vmlinuz + '-' + version_name

        copy_to(kernel, os.path.join(boot_directory, vmlinuz))


def copy_initrd(custom_disk_directory, custom_root_directory, boot_directory):
    initrd_list = get_initrd_list(custom_disk_directory, custom_root_directory)
    for initrd in initrd_list:
        # copy all initrd to boot directory
        initrdimg = os.path.basename(initrd)
        if initrdimg == INITRD:
            # rename casper/initrd to initrd-<version>
            #TODO: need to find a way to get the initrd version
            version_name = get_version_from_file_type(initrd)
            if version_name:
                initrdimg = initrdimg + '-' + version_name
            else:
                # TODO: This is temporary use the readlink
                initrdimg = os.readlink(os.path.join(boot_directory, 'initrd.img'))
                

        copy_to(initrd, os.path.join(boot_directory, initrdimg))


def update_boot_configuration(custom_disk_directory):
    """
    Update the boot configuration files, replacing references to vmlinuz
    and initrd with the correct file names based on the selected kernel.
    """
    grub_file = os.path.join(custom_disk_directory, 'boot', 'grub', 'grub.cfg')
    logger.info("Update boot configuration %s", grub_file)
    lines = []

    with open(grub_file, 'r') as f:
        for line in f.readlines():
            if 'linux' in line or 'vmlinuz' in line:
                # add boot=casper in line
                # linux  /casper/vmlinuz boot=casper
                line = line.replace('vmlinuz', 'vmlinuz boot=casper')

            lines.append(line)

    with open(grub_file, 'w') as f:
        for line in lines:
            f.write("%s" % line)
