from .wetb.gtsdf.gtsdf import load
from .file import File, WrongFormatError
import numpy as np
import pandas as pd

class HAWC2Hdf5File(File):

    @staticmethod
    def defaultExtensions():
        return ['.hdf5']

    @staticmethod
    def formatName():
        return 'HAWC2 hdf5 file'

    def __init__(self, filename=None, **kwargs):
        self.info = {}
        self.data = np.array([])
        super(HAWC2Hdf5File, self).__init__(filename=filename, **kwargs)

    def _read(self):
        try:
            time, data, info = load(self.filename)
            self.time = time
            self.time = self.time.reshape(self.time.size, 1) # force shape(C, 1) for concatenation
            self.data = data
            self.info['attribute_names'] = info['attribute_names']
            self.info['attribute_units'] = info['attribute_units']
            self.info['attribute_descr'] = info['attribute_descriptions']
        except WrongFormatError as e:
            raise WrongFormatError('hdf5 File {}: '.format(self.filename)+'\n'+e.args[0])

    def _toDataFrame(self):
        # Appending time to form the dataframe
        names = ['Time'] + self.info['attribute_names']
        units = ['s']    + self.info['attribute_units']
        units = [u.replace('(','').replace(')','').replace('[','').replace(']','') for u in units]
        data  = np.concatenate((self.time, self.data), axis=1)
        cols = [n + '_[' + u + ']' for n, u in zip(names, units)]
        return pd.DataFrame(data=data, columns=cols)

    def _write(self):
        pass             
