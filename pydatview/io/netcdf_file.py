from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from io import open
from builtins import map
from builtins import range
from builtins import chr
from builtins import str
from future import standard_library
standard_library.install_aliases()

from .file import File, WrongFormatError
import pandas as pd

#import xarray as xr  # 

class NetCDFFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.nc']

    @staticmethod
    def formatName():
        return 'NetCDF file (<=2D)'

    def _read(self):
        try:
            import xarray as xr
        except:
            raise Exception('Python module `xarray` not installed')

        self.data=xr.open_dataset(self.filename)

    def _write(self):
        self.data.to_netcdf(self.filename)

    def _toDataFrame(self):
        dfs={}
        for k in self.data.keys():
            # Not pretty...
            if len(self.data[k].shape)==2:
                dfs[k]=pd.DataFrame(data=self.data[k].values)
            elif len(self.data[k].shape)==1:
                dfs[k]=pd.DataFrame(data=self.data[k].values)
            #import pdb
            #pdb.set_trace()
        return dfs

