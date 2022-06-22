import unittest
import numpy as np
import pandas as pd
from pydatview.Tables import Table, TableList
import os



class TestTable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        d ={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0}
        cls.df1 = pd.DataFrame(data=d)
        d ={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0}
        cls.df2 = pd.DataFrame(data=d)

        cls.scriptdir = os.path.dirname(__file__)

    def test_table_name(self):
        t1=Table(data=self.df1)
        self.assertEqual(t1.raw_name, 'default')
        # Typically pyDatView adds tables like this:
        #
        #         self.tabList.load_tables_from_files(filenames=filenames, fileformat=fileformat, bAdd=bAdd)
        # 
        #         if len(dfs)>0:
        #             tabs=[Table(df=dfs, name='default', filename=filename, fileformat=F.formatName())]
        #         else:
        #             for k in list(dfs.keys()):
        #                 if len(dfs[k])>0:
        #                     tabs.append(Table(df=dfs[k], name=k, filename=filename, fileformat=F.formatName()))
        # OR
        #    if bAdd:
        #        self.tabList.append(Table(df=df, name=name))
        #    else:
        #        self.tabList = TableList( [Table(df=df, name=name)] )
        #
        # Tools add dfs like this to the GUI:
        #      self.tabList.from_dataframes(dataframes=dfs, names=names, bAdd=bAdd)
        #


    def test_load_files_misc_formats(self):
        tablist = TableList()
        files =[
                os.path.join(self.scriptdir,'../weio/weio/tests/example_files/CSVComma.csv'),
                os.path.join(self.scriptdir,'../weio/weio/tests/example_files/HAWCStab2.pwr')
                ]
        # --- First read without fileformats 
        tablist.load_tables_from_files(filenames=files, fileformats=None, bAdd=False)
        #print(tablist.fileformats)

        # --- Test iteration on tablist in passing..
        ffname1=[tab.fileformat.name for tab in tablist]

        # --- Then read with prescribed fileformats 
        fileformats1 = tablist.fileformats
        tablist.load_tables_from_files(filenames=files, fileformats=fileformats1, bAdd=False)
        ffname2 = [ff.name for ff in tablist.fileformats]

        self.assertEqual(ffname1, ffname2)


    def test_change_units(self):
        data = np.ones((1,3)) 
        data[:,0] *= 2*np.pi/60    # rad/s
        data[:,1] *= 2000          # N
        data[:,2] *= 10*np.pi/180  # rad
        df = pd.DataFrame(data=data, columns=['om [rad/s]','F [N]', 'angle_[rad]'])
        tab=Table(data=df)
        tab.changeUnits()
        np.testing.assert_almost_equal(tab.data.values[:,0],[1])
        np.testing.assert_almost_equal(tab.data.values[:,1],[2])
        np.testing.assert_almost_equal(tab.data.values[:,2],[10])
        self.assertEqual(tab.columns, ['om [rpm]', 'F [kN]', 'angle [deg]'])


if __name__ == '__main__':
#     TestTable.setUpClass()
#     tt= TestTable()
#     tt.test_load_files_misc_formats()
    unittest.main()
