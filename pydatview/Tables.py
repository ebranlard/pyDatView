import numpy as np
import os.path
from dateutil import parser
import pandas as pd
from pydatview.common import no_unit, ellude_common, getDt, exception2string, PyDatViewException
import pydatview.io as weio # File Formats and File Readers
from pydatview.formulae import evalFormula

# --------------------------------------------------------------------------------}
# --- TabList 
# --------------------------------------------------------------------------------{
class TableList(object): # todo inherit list

    def __init__(self, tabs=None, options=None):
        if tabs is None:
            tabs =[]
        self._tabs  = tabs
        self.hasswap=False

        self.options = self.defaultOptions() if options is None else options

    # --- Options 
    def saveOptions(self, optionts):
        options['naming']   = self.options['naming']
        options['dayfirst'] = self.options['dayfirst']
        
    @staticmethod
    def defaultOptions():
        options={}
        options['naming']   = 'Ellude'
        options['dayfirst'] = False
        return options

    # --- behaves like a list...
    #def __delitem__(self, key):
    #    self.__delattr__(key)

    def __getitem__(self, key):
        return self._tabs[key]

    def __setitem__(self, key, value):
        raise Exception('Setting not allowed')
        self._tabs[key] = value

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
        assert(len(dataframes)==len(names))
        if not bAdd:
            self.clean() # TODO figure it out
        # Returning a list of tables 
        for df,name in zip(dataframes, names):
            if df is not None:
                self.append(Table(data=df, name=name, dayfirst=self.options['dayfirst']))

    def load_tables_from_files(self, filenames=[], fileformats=None, bAdd=False, bReload=False, statusFunction=None):
        """ load multiple files into table list"""
        if not bAdd:
            self.clean() # TODO figure it out
        if bReload:
            self.hasswap=False

        if fileformats is None:
            fileformats=[None]*len(filenames)
        assert type(fileformats) ==list, 'fileformats must be a list'

        # Loop through files, appending tables within files
        warnList=[]
        newTabs=[]
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
                newTabs +=tabs
        
        return newTabs, warnList

    def _load_file_tabs(self, filename, fileformat=None, bReload=False):
        """ load a single file, returns a list (often of size one) of tables """
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

        # --- Creating list of tables here
        if dfs is None:
            pass
        elif not isinstance(dfs,dict):
            if len(dfs)>0:
                tabs=[Table(data=dfs, filename=filename, fileformat=fileformat, dayfirst=self.options['dayfirst'])]
        else:
            for k in list(dfs.keys()):
                if len(dfs[k])>0:
                    tabs.append(Table(data=dfs[k], name=str(k), filename=filename, fileformat=fileformat, dayfirst=self.options['dayfirst']))
        if len(tabs)<=0:
            warn='Warn: No dataframe found in file: '+filename+'\n'
        return tabs, warn

    def reloadOneTab(self, iTab, desired_fileformat=None):
        filename = self._tabs[iTab].filename
        if desired_fileformat is None:
            fileformat = self._tabs[iTab].fileformat
        else:
            raise Exception('TODO figure how to prescirbe the file format on reload')
        if filename is None or len(filename)==0:
            raise Exception('Cannot reload Table as it was not set from a file')

        # Find all the tables that have the same filename. NOTE: some may have been deleted..
        ITab = [iTab for iTab, t in enumerate(self._tabs) if t.filename==filename]

        # Store list of names
        OldNames = [t.name for t in self._tabs if t.filename==filename]

        # Load the file
        tabs, warn = self._load_file_tabs(filename, fileformat=fileformat, bReload=False)
        # Replace in tab list:
        nTabs = len(tabs)
        for i in range(nTabs): 
            if i>=len(ITab):
                # we append
                self._tabs.append(tabs[i])
            else:
                # NOTE we assume that these tables are added succesively, 
                iTab = ITab[i]
                self._tabs[iTab] = tabs[i]
                if not self.hasswap:
                    # If swapped were used, we can't really reuse their old names
                    self._tabs[iTab].name = OldNames[i]

    def haveSameColumns(self,I=None):
        if I is None:
            I=list(range(len(self._tabs)))
        A=[len(self._tabs[i].data.columns)==len(self._tabs[I[0]].data.columns) for i in I ]
        if all(A):
            B=[self._tabs[i].columns_clean==self._tabs[I[0]].columns_clean for i in I] #list comparison
            return all(B)
        else:
            return False

    def renameTable(self, iTab, newName):
        oldName = self._tabs[iTab].name
        if newName in [t.name for t in self._tabs]:
            raise PyDatViewException('Error: This table already exist, choose a different name.')
        # Renaming table
        self._tabs[iTab].rename(newName)
        return oldName

    def swap(self, i1, i2):
        """ Swap two elements of the list"""
        self.hasswap=True
        self._tabs[i1], self._tabs[i2] = self._tabs[i2], self._tabs[i1]

    def sort(self, method='byName'):
        if method=='byName':
            tabnames_display=self.getDisplayTabNames()
            self._tabs = [t for _,t in sorted(zip(tabnames_display,self._tabs))]
        else:
            raise PyDatViewException('Sorting method unknown: `{}`'.format(method))

    def mergeTabs(self, I=None, ICommonColPerTab=None, extrap='nan'):
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
            try:
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
            except:
                # --- Option 0 - Index concatenation 
                print('Using dataframe index concatenation...')
                df = pd.concat(dfs, axis=1)                 
        newName = self._tabs[I[0]].name+'_merged'
        self.append(Table(data=df, name=newName))
        return newName, df

    def vstack(self, I=None, commonOnly=False):
        """ 
        Vertical stacking of tables

        I: index of tables to stack, if None: all tables are stacked
        commonOnly: if True, keep only the common columns. 
                    Otherwise, NaN will be introduced for missing columns
        """
        if I is None:
            I = range(len(self._tabs))
        dfs = [self._tabs[i].data for i in I]

        if commonOnly:
            # --- Concatenate all but keep only common columns
            df = pd.concat(dfs, join='inner', ignore_index=True)
        else:
            # --- Concatenate all, not worrying about common columns
            df = pd.concat(dfs, ignore_index=True)
        # Set unique index
        if 'Index' in df.columns:
            df = df.drop(['Index'], axis=1)
        df.insert(0, 'Index', np.arange(df.shape[0]))
        # Add to table list 
        newName = self._tabs[I[0]].name+'_concat'
        self.append(Table(data=df, name=newName))
        return newName, df



    def deleteTabs(self, I):
        self._tabs = [t for i,t in enumerate(self._tabs) if i not in I]

    def setActiveNames(self,names):
        for t,tn in zip(self._tabs,names):
            t.active_name=tn

    def getDisplayTabNames(self):
        if self.options['naming']=='Ellude':
            # Temporary hack, using last names if all last names are unique
            names = [t.raw_name for t in self._tabs]
            last_names=[n.split('|')[-1] for n in names]
            if len(np.unique(last_names)) == len(names):
                return  ellude_common(last_names)
            else:
                return  ellude_common(names)
        elif self.options['naming']=='FileNames':
            return [os.path.splitext(os.path.basename(t.filename))[0] for t in self._tabs]
        else:
            raise PyDatViewException('Table naming unknown: {}'.format(self.options['naming']))

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

    @property
    def naming(self):
        return self.options['naming']

    @naming.setter
    def naming(self, naming):
        if naming not in ['FileNames', 'Ellude']:
            raise NotImplementedError('Naming',naming)
        self.options['naming']=naming


    def clean(self):
        del self._tabs
        self._tabs=[]

    def __repr__(self):
        return '\n'.join([t.__repr__() for t in self._tabs])

    # --- Mask related
