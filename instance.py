#!/usr/bin/python
import os, sys, socket

from commands import getoutput
from datetime import datetime
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
        self._last_updated = None
        self._attrs = dict()

        if update:
            self.update()

    def get_username(self):
        return self._username

    def get_instance_id(self):
        return self.instance_id

    def get_last_updated(self):
        return self._last_updated

    def get_attrs(self):
        return self._attrs

    def get_instance_path(self):
        return os.path.join(EUCA_LIB_PATH, 'instances', self._username, self._instance_id)

    def update(self):
        self.update_local()
        self.update_euca()

        self._last_updated = datetime.now()

    def update_local(self):
        # obtain the compute node host name
        try:
            self._attrs['host_name'] = socket.gethostname()
        except:
            self._attrs['host_name'] = 'unknown'
            
        # fetch mac address(es) from virsh
        try:
            self._attrs['mac_address'] = getoutput('virsh dumpxml %s | grep "mac address" | cut -d\\\' -f2' % self._instance_id).splitlines()[1:]
        except IndexError:
            pass        

        # check virsh for information about this instance
        try:
            data = getoutput('virsh list | grep "%s"' % self._instance_id).splitlines()[1].split()
            self._attrs['libvirt_id'] = data[0]
            self._attrs['libvirt_status'] = data[2]
        except IndexError:
            pass

        # read tail of console.log
        self._attrs['console_log'] = getoutput('tail %s' % os.path.join(self.get_instance_path(), 'console.log'))

    def update_euca(self):
        try:
            euca = Euca2ool()        
            conn = euca.make_connection()
            reservations = conn.get_all_instances(self._instance_id)
        except Exception, e:
            print >> sys.stderr, e
            return

        instance = None

        for r in reservations:
            for i in r.instances:
                if i.id == self._instance_id:
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
        print >> sys.stderr, 'last_updated: %s' % self._last_updated

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