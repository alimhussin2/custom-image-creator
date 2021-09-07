"""
Create iso image

do_image() - wrapper to create iso image
create_squashfs() - compress Linux file system
update_filesystem_size() - calculate size of filesystem and write it to filesystem.size.
update_checksum()
create_iso_image()
"""

import os
import subprocess

from utilities.util import run_cmd, get_rootfs_size_bytes, calculate_checksums
from utilities.logger import create_logger
from utilities.kernel import get_kernel_initrd, update_boot_configuration
from utilities.file_ops import copy_to
from utilities.iso import get_iso_report, generate_iso_template

logger = create_logger(__name__)

def do_iso_image(project_directory, iso_file_path, output_iso_path,
        custom_root_directory, custom_disk_directory, kernel_version):
    """
    Wrapper steps to create iso image
    """
    prepare_kernel(custom_root_directory, custom_disk_directory, kernel_version)
    update_boot_configuration(custom_disk_directory)
    create_squashfs(custom_root_directory, custom_disk_directory)
    update_filesystem_size(custom_root_directory, custom_disk_directory)
    update_checksums(custom_disk_directory)
    create_iso_image(project_directory, custom_disk_directory, iso_file_path, output_iso_path)
    calculate_checksums(output_iso_path)


def prepare_kernel(custom_root_directory, custom_disk_directory, kernel_version):
    """
    If new kernel is installed then
    copy vmlinuz and initrd to casper directory in custom_disk_directory.
    The initrd renamed to initrd
    """
    # get vmlinuz and initrd path based on kernel_version
    kernel_path = get_kernel_initrd(custom_disk_directory, custom_root_directory, kernel_version)

    # default vmlinuz and initrd
    target_vmlinuz_path = os.path.join(custom_disk_directory, 'casper', 'vmlinuz')
    target_initrd_path = os.path.join(custom_disk_directory, 'casper', 'initrd')

    # If it is new vmlinuz and initrd, then copy to custom disk
    if kernel_path['vmlinuz'] != target_vmlinuz_path:
        # remove existing vmlinuz and copy new vmlinuz file
        os.remove(target_vmlinuz_path)
        copy_to(kernel_path['vmlinuz'], target_vmlinuz_path)

    if kernel_path['initrd'] != target_initrd_path:
        # remove existing initrd and copy new initrd file
        os.remove(target_initrd_path)
        copy_to(kernel_path['initrd'], target_initrd_path)


def create_squashfs(custom_root_directory, custom_disk_directory):
    logger.info("Compress the Linux file system")
    logger.info("Source path is %s", custom_root_directory)

    target_path = os.path.join(custom_disk_directory, 'casper', 'filesystem.squashfs')
    logger.info("Target path is %s", target_path)

    # create filesystem.squashfs
    compression = "gzip"
    cmd = (
            "mksquashfs {source_path} {target_path}"
            " -noappend"
            " -comp {compression}"
            " -wildcards"
            " -e 'proc/*'"
            " -e 'proc/.*'"
            " -e 'run/*'"
            " -e 'run/.*'"
            " -e 'tmp/*'"
            " -e 'tmp/.*'"
            " -e 'var/crash/*'"
            " -e 'var/crash/.*'"
            " -e 'swapfile'"
            " -e 'root/.bash_history'"
            " -e 'root/.cache'"
            " -e 'root/.wget-hsts'"
            " -e 'home/*/.bash_history'"
            " -e 'home/*/.cache'"
            " -e 'home/*/.wget-hsts'"
        ).format(
            source_path=custom_root_directory,
            target_path=target_path,
            compression=compression
        )
    run_cmd(cmd)


def update_filesystem_size(custom_root_directory, custom_disk_directory):
    """
    Calculate the filesystem size and write to filesystem.size.
    This file is needed by installer
    """
    filesystem_size = get_rootfs_size_bytes(custom_root_directory)
    file_path = os.path.join(custom_disk_directory, "casper", "filesystem.size")
    with open(file_path, 'w') as f:
        f.write("%s" % filesystem_size)


def update_checksums(custom_disk_directory):
    logger.info("Update checksums")
    checksums_file_path = os.path.join(custom_disk_directory, "md5sum.txt")
    cmd = "find %s -type f -print0 | sudo xargs -0 md5sum | grep -v %s/isolinux/boot.cat" % (custom_disk_directory, custom_disk_directory)

    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    new_output = output.replace(custom_disk_directory, '.')

    #TODO: need to use relative path instead of absolute path
    with open(checksums_file_path, 'w') as f:
        f.write(new_output)


def create_iso_image(project_directory, custom_disk_directory, iso_file_path, output_iso_path):
    logger.info("Create disk image")
    iso_report = get_iso_report(iso_file_path)
    template = generate_iso_template(iso_report, project_directory, iso_file_path)
    cmd = (
            'xorriso ' \
            ' -as mkisofs ' \
            ' -r' \
            ' -J' \
            ' -joliet-long' \
            ' -l' \
            ' -iso-level 3' \
            ' {template}' \
            ' -o "{output}" {custom_disk_directory}'
        ).format(
            template=template,
            output=output_iso_path,
            custom_disk_directory=custom_disk_directory
        )
    logger.debug("cmd: %s", cmd)
    subprocess.run(cmd, shell=True)
    #run_cmd(cmd)
