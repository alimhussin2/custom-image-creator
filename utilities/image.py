"""
The steps to create a complete image with installed rootfs and kernel.
Start with do_image() as entry point.
"""

import os
import subprocess
import sys
import time

from utilities.logger import create_logger
from utilities.file_ops import copy_to, make_directory, make_directories
from utilities.iso import unmount
from utilities.container import unmount_chroot
from utilities.constant import DISK_NAME
from utilities.kernel import get_vmlinuz_list, get_initrd_list, copy_kernel, copy_initrd, select_kernel_initrd
from utilities.util import run_cmd, get_rootfs_size_bytes

logger = create_logger(__name__)

def do_image(target_disk_directory, project_directory, custom_root_directory,
        custom_disk_directory, kernel_version):
    """
    Step to build the image.

    """
    # image size in MB
    image_size = 10240
    disk_path = os.path.join(target_disk_directory, DISK_NAME)
    loop_device = prepare_image(disk_path, image_size)
    logger.debug("%s is mounted on loop device %s", DISK_NAME, loop_device)

    create_partition(loop_device, disk_path, image_size)
    format_partition(loop_device, image_size)
    show_partition_table(disk_path)
    prepare_rootfs(loop_device, project_directory, custom_root_directory,
            custom_disk_directory, kernel_version)
    cleanup(loop_device, project_directory)


def prepare_image(disk_path, image_size):
    """
    Create a blank image and mount it to loop device.
    Image size must be greater than boot partition + rootfs.
    Default image_size is 10GB.
    Return: loop device
    """
    logger.info("Creating raw disk image in %s", disk_path)
    # create a blank image
    cmd = "dd if=/dev/zero of=%s bs=1M count=%s" % (disk_path, image_size)
    ret = subprocess.run(cmd, shell=True)

    # mount the disk to loop device
    cmd = "losetup -fP %s" % disk_path
    ret = subprocess.run(cmd, shell=True)

    # get which loop device is used to mount the disk image
    cmd = "losetup -a | grep %s | awk -F ':' '{print $1}'" % DISK_NAME
    output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    return output


def get_partitions_details(image_size):
    """
    Partition 1 - vfat - for efi (500MB)
    Partition 2 - ext4 - for rootfs (image_size - efi - swap)
    Partition 3 - swap - 1024MB
    return: dictionary
    """
    # 1 500
    # 501 9215
    # 9216 10240
    efi_size = 500
    swap_size = 1024
    end_swap = image_size
    start_swap = end_swap - swap_size
    end_rootfs = start_swap - 1

    partitions = {
        "efi": {
            "start": 1,
            "end": 500,
            "format": "vfat",
            "flag": "boot"
        },
        "rootfs": {
            "start": 501,
            "end": end_rootfs,
            "format": "ext4"
        },
        "swap": {
            "start": start_swap,
            "end": end_swap,
            "format": "swap"
        }
    }
    return partitions

def create_partition(loop_device, disk_path, image_size):
    """
    Create a partition table such as gpt or msdos.
    If use UEFI, then create gpt partition.
    If use BIOS, then create msdos partition. This is not supported for now.
    Format the partition with vfat and ext4.
    Partition 1 - vfat - for efi (500MB)
    Partition 2 - ext4 - for rootfs (image_size - 500MB - swap)
    Partition 3 - swap - 1024MB
    """
    logger.info("Create GPT partition for %s", disk_path)

    # create gpt partition table
    cmd = "parted %s -s unit mb mktable gpt" % loop_device
    logger.debug("cmd: %s", cmd)
    ret, output = run_cmd(cmd)

    logger.debug("return value %s", ret)
    #if not ret:
    #    logger.error("Failed to create gpt partition for %s", disk_path)
    #    logger.error(output)
    #    cleanup_loop_device(loop_device)
    #    sys.exit(1)

    partitions = get_partitions_details(image_size)
    for key, value in partitions.items():
        logger.info("Create %s partition", key)
        start = value['start']
        end = value['end']
        cmd = "parted %s -s unit mb mkpart %s %s %s" % (loop_device, key, start, end)
        logger.debug("cmd: %s", cmd)
        ret, output = run_cmd(cmd)