#     @property
#     def maskStrings(self):
#         return [t.maskString for t in self._tabs]
# 
#     @property
#     def commonMaskString(self):
#         maskStrings=set(self.maskStrings)
#         if len(maskStrings) == 1:
#             return next(iter(maskStrings))
#         else:
#             return ''
# 
#     def clearCommonMask(self):
#         for t in self._tabs:
#             t.clearMask()
# 
#     def applyCommonMaskString(self,maskString,bAdd=True):
#         # Apply mask on tablist
#         dfs_new   = []
#         names_new = []
#         errors=[]
#         for i,t in enumerate(self._tabs):
#             try:
#                 df_new, name_new = t.applyMaskString(maskString, bAdd=bAdd)
#                 if df_new is not None: 
#                     # we don't append when string is empty
#                     dfs_new.append(df_new)
#                     names_new.append(name_new)
#             except Exception as e:
#                 errors.append('Mask failed for table: '+t.nickname+'\n'+exception2string(e))
# 
#         return dfs_new, names_new, errors


    # --- Formulas
    def storeFormulas(self):
        formulas = {}
        for tab in self._tabs:
            f = tab.formulas # list of dict('pos','formula','name')
            f = sorted(f, key=lambda k: k['pos']) # Sort formulae by position in list of formua
            formulas[tab.raw_name]=f # we use raw_name as key
        return formulas

    # --- Formulas
    def applyFormulas(self, formulas):
        """ formuals: dict as returned by storeFormulas"""
        for tab in self._tabs:
            if tab.raw_name in formulas.keys():
                for f in formulas[tab.raw_name]:
                    tab.addColumnByFormula(f['name'], f['formula'], f['pos']-1)


