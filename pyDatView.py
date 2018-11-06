#!/usr/bin/env python
from __future__ import absolute_import
import sys

#import click
#@click.option('-i','--inputfile', default='', help='Input file to read')
#@click.command()
#@click.argument('inputfile', default='')
def main(inputfiles=[]):
    import pydatview
    pydatview.pydatview(filenames=inputfiles)


def tests():
    import platform
    if platform.system()=='Windows':
        from pydatview.perfmon import Timer
        with Timer('Main import'):
            import pydatview
        with Timer('Test'):
            pydatview.test()

    else:
        # for now only weio tests
        import weio 
        import glob
        Files = glob.glob('_tests/*')+ glob.glob('weio/_tests/*')
        for f in Files:
            try:
                F = weio.read(f)
                s=F.formatName()
                s=s[:s.find('(')].replace('file','')[:20]
                print('[ OK ] {:30s}\t{:20s}'.format(f[:30],s))
            except weio.FormatNotDetectedError:
                print('[FAIL] {:30s}\tFormat not detected'.format(f[:30]))
                raise
            except:
                print('[FAIL] {:30s}\tException occured'.format(f[:30]))
                raise

if __name__ == '__main__':
    if len(sys.argv)>1:
        if sys.argv[1]=='--test':
            tests()
        else:
            main(sys.argv[1:])
    else:
        main()
