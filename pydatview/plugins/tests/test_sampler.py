import unittest
import numpy as np

from pydatview.plugins.base_plugin import demoPlotDataActionPanel
from pydatview.plugins.plotdata_sampler import *
from pydatview.plugins.plotdata_sampler import _DEFAULT_DICT


class TestSampler(unittest.TestCase):

    def test_showGUI(self):

        demoPlotDataActionPanel(SamplerToolPanel, plotDataFunction=samplerXY, data=_DEFAULT_DICT, tableFunctionAdd=samplerTabAdd, mainLoop=False, title='Sampler')


if __name__ == '__main__':
    unittest.main()

