import unittest

class TestGUI(unittest.TestCase):
    def test_gui(self):
        try:
            import wx
        except:
            raise unittest.SkipTest('S')
    
 
if __name__ == '__main__':
    unittest.main()
