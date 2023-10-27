import unittest
import numpy as np

from pydatview.plugins.base_plugin import demoPlotDataActionPanel, HAS_WX
from pydatview.plugins.plotdata_removeOutliers import *
from pydatview.plugins.plotdata_removeOutliers import _DEFAULT_DICT

class TestRemoveOutliers(unittest.TestCase):

    def test_showGUI(self):
        if HAS_WX:
            demoPlotDataActionPanel(RemoveOutliersToolPanel, plotDataFunction=removeOutliersXY, data=_DEFAULT_DICT, mainLoop=False, title='Remove Outliers')
        else:
            print('[WARN] skipping test because wx is not available.')


if __name__ == '__main__':
    unittest.main()


