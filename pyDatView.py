#!/usr/bin/env python
from __future__ import absolute_import
import sys

#import click
#@click.option('-i','--inputfile', default='', help='Input file to read')
#@click.command()
#@click.argument('inputfile', default='')
def main(inputfile=''):
    import pydatview
    pydatview.pydatview(filename=inputfile)

def tests():
    # for now only weio tests
    import weio 
    import glob
    for f in glob.glob('_tests/*'):
        weio.read(f)
    for f in glob.glob('weio/_tests/*'):
        weio.read(f)

if __name__ == '__main__':
    if len(sys.argv)>1:
        if sys.argv[1]=='--test':
            tests()
        else:
            main(sys.argv[1])
    else:
        main()
