#!/usr/bin/python3

import os
import shutil
import sys

from utilities.logger import create_logger

logger = create_logger(__name__)

def make_directory(directory):
    """
    Create a single directory
    """
    logger.info("Create directory %s", directory)
    if not os.path.exists(directory):
        os.mkdir(directory)
    else:
        logger.warning("Cannot create directory %s. Directory already exists", directory)


def make_directories(file_path):
    """
    Create all directories in the specific file path
    """
    logger.info("Create all directories in the path %s", file_path)
    if not os.path.exists(file_path):
        os.makedirs(file_path, exist_ok=True)
    else:
        logger.warning("Cannot create directories %s. The directory already exists", file_path)


def delete_directory(directory):
    """
    Remove the given directory
    """
    logger.info("Delete directory %s", directory)
    if os.path.exists(directory):
        try:
            shutil.rmtree(directory)
        except OSError as exception:
            logger.error("Exception %s", exception)
    else:
        logger.warning("Cannot delete directory %s. Directory does not exists", directory)


def get_directory_for_file(file_name, start_path):
    logger.info("Get directory for %s in %s", file_name, start_path)
    directory = ''
    # The directory may be a symlink
    for dirpath, dirnames, file_names in os.walk(start_path, followlinks=True):
        if file_name in file_names:
            directory = dirpath
            break

    if directory:
        logger.info("%s is in %s", file_name, directory)
    else:
        logger.info("%s is not in %s", file_name, directory)

    return directory


def get_directory_file_list(target_file_name, start_path):
    logger.info("Get file path for %s in %s", target_file_name, start_path)
    files_path = []
    
    for dirpath, dirnames, file_names in os.walk(start_path):
        for file_name in file_names:
            if target_file_name in file_name:
                full_path = os.path.join(dirpath, file_name)
                if not os.path.islink(full_path):
                    files_path.append(full_path)

    return files_path

def copy_to(source_path, dest_path):
    logger.info("Copy file")
    logger.info("Source path %s", source_path)
    logger.info("Destination path %s", dest_path)
    if os.path.exists(source_path):
        if os.path.isfile(source_path):
            shutil.copy(source_path, dest_path)
        else:
            shutil.copytree(source_path, dest_path)
    else:
        logger.error("Source file %s is not exists", source_path)
        sys.exit(1)
