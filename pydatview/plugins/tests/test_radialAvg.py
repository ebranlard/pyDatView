import unittest
import numpy as np
from pydatview.plugins.base_plugin import demoGUIPlugin, HAS_WX
from pydatview.plugins.data_radialavg import *
from pydatview.plugins.data_radialavg import _DEFAULT_DICT

class TestRadialAvg(unittest.TestCase):

    def test_showGUI(self):
        if HAS_WX:
            demoGUIPlugin(RadialToolPanel, actionCreator=radialAvgAction, mainLoop=False, title='Radial Avg')
        else:
            print('[WARN] skipping test because wx is not available.')

if __name__ == '__main__':
    unittest.main()

