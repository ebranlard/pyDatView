import unittest
import numpy as np
import pandas as pd
from pydatview.Tables import Table
import os



class TestTable(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        d ={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0}
        cls.df1 = pd.DataFrame(data=d)
        d ={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0}
        cls.df2 = pd.DataFrame(data=d)

    def test_table_name(self):
        print('  ')
        print('  ')
        t1=Table(data=self.df1)
        print(t1)
        print('  ')
        print('  ')
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

if __name__ == '__main__':
    unittest.main()
