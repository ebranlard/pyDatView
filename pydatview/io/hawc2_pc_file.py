""" 
Hawc2 pc file

"""
import pandas as pd
import numpy as np
import os

try:
    from .file import File, WrongFormatError, EmptyFileError
except:
    EmptyFileError = type('EmptyFileError', (Exception,),{})
    WrongFormatError = type('WrongFormatError', (Exception,),{})

from .wetb.hawc2.pc_file import PCFile

class HAWC2PCFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.dat','.pc','.txt']

    @staticmethod
    def formatName():
        return 'HAWC2 PC file'

    def __init__(self,filename=None,**kwargs):
        if filename:
            self.filename = filename
            self.read(**kwargs)
        else:
            self.filename = None
            self.data = PCFile()

    def read(self, filename=None, **kwargs):
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2,'File not found:',self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:',self.filename)
        # ---
        try:
            self.data = PCFile(self.filename)
        except Exception as e:    
            raise WrongFormatError('PC File {}: '.format(self.filename)+e.args[0])

    def write(self, filename=None):
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        # ---
        self.data.save(self.filename)

    def toDataFrame(self):
        cols=['Alpha_[deg]','Cl_[-]','Cd_[-]','Cm_[-]']

        dfs = {}
        for iset in self.data.pc_sets.keys():
            vt, vpolar = self.data.pc_sets[iset]
            for ipol in range(len(vt)):
                name='pc_set_{}_t_{}'.format(iset,vt[ipol])
                dfs[name] = pd.DataFrame(data=vpolar[ipol], columns=cols)
        return dfs


    # --- Useful function
    def add_set(self, set_label, thicknesses, profiles):
        """
        thicknesses: list of thicknesses
        profiles: list of polars, where each polar is an array (nx4) of alpha(deg), Cl, Cd, Cm
        """
        self.data.pc_sets[set_label] = (np.array(thicknesses), profiles) 

