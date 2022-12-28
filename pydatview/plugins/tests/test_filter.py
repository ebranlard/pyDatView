import unittest
import numpy as np

from pydatview.plugins.base_plugin import demoPlotDataActionPanel
from pydatview.plugins.plotdata_filter import *
from pydatview.plugins.plotdata_filter import _DEFAULT_DICT


class TestFilter(unittest.TestCase):

    def test_showGUI(self):

        demoPlotDataActionPanel(FilterToolPanel, plotDataFunction=filterXY, data=_DEFAULT_DICT, tableFunctionAdd=filterTabAdd, mainLoop=False, title='Filter')



if __name__ == '__main__':
    unittest.main()


