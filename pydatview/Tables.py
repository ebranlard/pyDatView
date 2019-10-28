import numpy as np
import os.path
from dateutil import parser
import pandas as pd
try:
    from .common import no_unit, ellude_common, getDt
except:
    from common import no_unit, ellude_common, getDt
try:
    import weio # File Formats and File Readers
except:
    print('')
    print('Error: the python package `weio` was not imported successfully.\n')
    print('Most likely the submodule `weio` was not cloned with `pyDatView`')
    print('Type the following command to retrieve it:\n')
    print('   git submodule update --init --recursive\n')
    print('Alternatively re-clone this repository into a separate folder:\n')
    print('   git clone --recurse-submodules https://github.com/ebranlard/pyDatView\n')
    sys.exit(-1)



# --------------------------------------------------------------------------------}
# --- TabList 
# --------------------------------------------------------------------------------{
class TableList(object): # todo inherit list
    def __init__(self,tabs=[]):
        self._tabs=tabs
        self.Naming='Ellude'

    def append(self,t):
        if isinstance(t,list):
            self._tabs += t
        else:
            self._tabs += [t]
        

    def from_dataframes(self, dataframes=[], names=[], bAdd=False):
        if not bAdd:
            self.clean() # TODO figure it out
        for df,name in zip(dataframes, names):
            # Returning a list of tables 
            self.append(Table(df=df, name=name))

    def load_tables_from_files(self, filenames=[], fileformat=None, bAdd=False):
        """ load multiple files, only trigger the plot at the end """
        if not bAdd:
            self.clean() # TODO figure it out
        warn=''
        for f in filenames:
            if f in self.unique_filenames:
                warn+= 'Warn: Cannot add a file already opened ' + f +'\n'
                pass
            else:
                tabs = self._load_file_tabs(f,fileformat=fileformat) 
                if len(tabs)<=0:
                    warn+= 'Warn: No dataframe found in file: '+f+'\n'
                self.append(tabs)
        return warn

    def _load_file_tabs(self,filename,fileformat=None):
        """ load a single file, adds table, and potentially trigger plotting """
        if not os.path.isfile(filename):
            raise Exception('Error: File not found: `'+filename+'`')
        try:
            F = weio.read(filename,fileformat = fileformat)
            dfs = F.toDataFrame()
        except weio.FileNotFoundError as e:
            raise Exception('Error: A file was not found!\n\n While opening:\n\n {}\n\n the following file was not found:\n\n {}'.format(filename, e.filename))
        except IOError:
            raise Exception('Error: IO Error thrown while opening file: '+filename )
        except MemoryError:
            raise Exception('Error: Insufficient memory!\n\nFile: '+filename+'\n\nTry closing and reopening the program, or use a 64 bit version of this program (i.e. of python).')
        except weio.EmptyFileError:
            raise Exception('Error: File empty!\n\nFile is empty: '+filename+'\n\nOpen a different file.')
        except weio.FormatNotDetectedError:
            raise Exception('Error: File format not detected!\n\nFile: '+filename+'\n\nUse an explicit file-format from the list')
        except weio.WrongFormatError as e:
            raise Exception('Error: Wrong file format!\n\nFile: '+filename+'\n\n'   \
                    'The file parser for the selected format failed to open the file.\n\n'+   \
                    'The reported error was:\n'+e.args[0]+'\n\n' +   \
                    'Double-check your file format and report this error if you think it''s a bug.')
        except weio.BrokenFormatError as e:
            raise Exception('Error: Inconsistency in the file format!\n\nFile: '+filename+'\n\n'   \
                    'The reported error was:\n'+e.args[0]+'\n\n' +   \
                    'Double-check your file format and report this error if you think it''s a bug.')
        except:
            raise
        # Returning a list of tables 
        tabs=[]
        if not isinstance(dfs,dict):
            if len(dfs)>0:
                tabs=[Table(df=dfs, name='default', filename=filename, fileformat=F.formatName())]
        else:
            for k in list(dfs.keys()):
                if len(dfs[k])>0:
                    tabs.append(Table(df=dfs[k], name=k, filename=filename, fileformat=F.formatName()))
        return tabs
            
    def getTabs(self):
        # TODO remove me later
        return self._tabs

    def len(self):
        return len(self._tabs)

    def haveSameColumns(self,I=None):
        if I is None:
            I=list(range(len(self._tabs)))
        A=[len(self._tabs[i].columns)==len(self._tabs[I[0]].columns) for i in I ]
        if all(A):
            B=[self._tabs[i].columns_clean==self._tabs[I[0]].columns_clean for i in I] #list comparison
            return all(B)
        else:
            return False

    def renameTable(self, iTab, newName):
        oldName = self._tabs[iTab].name
        if newName in [t.name for t in self._tabs]:
            raise Exception('Error: This table already exist, choose a different name.')
        # Renaming table
        self._tabs[iTab].rename(newName)
        return oldName

    def sort(self, method='byName'):
        if method=='byName':
            tabnames_display=self.getDisplayTabNames()
            self._tabs = [t for _,t in sorted(zip(tabnames_display,self._tabs))]
        else:
            raise Exception('Sorting method unknown: `{}`'.format(method))

    def deleteTabs(self, I):
        self._tabs = [t for i,t in enumerate(self._tabs) if i not in I]

    def setActiveNames(self,names):
        for t,tn in zip(self._tabs,names):
            t.active_name=tn

    def setNaming(self,naming):
        self.Naming=naming

    def getDisplayTabNames(self):
        if self.Naming=='Ellude':
            return  ellude_common([t.raw_name for t in self._tabs])
        elif self.Naming=='FileNames':
            return [os.path.splitext(os.path.basename(t.filename))[0] for t in self._tabs]
        else:
            raise Exception('Table naming unknown: {}'.format(self.Naming))

    @property
    def tabNames(self):
        return [t.name for t in self._tabs]

    @property
    def filenames(self):
        return [t.filename for t in self._tabs]

    @property
    def unique_filenames(self):
        return list(set([t.filename for t in self._tabs]))

    def clean(self):
        del self._tabs
        self._tabs=[]

    def __repr__(self):
        return '\n'.join([t.__repr__() for t in self._tabs])

    # --- Mask related
    @property
    def maskStrings(self):
        return [t.maskString for t in self._tabs]

    @property
    def commonMaskString(self):
        maskStrings=set(self.maskStrings)
        if len(maskStrings) == 1:
            return next(iter(maskStrings))
        else:
            return ''

    def clearCommonMask(self):
        for t in self._tabs:
            t.clearMask()

    def applyCommonMaskString(self,maskString,bAdd=True):
        dfs_new   = []
        names_new = []
        errors=[]
        for i,t in enumerate(self._tabs):
            try:
                df_new, name_new = t.applyMaskString(maskString, bAdd=bAdd)
                if df_new is not None: 
                    # we don't append when string is empty
                    dfs_new.append(df_new)
                    names_new.append(name_new)
            except:
                errors.append('Mask failed for table'+t.name) # TODO

        return dfs_new, names_new, errors


    # --- Element--related functions
    def get(self,i):
        return self._tabs[i]



