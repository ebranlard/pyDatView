import numpy as np
import os.path
from dateutil import parser
import pandas as pd
try:
    from .common import no_unit, ellude_common, getDt
except:
    from common import no_unit, ellude_common, getDt
import pydatview.io as weio # File Formats and File Readers



# --------------------------------------------------------------------------------}
# --- TabList 
# --------------------------------------------------------------------------------{
class TableList(object): # todo inherit list
    def __init__(self, tabs=None):
        if tabs is None:
            tabs =[]
        self._tabs  = tabs
        self.Naming = 'Ellude'

    # --- behaves like a list...
    def __iter__(self):
        self.__n = 0
        return self

    def __next__(self):
        if self.__n < len(self._tabs):
            self.__n += 1
            return self._tabs[self.__n-1]
        else:
            raise StopIteration

    def __len__(self):
        return len(self._tabs)

    def len(self):
        return len(self._tabs)

    def append(self, t):
        if isinstance(t,list):
            self._tabs += t
        else:
            self._tabs += [t]

    # --- Main high level methods
    def from_dataframes(self, dataframes=[], names=[], bAdd=False):
        if not bAdd:
            self.clean() # TODO figure it out
        # Returning a list of tables 
        for df,name in zip(dataframes, names):
            if df is not None:
                self.append(Table(data=df, name=name))

    def load_tables_from_files(self, filenames=[], fileformats=None, bAdd=False, bReload=False, statusFunction=None):
        """ load multiple files into table list"""
        if not bAdd:
            self.clean() # TODO figure it out

        if fileformats is None:
            fileformats=[None]*len(filenames)
        assert type(fileformats) ==list, 'fileformats must be a list'

        # Loop through files, appending tables within files
        warnList=[]
        for i, (f,ff) in enumerate(zip(filenames, fileformats)):
            if statusFunction is not None:
                statusFunction(i)
            if f in self.unique_filenames:
                warnList.append('Warn: Cannot add a file already opened ' + f)
            elif len(f)==0:
                pass
                #    warn+= 'Warn: an empty filename was skipped' +'\n'
            else:
                tabs, warnloc = self._load_file_tabs(f,fileformat=ff, bReload=bReload) 
                if len(warnloc)>0:
                    warnList.append(warnloc)
                self.append(tabs)
        
        return warnList

    def _load_file_tabs(self, filename, fileformat=None, bReload=False):
        """ load a single file, adds table """
        # Returning a list of tables 
        tabs=[]
        warn=''
        if not os.path.isfile(filename):
            warn = 'Error: File not found: `'+filename+'`\n'
            return tabs, warn

        fileformatAllowedToFailOnReload = (fileformat is not None) and bReload
        if fileformatAllowedToFailOnReload:
            try:
                F = fileformat.constructor(filename=filename)
                dfs = F.toDataFrame()
            except:
                warnLoc = 'Failed to read file:\n\n   {}\n\nwith fileformat: {}\n\nIf you see this message, the reader tried again and succeeded with "auto"-fileformat.\n\n'.format(filename, fileformat.name)
                tabs,warn = self._load_file_tabs(filename, fileformat=None, bReload=False)
                return tabs, warnLoc+warn

        else:

            try:
                #F = weio.read(filename, fileformat = fileformat)
                # --- Expanded version of weio.read
                F = None
                if fileformat is None:
                    fileformat, F = weio.detectFormat(filename)
                # Reading the file with the appropriate class if necessary
                if not isinstance(F, fileformat.constructor):
                    F=fileformat.constructor(filename=filename)
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
                tabs=[Table(data=dfs, filename=filename, fileformat=fileformat)]
        else:
            for k in list(dfs.keys()):
                if len(dfs[k])>0:
                    tabs.append(Table(data=dfs[k], name=str(k), filename=filename, fileformat=fileformat))
        if len(tabs)<=0:
            warn='Warn: No dataframe found in file: '+filename+'\n'
        return tabs, warn

    def getTabs(self):
        # TODO remove me later
        return self._tabs


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

    def mergeTabs(self, I=None, ICommonColPerTab=None, samplDict=None, extrap='nan'):
        """ 
        Merge table together.
        TODO: add options for how interpolation/merging is done

        I: index of tables to merge, if None: all tables are merged
        """
        from pydatview.tools.signal_analysis import interpDF
        #from pydatview.tools.signal_analysis import applySampler
        #df_new, name_new = t.applyResampling(iCol,sampDict, bAdd=bAdd)
        if I is None:
            I = range(len(self._tabs))

        dfs = [self._tabs[i].data for i in I]
        if ICommonColPerTab is None:
            # --- Option 0 - Index concatenation 
            print('Using dataframe index concatenation...')
            df = pd.concat(dfs, axis=1)
            # Remove duplicated columns
            #df = df.loc[:,~df.columns.duplicated()].copy()
        else:
            # --- Option 1 - We combine all the x from the common column together 
            # NOTE: We use unique and sort, which will distrupt the user data (e.g. Airfoil Coords)
            #       The user should then use other methods (when implemented)
            x_new=[]
            cols = []
            for it, icol in  zip(I, ICommonColPerTab):
                xtab = self._tabs[it].data.iloc[:, icol].values
                cols.append(self._tabs[it].data.columns[icol])
                x_new = np.concatenate( (x_new, xtab) ) 
            x_new = np.unique(np.sort(x_new)) 
            # Create interpolated dataframes based on x_new
            dfs_new = []
            for i, (col, df_old) in enumerate(zip(cols, dfs)):
                df = interpDF(x_new, col, df_old, extrap=extrap)
                if 'Index' in df.columns:
                    df = df.drop(['Index'], axis=1)
                if i>0:
                    df = df.drop([col], axis=1)
                dfs_new.append(df)
            df = pd.concat(dfs_new, axis=1)
            # Reindex at the end
            df.insert(0, 'Index', np.arange(df.shape[0]))
        newName = self._tabs[I[0]].name+'_merged'
        self.append(Table(data=df, name=newName))
        return newName, df

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

    # --- Properties
    @property
    def tabNames(self):
        return [t.name for t in self._tabs]

    @property
    def filenames(self):
        return [t.filename for t in self._tabs]

    @property
    def fileformats(self):
        return [t.fileformat for t in self._tabs]

    @property
    def unique_filenames(self):
        return list(set([t.filename for t in self._tabs]))

    @property
    def filenames_and_formats(self):
        """ return unique list of filenames with associated fileformats """
        filenames   = []
        fileformats = []
        for t in self._tabs:
            if t.filename not in filenames:
                filenames.append(t.filename)
                fileformats.append(t.fileformat)
        return filenames, fileformats

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
        # Apply mask on tablist
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

    # --- Resampling TODO MOVE THIS OUT OF HERE OR UNIFY
    def applyResampling(self,iCol,sampDict,bAdd=True):
        dfs_new   = []
        names_new = []
        errors=[]
        for i,t in enumerate(self._tabs):
