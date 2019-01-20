
from __future__ import absolute_import


if __name__ == '__main__':
    import sys
    import os
    root_dir=os.getcwd()
    script_dir=os.path.dirname(os.path.realpath(__file__))
    sys.path.append(root_dir)
#     print(root_dir)
    import pydatview
    #filenames=['../_TODO/DLC120_ws13_yeNEG_s2_r3_PIT.SFunc.outb','../_TODO/DLC120_ws13_ye000_s1_r1.SFunc.outb']
#     filenames=['../weio/_tests/CSVComma.csv']
#     filenames =[os.path.join(script_dir,f) for f in filenames]
    
    #pydatview.test(filenames=filenames)
    pydatview.test()
