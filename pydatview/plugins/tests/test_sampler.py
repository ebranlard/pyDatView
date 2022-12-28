import unittest
import numpy as np
from pydatview.plugins.base_plugin import demoPlotDataActionPanel, HAS_WX
from pydatview.plugins.plotdata_sampler import *
from pydatview.plugins.plotdata_sampler import _DEFAULT_DICT

class TestSampler(unittest.TestCase):

    def test_showGUI(self):
        if HAS_WX:
            demoPlotDataActionPanel(SamplerToolPanel, plotDataFunction=samplerXY, data=_DEFAULT_DICT, tableFunctionAdd=samplerTabAdd, mainLoop=False, title='Sampler')
        else:
            print('[WARN] skipping test because wx is not available.')

if __name__ == '__main__':
    unittest.main()

