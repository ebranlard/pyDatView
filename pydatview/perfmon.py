
from __future__ import print_function
import numpy as np
import time
import os
import psutil

def pretty_time(t):
    # fPrettyTime: returns a 6-characters string corresponding to the input time in seconds.
    #   fPrettyTime(612)=='10m12s'
    # AUTHOR: E. Branlard
    if(t<0):
        s='------';
    elif (t<1) :
        c=np.floor(t*100);
        s='{:2d}.{:02d}s'.format(0,int(c))
    elif(t<60) :
        s=np.floor(t);
        c=np.floor((t-s)*100);
        s='{:2d}.{:02d}s'.format(int(s),int(c))
    elif(t<3600) :
        m=np.floor(t/60);
        s=np.mod( np.floor(t), 60);
        s='{:2d}m{:02d}s'.format(int(m),int(s))
    elif(t<86400) :
        h=np.floor(t/3600);
        m=np.floor(( np.mod( np.floor(t) , 3600))/60);
        s='{:2d}h{:02d}m'.format(int(h),int(m))
    elif(t<8553600) : #below 3month
        d=np.floor(t/86400);
        h=np.floor( np.mod(np.floor(t), 86400)/3600);
        s='{:2d}d{:02d}h'.format(int(d),int(h))
    elif(t<31536000):
        m=t/(3600*24*30.5);
        s='{:4.1f}mo'.format(m)
        #s='+3mon.';
    else:
        y=t/(3600*24*365.25);
        s='{:.1f}y'.format(y)
    return s


class Timer(object):
    """ Time a set of commands, as a context manager
    with Timer('A name'):
        cmd1
        cmd2
    """
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.tstart = time.time()

    def __exit__(self, type, value, traceback):
        print('[TIME] ',end='')
        if self.name:
            print('{:31s}'.format(self.name[:30]),end='')
        print('Elapsed: {:6s}'.format(pretty_time(time.time() - self.tstart)))


def pretty_mem(m):
    # pretty_mem: returns 
    # AUTHOR: E. Branlard
    if(m<0):
        s='------';
    elif (m<1024) :
    #elif (m<1000) :
        s='{:4d}b'.format(m)
    elif (m<1048576) :
    #elif (m<1000000) :
        kb=float(m/1024.)
        s='{:6.1f}Kb'.format(kb)
    elif (m<2**30) :
    #elif (m<10**9) :
        mb=float(m/2**20)
        s='{:6.1f}Mb'.format(mb)
    elif (m<2**40) :
    #elif (m<10**12) :
        gb=float(m/2**30)
        s='{:6.1f}Gb'.format(gb)
    else:
        tb=float(m/2**40)
        s='{:6.1f}Tb'.format(tb)
    return s

class MemUse(object):
    """ Monitor memory use, as a contect managere
    with MemUse('A name'):
        cmd1
        cmd2
    """
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.memStart = psutil.virtual_memory().available
        #self.pid = os.getpid()
        #self.py  = psutil.Process(self.pid)
        #self.memStart = self.py.memory_info()[0]/2.**30

    def __exit__(self, type, value, traceback):
        memEnd = psutil.virtual_memory().available
        print('[MEM.] ',end='')
        if self.name:
            print('{:31s}'.format(self.name[:30]),end='')
        print('Used:  {}'.format(pretty_mem(self.memStart - memEnd)))

class PerfMon(object):
    """ Monitor time and Memory, as a context manager
    with PerfMon('A name'):
        cmd1
        cmd2
    """
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.tstart = time.time()
        self.memStart = psutil.virtual_memory().available

    def __exit__(self, type, value, traceback):
        memEnd = psutil.virtual_memory().available
        print('[PERF] ',end='')
        if self.name:
            print('{:31s}'.format(self.name[:30]),end='')
        print('Perf: {:6s}'.format(pretty_time(time.time() - self.tstart)),end='')
        print(' - {}'.format(pretty_mem(self.memStart - memEnd)))


def pretty_mem(m):
    # pretty_mem: returns 
    # AUTHOR: E. Branlard
    if(m<0):
        s='------';
    elif (m<1024) :
    #elif (m<1000) :
        s='{:4d}b'.format(m)
    elif (m<1048576) :
    #elif (m<1000000) :
        kb=float(m/1024.)
        s='{:6.1f}Kb'.format(kb)
    elif (m<2**30) :
    #elif (m<10**9) :
        mb=float(m/2**20)
        s='{:6.1f}Mb'.format(mb)
    elif (m<2**40) :
    #elif (m<10**12) :
        gb=float(m/2**30)
        s='{:6.1f}Gb'.format(gb)
    else:
        tb=float(m/2**40)
        s='{:6.1f}Tb'.format(tb)
    return s

class MemUse(object):
    """ Monitor memory use, as a contect managere
    with MemUse('A name'):
        cmd1
        cmd2
    """
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        mem = psutil.virtual_memory()
        self.memStart=mem.available
        #self.pid = os.getpid()
        #self.py  = psutil.Process(self.pid)
        #self.memStart = self.py.memory_info()[0]/2.**30

    def __exit__(self, type, value, traceback):
        mem = psutil.virtual_memory()
        memEnd=mem.available
        print('[MEM.] ',end='')
        if self.name:
            print('{:31s}'.format(self.name[:30]),end='')
        print('Used:  {}'.format(pretty_mem(self.memStart - memEnd)))




if __name__=='__main__':
    print(pretty_time(601))
    print(pretty_mem(2**10-1*2**0))
    print(pretty_mem(2**20-1*2**10))
    print(pretty_mem(2**30-1*2**20))
    print(pretty_mem(2**40-1*2**30))
