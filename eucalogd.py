#!/usr/bin/python
import os, sys, glob, time

from commands import getoutput
from daemon import Daemon
from settings import *
from instance import Instance

class EucaLogDaemon(Daemon):
    def start(self):
        print 'Starting daemon...'
        super(EucaLogDaemon, self).start()

    def restart(self):
        print 'Restarting daemon...'
        super(EucaLogDaemon, self).restart()

    def stop(self):
        print 'Stopping daemon...'
        super(EucaLogDaemon, self).stop()

    def run(self):
        # a hash of all instances on the current compute node.
        instances = dict()
        
        while True:
            # build a list of instances currently on disk.
            instance_paths = glob.glob(EUCA_LIB_PATH + 'instances/*/i-*')
            
            # initialize any new instances.
            for instance_path in instance_paths:
                path_parts = instance_path.split('/')
                username = path_parts[-2]
                instance_id = path_parts[-1]
                
                if username == 'logs':
                    continue
                
                if not instance_id in instances:
                    print >> sys.stderr, 'found instance: %s' % instance_id
                    instances[instance_id] = Instance(username, instance_id, update=False)
            
            # build a list of instance id's returned from virsh list.
            virsh_instance_ids = list()
            
            try:
                virsh = getoutput('virsh list | grep "i-"').splitlines()[1:]
            except KeyError:
                virsh = None
            
            if virsh:
                for data in virsh:
                    try:
                        virsh_instance_ids.add( data.split()[1] )
                    except:
                        continue
            
            # process instances.
            for instance in instances.itervalues():
                # if the instance doesn't exist on disk anymore, then it was terminated.
                if not os.path.exists(instance.get_instance_path()):
                    terminate_instance(instance)
                # if the instance was in virsh list before, but is now gone.
                elif instance.id not in virsh_instance_ids and instance.get_attr('libvrt_status'):
                    terminate_instance(instance)
                # otherwise update the instance's current status if is is still active.
                elif not instance.terminated:
                    instance.update()
            
            # sleep, my child.
            time.sleep(1)

def terminate_instance(instance):
    print >> sys.stderr, 'instance terminated: %s' % instance.id
    instance.mark_terminated()


def usage():
    print 'usage: %s start|stop|restart' % sys.argv[0]

if __name__ == "__main__":
    daemon = EucaLogDaemon('/tmp/eucalogd.pid')
    if len(sys.argv) == 2:
        if sys.argv[1] == 'start':
            daemon.start()
        elif sys.argv[1] == 'stop':
            daemon.stop()
        elif sys.argv[1] == 'restart':
            daemon.restart()
        else:
            usage()
            sys.exit(2)
        sys.exit(0)
    else:
        usage()
        sys.exit(2)