#             try:
            df_new, name_new = t.applyResampling(iCol, sampDict, bAdd=bAdd)
            if df_new is not None: 
                # we don't append when string is empty
                dfs_new.append(df_new)
                names_new.append(name_new)
#             except:
#                 errors.append('Resampling failed for table: '+t.active_name) # TODO
        return dfs_new, names_new, errors

    # --- Filtering  TODO MOVE THIS OUT OF HERE OR UNIFY
    def applyFiltering(self,iCol,options,bAdd=True):
        dfs_new   = []
        names_new = []
        errors=[]
        for i,t in enumerate(self._tabs):
#             try:
            df_new, name_new = t.applyFiltering(iCol, options, bAdd=bAdd)
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
#
class Table(object):
    """ 
    Main attributes:
      - data
      - columns
      - name
      - raw_name 
      - active_name
      - filename   
      - fileformat 
      - fileformat_name
      - nCols x nRows 
      - mask
      - maskString
      - formulas
    """
    # TODO sort out the naming
    # Main naming concepts:
    #    name        : 
    #    active_name : 
    #    raw_name    : 
    #    filename    : 
    def __init__(self,data=None,name='',filename='',columns=[], fileformat=None):
        # Default init
        self.maskString=''
        self.mask=None

        self.filename        = filename
        self.fileformat      = fileformat
        if fileformat is not None:
            self.fileformat_name = fileformat.name
        else:
            self.fileformat_name = ''
        self.formulas = []

        if not isinstance(data,pd.DataFrame):
            # ndarray??
            raise NotImplementedError('Tables that are not dataframe not implemented.')
        else:
            # --- Pandas DataFrame 
            self.data    = data 
            # Adding index
            if data.columns[0].lower().find('index')>=0:
                pass
            else:
                data.insert(0, 'Index', np.arange(self.data.shape[0]))
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
        s='Table object:\n'
        s+=' - name: {}\n'.format(self.name)
        s+=' - raw_name   : {}\n'.format(self.raw_name)
        s+=' - active_name: {}\n'.format(self.raw_name)
        s+=' - filename   : {}\n'.format(self.filename)
        s+=' - fileformat : {}\n'.format(self.fileformat)
        s+=' - fileformat_name : {}\n'.format(self.fileformat_name)
        s+=' - columns    : {}\n'.format(self.columns)
        s+=' - nCols x nRows: {}x{}\n'.format(self.nCols, self.nRows)
        return s

    def columnsFromDF(self,df):
        return [s.replace('_',' ') for s in df.columns.values.astype(str)]

    # --- Mask
    def clearMask(self):
        self.maskString=''
        self.mask=None

    def applyMaskString(self, sMask, bAdd=True):
        # Apply mask on Table
        df = self.data
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
                    self.maskString=sMask
            except:
                raise Exception('Error: The mask failed for table: '+self.name)
            if sum(mask)==0:
                self.clearMask()
                raise Exception('Error: The mask returned no value for table: '+self.name)
        return df_new, name_new

    # --- Important manipulation TODO MOVE THIS OUT OF HERE OR UNIFY
    def applyResampling(self, iCol, sampDict, bAdd=True):
        # Resample Table
        from pydatview.tools.signal_analysis import applySamplerDF
        colName=self.data.columns[iCol]
        df_new =applySamplerDF(self.data, colName, sampDict=sampDict)
        # Reindex afterwards
        if df_new.columns[0]=='Index':
            df_new['Index'] = np.arange(0,len(df_new))
        if bAdd:
            name_new=self.raw_name+'_resampled'
        else:
            name_new=None
            self.data=df_new
        return df_new, name_new

    def applyFiltering(self, iCol, options, bAdd=True):
        from pydatview.tools.signal_analysis import applyFilterDF
        colName=self.data.columns[iCol]
        df_new =applyFilterDF(self.data, colName, options)
        # Reindex afterwards
        if df_new.columns[0]=='Index':
            df_new['Index'] = np.arange(0,len(df_new))
        if bAdd:
            name_new=self.raw_name+'_filtered'
        else:
            name_new=None
            self.data=df_new
        return df_new, name_new


    def radialAvg(self,avgMethod, avgParam):
        import pydatview.fast.postpro as fastlib
        import pydatview.fast.fastfarm as fastfarm
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

    def changeUnits(self, flavor='WE'):
        """ Change units of the table """
        # NOTE: moved to a plugin, but interface kept
        from pydatview.plugins.data_standardizeUnits import changeUnits
        changeUnits(self, flavor=flavor)

    def convertTimeColumns(self):
        if len(self.data)>0:
            for i,c in enumerate(self.data.columns.values):
                y = self.data.iloc[:,i]
                if y.dtype == object:
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


    # --- Column manipulations
    def renameColumn(self,iCol,newName):
        self.columns[iCol]=newName
        self.data.columns.values[iCol]=newName

    def deleteColumns(self, ICol):
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

    def addColumn(self, sNewName, NewCol, i=-1, sFormula=''):
        print('>>> adding Column')
        if i<0:
            i=self.data.shape[1]
        elif i>self.data.shape[1]+1:
            i=self.data.shape[1]
        self.data.insert(int(i+1),sNewName,NewCol)
        self.columns=self.columnsFromDF(self.data)
        for f in self.formulas:
            if f['pos'] > i:
                f['pos'] = f['pos'] + 1
        self.formulas.append({'pos': i+1, 'formula': sFormula, 'name': sNewName})
    
    def setColumn(self,sNewName,NewCol,i,sFormula=''):
        if i<1:
            raise ValueError('Cannot set column at position ' + str(i))
        self.data = self.data.drop(columns=self.data.columns[i])
        self.data.insert(int(i),sNewName,NewCol)
        self.columns=self.columnsFromDF(self.data)
        for f in self.formulas:
            if f['pos'] == i:
                f['name'] = sNewName
                f['formula'] = sFormula
        
    def getColumn(self, i):
        """ Return column of data
        If a mask exist, the mask is applied

        TODO TODO TODO get rid of this!
        """
        if self.mask is not None:
            c = self.data.iloc[self.mask, i]
            x = self.data.iloc[self.mask, i].values
        else:
            c = self.data.iloc[:, i]
            x = self.data.iloc[:, i].values

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
        for i,c in enumerate(self.columns):
            c_no_unit = no_unit(c).strip()
            c_in_df   = df.columns[i]
            sFormula=sFormula.replace('{'+c_no_unit+'}','df[\''+c_in_df+'\']')
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


    def export(self, path):
        if isinstance(self.data, pd.DataFrame):
            df = self.data.drop('Index', axis=1)
            df.to_csv(path, sep=',', index=False)
        else:
            raise NotImplementedError('Export of data that is not a dataframe')



    # --- Properties
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

