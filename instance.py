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
        self._log('Discovered instance')
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
        syslog('%s: %s' % (self.id, message,), level, host=SYSLOG_SERVER, port=SYSLOG_PORT)
    
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
            print >> sys.stderr, '%s: %s changed to %s' % (self.id, key, str(value),)

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
            self.set_attr('host_name', socket.gethostname())
        except:
            self.set_attr('host_name', 'unknown')
        
        # fetch mac address(es) from virsh
        try:
            output = getoutput('virsh dumpxml %s | grep "mac address" | cut -d\\\' -f2' % self.id)

            if not 'error' in output:
                self.set_attr('mac_address', output.splitlines()[1:])
        except IndexError:
            pass
        
        # check virsh for information about this instance
        try:
            data = getoutput('virsh list | grep "%s"' % self.id).splitlines()[1].split()
            self.set_attr('libvirt_id', data[0])
            self.set_attr('libvirt_status', data[2])
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
            self.set_attr('image_id', instance.image_id)
            self.set_attr('kernel', instance.kernel)
            self.set_attr('ramdisk', instance.ramdisk)
            self.set_attr('private_dns_name', instance.private_dns_name)
            self.set_attr('state', instance.state)
            
            if instance.launch_time:
                self.set_attr('launch_time', instance.launch_time)
            
            if instance.instance_type:
                self.set_attr('instance_type', instance.instance_type)
        else:
            self.set_attr('state', 'unknown')

    
    def mark_terminated(self):
        """
        Marks the instance as terminated. Further attemps to call update() will be ignored.
        """
        self.terminated = True
        self._log('Instance terminated')
    
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
