import unittest
import numpy as np
import pandas as pd
from pydatview.tools.signal_analysis import *

# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
class TestSignal(unittest.TestCase):

    def test_zero_crossings(self):
        self.assertEqual(zero_crossings(np.array([0        ]))[0].size,0       )
        self.assertEqual(zero_crossings(np.array([0      ,0]))[0].size,0)
        self.assertEqual(zero_crossings(np.array([0      ,1]))[0].size,0)
        self.assertEqual(zero_crossings(np.array([-1,0,0, 1]))[0].size,0)
        self.assertEqual(zero_crossings(np.array([-1     ,1])), (0.5, 0, 1))
        self.assertEqual(zero_crossings(np.array([ 1,    -1])), (0.5, 0,-1))
        self.assertEqual(zero_crossings(np.array([-1,0,   1])), (1.0, 1,  1))
        xz,iz,sz=zero_crossings(np.array([-1,1,-1]))
        self.assertTrue(np.all(xz==[0.5,1.5]))
        self.assertTrue(np.all(iz==[0,1]))
        self.assertTrue(np.all(sz==[1,-1]))
        self.assertEqual(zero_crossings(np.array([ 1,-1]),direction='up'  )[0].size,0)
        self.assertEqual(zero_crossings(np.array([-1, 1]),direction='down')[0].size,0)

    def test_up_down_sample(self):
        name = 'Time-based'
        x, y = applySampler(range(0, 4), [5, 0, 5, 0], {'name': name, 'param': [2]})
        self.assertTrue(np.all(x==[0.5, 2.5]))
        self.assertTrue(np.all(y==[2.5, 2.5]))
        x, y = applySampler(range(0, 3), [5, 0, 5], {'name': name, 'param': [0.5]})
        self.assertTrue(np.all(x==[0, 0.5, 1, 1.5, 2]))
        self.assertTrue(np.all(y==[5, 2.5, 0, 2.5, 5]))
        x, df = applySampler(range(0, 6), None, {'name': name, 'param': [3]}, pd.DataFrame({"y": [0, 6, 6, 2, -4, -4]}))
        self.assertTrue(np.all(x==[1, 4]))
        self.assertTrue(np.all(df["y"]==[4, -2]))
        x, df = applySampler(range(0, 3), None, {'name': name, 'param': [0.5]}, pd.DataFrame({"y": [0, 6, -6]}))
        self.assertTrue(np.all(x==[0, 0.5, 1, 1.5, 2]))
        self.assertTrue(np.all(df["y"]==[0, 3, 6, 0, -6]))

    def test_interpDF(self):

        df = data=pd.DataFrame(data={'ID': np.arange(0,3),'ColA': [10,11,12]})
        x_new = [-1,0,0.5,1,20,1.5,2,-3]

        #  Interpolation with nan out of bounds
        df_new = interpDF(x_new, 'ID',  df, extrap='nan')
        x_ref = [np.nan, 10, 10.5, 11, np.nan, 11.5, 12, np.nan]
        np.testing.assert_almost_equal(df_new['ColA'], x_ref)
        np.testing.assert_almost_equal(df_new['ID'], x_new) # make sure ID is not replaced by nan

        #  Interpolation with bounded values outside
        df_new = interpDF(x_new, 'ID',  df) #, extrap='bounded')
        x_ref = [10, 10, 10.5, 11, 12, 11.5, 12, 10]
        np.testing.assert_almost_equal(df_new['ColA'], x_ref)

    def test_interp(self, plot=False):
        x = np.linspace(0,1,10)
        y1= x**2
        y2= x**3
        Y = np.stack((y1,y2))

        # --- Check that we retrieve proper value on nodes
        x_new = x
        Y_new = multiInterp(x_new, x, Y)
        np.testing.assert_almost_equal(Y_new, Y)

        # using interpArray
        Y_new2 = np.zeros(Y_new.shape)
        for i,x0 in enumerate(x_new):
            Y_new2[:,i] = interpArray(x0, x, Y)
        np.testing.assert_almost_equal(Y_new2, Y)

        # --- Check that we retrieve proper value on misc nodes
        x_new  = np.linspace(-0.8,1.5,20)
        Y_new  = multiInterp(x_new, x, Y)
        y1_new = np.interp(x_new, x, Y[0,:])
        y2_new = np.interp(x_new, x, Y[1,:])
        Y_ref  = np.stack((y1_new, y2_new))
        np.testing.assert_almost_equal(Y_new, Y_ref)

        # using interpArray
        Y_new2 = np.zeros(Y_new.shape)
        for i,x0 in enumerate(x_new):
            Y_new2[:,i] = interpArray(x0, x, Y)
        np.testing.assert_almost_equal(Y_new2, Y_ref)




if __name__ == '__main__':
    TestSignal().test_interpDF()
    TestSignal().test_interp()
#     unittest.main()
