#!/usr/bin/env python
from __future__ import absolute_import
import pydatview
import sys
#import click
#@click.option('-i','--inputfile', default='', help='Input file to read')
#@click.command()
#@click.argument('inputfile', default='')
def main(inputfile=''):
    pydatview.pydatview(filename=inputfile)


if __name__ == '__main__':
    if len(sys.argv)>1:
        main(sys.argv[1])
    else:
        main()
