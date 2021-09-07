#!/usr/bin/python3

import os
import argparse
import subprocess
import sys

from utilities.iso import mount, unmount
from utilities.file_ops import make_directory, make_directories, delete_directory
from utilities.logger import create_logger
from utilities.extract import copy_original_iso_files, extract_squashfs
from utilities.container import create_virtual_environment
from utilities.create_scripts import add_sources_list, do_script 
from utilities.metadata import modify_release_description, create_filesystem_manifest
from utilities.image_iso import do_iso_image
from utilities.util import remove_apt_proxy
from utilities.parser import *

logger = create_logger(__name__)

def parser():
    description = """\
            Creating custom Ubuntu image with ISO format.
            Customization such as installing new kernel and userspace packages.
            """
    ap = argparse.ArgumentParser(description=description)

    # Positional arguments
    proj_dir = ap.add_argument('project_directory', action='store', default=None,
            help='Where this project should be stored')

    config = ap.add_argument('configuration', action='store', default=None,
            help='Path to config.json')

    # Optional arguments
    ap.add_argument('-d', '--debug', action='store_true',
            help='Show debug message')

    proj_name = ap.add_argument('-p', '--project-name', action='store', default='my_project',
            required=False,
            help="Name of this project. Default is 'my_project'")

    config_variant = ap.add_argument('-t', '--variant', action='store', default='default',
            required=False,
            help="Configuration variant to use to build the custom image from config.json. Default is 'default'")

    output_image = ap.add_argument('-o', '--output-file', action='store', default='',
            required=False,
            help="Path for output image name. Default is '<iso_image_name>-custom.iso' and the output image will be stored in project directory")

    proxy = ap.add_argument('-P', '--proxy', action='store', default=None, required=False,
            help="Proxy setting in json format.")

    keep = ap.add_argument('-k', '--keep-project', action='store_true',
            help="Keep the project files.")

    return ap.parse_args()


def do_cleanup(project_directory, output_image):
    """
    Remove all of the project files after
    creating the custom image.
    """
    if project_directory in output_image:
        temp_dir = os.path.join(os.path.dirname(project_directory), 'temp_dir')
        os.rename(project_directory, temp_dir)
        make_directory(project_directory)

        output_path = os.path.dirname(output_image)
        files = os.listdir(temp_dir)
        for f in files:
            if f.endswith('.iso') or f.endswith('.md5sums'):
                src = os.path.join(temp_dir, f)
                dst = os.path.join(output_path, f)
                os.rename(src, dst)
        delete_directory(temp_dir)

    else:
        delete_directory(project_directory)


def run():
    project_name = None
    project_directory = None
    variant = None
    proxy_path = None
    configuration_path = None
    output_iso_path = None
    keep_project = None

    args = parser()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Set logger level to DEBUG")

    if args.project_name:
        project_name = args.project_name
        logger.info("project name is %s", project_name)

    if args.project_directory:
        project_directory = os.path.join(args.project_directory, project_name)
        logger.info("project directory is %s", project_directory)

    if args.variant:
        variant = args.variant
        logger.info("variant is %s", variant)

    if args.configuration:
        logger.info("configuration path is %s", args.configuration)
        configuration_path = args.configuration
    else:
        configuration_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), args.configuration)

    config = load_config(configuration_path)
    if not config:
        logger.error("Configuration file is not found at %s", configuration_path)
        sys.exit(1)

    # get path to ubuntu iso image
    iso_file_path = get_base_image(config, variant)
    if args.output_file:
        if not '/' in args.output_file:
            output_iso_path = os.path.join(project_directory, args.output_file)
        else:
            output_iso_path = args.output_file
    else:
        input_iso_image = os.path.basename(iso_file_path)
        images_types = get_image_types(config, variant)
        output_iso_image = None
        for image_type in images_types.split(' '):
            if 'iso' in image_type:
                output_iso_image = input_iso_image.replace('.iso', '-custom.iso')
                break
        output_iso_path = os.path.join(project_directory, output_iso_image)

    logger.info("Output image is %s", output_iso_path)

    if args.proxy:
        proxy_path = args.proxy
        logger.info("proxy path: %s", proxy_path)

    if args.keep_project:
        keep_project = True

    iso_mount_point = os.path.join(project_directory, "source-disk")
    custom_disk_directory = os.path.join(project_directory, "custom-disk")
    custom_root_directory = os.path.join(project_directory, "custom-root")

    logger.info("iso mount point: %s", iso_mount_point)
    logger.info("custom disk directory: %s", custom_disk_directory)
    logger.info("custom root directory: %s", custom_root_directory)

    kernel_version = get_kernel_version(config, variant)

    # create project path
    make_directories(project_directory)

    # mount iso image, extract rootfs
    ret = mount(iso_file_path, iso_mount_point)
    if ret > 0:
        logger.error("mount failed, ret: %s", ret)
        sys.exit(2)

    copy_original_iso_files(iso_mount_point, custom_disk_directory)
    extract_squashfs(iso_mount_point, custom_root_directory)

    # unmount source-disk
    unmount(iso_mount_point)
    target_directory = project_directory

    sources_list = get_sources_list(config, variant)
    if sources_list:
        add_sources_list(target_directory, sources_list)

    # prepare script for installing kernel and userspace packages in chroot/container
    packages_list = get_packages_list(config, variant)
    urls = get_kernel_overlays(config, variant)

    # generate installing packages, kernel scripts
    do_script(target_directory, packages_list, urls, kernel_version, proxy_path)

    # spawn the chroot
    create_virtual_environment(custom_root_directory)

    # exit from chroot
    remove_apt_proxy(custom_root_directory)

    # modify metadata such as release description, manifest outside of chroot
    modify_release_description(custom_root_directory)
    create_filesystem_manifest(custom_root_directory, custom_disk_directory)

    # create image
    images_types = get_image_types(config, variant)
    for image_type in images_types.split(' '):
        if 'iso' in image_type:
            # create image with iso format
            do_iso_image(project_directory, iso_file_path, output_iso_path,
                custom_root_directory, custom_disk_directory, kernel_version)

        else:
            logger.error("Unknown image type %s", image_type)

    unmount(iso_mount_point)

    # clean up the project directory
    if not keep_project:
        do_cleanup(project_directory, output_iso_path)


if __name__ == '__main__':
    run()
    sys.exit(0)

