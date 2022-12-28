import unittest
import numpy as np

from pydatview.plugins.base_plugin import demoPlotDataActionPanel, HAS_WX
from pydatview.plugins.plotdata_binning import *
from pydatview.plugins.plotdata_binning import _DEFAULT_DICT

class TestBinning(unittest.TestCase):

    def test_showGUI(self):
        if HAS_WX:
            demoPlotDataActionPanel(BinningToolPanel, plotDataFunction=bin_plot, data=_DEFAULT_DICT, tableFunctionAdd=binTabAdd, mainLoop=False, title='Binning')
        else:
            print('[WARN] skipping test because wx is not available.')


if __name__ == '__main__':
    unittest.main()