def format_partition(loop_device, image_size):
    """
    Format the partitions according to get_partitions_details().
    """
    number = 1
    partitions = get_partitions_details(image_size)

    for key, value in partitions.items():
        lo_partition = loop_device + 'p' + str(number)
        logger.info("Formatting partition %s with %s", key, value['format'])

        if 'vfat' in value['format']:
            cmd = "mkfs.vfat %s" % lo_partition
        elif 'ext' in value['format']:
            cmd = "mkfs.%s %s" % (value['format'], lo_partition)
        elif 'swap' in value['format']:
            cmd = "mkswap %s" % lo_partition
        else:
            logger.error("Failed to format partition %s. Unknown partition format %s", number, value['format'])
            cleanup_loop_device(loop_device)
            sys.exit(1)

        logger.debug("cmd: %s", cmd)
        ret, output = run_cmd(cmd)
        #if not ret:
        #    logger.error("Failed to format the partition %s with format %s", number, value['format'])
        #    cleanup_loop_device(loop_device)
        #    sys.exit(1)

        # Set the boot partition
        if 'flag' in value and 'boot' in value['flag']:
            cmd = "parted %s set %s boot on" % (loop_device, number)
            logger.debug("cmd: %s", cmd)
            ret, output = run_cmd(cmd)
            #if not ret:
            #    logger.error("Failed to set the partition %s as boot partition", number)
            #    cleanup_loop_device(loop_device)
            #    sys.exit(1)

        number += 1


def show_partition_table(disk_path):
    """
    Show the partition table for given disk.
    """
    logger.info("Show partition table for %s", disk_path)
    cmd = "parted %s unit B -s print" % disk_path
    logger.debug("cmd: %s", cmd)
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    logger.info(output)


def prepare_rootfs(loop_device, project_directory, custom_root_directory,
        custom_disk_directory, kernel_version):
    """
    Copy the kernel, rootfs to disk image.
    Partition 1 - for efi
    Partition 2 - for rootfs
    Partition 3 - for swap
    """
    p1 = loop_device + 'p1'
    p2 = loop_device + 'p2'

    logger.info("Preparing rootfs")
    rootfs_directory = os.path.join(project_directory, "rootfs")
    boot_directory = os.path.join(rootfs_directory, "boot")
    make_directory(rootfs_directory)

    # mount the disk of partition 2
    cmd = "mount %s %s" % (p2, rootfs_directory)
    ret = subprocess.run(cmd, shell=True)

    # copy the rootfs from custom_root_directory to the rootfs_directory
    cmd = "rsync -a %s %s" % (custom_root_directory, rootfs_directory)
    subprocess.run(cmd, shell=True)

    # mount efi partition
    efi_path = os.path.join(boot_directory, "efi")
    make_directories(efi_path)
    cmd = "mount %s %s" % (p1, efi_path)
    subprocess.run(cmd, shell=True)

    # copy the kernel, efi and initrd
    #TODO: check if there is a new kernel and initrd installed.
    # If new kernel is installed, need to get the version from the config.json.
    # If no kernel installed then copy from custom_disk_directory

    copy_kernel(custom_disk_directory, custom_root_directory, boot_directory)
    copy_initrd(custom_disk_directory, custom_root_directory, boot_directory)

    # select kernel and initrd based on config.json and create symlink
    select_kernel_initrd(boot_directory, kernel_version)
    # update grub file


def cleanup_loop_device(loop_device):
    logger.info("Unmount loop device %s", loop_device)
    cmd = "losetup -d %s" % loop_device
    logger.debug("cmd: %s", cmd)
    subprocess.run(cmd, shell=True)


def cleanup(loop_device, project_directory):
    """
    Unmount all bind mount and losetup
    """
    rootfs_directory = os.path.join(project_directory, "rootfs")
    efi_path = os.path.join(rootfs_directory, "boot", "efi")
    logger.info("Clean up bind mount and losetup")

    # cleanup chroot environment
    #unmount_chroot(rootfs_directory)
    unmount(efi_path)
    unmount(rootfs_directory)

    cleanup_loop_device(loop_device)
