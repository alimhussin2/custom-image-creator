#!/usr/bin/python3

import os
import re
import subprocess
import zlib

from utilities.logger import create_logger
from utilities.file_ops import make_directory, delete_directory
from utilities.util import run_cmd

logger = create_logger(__name__)

def mount(iso_file_path, iso_mount_point):
    """
    Mount the iso file to the mount point
    """
    if os.path.exists(iso_file_path):
        make_directory(iso_mount_point)
        user_id = 1000
        group_id = 1000
        cmd = ("mount --options loop,uid={user_id},gid={group_id} {iso_file_path} {iso_mount_point}").format(
            user_id=user_id,
            group_id=group_id,
            iso_file_path=iso_file_path,
            iso_mount_point=iso_mount_point
                )
        #program = '/usr/share/cubic/commands/mount-iso'
        #cmd = 'pkexec "%s" "%s" "%s" "%s" "%s"' % (program, iso_file_path, iso_mount_point, user_id, group_id)
        logger.debug(cmd)
        ret = subprocess.run(cmd, shell=True)
        ret = ret.returncode
    else:
        logger.error("File %s is not exists", iso_file_path)
        ret = 1
    return ret


def unmount(iso_mount_point):
    """
    Unmount a mount point
    """
    if os.path.ismount(iso_mount_point):
        logger.info("Unmount %s", iso_mount_point)
        cmd = "umount %s" % iso_mount_point
        logger.debug("cmd: %s", cmd)
        subprocess.run(cmd, shell=True)


def remove_mount_point(iso_mount_point):
    """
    Unmount and remove the mount point
    """
    if os.path.exists(iso_mount_point):
        ret = unmount(iso_mount_point)
        if ret == 0:
            logger.info("Successfully unmount %s", iso_mount_point)
            delete_directory(iso_mount_point)
        else:
            logger.error("Failed to unmount %s", iso_mount_point)


def get_iso_report(iso_file_path):
    """
    Get iso report

    -V 'Ubuntu 20.04.1 LTS amd64'
    --modification-date='2020073116511200'
    -isohybrid-mbr --interval:local_fs:0s-15s:zero_mbrpt,zero_gpt,zero_apm:'partition-1.img'
    -partition_cyl_align off
    -partition_offset 0
    --mbr-force-bootable
    -apm-block-size 2048
    -iso_mbr_part_type 0x00
    -c '/isolinux/boot.cat'
    -b '/isolinux/isolinux.bin'
    -no-emul-boot
    -boot-load-size 4
    -boot-info-table
    -eltorito-alt-boot
    -e '/boot/grub/efi.img'
    -no-emul-boot
    -boot-load-size 7936
    -isohybrid-gpt-basdat
    -isohybrid-apm-hfsplus
    """
    logger.info("Get iso report for %s", iso_file_path)
    cmd = "xorriso -indev %s -report_el_torito as_mkisofs" % iso_file_path
    ret, output = run_cmd(cmd)
    iso_report = ''.join(output.partition('-V')[1:])
    logger.info("The iso report is %s", iso_report)
    return iso_report


def generate_iso_template(iso_report, project_directory, iso_file_path):
    logger.info("Generate the ISO template")
    template = ''
    lines = iso_report.split(os.linesep)
    number = 1
    for line in lines:
        # remove '\r\n' at the end of each line
        line = line.strip()

        # Apply rules to create the template
        # remove the modification timestamp
        if line.startswith('--modification-date'):
            line = ''

        if '--interval' in line:
            image_file_name = "partition-%s.img" % number
            line = handle_interval_path(line, image_file_name, project_directory, iso_file_path)
            number += 1

        if '-part_like_isohybrid' in line:
            line = line.replace('-part_like_isohybrid', '-appended_part_as_gpt')

        if line:
            #template = template + line + os.linesep
            template = template + line + ' '

    return template


