import unittest
import numpy as np

from pydatview.plugins.base_plugin import demoPlotDataActionPanel
from pydatview.plugins.plotdata_binning import *
from pydatview.plugins.plotdata_binning import _DEFAULT_DICT


class TestBinning(unittest.TestCase):

    def test_showGUI(self):

        demoPlotDataActionPanel(BinningToolPanel, plotDataFunction=bin_plot, data=_DEFAULT_DICT, tableFunctionAdd=binTabAdd, mainLoop=False, title='Binning')


if __name__ == '__main__':
    unittest.main()

