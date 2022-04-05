import numpy as np
import os.path
from dateutil import parser
import pandas as pd
import pydatview.fast.fastlib as fastlib
import pydatview.fast.fastfarm as fastfarm
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
        # Returning a list of tables 
        for df,name in zip(dataframes, names):
            if df is not None:
                self.append(Table(data=df, name=name))

    def load_tables_from_files(self, filenames=[], fileformat=None, bAdd=False):
        """ load multiple files, only trigger the plot at the end """
        if not bAdd:
            self.clean() # TODO figure it out
        warnList=[]
        for f in filenames:
            if f in self.unique_filenames:
                warnList.append('Warn: Cannot add a file already opened ' + f)
            elif len(f)==0:
                pass
                #    warn+= 'Warn: an empty filename was skipped' +'\n'
            else:
                tabs, warnloc = self._load_file_tabs(f,fileformat=fileformat) 
                if len(warnloc)>0:
                    warnList.append(warnloc)
                self.append(tabs)
        
        return warnList

    def _load_file_tabs(self,filename,fileformat=None):
        """ load a single file, adds table, and potentially trigger plotting """
        # Returning a list of tables 
        tabs=[]
        warn=''
        if not os.path.isfile(filename):
            warn = 'Error: File not found: `'+filename+'`\n'
            return tabs, warn
        try:
            F = weio.read(filename,fileformat = fileformat)
            dfs = F.toDataFrame()
        except weio.FileNotFoundError as e:
            warn = 'Error: A file was not found!\n\n While opening:\n\n {}\n\n the following file was not found:\n\n {}\n'.format(filename, e.filename)
        except IOError:
            warn = 'Error: IO Error thrown while opening file: '+filename+'\n'
        except MemoryError:
            warn='Error: Insufficient memory!\n\nFile: '+filename+'\n\nTry closing and reopening the program, or use a 64 bit version of this program (i.e. of python).\n'
        except weio.EmptyFileError:
            warn='Error: File empty!\n\nFile is empty: '+filename+'\n\nOpen a different file.\n'
        except weio.FormatNotDetectedError:
            warn='Error: File format not detected!\n\nFile: '+filename+'\n\nUse an explicit file-format from the list\n'
        except weio.WrongFormatError as e:
            warn='Error: Wrong file format!\n\nFile: '+filename+'\n\n'   \
                    'The file parser for the selected format failed to open the file.\n\n'+   \
                    'The reported error was:\n'+e.args[0]+'\n\n' +   \
                    'Double-check your file format and report this error if you think it''s a bug.\n'
        except weio.BrokenFormatError as e:
            warn = 'Error: Inconsistency in the file format!\n\nFile: '+filename+'\n\n'   \
                   'The reported error was:\n\n'+e.args[0]+'\n\n' +   \
                   'Double-check your file format and report this error if you think it''s a bug.'
        except:
            raise
        if len(warn)>0:
            return tabs, warn

        if dfs is None:
            pass
        elif not isinstance(dfs,dict):
            if len(dfs)>0:
                tabs=[Table(data=dfs, filename=filename, fileformat=F.formatName())]
        else:
            for k in list(dfs.keys()):
                if len(dfs[k])>0:
                    tabs.append(Table(data=dfs[k], name=str(k), filename=filename, fileformat=F.formatName()))
        if len(tabs)<=0:
            warn='Warn: No dataframe found in file: '+filename+'\n'
        return tabs, warn

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
            # Temporary hack, using last names if all last names are unique
            names = [t.raw_name for t in self._tabs]
            last_names=[n.split('|')[-1] for n in names]
            if len(np.unique(last_names)) == len(names):
                return  ellude_common(last_names)
            else:
                return  ellude_common(names)
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
                errors.append('Mask failed for table: '+t.active_name) # TODO

        return dfs_new, names_new, errors

    def applyResampling(self,iCol,sampDict,bAdd=True):
        dfs_new   = []
        names_new = []
        errors=[]
        for i,t in enumerate(self._tabs):
#             try:
            df_new, name_new = t.applyResampling(iCol,sampDict, bAdd=bAdd)
            if df_new is not None: 
                # we don't append when string is empty
                dfs_new.append(df_new)
                names_new.append(name_new)
