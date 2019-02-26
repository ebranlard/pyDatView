import numpy as np
import os.path
from dateutil import parser
import pandas as pd
try:
    from .common import no_unit
except:
    from common import no_unit

# --------------------------------------------------------------------------------}
# --- TabList 
# --------------------------------------------------------------------------------{
def haveSameColumns(tabs,I=None):
    if I is None:
        I=list(range(len(tabs)))
    A=[len(tabs[i].columns)==len(tabs[I[0]].columns) for i in I ]
    if all(A):
        B=[tabs[i].columns_clean==tabs[I[0]].columns_clean for i in I] #list comparison
        #B=[all(tabs[i].columns==tabs[I[0]].columns) for i in I ] #np array comparison
        return all(B)
    else:
        return False

# --------------------------------------------------------------------------------}
# --- Table 
# --------------------------------------------------------------------------------{
class Table(object):
    def __init__(self,data=[],columns=[],name='',filename='',df=None):
        if df is not None:
            # pandas
            if len(name)==0:
                if df.columns.name is not None:
                    self.name=df.columns.name
                else:
                    self.name='default'
            else:
                self.name=name
            self.data    = df
            self.columns = self.columnsFromDF(df)
        else: 
            # ndarray??
            raise Exception('Implementation of tables with ndarray dropped for now')
        self.filename = filename
        #self.name=os.path.dirname(filename)+'|'+os.path.splitext(os.path.basename(self.filename))[0]+'|'+ self.name
        if len(self.filename)>0:
            base=os.path.splitext(self.filename)[0]
        else:
            base=''
        self.name=base.replace('/','|').replace('\\','|')+'|'+ self.name
        self.active_name=self.name
        
        self.convertTimeColumns()

    def __repr__(self):
        return 'Tab {} ({}x{})'.format(self.name,self.nCols,self.nRows)


    def columnsFromDF(self,df):
        return [s.replace('_',' ') for s in df.columns.values.astype(str)]

    def convertTimeColumns(self):
        if len(self.data)>0:
            for i,c in enumerate(self.columns):
                y = self.data.iloc[:,i]
                if y.dtype == np.object and isinstance(y.values[0], str):
                    try:
                        parser.parse(y.values[0])
                        isDate=True
                    except:
                        if y.values[0]=='NaT':
                            isDate=True
                        else:
                            isDate=False
                    if isDate:
                        print('Converting column {} to datetime'.format(c))
                        self.data.iloc[:,i]=pd.to_datetime(self.data.iloc[:,i].values).to_pydatetime()

    def renameColumn(self,iCol,newName):
        self.columns[iCol]=newName
        self.data.columns.values[iCol]=newName

    def deleteColumns(self,ICol):
        df=self.data
        df.drop(df.columns[ICol],axis=1,inplace=True)
        for i in sorted(ICol, reverse=True):
            del(self.columns[i])

    def rename(self,new_name):
        self.name='>'+new_name

    def addColumn(self,sNewName,NewCol,i=-1):
        if i<0:
            i=self.data.shape[1]
        self.data.insert(i,sNewName,NewCol)
        self.columns=self.columnsFromDF(self.data)

    def evalFormula(self,sFormula):
        df = self.data
        Index = np.array(range(df.shape[0]))
        sFormula=sFormula.replace('{Index}','Index')
        for i,c in enumerate(self.columns):
            c_no_unit = no_unit(c).strip()
            c_in_df   = df.columns[i]
            sFormula=sFormula.replace('{'+c_no_unit+'}','df[\''+c_in_df+'\']')
        #print(sFormula)
        try:
            NewCol=eval(sFormula)
            return NewCol
        except:
            return None

    def addColumnByFormula(self,sNewName,sFormula,i=-1):
        NewCol=self.evalFormula(sFormula)
        if NewCol is None:
            return False
        else:
            self.addColumn(sNewName,NewCol,i)
            return True

    @property
    def columns_clean(self):
        return [no_unit(s) for s in self.columns]

    @property
    def name(self):
        if len(self.__name)<=0:
            return ''
        if self.__name[0]=='>':
            return self.__name[1:]
        else:
            return self.__name

    @property
    def raw_name(self):
        return self.__name

    @name.setter
    def name(self,new_name):
        self.__name=new_name

    @property
    def nCols(self):
        return len(self.columns) 

    @property
    def nRows(self):
        return len(self.data.iloc[:,0]) # TODO if not panda

