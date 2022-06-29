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

if __name__ == '__main__':
    unittest.main()
