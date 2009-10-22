#!/usr/bin/python
import os, sys, socket

from commands import getoutput
from datetime import datetime
from euca2ools import Euca2ool
from settings import *
from syslog_client import syslog, LEVEL

class Instance():
    """
    Gathers information about a Eucalyptus instance.
    Designed to work on compute notes configured with libvirt.
    """
    
    def __init__(self, username, instance_id, update=True):
        self.id = instance_id
        self.username = username
        self.last_updated = None
        self.terminated = False
        self._attrs = dict()
        self._create_log_hardlink()
        
        if update:
            self.update()
    
    def _create_log_hardlink(self):
        """
        Create a hardlink to the instance's console.log so that
        when an instance is torn down, the log is never lost.
        """
        source = os.path.join(self.get_instance_path(), 'console.log')
        target = os.path.join(EUCA_LOG_PATH, self.id + '.log')
        
        # If the hard link already exists, return.
        if os.path.exists(target):
            return
        
        # Ensure the log path exists.
        if not os.path.exists(EUCA_LOG_PATH):
            os.makedirs(EUCA_LOG_PATH)
        
        # Ensure the console.log file exists.
        if not os.path.exists(source):
            open(source, 'a').close()
        
        # Create the hard link.
        os.link(source, target)
    
    def _log_change(self, key, value):
        """
        Used to log attribute changes to the syslog server.
        """
        self._log('%s changed to %s' % (key, value,))
    
    def _log(self, message, level=LEVEL.notice):
        """
        Logs a message to the syslog server defined by SYSLOG_SERVER.
        """
        syslog(message, level, host=SYSLOG_SERVER, port=SYSLOG_PORT)
    
    def get_attr(self, key):
        """
        Returns the specified instance attribute.
        """
        if key in self._attrs.keys():
            return self._attrs[key]
        else:
            return None
    
    def set_attr(self, key, value):
        """
        Changes the specified instance attribute.
        If the value is different or new, the change will 
        be logged to the syslog server.
        """
        changed = False
        
        if key in self._attrs:
            if self._attrs[key] != value:
                changed = True
        else:
            changed = True
        
        if changed:
            self._attrs[key] = value
            self._log_change(key, value)
    
    def get_attrs(self):
        """
        Returns a dictionary of all instance attributes.
        """
        return self._attrs
        
    def get_instance_path(self):
        """
        Returns the location of the instance on the file system.
        """
        return os.path.join(EUCA_LIB_PATH, 'instances', self.username, self.id)
    
    def update(self):
        """
        Causes the instance to update its current status.
        """
        
        if not self.terminated:
            self.update_local()
            self.update_euca()
            self.last_updated = datetime.now()
    
    def update_local(self):
        """
        Causes the instance to update attributes that come from the local compute node.
        """
        # obtain the compute node host name
        try:
            self._attrs['host_name'] = socket.gethostname()
        except:
            self._attrs['host_name'] = 'unknown'
        
        # fetch mac address(es) from virsh
        try:
            self._attrs['mac_address'] = getoutput('virsh dumpxml %s | grep "mac address" | cut -d\\\' -f2' % self.id).splitlines()[1:]
        except IndexError:
            pass
        
        # check virsh for information about this instance
        try:
            data = getoutput('virsh list | grep "%s"' % self.id).splitlines()[1].split()
            self._attrs['libvirt_id'] = data[0]
            self._attrs['libvirt_status'] = data[2]
        except IndexError:
            pass
        
        # read tail of console.log
        #self._attrs['console_log'] = getoutput('tail %s' % os.path.join(self.get_instance_path(), 'console.log'))
    
    def update_euca(self):
        """
        Causes the instance to update attributes that come from eucalyptus.
        """
        try:
            euca = Euca2ool()
            conn = euca.make_connection()
            reservations = conn.get_all_instances(self.id)
        except Exception, e:
            print >> sys.stderr, e
            return
        
        instance = None
        
        for r in reservations:
            for i in r.instances:
                if i.id == self.id:
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
    
    def mark_terminated(self):
        """
        Marks the instance as terminated. Further attemps to call update() will be ignored.
        """
        self.terminated = True
    
    def show_details(self):
        print >> sys.stderr, 'instance id: %s' % self.id
        print >> sys.stderr, 'username: %s' % self.username
        print >> sys.stderr, 'last_updated: %s' % self.last_updated
        
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
