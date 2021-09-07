Ubuntu Custom Image Creator
===========================

Tools used to custom Ubuntu image such as installing new kernel and userspace packages.
This tool need supersuser privilege. Make sure run with `sudo`.

Quick Run
---------
Example to customize Ubuntu 21.04 with kernel 5.10 and install some usespace packages.
For more detail on type `$ sudo ./build_image.py -h`.

Prerequisite
------------
If you are behind the proxy, create a `proxy.json` file in any directory.
For example creating in `$HOME/ubuntu-project/proxy.json`
See the template of `proxy.json` in this repository to set the proxy.

1. Rebuild ISO image with proxy \
`$ sudo ./build_image.py $HOME/ubuntu-project config.json -p custom_ubuntu_21.04-kernel-5.10 -t ubuntu-21.04-custom -p $HOME/ubuntu-project/proxy.json`

OR

1. Rebuild ISO image without proxy \
`$ sudo ./build_image.py $HOME/ubuntu-project config.json -p custom_ubuntu_21.04-kernel-5.10 -t ubuntu-21.04-custom`

2. Flash the image to USB pendrive \
`$ sudo dd if=$HOME/project/custom_ubuntu_21.04-kernel-5.10/<ubuntu>.iso of=<device> status=progress`


Build Steps
-----------
1. Download kernel overlays
2. Download Ubuntu based image
3. Extract Ubuntu based image
4. Install kernel overlays
5. Add source list
6. Install user space packages
7. Compress the custom image

Config file
-----------
- config name:
 - kernel overlay url:
 - Ubuntu based url:
 - source list:
 - list of userspace packages:
 - compress format:

Build Steps Details
-------------------
1. Download kernel overlays
- The kernel overlay
- linux-headers
- linux-image
- linux-image-dbg
- linux-libc-dev
- kernel.config

2. Download Ubuntu based image
- Download from official Ubuntu website

3. Extract Ubuntu based image
- Ubuntu ISO image is mounted to source-disk
- Copy Ubuntu rootfs to custom-disk
- Copy Kernel Overlay to custom-root

4. Enter chroot/container
5. Install kernel overlays
6. Add source list
7. Install userspace packages
8. Exit from chroot/container
9. Overwrite the metadata, manifest
10. Compress the custom image
11. Calculate MD5sum of the generated custom image


File Structure
--------------
project_directory
- custom-disk
- custom-root
  - /boot/efi
    - EFI
  - /root
    - entrypoint.d
- source-disk
- rootfs
- entrypoint.d
  - entrypoint.sh
  - install_kernel.sh
  - install_packages.sh
