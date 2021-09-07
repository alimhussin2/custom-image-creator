#!/usr/bin/python3

import os
import subprocess
import shutil

from utilities.logger import create_logger
from utilities.file_ops import get_directory_for_file

logger = create_logger(__name__)

def get_casper_directory(iso_mount_point, custom_disk_directory):
    found = False
    casper_directory = None
    logger.info("Find the compressed Linux file system")
    if not found:
        try:
            directory = get_directory_for_file('filesystem.squashfs', iso_mount_point)
            casper_directory = os.path.relpath(directory, iso_mount_point)
            logger.debug("The compressed Linux file system directory is %s", casper_directory)
            found = True
        except ValueError as exception:
            logger.error("Unable to find the compressed Linux file system in %s", iso_mount_point)

    # look for the casper relative directory in the custom disk directory
    if not found:
        try:
            directory = get_directory_for_file('filesystem.squashfs', custom_disk_directory)
            casper_directory = os.path.relpath(directory, custom_disk_directory)
            logger.debug("The compressed Linux file system directory is %s", casper_directory)
            found = True
        except ValueError as exception:
            logger.error("Unable to find the compressed Linux file system in %s", custom_disk_directory)

    return casper_directory


def copy_original_iso_files(iso_mount_point, custom_disk_directory):
    logger.info("Copy original disk image")
    source_path = os.path.join(iso_mount_point, '')
    logger.info("The source path is %s", source_path)

    target_path = os.path.join(custom_disk_directory, '')
    logger.info("The target path is %s", target_path)

    casper_directory = get_casper_directory(iso_mount_point, custom_disk_directory)

    # Copy files from the original iso.
    # Exclude or copy the following files as indicated.
    #
    # do not copy: /md5sum.txt
    # do not copy: /MD5SUMS (for Linux Mint)
    # do not copy: /casper/filesystem.manifest
    # ~ ~ ~  copy: /casper/filesystem.manifest-remove
    # ~ ~ ~  copy: /casper/filesystem.manifest-minimal-remove
    # do not copy: /casper/filesystem.size
    # do not copy: /casper/filesystem.squashfs
    # do not copy: /casper/filesystem.squashfs.gpg
    # ~ ~ ~  copy: /casper/initrd
    # ~ ~ ~  copy: /casper/vmlinuz
    #
    # Some important rsync options:
    #
    #   -rlptgoD
    #
    #     -r --recursive
    #     -l --links
    #     -p --perms (do not use)
    #     -t --times
    #     -g --group
    #     -O --owner
    #     -D --devices --specials

    # Use info=progress2 to get the total progress, instead of the
    # progress for individual files.
    # Add read and write permissions for the user.
    # Set read and write permissions for group and other.
    cmd = (
        'rsync'
        ' --info=progress2 "{source_path}" "{target_path}"'
        ' --delete'
        # ' --archive'
        ' --recursive'
        ' --links'
        ' --chmod=u+rwX,g=rX,o=rX'
        ' --exclude="md5sum.txt"'
        ' --exclude="MD5SUMS"'
        ' --exclude=".disk/release_notes_url"'
        ' --exclude="/{casper_directory}/filesystem.manifest"'
        ' --exclude="/{casper_directory}/filesystem.size"'
        ' --exclude="/{casper_directory}/filesystem.squashfs"'
        ' --exclude="/{casper_directory}/filesystem.squashfs.gpg"').format(
            source_path=source_path,
            target_path=target_path,
            casper_directory=casper_directory)
    logger.debug(cmd)
    ret = subprocess.run(cmd, shell=True)
    return ret.returncode


def extract_squashfs(iso_mount_point, custom_root_directory):
    logger.info("Extract the compressed Linux file system")
    target_path = custom_root_directory
    logger.info("Target path is %s", target_path)

    casper_directory = get_casper_directory(iso_mount_point, custom_root_directory)
    source_path = os.path.join(iso_mount_point, casper_directory, 'filesystem.squashfs')
    logger.info("Source path is %s", source_path)

    if os.path.exists(source_path):
        if os.path.exists(target_path):
            shutil.rmtree(target_path)

        cmd = "unsquashfs -dest %s %s" % (target_path, source_path)
        ret = subprocess.run(cmd, shell=True)
        ret = ret.returncode
    else:
        logger.error("Source path %s is not exists", source_path)
        ret = 1

    return ret
