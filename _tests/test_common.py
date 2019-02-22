import unittest
import numpy as np
import pandas as pd
from pydatview.common import unit,no_unit,ellude_common,getDt
import datetime



class TestCommon(unittest.TestCase):
    def assertEqual(self, first, second, msg=None):
        #print('>',first,'<',' >',second,'<')
        super(TestCommon, self).assertEqual(first, second, msg)
    
    def test_unit(self):
        self.assertEqual(unit   ('speed [m/s]'),'m/s'  )
        self.assertEqual(unit   ('speed [m/s' ),'m/s'  ) # ...
        self.assertEqual(no_unit('speed [m/s]'),'speed')

    def test_date(self):
        def test_dt(datestr,dt_ref):
            # Type: Numpy array  - Elements: datetime64
            x=np.array(datestr, dtype='datetime64')
            self.assertEqual(getDt(x),dt_ref)
            # Type: Pandas DatetimeIndex - Elements: TimeSamp
            df = pd.DataFrame(data=datestr)
            x  = pd.to_datetime(df.iloc[:,0].values)
            self.assertEqual(getDt(x),dt_ref)
            # Type: Numpy array  - Elements: datetime.datetime
            df = pd.DataFrame(data=datestr)
            x  = pd.to_datetime(df.iloc[:,0].values).to_pydatetime()
            self.assertEqual(getDt(x),dt_ref)

        test_dt(['2008-01-01','2009-01-01'],24*366*3600); # year
        test_dt(['2008-01-01','2008-02-01'],24*3600*31);  #month
        test_dt(['2000-10-15 01:00:00', '2000-10-15 02:00:00'],3600); # hour
        test_dt(['2000-10-15 00:00:05.000001', '2000-10-15 00:00:05.000002'],0.000001);#mu s
        self.assertEqual(getDt([0,1]),1)
        self.assertEqual(getDt([0.0,0.1]),0.1)
        self.assertEqual(getDt(np.array([0,1])),1)
    
    def test_ellude(self):
        self.assertListEqual(ellude_common(['AAA','ABA']),['A','B'])

        # unit test for #25
        S=ellude_common(['A.txt','A_.txt'])
        if any([len(s)<=1 for s in S]):
            raise Exception('[FAIL] ellude common with underscore difference, Bug #25')

 
if __name__ == '__main__':
    unittest.main()
