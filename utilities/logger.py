#!/usr/bin/python3

import logging

def create_logger(name):
    logger = logging.getLogger(name)
    logger_handler = logging.StreamHandler()
    logger_format = logging.Formatter('%(levelname)s: %(message)s')
    logger_handler.setFormatter(logger_format)
    logger_handler.setLevel(logging.DEBUG)
    logger.addHandler(logger_handler)
    logger.setLevel(logging.DEBUG)
    return logger
