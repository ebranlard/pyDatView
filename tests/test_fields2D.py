import unittest
import numpy as np
import pandas as pd
from pydatview.Fields2D import * #Fields2D, extract2Dfields
import os



class TestFields2D(unittest.TestCase):

    def test_fast_out(self):
        # Check that FAST Out can create 2D Field that is handled by 
        from pydatview.io.fast_output_file import FASTOutputFile
        d ={
            'ColA': np.linspace(0,1,100)+1,
            'Time_[s]': np.linspace(0,1,100)+1,
            'Azimuth_[deg]': np.linspace(0,1,100)+1,
            'AB1N001Alpha_[deg]': np.random.normal(0,1,100)+0,
            'AB1N003Alpha_[deg]': np.random.normal(0,1,100)+0,
            }
        df = pd.DataFrame(data=d)
        fo = FASTOutputFile()
        fo.data=df
        fields = fo.to2DFields()
        f = Fields2D(fields)
        np.testing.assert_array_equal(list(f.ds.coords.keys()), ['t','r','psi'])
        np.testing.assert_array_almost_equal(f.ds['t'], df['Time_[s]'])
        np.testing.assert_almost_equal(f.ds['r'], [0, 0.5, 1.0])

        # Check interface
        keys = f.keys()
        self.assertEqual(len(f.keys()), 2)
        d = f.iloc(1)
        self.assertEqual(d['sx']       ,'t [s]')
        self.assertEqual(d['sy']       ,'r [-]')
        self.assertTrue(d['fieldname'].find('B1Alpha')>1)

if __name__ == '__main__':
#     TestFields2D.setUpClass()
#     TestFields2D().test_resample()
    unittest.main()
