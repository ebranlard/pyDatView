from __future__ import division,unicode_literals,print_function,absolute_import
from builtins import map, range, chr, str
from io import open
from future import standard_library
standard_library.install_aliases()

from .file import File, WrongFormatError, BrokenFormatError
import numpy as np
import pandas as pd

# from pandas import ExcelWriter
from pandas import ExcelFile

class ExcelFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.xls','.xlsx']

    @staticmethod
    def formatName():
        return 'Excel file'

    def _read(self):
        self.data=dict()
        # Reading all sheets
        try:
            xls = pd.ExcelFile(self.filename,  engine='openpyxl')
        except:
            xls = pd.ExcelFile(self.filename)
        dfs = {}
        for sheet_name in xls.sheet_names:
            # Reading sheet
            df = xls.parse(sheet_name, header=None)
            # TODO detect sub tables
            # Dropping empty rows and cols
            df.dropna(how='all',axis=0,inplace=True)
            df.dropna(how='all',axis=1,inplace=True)
            #print(df.shape)
            if df.shape[0]>0:
                # Setting first row as header
                df=df.rename(columns=df.iloc[0]).drop(df.index[0]).reset_index(drop=True)
                #print(df)
                self.data[sheet_name]=df

    #def toString(self):
    #    s=''
    #    return s

    def _write(self):
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter(self.filename, engine='xlsxwriter')
        # Convert the dataframe to an XlsxWriter Excel object.
        for k,_ in self.data.items():
            df = self.data[k]
            df.to_excel(writer, sheet_name=k, index=False)
        # # Account info columns (set size)
        # worksheet.set_column('B:D', 20)
        # # Total formatting
        # total_fmt = workbook.add_format({'align': 'right', 'num_format': '$#,##0',
        #                                  'bold': True, 'bottom':6})
        # # Total percent format
        # total_percent_fmt = workbook.add_format({'align': 'right', 'num_format': '0.0%',
        #                                          'bold': True, 'bottom':6})
        # workbook = writer.book
        # worksheet = writer.sheets['report']
        # Highlight the top 5 values in Green
        #worksheet.conditional_format(color_range, {'type': 'top',
        #                                           'value': '5',
        #                                           'format': format2})
        ## Highlight the bottom 5 values in Red
        #worksheet.conditional_format(color_range, {'type': 'bottom',
        #                                           'value': '5',
        #                                           'format': format1})
        # Close the Pandas Excel writer and output the Excel file.
        writer.save()

    def __repr__(self):
        s ='Class XXXX (attributes: data)\n'
        return s


    def _toDataFrame(self):
        #cols=['Alpha_[deg]','Cl_[-]','Cd_[-]','Cm_[-]']
        #dfs[name] = pd.DataFrame(data=..., columns=cols)
        #df=pd.DataFrame(data=,columns=) 
        return self.data

