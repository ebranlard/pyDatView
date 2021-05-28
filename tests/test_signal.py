import unittest
import numpy as np
from pydatview.tools.signal import *

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

 
if __name__ == '__main__':
    unittest.main()