def handle_interval_path(line, image_file_name, project_directory, iso_file_path):
    """
    Update the interval path
    """

    if '--interval' not in line:
        return False, line

    logger.info("Interval path %s", line)

    # Format: interval:"Flags":"Interval":"Zeroizers":"Source"
    # [1] = text before
    # [ ] = --interval
    # [2] = 1st argument of interval (flags)
    # [3] = 2nd argument of interval (interval)
    # [4] = 3rd argument of interval (zeroizers)
    # [5] = 4th argument of interval (source)
    # [6] = text after

    result = re.search(r"(.*?)\s*--interval:(.*):(.*):(.*):('.*'|[^'\s]*)\s*(.*)", line)
    before = result[1].strip()
    flags = result[2].strip()
    interval = result[3].strip()
    zeroizers = result[4].strip()
    source = result[5].strip("'")
    after = result[6]

    if flags == "local_fs":
        # interval path:
        # flags     - unchanged
        # interval  -   changed
        # zeroizers - unchanged
        # source    -   changed

        # Get the interval information (range of bytes in the original ISO)

        interval_information = parse_interval(interval)
        if not interval_information:
            return line

        start_block, stop_block, block_count, block_units, block_size = interval_information

        # Get iso partition image file name
        image_file_path = os.path.join(project_directory, image_file_name)

        # Create the iso partition image file
        extract_image(iso_file_path, image_file_path, block_size, start_block, block_count)

        # Create a new interval using the original units.
        start_block = 0
        stop_block = block_count - 1
        interval = '{start}{units}-{stop}{units}'.format(start=start_block, stop=stop_block, units=block_units)

        # Get the source.
        source = "'%s'" % image_file_path
    
    elif flags.startswith('appended_partition'):
        # Interval path:
        # flags     -   changed
        # interval  - unchanged
        # zeroizers - unchanged
        # source    - unchanged

        # update the flags
        flags = re.search(r'(appended_partition_\d{0,3}).*', flags).group(1)

    else:
        return line

    # Correct spacing between quotes is critical.
    space_before, space_after = get_spacers(before, after)

    # Assemble the new line.
    line = "{before}{space_before}--interval:{flags}:{interval}:{zeroizers}:{source}{space_after}{after}".format(
        before=before,
        flags=flags,
        interval=interval,
        zeroizers=zeroizers,
        source=source,
        after=after,
        space_before=space_before,
        space_after=space_after)

    logger.info("New interval path %s", line)

    return line


def get_spacers(before, after):

    # Correct spacing between quotes is critical.
    if before and after and before[-1] == "'" and after[0] == "'":
        space_before = ''
        space_after = ''
    elif before and after:
        space_before = ' '
        space_after = ' '
    elif before and not after:
        space_before = ' '
        space_after = ''
    elif not before and after:
        space_before = ''
        space_after = ' '
    else:
        space_before = ''
        space_after = ''

    return space_before, space_after

def parse_interval(interval):
    """
    The interval references a range of bytes in the original ISO.
    """
    logger.info("The interval is %s", interval)
    start_block, stop_block = interval.split('-')

    # Get the start block
    result = re.search(r'(\d+)(\w*)', start_block)
    start_block = int(result.group(1))
    logger.info("The start block is %s", start_block)

    # Get the block units (k, m, g, t, s, d).
    block_units = result.group(2)
    logger.info("The block units are %s", block_units)

    # Get the block size.
    # Assume start block size is same as stop block size.
    # Units for xorriso command: 1024, 1024k, 1024m, 1024g, 2048, 512.
    MULTIPLES = {'k': 'KIB', 'm': 'MIB', 'g': 'GIB', 't': 'TIB', 's': 2048, 'd': 512}

    block_size = MULTIPLES.get(block_units, 1)
    logger.info("The block size is %s", block_size)

    # Get the stop block.
    result = re.search(r'(\d+)(\w*)', stop_block)
    stop_block = int(result.group(1))
    logger.info("The stop block is %s", stop_block)

    # Get the block count.
    block_count = stop_block - start_block + 1
    logger.info("The block count is %s", block_count)

    return start_block, stop_block, block_count, block_units, block_size


def extract_image(iso_file_path, image_file_path, block_size, skip_blocks, block_count):
    logger.info("Extract image")
    logger.info("Extract image from %s", iso_file_path)
    logger.info("Extract image to %s", image_file_path)
    
    cmd = ("dd if={input_file} of={output_file} bs={block_size} skip={skip_blocks} count={block_count}").format(
            input_file=iso_file_path,
            output_file=image_file_path,
            block_size=block_size,
            skip_blocks=skip_blocks,
            block_count=block_count
        )
    logger.debug("cmd: %s", cmd)
    ret, output = run_cmd(cmd)


def encode_iso(t):

    b = t.encode('utf-8')
    z = zlib.compress(b)
    h = z.hex().upper()

    return h

def decode_iso(h):

    z = bytes.fromhex(h)
    b = zlib.decompress(z)
    t = b.decode('utf-8')

    return t
