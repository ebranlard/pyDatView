from .file import File, WrongFormatError, BrokenFormatError
import numpy as np
import pandas as pd

class TDMSFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.tdms']

    @staticmethod
    def formatName():
        return 'TDMS file'

    def _read(self):
        try:
            from nptdms import TdmsFile
        except:
            raise Exception('Install the library nptdms to read this file')

        fh = TdmsFile(self.filename, read_metadata_only=False)
        channels_address = list(fh.objects.keys())
        channels_address = [ s.replace("'",'') for s in channels_address]
        channel_keys= [ s.split('/')[1:]  for s in channels_address if len(s.split('/'))==3]
        # --- Setting up list of signals and times
        signals=[]
        times=[]
        for i,ck in enumerate(channel_keys):
            channel = fh.object(ck[0],ck[1])
            signals.append(channel.data)
            times.append  (channel.time_track())

        lenTimes = [len(time) for time in times]
        minTimes = [np.min(time) for time in times]
        maxTimes = [np.max(time) for time in times]
        if len(np.unique(lenTimes))>1:
            print(lenTimes)
            raise NotImplementedError('Different time length') 
            # NOTE: could use fh.as_dataframe
        if len(np.unique(minTimes))>1:
            print(minTimes)
            raise NotImplementedError('Different time span') 
        if len(np.unique(maxTimes))>1:
            print(maxTimes)
            raise NotImplementedError('Different time span') 
        # --- Gathering into a data frame with time
        time =times[0]
        signals = [time]+signals
        M = np.column_stack(signals)
        colnames = ['Time_[s]'] + [ck[1] for ck in channel_keys]
        self['data'] =  pd.DataFrame(data = M, columns=colnames)

#     def toString(self):
#         s=''
#         return s
#     def _write(self):
#         pass

    def __repr__(self):
        s ='Class TDMS (key: data)\n'
        return s

    def _toDataFrame(self):
        return self['data']

