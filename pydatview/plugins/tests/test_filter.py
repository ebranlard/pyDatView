import unittest
import numpy as np

from pydatview.plugins.base_plugin import demoPlotDataActionPanel, HAS_WX
from pydatview.plugins.plotdata_filter import *
from pydatview.plugins.plotdata_filter import _DEFAULT_DICT

class TestFilter(unittest.TestCase):

    def test_showGUI(self):
        if HAS_WX:
            demoPlotDataActionPanel(FilterToolPanel, plotDataFunction=filterXY, data=_DEFAULT_DICT, tableFunctionAdd=filterTabAdd, mainLoop=False, title='Filter')
        else:
            print('[WARN] skipping test because wx is not available.')



if __name__ == '__main__':
    unittest.main()


