#!/usr/bin/python
import os, sys
import socket
import fcntl
import struct

from commands import getoutput

EUCA_LIB_PATH = '/var/lib/eucalyptus/'

class Instance():
    """
    Gathers information about a Eucalyptus instance.
    Designed to work on compute notes configured with libvirt.
    """
    
    def __init__(self, username, instance_id, update=True):
        self._username = username
        self._instance_id = instance_id
        self._attrs = dict()

        if update:
            self.update()

    def get_username(self):
        return self._username

    def get_instance_id(self):
        return self.instance_id

    def get_attrs(self):
        return self._attrs

    def get_instance_path(self):
        return os.path.join(EUCA_LIB_PATH, 'instances', self._username, self._instance_id)

    def update(self):
        # obtain the compute node host name
        self._attrs['host_name'] = socket.gethostname()
            
        # obtain the compute node host ip
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._attrs['host_ip'] = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', 'eth0')
        )[20:24])
 
        # check local file system

        # TODO: support multiple mac addresses per instance.
        # the virsh call below will return one mac addresses
        # per adapater.

        # fetch mac address from virsh
        self._attrs['mac_address'] = getoutput('virsh dumpxml %s | grep "mac address" | cut -d\\\' -f2' % self._instance_id).splitlines()[1]
        
        # check virsh for information about this instance
        data = getoutput('virsh list | grep "%s"' % self._instance_id).splitlines()[1].split()
        
        self._attrs['libvirt_id'] = data[0]
        self._attrs['libvirt_status'] = data[2]

        # read tail of console.log
        self._attrs['console_log'] = getoutput('tail %s' % os.path.join(self.get_instance_path(), 'console.log'))

    def show_details(self):
        print >> sys.stderr, 'instance id: %s' % self._instance_id

        for key, value in self._attrs.iteritems():
            print >> sys.stderr, '\n%s:\n%s' % (key, value,)


def usage():
    print >> sys.stderr, 'Usage: python instance.py [euca username] [instance id]'

def main(argv=None):
    if len(argv) < 3:
        usage()
        return 1
        
    instance = Instance(argv[1], argv[2])
    instance.show_details()
        

if __name__ == "__main__":
    sys.exit(main(sys.argv))
