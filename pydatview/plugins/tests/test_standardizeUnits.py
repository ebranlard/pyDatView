import unittest
import numpy as np
import pandas as pd
from pydatview.plugins.data_standardizeUnits import changeUnits

class TestChangeUnits(unittest.TestCase):

    def test_change_units(self):
        from pydatview.Tables import Table
        data = np.ones((1,3)) 
        data[:,0] *= 2*np.pi/60    # rad/s
        data[:,1] *= 2000          # N
        data[:,2] *= 10*np.pi/180  # rad
        df = pd.DataFrame(data=data, columns=['om [rad/s]','F [N]', 'angle_[rad]'])
        tab=Table(data=df)
        changeUnits(tab, flavor='WE')
        np.testing.assert_almost_equal(tab.data.values[:,0],[1])
        np.testing.assert_almost_equal(tab.data.values[:,1],[2])
        np.testing.assert_almost_equal(tab.data.values[:,2],[10])
        self.assertEqual(tab.columns, ['om [rpm]', 'F [kN]', 'angle [deg]'])


if __name__ == '__main__':
    unittest.main()
