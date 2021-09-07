"""
Parser the config.json
"""

import os
import json
import re

from utilities.logger import create_logger
from utilities.util import run_cmd
from utilities.file_ops import make_directories

logger = create_logger(__name__)

def load_config(config_path):
    config = None
    if os.path.exists(config_path):
        f = open(config_path)
        config = json.load(f)

    return config


def get_packages_list(config, variant):
    """
    Return list of packages from the config
    """
    list_packagtes = None
    if 'packages' in config['variant'][variant]:
        list_packages = config['variant'][variant]['packages']

    return list_packages


def get_sources_list(config, variant):
    """
    Return list of sources from the config
    """
    sources_list = None
    if 'source_list' in config['variant'][variant]:
        sources_list = config['variant'][variant]['source_list']

    return sources_list


def get_kernel_overlays(config, variant):
    """
    Return list of kernel overlays url
    """
    kernel_overlays = None
    if 'kernel' in config['variant'][variant]:
        kernel_overlays = config['variant'][variant]['kernel']['overlays']

    return kernel_overlays


def get_kernel_version(config, variant):
    """
    Return kernel version from the config
    """
    version = None
    if 'kernel' in config['variant'][variant]:
        version = config['variant'][variant]['kernel']['version']
        
    return version


def get_cache_directory(config, variant):
    """
    Return cache directory from the config
    """
    cache_directory = None
    if 'cache' in config:
        cache_directory = config['cache']

    return cache_directory


def get_base_image_url(config, variant):
    """
    Return link of Ubuntu base image.
    If not defined then use the default base image
    """
    image = None
    if 'base_image' in config['variant'][variant]:
        image = config['variant'][variant]['base_image']
    else:
        image = config['base_image']

    return image


def get_base_image(config, variant):
    """
    Check base image from cache directory if exists.
    Else, download it to cache directory/base-image/<version>.
    """
    # get cache directory
    cache_directory = get_cache_directory(config, variant)

    # Get the base image name
    base_image_url = get_base_image_url(config, variant)
    image_iso = os.path.basename(base_image_url)
    image_version = '0.0'
    image_version = re.search(r'(\d+\.\d+)', image_iso)
    if image_version:
        image_version = image_version.group(0)

    cache_base_image_directory = os.path.join(cache_directory, 'base-image', image_version)
    base_image = os.path.join(cache_base_image_directory, image_iso)
    logger.info("base image in %s", base_image)

    if os.path.exists(base_image):
        logger.info("Base image %s exists in cache directory %s", image_iso, base_image)
        return base_image

        """
        # validate the checksums
        sha256sums = os.path.join(cache_base_image_directory, image_version, 'SHA256SUMS')
        if os.path.exists(sha256sums):
            cmd = "sha256sum -c %s" % sha256sums
            ret, output = run_cmd(cmd)

            if ret == 0:
                return base_image
        """

    make_directories(cache_base_image_directory)
    logger.info("Downloading %s", image_iso)
    cmd = "wget --directory-prefix=%s %s" % (cache_base_image_directory, base_image_url)
    logger.debug("cmd: %s", cmd)
    run_cmd(cmd)

    #base_image_path = os.path.dirname(base_image_url)
    #cmd = "wget --directory-prefix=%s %s" % (cache_base_image_directory, os.path.join(base_image_path, 'SHA256SUMS'))
    #logger.debug("cmd: %s", cmd)
    #run_cmd(cmd)

    return base_image


def get_image_types(config, variant):
    """
    Return the list of image type such as iso or img.
    The image type is the output format of generate image.
    """
    image_type = None
    if 'image_type' in config['variant'][variant]:
        image_type = config['variant'][variant]['image_type']
    else:
        image_type = config['image_type']

    return image_type


