#!/usr/bin/python
import os, sys, socket

from commands import getoutput
from euca2ools import Euca2ool

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
        self.update_local()
        self.update_euca()

    def update_local(self):
        # obtain the compute node host name
        self._attrs['host_name'] = socket.gethostname()
            
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

    def update_euca(self):
        try:
            euca = Euca2ool()
        except Exception, e:
            print >> sys.stderr, e
            return

        conn = euca.make_connection()
        reservations = conn.get_all_instances(self._instance_id)

        reservation = None
        instance = None

        for r in reservations:
            for i in r.instances:
                if i.id == self._instance_id:
                    reservation = r
                    instance = i
                    break

        if instance:
            self._attrs['image_id'] = instance.image_id
            self._attrs['kernel'] = instance.kernel
            self._attrs['ramdisk'] = instance.ramdisk
            self._attrs['private_dns_name'] = instance.private_dns_name
            self._attrs['state'] = instance.state
            self._attrs['previous_state'] = instance.previous_state
            self._attrs['shutdown_state'] = instance.shutdown_state

            if instance.launch_time:
                self._attrs['launch_time'] = instance.launch_time

            if instance.instance_type:
                self._attrs['instance_type'] = instance.instance_type
 

    def show_details(self):
        print >> sys.stderr, 'instance id: %s' % self._instance_id
        print >> sys.stderr, 'username: %s' % self._username

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
