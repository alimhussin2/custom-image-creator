import os
import subprocess

from utilities.logger import create_logger
from utilities.file_ops import copy_to
from utilities.iso import unmount 
from utilities.constant import *
from utilities.util import run_cmd

logger = create_logger(__name__)

def prepare_customize_script(custom_root_directory):
    """
    Copy script to custom_root_directory to be invoked
    in the virtual environment
    """
    logger.info("Prepare customize script for virtual environment")
    # script is generated in entrypoint.d/entrypoint.sh
    base_path = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(base_path, ENTRYPOINT_DIRECTORY)

    dest_path = os.path.join(os.path.dirname(custom_root_directory), ENTRYPOINT_DIRECTORY)
    copy_to(source_path, dest_path)


def create_virtual_environment(custom_root_directory):
    """
    Spawn a container to host rootfs. This operation require
    superuser privilege.
    Bind the host's resolv.conf file to the container's resolv.conf as 
    read only.
    """
    #prepare_customize_script(custom_root_directory)
    logger.info("Create virtual environment")
    machine_name = "custom-ubuntu"
    bind_path = RESOLV_FILE
    script_directory = os.path.join(os.path.dirname(custom_root_directory), ENTRYPOINT_DIRECTORY)
    root_path = os.path.join(ROOT_USER_DIRECTORY, ENTRYPOINT_DIRECTORY)
    script_file = os.path.join(root_path, SCRIPT_ENTRYPOINT)

    cmd = (
        'sudo systemd-nspawn'
        ' --quiet'
        ' --notify-ready=yes'
        ' --register=yes'
        ' --bind-ro="{bind_path}"'
        ' --bind={script_directory}:{root_path}'
        ' --machine="{machine_name}"'
        ' --directory="{directory_path}"'
        ' /bin/bash "{script_file}"'
        ).format(
            bind_path=bind_path,
            script_directory=script_directory,
            root_path=root_path,
            machine_name=machine_name,
            directory_path=custom_root_directory,
            script_file=script_file,
        )

    logger.debug("cmd: %s", cmd)

    ret = subprocess.run(cmd, shell=True)
    ret = ret.returncode
    return ret


def prepare_chroot(custom_root_directory):
    """
    chroot into the custom_root_directory.
    """
    logger.info("Chroot into the %s", custom_root_directory)
    
    # mount /proc /dev /sys
    cmd = "mount -o bind /proc %s/proc" % custom_root_directory
    subprocess.run(cmd, shell=True)
    cmd = "mount -o bind /sys %s/sys" % custom_root_directory
    subprocess.run(cmd, shell=True)
    cmd = "mount -o bind /dev %s/dev" % custom_root_directory
    subprocess.run(cmd, shell=True)

    # chroot in
    #TODO: find a way to supply command to chroot
    cmd = "chroot %s /bin/bash" % custom_root_directory
    run_cmd(cmd)


def unmount_chroot(custom_root_directory):
    logger.info("Unmount chroot")
    unmount(os.path.join(custom_root_directory, "proc"))
    unmount(os.path.join(custom_root_directory, "sys"))
    unmount(os.path.join(custom_root_directory, "dev"))
