import os
import time
import pydatview
import pandas as pd
import numpy as np
import wx
from pydatview.perfmon import PerfMon, Timer
from pydatview.main import MainFrame
import pydatview.io as weio
import gc
scriptDir = os.path.dirname(__file__)

def test_heavy():
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
            frame.load_dfs([df])
            del df
        time.sleep(dt) 
        with PerfMon('Redraw 1'):
            frame.selPanel.colPanel1.lbColumns.SetSelection(-1)
            frame.selPanel.colPanel1.lbColumns.SetSelection(2)
            frame.redraw()
        time.sleep(dt) 
        with PerfMon('Redraw 1 (igen)'):
            frame.selPanel.colPanel1.lbColumns.SetSelection(-1)
            frame.selPanel.colPanel1.lbColumns.SetSelection(2)
            frame.redraw()
        time.sleep(dt) 
        with PerfMon('FFT 1'):
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(True)
            #frame.plotPanel.cbLogX.SetValue(True)
            #frame.plotPanel.cbLogY.SetValue(True)
            frame.redraw()
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(False)
        time.sleep(dt) 
        with PerfMon('Plot 3'):
            frame.selPanel.colPanel1.lbColumns.SetSelection(4)
            frame.selPanel.colPanel1.lbColumns.SetSelection(6)
            frame.onColSelectionChange()
        time.sleep(dt) 
        with PerfMon('Redraw 3'):
            frame.redraw()
        time.sleep(dt) 
        with PerfMon('FFT 3'):
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(True)
            frame.redraw()
            frame.plotPanel.pltTypePanel.cbFFT.SetValue(False)



def test_debug(show=False):
    dt = 0
    with Timer('Test'):
        with Timer('read'):
            df1 =weio.read(os.path.join(scriptDir,'../ad_driver_m50.1.outb')).toDataFrame()
            df2 =weio.read(os.path.join(scriptDir,'../ad_driver_p50.csv')).toDataFrame()

        time.sleep(dt) 
        with PerfMon('Plot 1'):
            app = wx.App(False)
            frame = MainFrame()
            frame.load_dfs([df1,df2])
            frame.selPanel.tabPanel.lbTab.SetSelection(0)
            frame.selPanel.tabPanel.lbTab.SetSelection(1)
            frame.onTabSelectionChange()
            #frame.redraw()
    if show:
        app.MainLoop()


def test_files(filenames):
    pydatview.test(filenames=filenames)

if __name__ == '__main__':
#     filenames =[os.path.join(script_dir,f) for f in filenames]

    test_heavy()
    #test_debug(False)