#             except:
#                 errors.append('Resampling failed for table: '+t.active_name) # TODO

        return dfs_new, names_new, errors




    # --- Radial average related
    def radialAvg(self,avgMethod,avgParam):
        dfs_new   = []
        names_new = []
        errors=[]
        for i,t in enumerate(self._tabs):
            dfs, names = t.radialAvg(avgMethod,avgParam)
            for df,n in zip(dfs,names):
                if df is not None:
                    dfs_new.append(df)
                    names_new.append(n)
        return dfs_new, names_new, errors


    # --- Element--related functions
    def get(self,i):
        return self._tabs[i]



# --------------------------------------------------------------------------------}
# --- Table 
# --------------------------------------------------------------------------------{
# TODO sort out the naming
#
# Main naming concepts:
#    name        : 
#    active_name : 
#    raw_name    : 
#    filename    : 
class Table(object):
    def __init__(self,data=None,name='',filename='',columns=[],fileformat=''):
        # Default init
        self.maskString=''
        self.mask=None

        self.filename   = filename
        self.fileformat = fileformat
        self.formulas = []

        if not isinstance(data,pd.DataFrame):
            # ndarray??
            raise NotImplementedError('Tables that are not dataframe not implemented.')
        else:
            # --- Pandas DataFrame 
            self.data    = data 
            self.columns = self.columnsFromDF(data)
            # --- Trying to figure out how to name this table
            if name is None or len(str(name))==0:
                if data.columns.name is not None:
                    name=data.columns.name

        self.setupName(name=str(name))
        
        self.convertTimeColumns()


    def setupName(self,name=''):
        # Creates a "codename": path | basename | name | ext
        splits=[]
        ext=''
        if len(self.filename)>0:
            base_dir = os.path.dirname(self.filename)
            if len(base_dir)==0:
                base_dir= os.getcwd() 
                self.filename=os.path.join(base_dir,self.filename)
            splits.append(base_dir.replace('/','|').replace('\\','|'))
            basename,ext=os.path.splitext(os.path.basename(self.filename))
            if len(basename)>0:
                splits.append(basename)
        if name is not None and len(name)>0:
            splits.append(name)
        #if len(ext)>0:
        #    splits.append(ext)
        self.extension=ext
        name='|'.join(splits)
        if len(name)==0:
            name='default'
        self.name=name
        self.active_name=self.name


    def __repr__(self):
        return 'Tab {} ({}x{}) (raw: {}, active: {}, file: {})'.format(self.name,self.nCols,self.nRows,self.raw_name, self.active_name,self.filename)

    def columnsFromDF(self,df):
        return [s.replace('_',' ') for s in df.columns.values.astype(str)]


    def clearMask(self):
        self.maskString=''
        self.mask=None

    def addLabelToName(self,label):
        print('raw_name',self.raw_name)
        raw_name=self.raw_name
        sp=raw_name.split('|')
        print(sp)

    def applyMaskString(self,maskString,bAdd=True):
        df = self.data
        Index = np.array(range(df.shape[0]))
        sMask=maskString.replace('{Index}','Index')
        for i,c in enumerate(self.columns):
            c_no_unit = no_unit(c).strip()
            c_in_df   = df.columns[i]
            # TODO sort out the mess with asarray (introduced to have and/or
            # as array won't work with date comparison
            # NOTE: using iloc to avoid duplicates column issue
            if isinstance(df.iloc[0,i], pd._libs.tslibs.timestamps.Timestamp):
                sMask=sMask.replace('{'+c_no_unit+'}','df[\''+c_in_df+'\']')
            else:
                sMask=sMask.replace('{'+c_no_unit+'}','np.asarray(df[\''+c_in_df+'\'])')
        df_new   = None
        name_new = None
        if len(sMask.strip())>0 and sMask.strip().lower()!='no mask':
            try:
                mask = np.asarray(eval(sMask))
                if bAdd:
                    df_new = df[mask]
                    name_new=self.raw_name+'_masked'
                else:
                    self.mask=mask
                    self.maskString=maskString
            except:
                raise Exception('Error: The mask failed for table: '+self.name)
        return df_new, name_new

    def applyResampling(self,iCol,sampDict,bAdd=True):
        from pydatview.tools.signal import applySamplerDF
        if iCol==0:
            raise Exception('Cannot resample based on index')
        colName=self.data.columns[iCol-1]
        df_new =applySamplerDF(self.data, colName, sampDict=sampDict)
        df_new
        if bAdd:
            name_new=self.raw_name+'_resampled'
        else:
            name_new=None
            self.data=df_new
        return df_new, name_new


    def radialAvg(self,avgMethod, avgParam):
        df = self.data
        base,out_ext = os.path.splitext(self.filename)

        # --- Detect if it's a FAST Farm file
        sCols = ''.join(df.columns)
        if sCols.find('WkDf')>1 or sCols.find('CtT')>0:
            # --- FAST FARM files
            Files=[base+ext for ext in ['.fstf','.FSTF','.Fstf','.fmas','.FMAS','.Fmas'] if os.path.exists(base+ext)]
            if len(Files)==0:
                fst_in=None
                #raise Exception('Error: No .fstf file found with name: '+base+'.fstf')
            else:
                fst_in=Files[0]

            dfRad,_,dfDiam =  fastfarm.spanwisePostProFF(fst_in,avgMethod=avgMethod,avgParam=avgParam,D=1,df=df)
            dfs_new  = [dfRad,dfDiam]
            names_new=[self.raw_name+'_rad',self.raw_name+'_diam']
        else:
            # --- FAST files

            # HACK for AD file to find the right .fst file
            iDotAD=base.lower().find('.ad')
            if iDotAD>1:
                base=base[:iDotAD]
            #
            Files=[base+ext for ext in ['.fst','.FST','.Fst','.dvr','.Dvr','.DVR'] if os.path.exists(base+ext)]
            if len(Files)==0:
                fst_in=None
                #raise Exception('Error: No .fst file found with name: '+base+'.fst')
            else:
                fst_in=Files[0]


            dfRadED, dfRadAD, dfRadBD= fastlib.spanwisePostPro(fst_in, avgMethod=avgMethod, avgParam=avgParam, out_ext=out_ext, df = self.data)
            dfs_new  = [dfRadAD, dfRadED, dfRadBD]
            names_new=[self.raw_name+'_AD', self.raw_name+'_ED', self.raw_name+'_BD'] 
        return dfs_new, names_new

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
                            try:
                                self.data[c]=pd.to_datetime(self.data[c].values).to_pydatetime()
                                print('Column {} converted to datetime'.format(c))
                            except:
                                # Happens if values are e.g. "Monday, Tuesday"
                                print('Conversion to datetime failed, column {} inferred as string'.format(c))
                        else:
                            print('Column {} inferred as string'.format(c))
                    elif isinstance(y.values[0], (float, int)):
                        try:
                            self.data[c]=self.data[c].astype(float)
                            print('Column {} converted to float (likely nan)'.format(c))
                        except:
                            self.data[c]=self.data[c].astype(str)
                            print('Column {} inferred and converted to string'.format(c))
                    else :
                        print('>> Unknown type:',type(y.values[0]))
            #print(self.data.dtypes)

    def renameColumn(self,iCol,newName):
        self.columns[iCol]=newName
        self.data.columns.values[iCol]=newName

    def deleteColumns(self,ICol):
        """ Delete columns by index, not column names which can have duplicates"""
        IKeep =[i for i in np.arange(self.data.shape[1]) if i not in ICol]
        self.data = self.data.iloc[:, IKeep] # Drop won't work for duplicates
        for i in sorted(ICol, reverse=True):
            del(self.columns[i])
            for f in self.formulas:
                if f['pos'] == (i + 1):
                    self.formulas.remove(f)
                    break
            for f in self.formulas:
                if f['pos'] > (i + 1):
                    f['pos'] = f['pos'] - 1

    def rename(self,new_name):
        self.name='>'+new_name

    def addColumn(self,sNewName,NewCol,i=-1,sFormula=''):
        if i<0:
            i=self.data.shape[1]
        self.data.insert(int(i),sNewName,NewCol)
        self.columns=self.columnsFromDF(self.data)
        for f in self.formulas:
            if f['pos'] > i:
                f['pos'] = f['pos'] + 1
        self.formulas.append({'pos': i+1, 'formula': sFormula, 'name': sNewName})
    
    def setColumn(self,sNewName,NewCol,i,sFormula=''):
        if i<1:
            raise ValueError('Cannot set column at position ' + str(i))
        self.data = self.data.drop(columns=self.data.columns[i-1])
        self.data.insert(int(i-1),sNewName,NewCol)
        self.columns=self.columnsFromDF(self.data)
        for f in self.formulas:
            if f['pos'] == i:
                f['name'] = sNewName
                f['formula'] = sFormula
        
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
            self.addColumn(sNewName,NewCol,i,sFormula)
            return True
    
    def setColumnByFormula(self,sNewName,sFormula,i=-1):
        NewCol=self.evalFormula(sFormula)
        if NewCol is None:
            return False
        else:
            self.setColumn(sNewName,NewCol,i,sFormula)
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
