import numpy as np
import pandas as pd
import os

try:
    from .file import File, WrongFormatError, BrokenFormatError
except:
    File = dict
    class WrongFormatError(Exception): pass
    class BrokenFormatError(Exception): pass

class TDMSFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.tdms']

    @staticmethod
    def formatName():
        return 'TDMS file'

    def __init__(self, filename=None, **kwargs):
        """ Class constructor. If a `filename` is given, the file is read. """
        self.filename = filename
        if filename:
            self.read(**kwargs)

    def read(self, filename=None, **kwargs):
        """ Reads the file self.filename, or `filename` if provided """
        
        # --- Standard tests and exceptions (generic code)
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2,'File not found:',self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:',self.filename)
        try:
            from nptdms import TdmsFile
        except:
            raise Exception('Install the library nptdms to read this file')

        fh = TdmsFile(self.filename, read_metadata_only=False)
        # --- OLD, using some kind of old version of tdms and probably specific to one file
        #   channels_address = list(fh.objects.keys())
        #   channels_address = [ s.replace("'",'') for s in channels_address]
        #   channel_keys= [ s.split('/')[1:]  for s in channels_address if len(s.split('/'))==3]
        #   # --- Setting up list of signals and times
        #   signals=[]
        #   times=[]
        #   for i,ck in enumerate(channel_keys):
        #       channel = fh.object(ck[0],ck[1])
        #       signals.append(channel.data)
        #       times.append  (channel.time_track())

        #   lenTimes = [len(time) for time in times]
        #   minTimes = [np.min(time) for time in times]
        #   maxTimes = [np.max(time) for time in times]
        #   if len(np.unique(lenTimes))>1:
        #       print(lenTimes)
        #       raise NotImplementedError('Different time length') 
        #       # NOTE: could use fh.as_dataframe
        #   if len(np.unique(minTimes))>1:
        #       print(minTimes)
        #       raise NotImplementedError('Different time span') 
        #   if len(np.unique(maxTimes))>1:
        #       print(maxTimes)
        #       raise NotImplementedError('Different time span') 
        #   # --- Gathering into a data frame with time
        #   time =times[0]
        #   signals = [time]+signals
        #   M = np.column_stack(signals)
        #   colnames = ['Time_[s]'] + [ck[1] for ck in channel_keys]
        #   self['data'] =  pd.DataFrame(data = M, columns=colnames)
        # --- NEW
        self['data'] = fh

    @property
    def groupNames(self):
        return [group.name for group in self['data'].groups()]

    def __repr__(self):
        s ='Class TDMS (key: data)\n'
        s +=' - data: TdmsFile\n'
        s +=' * groupNames: {}\n'.format(self.groupNames)
        #for group in fh.groups():
        #   for channel in group.channels():
        #       print(group.name)
        #       print(channel.name)
        return s

    def toDataFrame(self):

        df = self['data'].as_dataframe(time_index=True)

        # Cleanup columns
        colnames = df.columns
        colnames=[c.replace('\'','') for c in colnames]
        colnames=[c[1:] if c.startswith('/') else c for c in colnames]
        # If there is only one group, we remove the group key
        groupNames = self.groupNames
        if len(groupNames)==1:
            nChar = len(groupNames[0])
            colnames=[c[nChar+1:] for c in colnames] # +1 for the "/"

        df.columns = colnames

        df.insert(0,'Time_[s]', df.index.values)
        df.index=np.arange(0,len(df))

        return df

if __name__ == '__main__':
    df = TDMSFile('DOE15_FastData_2019_11_19_13_51_35_50Hz.tdms').toDataFrame()
    print(df)
