#!/usr/bin/python
#
# Copyright 2015 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requires Python 2.4+


import os
import os.path
import sys
import imp
import base64
import re
import json
import platform
import shutil
import time
import traceback
import datetime
import subprocess
import inspect

from AbstractPatching import AbstractPatching
from Common import *
from CommandExecutor import *

class redhatPatching(AbstractPatching):
    def __init__(self, logger, distro_info):
        super(redhatPatching, self).__init__(distro_info)
        self.logger = logger
        self.command_executor = CommandExecutor(logger)
        self.distro_info = distro_info
        if distro_info[1].startswith("6."):
            self.base64_path = '/usr/bin/base64'
            self.bash_path = '/bin/bash'
            self.blkid_path = '/sbin/blkid'
            self.cat_path = '/bin/cat'
            self.cryptsetup_path = '/sbin/cryptsetup'
            self.dd_path = '/bin/dd'
            self.e2fsck_path = '/sbin/e2fsck'
            self.echo_path = '/bin/echo'
            self.getenforce_path = '/usr/sbin/getenforce'
            self.setenforce_path = '/usr/sbin/setenforce'
            self.lsblk_path = '/bin/lsblk' 
            self.lsscsi_path = '/usr/bin/lsscsi'
            self.mkdir_path = '/bin/mkdir'
            self.mount_path = '/bin/mount'
            self.openssl_path = '/usr/bin/openssl'
            self.resize2fs_path = '/sbin/resize2fs'
            self.touch_path = '/bin/touch'
            self.umount_path = '/bin/umount'
        else:
            self.base64_path = '/usr/bin/base64'
            self.bash_path = '/usr/bin/bash'
            self.blkid_path = '/usr/bin/blkid'
            self.cat_path = '/bin/cat'
            self.cryptsetup_path = '/usr/sbin/cryptsetup'
            self.dd_path = '/usr/bin/dd'
            self.e2fsck_path = '/sbin/e2fsck'
            self.echo_path = '/usr/bin/echo'
            self.getenforce_path = '/usr/sbin/getenforce'
            self.setenforce_path = '/usr/sbin/setenforce'
            self.lsblk_path = '/usr/bin/lsblk'
            self.lsscsi_path = '/usr/bin/lsscsi'
            self.mkdir_path = '/usr/bin/mkdir'
            self.mount_path = '/usr/bin/mount'
            self.openssl_path = '/usr/bin/openssl'
            self.resize2fs_path = '/sbin/resize2fs'
            self.touch_path = '/usr/bin/touch'
            self.umount_path = '/usr/bin/umount'

    def install_extras(self):
        epel_packages_installed = False
        attempt = 0

        while not epel_packages_installed:
            attempt += 1
            self.logger.log("Attempt #{0} to locate EPEL packages".format(attempt))
            if self.distro_info[1].startswith("6."):
                if self.command_executor.Execute("rpm -q ntfs-3g python-pip"):
                    epel_cmd = "yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm"

                    if self.command_executor.Execute("rpm -q epel-release"):
                        self.command_executor.Execute(epel_cmd)

                    self.command_executor.Execute("yum install -y ntfs-3g python-pip")

                    if not self.command_executor.Execute("rpm -q ntfs-3g python-pip"):
                        epel_packages_installed = True
                else:
                    epel_packages_installed = True
            else:
                if self.command_executor.Execute("rpm -q ntfs-3g python2-pip"):
                    epel_cmd = "yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm"

                    if self.command_executor.Execute("rpm -q epel-release"):
                        self.command_executor.Execute(epel_cmd)

                    self.command_executor.Execute("yum install -y ntfs-3g python2-pip")

                    if not self.command_executor.Execute("rpm -q ntfs-3g python2-pip"):
                        epel_packages_installed = True
                else:
                    epel_packages_installed = True

        packages = ['cryptsetup',
                    'lsscsi',
                    'psmisc',
                    'cryptsetup-reencrypt',
                    'lvm2',
                    'uuid',
                    'at',
                    'patch',
                    'procps-ng',
                    'util-linux',
                    'gcc',
                    'libffi-devel',
                    'openssl-devel',
                    'python-devel',
                    'nmap-ncat']

        if self.distro_info[1].startswith("6."):
            packages.remove('cryptsetup')
            packages.remove('procps-ng')
            packages.remove('util-linux')

        if self.command_executor.Execute("rpm -q " + " ".join(packages)):
            self.command_executor.Execute("yum install -y " + " ".join(packages))

        if self.command_executor.Execute("pip show adal"):
            self.command_executor.Execute("pip install --upgrade six")
            self.command_executor.Execute("pip install adal")

    def update_prereq(self):
        if self.distro_info[1] in ["7.2", "7.3", "7.4"]:
             # Execute unpatching commands only if all the three patch files are present.
            if os.path.exists("/lib/dracut/modules.d/90crypt/cryptroot-ask.sh.orig"):
                if os.path.exists("/lib/dracut/modules.d/90crypt/module-setup.sh.orig"):
                    if os.path.exists("/lib/dracut/modules.d/90crypt/parse-crypt.sh.orig"):
                        redhatPatching.create_autounlock_initramfs(self.logger, self.command_executor)

    @staticmethod
    def append_contents_to_file(contents, path):
        with open(path, 'a') as f:
            f.write(contents)

    @staticmethod
    def create_autounlock_initramfs(logger, command_executor):
        logger.log("Removing patches and recreating initrd image")

        scriptdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        ademoduledir = os.path.join(scriptdir, '../oscrypto/91ade')
        dracutmodulesdir = '/lib/dracut/modules.d'
        udevaderulepath = os.path.join(dracutmodulesdir, '91ade/50-udev-ade.rules')

        proc_comm = ProcessCommunicator()

        command_executor.Execute('cp -r {0} /lib/dracut/modules.d/'.format(ademoduledir), True)

        crypt_cmd = "cryptsetup status osencrypt | grep device:"
        command_executor.ExecuteInBash(crypt_cmd, communicator=proc_comm, suppress_logging=True)
        matches = re.findall(r'device:(.*)', proc_comm.stdout)
        if not matches:
            raise Exception("Could not find device in cryptsetup output")
        root_device = matches[0].strip()

        udevadm_cmd = "udevadm info --attribute-walk --name={0}".format(root_device)
        command_executor.Execute(command_to_execute=udevadm_cmd, raise_exception_on_failure=True, communicator=proc_comm)
        matches = re.findall(r'ATTR{partition}=="(.*)"', proc_comm.stdout)
        if not matches:
            raise Exception("Could not parse ATTR{partition} from udevadm info")
        partition = matches[0]
        sed_cmd = 'sed -i.bak s/ENCRYPTED_DISK_PARTITION/{0}/ "{1}"'.format(partition, udevaderulepath)
        command_executor.Execute(command_to_execute=sed_cmd, raise_exception_on_failure=True)

        command_executor.Execute('mv /lib/dracut/modules.d/90crypt/cryptroot-ask.sh.orig /lib/dracut/modules.d/90crypt/cryptroot-ask.sh', False)
        command_executor.Execute('mv /lib/dracut/modules.d/90crypt/module-setup.sh.orig /lib/dracut/modules.d/90crypt/module-setup.sh', False)
        command_executor.Execute('mv /lib/dracut/modules.d/90crypt/parse-crypt.sh.orig /lib/dracut/modules.d/90crypt/parse-crypt.sh', False)
        
        sed_grub_cmd = "sed -i.bak '/rd.luks.uuid=osencrypt/d' /etc/default/grub"
        command_executor.Execute(sed_grub_cmd)
    
        redhatPatching.append_contents_to_file('\nGRUB_CMDLINE_LINUX+=" rd.debug"\n', 
                                               '/etc/default/grub')

        redhatPatching.append_contents_to_file('osencrypt UUID=osencrypt-locked none discard,header=/osluksheader\n',
                                               '/etc/crypttab')

        command_executor.Execute('/usr/sbin/dracut -I ntfs-3g -f -v', True)
        command_executor.Execute('grub2-mkconfig -o /boot/grub2/grub.cfg', True)