#     # --- Resampling TODO MOVE THIS OUT OF HERE OR UNIFY
#     def applyResampling(self,iCol,sampDict,bAdd=True):
#         """ Apply resampling on table list 
#         TODO Make this part of the action
#         """
#         dfs_new   = []
#         names_new = []
#         errors=[]
#         for i,t in enumerate(self._tabs):
#             try:
#                 df_new, name_new = t.applyResampling(iCol, sampDict, bAdd=bAdd)
#                 if df_new is not None: 
#                     # we don't append when string is empty
#                     dfs_new.append(df_new)
#                     names_new.append(name_new)
#             except Exception as e:
#                 errors.append('Resampling failed for table: '+t.nickname+'\n'+exception2string(e))
#         return dfs_new, names_new, errors
# 
#     # --- Filtering  TODO MOVE THIS OUT OF HERE OR UNIFY
#     def applyFiltering(self,iCol,options,bAdd=True):
#         """ Apply filtering on table list 
#         TODO Make this part of the action
#         """
#         dfs_new   = []
#         names_new = []
#         errors=[]
#         for i,t in enumerate(self._tabs):
#             try:
#                 df_new, name_new = t.applyFiltering(iCol, options, bAdd=bAdd)
#                 if df_new is not None: 
#                     # we don't append when string is empty
#                     dfs_new.append(df_new)
#                     names_new.append(name_new)
#             except Exception as e:
#                 errors.append('Filtering failed for table: '+t.nickname+'\n'+exception2string(e))
#         return dfs_new, names_new, errors
# 
#     # --- Radial average related
#     def radialAvg(self,avgMethod,avgParam):
#         """ Apply radial average on table list 
#         TODO Make this part of the action
#         """
#         dfs_new   = []
#         names_new = []
#         errors=[]
#         for i,t in enumerate(self._tabs):
#             try:
#                 dfs, names = t.radialAvg(avgMethod,avgParam)
#                 for df,n in zip(dfs,names):
#                     if df is not None:
#                         dfs_new.append(df)
#                         names_new.append(n)
#             except Exception as e:
#                 errors.append('Radial averaging failed for table: '+t.nickname+'\n'+exception2string(e))
#         return dfs_new, names_new, errors


    @staticmethod
    def createDummy(nTabs=3, n=30, addLabel=True):
        tabs=[]
        label=''
        for iTab in range(nTabs):
            if addLabel:
                label='_'+str(iTab)
            tabs.append( Table.createDummy(n=n, label=label))
        tablist = TableList(tabs)
        return tablist


