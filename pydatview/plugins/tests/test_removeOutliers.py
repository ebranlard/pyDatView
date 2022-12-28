import unittest
import numpy as np

from pydatview.plugins.base_plugin import demoPlotDataActionPanel
from pydatview.plugins.plotdata_removeOutliers import *
from pydatview.plugins.plotdata_removeOutliers import _DEFAULT_DICT


class TestRemoveOutliers(unittest.TestCase):

    def test_showGUI(self):

        demoPlotDataActionPanel(RemoveOutliersToolPanel, plotDataFunction=removeOutliersXY, data=_DEFAULT_DICT, mainLoop=False, title='Remove Outliers')


if __name__ == '__main__':
    unittest.main()