# --------------------------------------------------------------------------------}
# --- Table 
# --------------------------------------------------------------------------------{
class Table(object):
    def __init__(self,data=[],columns=[],name='',filename='',df=None, fileformat=''):
        # Default init
        self.maskString=''
        self.mask=None

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
        self.fileformat = fileformat
        #self.name=os.path.dirname(filename)+'|'+os.path.splitext(os.path.basename(self.filename))[0]+'|'+ self.name
        if len(self.filename)>0:
            base=os.path.splitext(self.filename)[0]
        else:
            base=''
        base2=base.replace('/','|').replace('\\','|')
        if len(base2)>0:
            self.name=base2 +'|'+ self.name
        self.active_name=self.name
        
        self.convertTimeColumns()

    def __repr__(self):
        return 'Tab {} ({}x{}) (raw: {}, active: {}, file: {})'.format(self.name,self.nCols,self.nRows,self.raw_name, self.active_name,self.filename)

    def columnsFromDF(self,df):
        return [s.replace('_',' ') for s in df.columns.values.astype(str)]


    def clearMask(self):
        self.maskString=''
        self.mask=None

    def applyMaskString(self,maskString,bAdd=True):
        df = self.data
        sMask=maskString.replace('{Index}','Index')
        for i,c in enumerate(self.columns):
            c_no_unit = no_unit(c).strip()
            c_in_df   = df.columns[i]
            sMask=sMask.replace('{'+c_no_unit+'}','np.asarray(df[\''+c_in_df+'\'])')
        df_new   = None
        name_new = None
        if len(sMask.strip())>0 and sMask.strip().lower()!='no mask':
            try:
                self.mask = eval(sMask)
                if bAdd:
                    df_new = df[self.mask]
                    name_new=self.raw_name+'_masked'
            except:
                raise Exception('Error: The mask failed for table: '+self.name)
        return df_new, name_new


    def convertTimeColumns(self):
        if len(self.data)>0:
            for i,c in enumerate(self.data.columns.values):
                y = self.data.iloc[:,i]
                if y.dtype == np.object:
                    if isinstance(y.values[0], str):
                        # tring to convert to date
                        try:
                            parser.parse(y.values[0])
                            isDate=True
                        except:
                            if y.values[0]=='NaT':
                                isDate=True
                            else:
                                isDate=False
                        if isDate:
                            self.data[c]=pd.to_datetime(self.data[c].values).to_pydatetime()
                            print('Column {} converted to datetime'.format(c))
                        else:
                            print('Column {} inferred to string'.format(c))
                    elif isinstance(y.values[0], (float, int)):
                        try:
                            self.data[c]=self.data[c].astype(float)
                            print('Column {} converted to float (likely nan)'.format(c))
                        except:
                            self.data[c]=self.data[c].astype(str)
                            print('Column {} inferred to string'.format(c))
                    else :
                        print('>> Unknown type:',type(y.values[0]))
            #print(self.data.dtypes)

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

    def getColumn(self,i):
        """ Return column of data, where i=0 is the index column
        If a mask exist, the mask is applied
        """
        if i <= 0 :
            x = np.array(range(self.data.shape[0]))
            if self.mask is not None:
                x=x[self.mask]

            c = None
            isString = False
            isDate   = False
        else:
            if self.mask is not None:
                c = self.data.iloc[self.mask, i-1]
                x = self.data.iloc[self.mask, i-1].values
            else:
                c = self.data.iloc[:, i-1]
                x = self.data.iloc[:, i-1].values

            isString = c.dtype == np.object and isinstance(c.values[0], str)
            if isString:
                x=x.astype(str)
            isDate   = np.issubdtype(c.dtype, np.datetime64)
            if isDate:
                dt=getDt(x)
                if dt>1:
                    x=x.astype('datetime64[s]')
                else:
                    x=x.astype('datetime64')
        return x,isString,isDate,c



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


    def export(self,path):
        if isinstance(self.data, pd.DataFrame):
            try:
                self.data.to_csv(path,sep=',',index=False) #python3
            except:
                self.data.to_csv(path,sep=str(u',').encode('utf-8'),index=False) #python 2.
        else:
            raise NotImplementedError('Export of data that is not a dataframe')



    @property
    def basename(self):
        return os.path.splitext(os.path.basename(self.filename))[0]

    @property
    def shapestring(self):
        return '{}x{}'.format(self.nCols, self.nRows)

    @property
    def shape(self):
        return (self.nRows, self.nCols)


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


if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table
    import numpy as np

    def OnTabPopup(event):
        self.PopupMenu(TablePopup(self,selPanel.tabPanel.lbTab), event.GetPosition())
