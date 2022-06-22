from __future__ import unicode_literals
from __future__ import print_function
from io import open
import numpy as np

def yaml_read(filename,dictIn=None):
    """
    read yaml files only supports:
       - Key value pairs: 
             key: value
       - Key with lists of lists:
             key:  
               - [0,1]
               - [0,1]
       - Comments are stripped based on first # found (in string or not)
       - Keys are found based on first : found (in string or not)
    """
    # Read all lines at once
    with open(filename, 'r', errors="surrogateescape") as f:
        lines=f.read().splitlines()


    if dictIn is None:
        d=dict()
    else:
        d=dictIn

    def cleanComment(l):
        """ remove comments from a line"""
        return l.split('#')[0].strip()

    def readDashList(iStart):
        """ """
        i=iStart
        while i<len(lines):
            l = lines[i].strip()
            if len(l)==0:
                iEnd=i-1
                break
            if l[0]=='-':
                iEnd=i
                i+=1
            else:
                iEnd=i-1
                break
        n=iEnd-iStart+1
        FirstElems = cleanComment(lines[iStart])[1:].replace(']','').replace('[','').split(',')
        FirstElems = np.array([v.strip() for v in FirstElems if len(v.strip())>0])
        try: 
            FirstElems=FirstElems.astype(int)
            mytype=int
        except:
            try: 
                FirstElems=FirstElems.astype(float)
                mytype=float
            except:
                raise Exception('Cannot convert line to float or int: {}'.format(lines[iStart]))
        M = np.zeros((n,len(FirstElems)), mytype)
        if len(FirstElems)>0:
            for i in np.arange(iStart,iEnd+1):
                elem = cleanComment(lines[i])[1:].replace(']','').replace('[','').split(',')
                M[i-iStart,:] = np.array([v.strip() for v in elem if len(v)>0]).astype(mytype)
        return M, iEnd+1

    i=0
    while i<len(lines):
        l=cleanComment(lines[i])
        i+=1;
        if len(l)==0:
            continue
        sp=l.split(':')
        if len(sp)==2 and len(sp[1].strip())==0:
            key=sp[0]
            array,i=readDashList(i)
            d[key]=array
        elif len(sp)==2:
            key=sp[0]
            val=sp[1]
            try:
                d[key]=int(val)
            except:
                try:
                    d[key]=float(val)
                except:
                    d[key]=val.strip()
        else:
            raise Exception('Line {:d} has colon, number of splits is {}, which is not supported'.format(len(sp)))
    return d



if __name__=='__main__':
    d=read('test.yaml')
    #d=yaml_read('TetraSpar_outputs_DOUBLE_PRECISION.SD.sum.yaml')
    print(d.keys())
    print(d)
    print(d['nNodes_I'])

