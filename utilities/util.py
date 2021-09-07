import os
import json
import subprocess

from utilities.logger import create_logger

logger = create_logger(__name__)

def run_cmd(cmd, shell=True):
    """
    Wrapper for subprocess
    """
    sout = subprocess.PIPE
    serr = subprocess.STDOUT

    process = subprocess.Popen(cmd, shell=shell, stdout=sout, stderr=serr)
    sout, serr = process.communicate()
    # combine stdout and stderr, filter None and decode
    out = ''.join([out.decode('utf-8') for out in [sout, serr] if out])

    return process.returncode, out


def get_rootfs_size_bytes(custom_root_directory):
    """
    Calculate the size of rootfs and return in bytes.
    """
    logger.info("Calculate rootfs in %s", custom_root_directory)
    cmd = "du --block-size=1 --summarize %s | awk '{print $1}'" % custom_root_directory
    output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    logger.info("The rootfs size is %s bytes", output)
    return output


def calculate_checksums(file_path):
    """
    Calculate file checksums and create a file
    """
    logger.info("Calculate checksums for %s", file_path)
    if os.path.exists(file_path):
        cmd = "md5sum %s" % file_path
        ret, output = run_cmd(cmd)
        output = output.replace(os.path.dirname(file_path) + '/', '')
        md5sum_file = file_path + '.md5sums'
        with open(md5sum_file, 'w') as f:
            f.write(output)

        logger.info("md5sums %s", output)


def load_config(config_path):
    config = None
    if os.path.exists(config_path):
        f = open(config_path)
        config = json.load(f)

    return config


def get_proxy(file_path):
    """
    Get sting of proxy setting in proxy.json
    """
    proxy = ''
    if file_path == None or file_path == '':
        return False, proxy

    if os.path.exists(file_path):
        proxy_setting = load_config(file_path)
        for key, value in proxy_setting.items():
            data = ("{key}='{value}'\n").format(key=key, value=value)
            #logger.info(data)
            proxy += data
        return True, proxy

    else:
        return False, proxy


def set_apt_proxy(file_path, custom_root_directory):
    """
    Set the apt proxy configuration in <custom_root_directory>/etc/apt/apt.conf.d/
    """
    proxy = ''
    rel_proxy_path = "etc/apt/apt.conf.d/my_proxy"
    proxy_path = os.path.join(custom_root_directory, rel_proxy_path)

    if file_path == None or file_path == '':
        return

    if os.path.exists(file_path):
        proxy_setting = load_config(file_path)
        for key, value in proxy_setting.items():
            if 'http' == key:
                proxy += 'Acquire::http::proxy "%s";\n' % value

            if 'https' == key:
                proxy += 'Acquire::https::proxy "%s";\n' % value

        with open(proxy_path, 'w') as f:
            f.write(proxy)


def remove_apt_proxy(custom_root_directory):
    rel_proxy_path = "etc/apt/apt.conf.d/my_proxy"
    proxy_path = os.path.join(custom_root_directory, rel_proxy_path)

    if os.path.exists(proxy_path):
        os.remove(proxy_path)
        logger.info("Removing proxy file %s", proxy_path)