# --------------------------------------------------------------------------------}
# --- Table 
# --------------------------------------------------------------------------------{
#
class Table(object):
    """ 
    Main attributes:
      - data
      - columns       # TODO get rid of me
      - name
      - raw_name      # Should be unique and can be used for identification
      - ID            # Should be unique and can be used for identification
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
    def __init__(self, data=None, name='', filename='', fileformat=None, dayfirst=False):
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

        if not isinstance(data, pd.DataFrame):
            raise NotImplementedError('Tables that are not dataframe not implemented.')
        
        # --- Modify and store input DataFrame 
        self.setData(data, dayfirst=dayfirst)

        # --- Trying to figure out how to name this table
        if name is None or len(str(name))==0:
            if data.columns.name is not None:
                name=data.columns.name
        self.setupName(name=str(name))

    def setData(self, data, dayfirst=False):
        # Adding index
        if data.columns[0].lower().find('index')>=0:
            pass
        else:
            data.insert(0, 'Index', np.arange(data.shape[0]))

        # Delete empty columns at the end (e.g. csv files)
        while True:
            if data.columns[-1]=='' and data.iloc[:,-1].isnull().all():
                print('[Info] Removing last column because all NaN')
                data=data.iloc[:,:-1]
            else:
                break


        # --- Store in object
        self.data    = data 
        self.convertTimeColumns(dayfirst=dayfirst)

    #def reload(self):
    #    Not Obvious how to do that for files thatreturn several tables
    #    if self.filename is None or len(self.filename)==0:
    #        raise Exception('Cannot reload Table, as it was not set from a file')
    #    print('>>> Table reload')

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
        s+=' - maskString: {}\n'.format(self.maskString)
        return s


    # --- Mask
    def clearMask(self):
        self.maskString=''
        self.mask=None

    def applyMaskString(self, sMask, bAdd=True):
        # Apply mask on Table
        df = self.data
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
                # TODO come up with better error messages
                raise Exception('Error: The mask failed to evaluate for table: '+self.nickname)
            if sum(mask)==0:
                self.clearMask()
                raise PyDatViewException('Error: The mask returned no value for table: '+self.nickname)
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


    def radialAvg(self, avgMethod, avgParam):
        # TODO make this a pluggin
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

            out= fastlib.spanwisePostPro(fst_in, avgMethod=avgMethod, avgParam=avgParam, out_ext=out_ext, df = self.data)
            dfRadED=out['ED_bld']; dfRadAD = out['AD']; dfRadBD = out['BD']

            dfs_new  = [dfRadAD, dfRadED, dfRadBD]
            names_new=[self.raw_name+'_AD', self.raw_name+'_ED', self.raw_name+'_BD'] 
        if all(df is None for df in dfs_new):
            raise PyDatViewException('No OpenFAST radial data found for table: '+self.nickname)
        return dfs_new, names_new

    def changeUnits(self, data=None):
        """ Change units of the table """
        if data is None:
            data={'flavor':'WE'}
        # NOTE: moved to a plugin, but interface kept
        from pydatview.plugins.data_standardizeUnits import changeUnits
        changeUnits(self, data=data)

    def convertTimeColumns(self, dayfirst=False):
        if len(self.data)>0:
            for i,c in enumerate(self.data.columns.values):
                y = self.data.iloc[:,i]
                if y.dtype == object:
                    if isinstance(y.values[0], str):
                        # tring to convert to date
                        try:
                            vals = parser.parse(y.values[0])
                            isDate=True
                        except:
                            if y.values[0]=='NaT':
                                isDate=True
                            else:
                                isDate=False
                        if isDate:
                            print('[INFO] Converting column {} to datetime, dayfirst: {}. May take a while...'.format(c, dayfirst))
                            try:
                                # TODO THIS CAN BE VERY SLOW...
                                self.data[c]=pd.to_datetime(self.data[c].values, dayfirst=dayfirst, infer_datetime_format=True).to_pydatetime()
                                print('       Done.')
                            except:
                                try:
                                    print('[FAIL] Attempting without infer datetime. May take a while...')
                                    self.data[c]=pd.to_datetime(self.data[c].values, dayfirst=dayfirst, infer_datetime_format=False).to_pydatetime()
                                    print('       Done.')
                                except:
                                    # Happens if values are e.g. "Monday, Tuesday"
                                    print('[FAIL] Inferring column as string instead')
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
        self.data.columns.values[iCol]=newName

    def renameColumns(self, strReplDict=None):
        """ Rename all the columns  of given table
        - strReplDict: a string replacement dictionary of the form: {'new':'old'}
        """
        if strReplDict is not None:
            cols = self.data.columns
            newcols = []
            for c in cols:
                for new,old in strReplDict.items():
                    c = c.replace(old,new)
                newcols.append(c)
            self.data.columns = newcols

    def deleteColumns(self, ICol):
        """ Delete columns by index, not column names which can have duplicates"""
        IKeep =[i for i in np.arange(self.data.shape[1]) if i not in ICol]
        self.data = self.data.iloc[:, IKeep] # Drop won't work for duplicates
        # TODO find a way to add a "formula" attribute to a column of a dataframe to avoid dealing with "pos".
        for i in sorted(ICol, reverse=True):
            # Remove formulae if these are part of the columns deleted
            for f in self.formulas:
                if f['pos'] == i:
                    self.formulas.remove(f)
                    break
            # Shift formulae locations due to column being removed
            for f in self.formulas:
                if f['pos'] > i:
                    f['pos'] = f['pos'] - 1

    def rename(self,new_name):
        self.name='>'+new_name

    def addColumn(self, sNewName, NewCol, i=-1, sFormula=''):
        if i<0:
            i=self.data.shape[1]
        elif i>self.data.shape[1]+1:
            i=self.data.shape[1]
        self.data.insert(int(i+1),sNewName,NewCol)
        # Due to new column, formulas position needs to be incremented.
        for f in self.formulas:
            if f['pos'] > i:
                f['pos'] = f['pos'] + 1
        self.formulas.append({'pos': i+1, 'formula': sFormula, 'name': sNewName})
    
    def setColumn(self,sNewName,NewCol,i,sFormula=''):
        if i<1:
            raise ValueError('Cannot set column at position ' + str(i))
        self.data = self.data.drop(columns=self.data.columns[i])
        self.data.insert(int(i),sNewName,NewCol)
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

        isString = c.dtype == object and isinstance(c.values[0], str)
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

    def addColumnByFormula(self, sNewName, sFormulaRaw, i=-1):
        NewCol=evalFormula(self.data, sFormulaRaw)
        if NewCol is None:
            return False
        else:
            self.addColumn(sNewName,NewCol,i,sFormulaRaw)
            return True
    
    def setColumnByFormula(self, sNewName, sFormulaRaw, i=-1):
        NewCol=evalFormula(self.data, sFormulaRaw)
        if NewCol is None:
            return False
        else:
            self.setColumn(sNewName,NewCol,i,sFormulaRaw)
            return True


    def export(self, path, fformat='auto'):
        from pydatview.io.converters import writeDataFrameAutoFormat, writeDataFrameToFormat
        df = self.data
        base, ext = os.path.splitext(path)
        if 'Index' in df.columns.values:
            df = df.drop(['Index'], axis=1)
        if fformat=='auto':
            writeDataFrameAutoFormat(df, path)
        else:
            writeDataFrameToFormat(df, path, fformat=fformat)



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
    def columns(self):
        return self.data.columns.values #.astype(str)

    @columns.setter
    def columns(self, cols):
        raise Exception('Columns is read only')

    @property
    def columns_clean(self):
        return [no_unit(s) for s in self.data.columns.values.astype(str)]

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
    def nickname(self):
        sp = self.name.split('|')
        return sp[-1]

    @property
    def nCols(self):
        return len(self.columns) 

    @property
    def nRows(self):
        return len(self.data.iloc[:,0]) # TODO if not panda
    
    @staticmethod
    def createDummy(n, label='', columns=None, nCols=None):
        """ create a dummy table of length n
        If columns or nCols are provided, they are used for the 
        """
        # 
        if nCols is None and columns is None:
            t       = np.linspace(0, 4*np.pi, n)
            x       = np.sin(t)+10
            alpha_d = np.linspace(0, 360, n)
            P       = np.random.normal(0,100,n)+5000
            RPM     = np.random.normal(-0.2,0.2,n) + 12.
            d={'Time_[s]':t,  
                    'x{}_[m]'.format(label): x, 
                    'alpha{}_[deg]'.format(label):alpha_d,
                    'P{}_[W]'.format(label):P, 
                    'RotSpeed{}_[rpm]'.format(label):RPM}
        else:
            units=['m','m/s','kn','rad','w','deg']
            if columns is None:
                columns = ['C{}{}_[{}]'.format(i,label, units[np.mod(i, len(units))] ) for i in range(nCols)]
            nCols=len(columns)
        
            d = np.zeros((n, nCols))
            for i in range(nCols):
                d[:,i] = np.random.normal(0, 1, n) + i
        df = pd.DataFrame(data=d, columns= columns)
        return Table(data=df, name='Dummy '+label)




if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table
    import numpy as np





