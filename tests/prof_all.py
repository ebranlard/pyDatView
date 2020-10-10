
from __future__ import absolute_import


def test_heavy():
    import time
    import sys
    import pydatview
    import pandas as pd
    import numpy as np
    import wx
    from pydatview.perfmon import PerfMon, Timer
    from pydatview.pydatview import MainFrame
    from pydatview.GUISelectionPanel import ellude_common
    import gc
    dt = 0
    with Timer('Test'):
        # --- Test df
        with PerfMon('Data creation'):
            nRow =10**7;
            nCols=10;
            d={}
            d['col0'] = np.linspace(0,1,nRow);
            for iC in range(1,nCols):
                name='col{}'.format(iC)
                d[name] = np.random.normal(0,1,nRow)+2*iC
            tend = time.time()
            df = pd.DataFrame(data=d)
            del d
        time.sleep(dt) 
        with PerfMon('Plot 1'):
            app = wx.App(False)
            frame = MainFrame()
            frame.load_df(df)
            del df
        time.sleep(dt) 
        with PerfMon('Redraw 1'):
            frame.selPanel.colPanel1.lbColumns.SetSelection(-1)
            frame.selPanel.colPanel1.lbColumns.SetSelection(2)
            frame.plotPanel.redraw()
        time.sleep(dt) 
        with PerfMon('Redraw 1 (igen)'):
            frame.selPanel.colPanel1.lbColumns.SetSelection(-1)
            frame.selPanel.colPanel1.lbColumns.SetSelection(2)
            frame.plotPanel.redraw()
        time.sleep(dt) 
        with PerfMon('FFT 1'):
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(True)
            #frame.plotPanel.cbLogX.SetValue(True)
            #frame.plotPanel.cbLogY.SetValue(True)
            frame.plotPanel.redraw()
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(False)
        time.sleep(dt) 
        with PerfMon('Plot 3'):
            frame.selPanel.colPanel1.lbColumns.SetSelection(4)
            frame.selPanel.colPanel1.lbColumns.SetSelection(6)
            frame.onColSelectionChange()
        time.sleep(dt) 
        with PerfMon('Redraw 3'):
            frame.plotPanel.redraw()
        time.sleep(dt) 
        with PerfMon('FFT 3'):
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(True)
            frame.plotPanel.redraw()
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(False)



if __name__ == '__main__':
    import sys
    import os
    root_dir=os.getcwd()
    script_dir=os.path.dirname(os.path.realpath(__file__))
    sys.path.append(root_dir)
#     print(root_dir)
    #filenames=['../_TODO/DLC120_ws13_yeNEG_s2_r3_PIT.SFunc.outb','../_TODO/DLC120_ws13_ye000_s1_r1.SFunc.outb']
#     filenames=['../weio/_tests/CSVComma.csv']
#     filenames =[os.path.join(script_dir,f) for f in filenames]
    
    #pydatview.test(filenames=filenames)

    test_heavy()
