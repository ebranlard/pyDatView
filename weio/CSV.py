from .File import File
import pandas as pd

class CSVFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.csv']

    @staticmethod
    def formatName():
        return 'CSV file (.csv)'

#    @classmethod
#    def isRightFormat(cls, filename):


    def __init__(self, *args, **kwargs):
        self.sep=None
        self.data=[]
        self.nHeader=0
        super(CSVFile, self).__init__(*args, **kwargs)

    def _read(self):
        #print('Reading CSV file')
        if self.sep is None:
            # Detecting separator by reading first lines of the file
            with open(self.filename) as f:
                head=[next(f).strip() for x in range(2)]
            # comma, semi columns or tab
            if head[1].find(',')>0:
                self.sep=','
            elif head[1].find(';')>0:
                self.sep=';'
            else:
                self.sep='\t'
        self.data = pd.read_csv(self.filename,sep=self.sep)
        self.data.rename(columns=lambda x: x.strip(),inplace=True)

    def _write(self):
        self.data.to_csv(self.filename,sep=self.false,index=False)

    def _toDataFrame(self):
        return self.data

