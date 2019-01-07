from __future__ import division, unicode_literals, print_function, absolute_import
from builtins import map, range, chr, str
from io import open
from future import standard_library
standard_library.install_aliases()

import wx
import dateutil # required by matplotlib
import matplotlib
matplotlib.use('Agg') # Important for Windows version of installer
from matplotlib import rc as matplotlib_rc
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.figure import Figure
from matplotlib.pyplot import rcParams as pyplot_rc
from matplotlib.widgets import Cursor
#from matplotlib import pyplot as plt
import numpy as np
import os.path 
import pandas as pd
import sys
import traceback 
from dateutil import parser
import gc

from .GUIMultiSplit import MultiSplit
from .spectral import pwelch, hamming , boxcar, hann, fnextpow2
import weio # File Formats and File Readers



# --------------------------------------------------------------------------------}
# --- GLOBAL 
# --------------------------------------------------------------------------------{
PROG_NAME='pyDatView'
PROG_VERSION='v0.1-local'
try:
    FILE_FORMATS            = weio.fileFormats()
except:
    print('')
    print('Error: the python package `weio` was not imported successfully.\n')
    print('Most likely the submodule `weio` was not cloned with `pyDatView`')
    print('Type the following command to retrieve it:\n')
    print('   git submodule update --init --recursive\n')
    print('Alternatively re-clone this repository into a separate folder:\n')
    print('   git clone --recurse-submodules https://github.com/ebranlard/pyDatView\n')
    sys.exit(-1)
FILE_FORMATS_EXTENSIONS = [['.*']]+[f.extensions for f in FILE_FORMATS]
FILE_FORMATS_NAMES      = ['auto (any supported file)'] + [f.name for f in FILE_FORMATS]
FILE_FORMATS_NAMEXT     =['{} ({})'.format(n,','.join(e)) for n,e in zip(FILE_FORMATS_NAMES,FILE_FORMATS_EXTENSIONS)]
FILE_READER             = weio.read

SIDE_COL = [150,150,280,400]

#matplotlib.rcParams['text.usetex'] = False
# matplotlib.rcParams['font.sans-serif'] = 'DejaVu Sans'
#matplotlib.rcParams['font.family'] = 'Arial'
#matplotlib.rcParams['font.sans-serif'] = 'Arial'
# matplotlib.rcParams['font.family'] = 'sans-serif'

font = {'size'   : 9}
matplotlib_rc('font', **font)
pyplot_rc['agg.path.chunksize'] = 20000
def getMonoFont():
    return wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Monospace')

# --------------------------------------------------------------------------------}
# --- Helper functions
# --------------------------------------------------------------------------------{
def YesNo(parent, question, caption = 'Yes or no?'):
    dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_YES
    dlg.Destroy()
    return result
def Info(parent, message, caption = 'Info'):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()
def Warn(parent, message, caption = 'Warning!'):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_WARNING)
    dlg.ShowModal()
    dlg.Destroy()
def Error(parent, message, caption = 'Error!'):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()
    dlg.Destroy()

def getColumn(df,i):
    if i == wx.NOT_FOUND or i == 0:
        x = np.array(range(len(df.iloc[:, 1])))
        c = None
        isString = False
        isDate   = False
    else:
        c = df.iloc[:, i-1]
        x = df.iloc[:, i-1].values
        isString = c.dtype == np.object and isinstance(c.values[0], str)
        isDate   = np.issubdtype(c.dtype, np.datetime64)
        if isDate:
            x=x.astype('datetime64[s]')

    return x,isString,isDate,c

def pretty_time(t):
    # fPrettyTime: returns a 6-characters string corresponding to the input time in seconds.
    #   fPrettyTime(612)=='10m12s'
    # AUTHOR: E. Branlard
    if(t<0):
        s='------';
    elif (t<1) :
        c=np.floor(t*100);
        s='{:2d}.{:02d}s'.format(0,int(c))
    elif(t<60) :
        s=np.floor(t);
        c=np.floor((t-s)*100);
        s='{:2d}.{:02d}s'.format(int(s),int(c))
    elif(t<3600) :
        m=np.floor(t/60);
        s=np.mod( np.floor(t), 60);
        s='{:2d}m{:02d}s'.format(int(m),int(s))
    elif(t<86400) :
        h=np.floor(t/3600);
        m=np.floor(( np.mod( np.floor(t) , 3600))/60);
        s='{:2d}h{:02d}m'.format(int(h),int(m))
    elif(t<8553600) : #below 3month
        d=np.floor(t/86400);
        h=np.floor( np.mod(np.floor(t), 86400)/3600);
        s='{:2d}d{:02d}h'.format(int(d),int(h))
    elif(t<31536000):
        m=t/(3600*24*30.5);
        s='{:4.1f}mo'.format(m)
        #s='+3mon.';
    else:
        y=t/(3600*24*365.25);
        s='{:.1f}y'.format(y)
    return s

def common_start(*strings):
    """ Returns the longest common substring
        from the beginning of the `strings`
    """
    if len(strings)==1:
        strings=tuple(strings[0])
    def _iter():
        for z in zip(*strings):
            if z.count(z[0]) == len(z):  # check all elements in `z` are the same
                yield z[0]
            else:
                return
    return ''.join(_iter())

def common_end(*strings):
    if len(strings)==1:
        strings=strings[0]
    else:
        strings=list(strings)
    strings = [s[-1::-1] for s in strings]
    return common_start(strings)[-1::-1]


def ellude_common(strings):
    # Selecting only the strings that do not start with the safe '>' char
    S = [s for i,s in enumerate(strings) if ((len(s)>0) and (s[0]!= '>'))]
    if len(S)==1:
        ns=S[0].rfind('|')+1
        ne=0;
    else:
        ss = common_start(S)
        se = common_end(S)
        iu = ss[:-1].rfind('_')
        ip = ss[:-1].rfind('_')
        if iu > 0:
            if ip>0:
                if iu>ip:
                    ss=ss[:iu+1]
            else:
                ss=ss[:iu+1]

        iu = se[:-1].find('_')
        if iu > 0:
            se=se[iu:]
        iu = se[:-1].find('.')
        if iu > 0:
            se=se[iu:]
        ns=len(ss)     
        ne=len(se)     

    for i,s in enumerate(strings):
        if len(s)>0 and s[0]=='>':
            strings[i]=s[1:]
        else:
            s=s[ns:]
            if ne>0:
                s = s[:-ne]
            strings[i]=s.lstrip('_')
            if len(strings[i])==0:
                strings[i]='tab{}'.format(i)
    return strings

def no_unit(s):
    iu=s.rfind(' [')
    if iu>1:
        return s[:iu]
    else:
        return s


# --------------------------------------------------------------------------------}
# --- Table 
# --------------------------------------------------------------------------------{
class Table(object):
    def __init__(self,data=[],columns=[],name='',filename='',df=None):
        if df is not None:
            # pandas
            if len(name)==0:
                self.name=df.column.name
            else:
                self.name=name
            self.data    = df
            self.columns = [s.replace('_',' ') for s in df.columns.values]
        else: 
            # ndarray??
            raise Exception('Implementation of tables with ndarray dropped for now')
        self.filename = filename
        #self.name=os.path.dirname(filename)+'|'+os.path.splitext(os.path.basename(self.filename))[0]+'|'+ self.name
        self.name=os.path.splitext(self.filename)[0].replace('/','|').replace('\\','|')+'|'+ self.name
        
        self.convertTimeColumns()

    def __repr__(self):
        return 'Tab {} ({}x{})'.format(self.name,self.nCols,self.nRows)

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

    def rename(self,new_name):
        self.name='>'+new_name

    @property
    def columns_clean(self):
        return [no_unit(s) for s in self.columns]

    @property
    def name(self):
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
# --- Drag and drop 
# --------------------------------------------------------------------------------{
# Implement File Drop Target class
class FileDropTarget(wx.FileDropTarget):
   def __init__(self, parent):
      wx.FileDropTarget.__init__(self)
      self.parent = parent
   def OnDropFiles(self, x, y, filenames):
      filenames = [f for f in filenames if not os.path.isdir(f)]
      if len(filenames)>0:
          # TODO detect if ctrl is held for bAdd or not
          self.parent.load_files(filenames,fileformat=None,bAdd=True)
      return True


# --------------------------------------------------------------------------------}
# --- Popup menus
# --------------------------------------------------------------------------------{
class TablePopup(wx.Menu):
    def __init__(self, mainframe, parent):
        wx.Menu.__init__(self)
        self.parent = parent
        self.mainframe = mainframe
        self.ISel = self.parent.GetSelections()

        if len(self.ISel)>0:
            item = wx.MenuItem(self, -1, "Delete")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnDelete, item)

        if len(self.ISel)==1:
            item = wx.MenuItem(self, -1, "Rename")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnRename, item)

        if len(self.ISel)==1:
            item = wx.MenuItem(self, -1, "Export")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnExport, item)

    def OnDelete(self, event):
        self.mainframe.deleteTabs(self.ISel)

    def OnRename(self, event):
        oldName = self.parent.GetString(self.ISel[0])
        dlg = wx.TextEntryDialog(self.parent, 'New table name:', 'Rename table',oldName,wx.OK|wx.CANCEL)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            newName=dlg.GetValue()
            self.mainframe.renameTable(self.ISel[0],newName)

    def OnExport(self, event):
        self.mainframe.exportTab(self.ISel[0]);

class ColumnPopup(wx.Menu):
    def __init__(self, parent):
        wx.Menu.__init__(self)
        self.parent = parent
        self.ISel = self.parent.lbColumns.GetSelections()

        if len(self.ISel)>=1 and self.ISel[0]>0: 
            item = wx.MenuItem(self, -1, "Rename")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnRename, item)

    def OnRename(self, event):
        oldName = self.parent.lbColumns.GetString(self.ISel[0])
        dlg = wx.TextEntryDialog(self.parent, 'New column name:', 'Rename column',oldName,wx.OK|wx.CANCEL)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            newName=dlg.GetValue()
            self.parent.tab.renameColumn(self.ISel[0]-1,newName)
            self.parent.updateColumn(self.ISel[0],newName) #faster
            self.parent.selPanel.updateLayout()
            # a trigger for the plot is required but skipped for now

#     def OnDelete(self, event):
#         ISel=self.parent.GetSelections()
#         print("Column delete event",ISel)

# --------------------------------------------------------------------------------}
# --- InfoPanel 
# --------------------------------------------------------------------------------{
class InfoPanel(wx.Panel):
    """ Display the list of the columns for the user to select """
    def __init__(self, parent):
        # Superclass constructor
        super(InfoPanel,self).__init__(parent)
        # GUI
        self.tInfo = wx.TextCtrl(self,size = (200,5),style = wx.TE_MULTILINE)
        self.tInfo.SetFont(getMonoFont())

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tInfo, 2, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)
        self.SetMaxSize((-1, 50))

    def showStats(self,files,tabs,ITab,ColIndexes,ColNames,iX,erase=False):
        if erase:
            self.clean()
#        if files is not None:
#            for i,f in enumerate(files):
#                self.tInfo.AppendText('File {}: {}\n'.format(i,f))
#
        for iTab in ITab:
            tab = tabs[iTab]
            x,_,_,_=getColumn(tab.data,iX)
            for i,s in zip(ColIndexes,ColNames):
                y,yIsString,yIsDate,_=getColumn(tab.data,i)
                if yIsString:
                    self.tInfo.AppendText('{:15s} (string) first:{}  last:{}  min:{}  max:{}\n'.format(s,y[0],y[-1],min(y,key=len),max(y,key=len)))
                elif yIsDate:
                    dt0=y[1]-y[0]
                    dt    = pretty_time(np.timedelta64((y[1]-y[0]),'s').item().total_seconds())
                    dtAll = pretty_time(np.timedelta64((y[-1]-y[0]),'s').item().total_seconds())
                    self.tInfo.AppendText('{:15s} (date) first:{} last:{} dt:{} range:{}\n'.format(s,y[0],y[-1],dt,dtAll))
                else:
                    #self.tInfo.AppendText('{:15s} mean:{:10.3e}  std:{:10.3e}  min:{:10.3e}  max:{:10.3e}  dx:{:10.3e}  n:{:d}\n'.format(s,np.nanmean(y),np.nanstd(y),np.nanmin(y),np.nanmax(y),x[1]-x[0],len(y) ))
                    self.tInfo.AppendText('{:15s} mean:{:10.3e}  std:{:10.3e}  min:{:10.3e}  max:{:10.3e}\n'.format(s,np.nanmean(y),np.nanstd(y),np.nanmin(y),np.nanmax(y),x[1]-x[0],len(y) ))
        self.tInfo.ShowPosition(0)

    def clean(self):
        self.tInfo.SetValue("")

        
# --------------------------------------------------------------------------------}
# --- ColumnPanel
# --------------------------------------------------------------------------------{
class ColumnPanel(wx.Panel):
    """ A list of columns for x and y axis """
    def __init__(self, parent, selPanel):
        # Superclass constructor
        super(ColumnPanel,self).__init__(parent)
        self.selPanel = selPanel;
        # Data
        self.tab=[]
        # GUI
        self.comboX = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        self.comboX.SetFont(getMonoFont())
        self.lbColumns=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED )
        self.lbColumns.SetFont(getMonoFont())
        # Events
        self.lbColumns.Bind(wx.EVT_RIGHT_DOWN, self.OnColPopup)
        # Layout
        sizerX = wx.BoxSizer(wx.HORIZONTAL)
        sizerX.Add(self.comboX   , 0, flag=wx.TOP | wx.BOTTOM | wx.EXPAND, border=5)
        sizerCol = wx.BoxSizer(wx.VERTICAL)
        sizerCol.Add(sizerX        , 0, border=5)
        sizerCol.Add(self.lbColumns, 2, flag=wx.EXPAND, border=0)
        self.SetSizer(sizerCol)
        
    def OnColPopup(self,event):
        menu = ColumnPopup(self)
        self.PopupMenu(menu, event.GetPosition())
        menu.Destroy()

    def getDefaultColumnX(self,tab,nColsMax):
        # Try the first column for x-axis, except if it's a string
        iSelect = min(1,nColsMax)
        _,isString,_,_=getColumn(tab.data,iSelect)
        if isString:
            iSelect = 0 # we roll back and select the index
        return iSelect

    def getDefaultColumnY(self,tab,nColsMax):
        # Try the first column for x-axis, except if it's a string
        iSelect = min(2,nColsMax)
        _,isString,_,_=getColumn(tab.data,iSelect)
        if isString:
            iSelect = 0 # we roll back and select the index
        return iSelect

    def setTab(self,tab,xSel=-1,ySel=[]):
        """ Set the table used for the columns, update the GUI """
        self.tab=tab;
        self.setColumnNames(xSel,ySel)

    def updateColumnNames(self):
        """ Update of column names from table, keeping selection """
        xSel,ySel,_,_ = self.getColumnSelection()
        self.setColumnNames(xSel,ySel)

    def updateColumn(self,i,newName):
        """ Update of one column name"""
        self.lbColumns.SetString(i,newName)
        self.comboX.SetString(i,newName)

    def setColumnNames(self,xSel=-1,ySel=[]):
        """ Set columns from table """
        # Populating..
        columns=['Index']+self.tab.columns
        self.lbColumns.Set(columns)
        self.comboX.Set(columns)
        # Restoring previous selection
        for i in ySel:
            if i<len(columns):
                self.lbColumns.SetSelection(i)
                self.lbColumns.EnsureVisible(i)
        if len(self.lbColumns.GetSelections())<=0:
            self.lbColumns.SetSelection(self.getDefaultColumnY(self.tab,len(columns)))
        if (xSel<0) or xSel>len(columns):
            self.comboX.SetSelection(self.getDefaultColumnX(self.tab,len(columns)))
        else:
            self.comboX.SetSelection(xSel)

    def forceOneSelection(self):
        ISel=self.lbColumns.GetSelections()
        self.lbColumns.SetSelection(-1)
        if len(ISel)>0:
            self.lbColumns.SetSelection(ISel[0])

    def empty(self):
        self.lbColumns.Clear()
        self.comboX.Clear()

    def getColumnSelection(self):
        iX = self.comboX.GetSelection()
        sX = self.comboX.GetStringSelection()
        IY = self.lbColumns.GetSelections()
        SY = [self.lbColumns.GetString(i) for i in IY]
        return iX,IY,sX,SY


# --------------------------------------------------------------------------------}
# --- Table Panel
# --------------------------------------------------------------------------------{
class TablePanel(wx.Panel):
    """ Display list of tables """
    def __init__(self, parent):
        # Superclass constructor
        super(TablePanel,self).__init__(parent)
        # DATA
        label = wx.StaticText( self, -1, 'Tables: ')
        self.lbTab=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED)
        self.lbTab.SetFont(getMonoFont())
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, border=5)
        sizer.Add(self.lbTab, 2, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)

    def setTabNames(self,tabnames):    
        self.lbTab.Set(tabnames)

    def empty(self):    
        self.lbTab.Clear()


# --------------------------------------------------------------------------------}
# --- Selection Panel 
# --------------------------------------------------------------------------------{
SEL_MODES    = ['auto','Same tables'    ,'Different tables'  ]
SEL_MODES_ID = ['auto','sameColumnsMode','twoColumnsMode']

class SelectionPanel(wx.Panel):
    """ Display options for the user to select data """
    def __init__(self, parent, tabs, mode='auto'):
        # Superclass constructor
        super(SelectionPanel,self).__init__(parent)
        # DATA
        self.tabs          = []
        self.itabForCol    = None
        self.parent        = parent
        self.tabSelections = {}
        self.tabSelected   = []
        self.modeRequested = mode

        # GUI DATA
        self.splitter  = MultiSplit(self, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(70)
        self.tabPanel  = TablePanel (self.splitter);
        self.colPanel1 = ColumnPanel(self.splitter, self);
        self.colPanel2 = ColumnPanel(self.splitter, self);
        self.tabPanel.Hide()
        self.colPanel1.Hide()
        self.colPanel2.Hide()

        # Layout
        self.updateLayout()
        VertSizer = wx.BoxSizer(wx.VERTICAL)
        VertSizer.Add(self.splitter, 2, flag=wx.EXPAND, border=0)
        self.SetSizer(VertSizer)

        # TRIGGERS
        if len(tabs)>0:
            #print(tabs)
            self.updateTables(tabs)
            self.selectDefaultTable()
            # TODO
            #self.colPanel1.selectDefaultColumns(self.tabs[self.itabForCol])

    def updateLayout(self,mode=None):
        if mode is None:
            mode=self.modeRequested
        else:
            self.modeRequested = mode
        if mode=='auto':
            self.autoMode()
        elif mode=='sameColumnsMode':
            self.sameColumnsMode()
        elif mode=='twoColumnsMode':
            self.twoColumnsMode()
        else:
            raise Exception('Wrong mode for selection layout: {}'.format(self.mode))


    def autoMode(self):
        if hasattr(self,'tabs'):
            if len(self.tabs)<=0:
                self._mode='auto'
                self.splitter.removeAll()
            elif len(self.tabs)==1:
                self.sameColumnsMode()
            else:
                if haveSameColumns(self.tabs):
                    self.sameColumnsMode()
                else:
                    self.twoColumnsMode()

    def sameColumnsMode(self):
        self._mode='sameColumnsMode'
        self.splitter.removeAll()
        if hasattr(self,'tabs'):
            if len(self.tabs)>1:
                self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel1) 

    def twoColumnsMode(self):
        self._mode='twoColumnsMode'
        self.splitter.removeAll()
        self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel2) 
        self.splitter.AppendWindow(self.colPanel1) 
        self.splitter.setEquiSash()
        #self.parent.GetParent().GetParent().GetParent().resizeSideColumn(SIDE_COL_LARGE)

    def updateTables(self,tabs):
        """ Update the list of tables, while keeping the selection if any """
        # TODO PUT ME IN TABLE PANEL
        #print('UPDATING TABLES')
        # Emptying GUI - TODO only if needed
        self.colPanel1.empty()
        self.colPanel2.empty()
        # Adding
        self.tabs = tabs
        tabnames =[t.name for t in tabs]
        raw_names=[t.raw_name for t in tabs]
        etabnames=ellude_common(raw_names)
        self.tabPanel.setTabNames(etabnames);
        for tn in tabnames:
            if tn not in self.tabSelections.keys():
                self.tabSelections[tn]={'xSel':-1,'ySel':[]}
            else:
                pass # do nothing

        # Reselecting
        if len(self.tabSelected)>0:        
            # Removed line below since two column mode implemented
            #if not haveSameColumns(tabs,ISel):
            #    ISel=[ISel[0]]
            for i in self.tabSelected:
                if i<len(tabs):
                    self.tabPanel.lbTab.SetSelection(i)
            #
        if len(self.tabPanel.lbTab.GetSelections())==0:
            self.selectDefaultTable()
        if len(self.tabs)>0:
            # Trigger - updating columns and layout
            ISel=self.tabPanel.lbTab.GetSelections()
            self.tabSelected=ISel
            if len(ISel)>=2:
                self.setTabForCol(ISel[0],1)
                self.setTabForCol(ISel[1],2)
            else:
                self.setTabForCol(ISel[0],1)
        self.updateLayout(self.modeRequested)

    def setTabForCol(self,iTabSel,iPanel):
        t  = self.tabs[iTabSel]
        ts = self.tabSelections[t.name]
        if iPanel==1:
            self.colPanel1.setTab(t,ts['xSel'],ts['ySel'])
        elif iPanel==2:
            self.colPanel2.setTab(t,ts['xSel'],ts['ySel'])
        else:
            raise Exception('Wrong ipanel')

    def selectDefaultTable(self):
        # Selecting the first table
        if self.tabPanel.lbTab.GetCount()>0:
            self.tabPanel.lbTab.SetSelection(0)
            self.tabSelected=[0]
        else:
            self.tabSelected=[]


    def update_tabs(self, tabs):
        self.updateTables(tabs)

    def renameTable(self,iTab, oldName, newName):
        #self.printSelection()
        self.tabSelections[newName] = self.tabSelections.pop(oldName)
        raw_names=[t.raw_name for t in self.tabs]
        etabnames=ellude_common(raw_names)
        self.tabPanel.setTabNames(etabnames);
        #self.printSelection()

    def saveSelection(self):
        #self.ISel=self.tabPanel.lbTab.GetSelections()
        ISel=self.tabSelected # 
        #print('Saving selection, tabSelected were:',self.tabSelected)
        if haveSameColumns(self.tabs,ISel):
            for ii in ISel:
                t=self.tabs[ii]
                self.tabSelections[t.name]['xSel'] = self.colPanel1.comboX.GetSelection()
                self.tabSelections[t.name]['ySel'] = self.colPanel1.lbColumns.GetSelections()
        else:
            if len(ISel)>=1:
                t=self.tabs[ISel[0]]
                self.tabSelections[t.name]['xSel'] = self.colPanel1.comboX.GetSelection()
                self.tabSelections[t.name]['ySel'] = self.colPanel1.lbColumns.GetSelections()
            if len(ISel)>=2:
                t=self.tabs[ISel[1]]
                self.tabSelections[t.name]['xSel'] = self.colPanel2.comboX.GetSelection()
                self.tabSelections[t.name]['ySel'] = self.colPanel2.lbColumns.GetSelections()
        self.tabSelected = self.tabPanel.lbTab.GetSelections();

    def printSelection(self):
        print('Number of tabSelections stored:',len(self.tabSelections))
        TS=self.tabSelections
        for i,t in enumerate(self.tabs):
            tn=t.name
            if tn not in TS.keys():
                print('Tab',i,'>>> Name {} not found in selection'.format(tn))
            else:
                print('Tab',i,'xSel:',TS[tn]['xSel'],'ySel:',TS[tn]['ySel'],'Name:',tn)

    def getFullSelection(self):
        ID = []
        iX1=None; IY1=None; sX1=None; SY1=None;
        iX2=None; IY2=None; sX2=None; SY2=None;
        ITab=None;
        STab=None;
        if hasattr(self,'tabs') and len(self.tabs)>0:
            ITab,STab = self.getSelectedTables()
            iX1,IY1,sX1,SY1 = self.colPanel1.getColumnSelection()
            if self._mode =='sameColumnsMode':
                for i,itab in enumerate(ITab):
                    for j,iy in enumerate(IY1):
                        ID.append([itab,iX1,iy])
            elif self._mode =='twoColumnsMode':
                if len(ITab)>=1:
                    for j,iy in enumerate(IY1):
                        ID.append([ITab[0],iX1,iy])
                if len(ITab)>=2:
                    iX2,IY2,sX2,SY2 = self.colPanel2.getColumnSelection()
                    for j,iy in enumerate(IY2):
                        ID.append([ITab[1],iX2,iy])
            else:
                raise Exception('Unknown mode {}'.format(self._mode))
        return ID,ITab,iX1,IY1,iX2,IY2,STab,sX1,SY1,sX2,SY2

    def getSelectedTables(self):
        I=self.tabPanel.lbTab.GetSelections()
        S=[self.tabPanel.lbTab.GetString(i) for i in I]
        return I,S

    def clean_memory(self):
        self.colPanel1.empty()
        self.colPanel2.empty()
        self.tabPanel.empty()
        if hasattr(self,'tabs'):
            del self.tabs

# --------------------------------------------------------------------------------}
# --- Plot Panel 
# --------------------------------------------------------------------------------{
class MyNavigationToolbar2Wx(NavigationToolbar2Wx): 
    def __init__(self, canvas):
        # Taken from matplotlib/backend_wx.py but added style:
        wx.ToolBar.__init__(self, canvas.GetParent(), -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT | wx.TB_NODIVIDER)
        NavigationToolbar2.__init__(self, canvas)
        self.canvas = canvas
        self._idle = True
        self.statbar = None
        self.prevZoomRect = None
        self.retinaFix = 'wxMac' in wx.PlatformInfo
        # --- Modif
        #NavigationToolbar2Wx.__init__(self, plotCanvas)
        self.DeleteToolByPos(1)
        self.DeleteToolByPos(1)
        self.SetBackgroundColour('white')
        #self.SetToolBitmapSize((22,22))

class SpectralCtrlPanel(wx.Panel):
    def __init__(self, parent):
        # Superclass constructor
        super(SpectralCtrlPanel,self).__init__(parent)
        #self.SetBackgroundColour('gray')
        # data
        self.parent   = parent
        # GUI
        lb = wx.StaticText( self, -1, 'Type:')
        self.cbType            = wx.ComboBox(self, choices=['PSD','f x PSD','Amplitude'] , style=wx.CB_READONLY)
        self.cbType.SetSelection(0)
        lbAveraging            = wx.StaticText( self, -1, 'Avg.:')
        self.cbAveraging       = wx.ComboBox(self, choices=['None','Welch'] , style=wx.CB_READONLY)
        self.cbAveraging.SetSelection(1)
        self.lbAveragingMethod = wx.StaticText( self, -1, 'Window:')
        self.cbAveragingMethod = wx.ComboBox(self, choices=['Hamming','Hann','Rectangular'] , style=wx.CB_READONLY)
        self.cbAveragingMethod.SetSelection(0)
        self.lbP2 = wx.StaticText( self, -1, '2^n:')
        self.scP2 = wx.SpinCtrl(self, value='11',size=wx.Size(40,-1))
        self.lbWinLength = wx.StaticText( self, -1, '(2048)  ')
        self.scP2.SetRange(3, 19)
        lbMaxFreq     = wx.StaticText( self, -1, 'Xlim:')
        self.tMaxFreq = wx.TextCtrl(self,size = (30,-1),style=wx.TE_PROCESS_ENTER)
        self.tMaxFreq.SetValue("-1")
        self.cbDetrend = wx.CheckBox(self, -1, 'Detrend',(10,10))
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(lb                    ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.cbType           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbAveraging           ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.cbAveraging      ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.lbAveragingMethod,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.cbAveragingMethod,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.lbP2             ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.scP2             ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.lbWinLength      ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbMaxFreq             ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.tMaxFreq         ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.cbDetrend        ,0, flag = wx.CENTER|wx.LEFT,border = 7)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_COMBOBOX  ,self.onSpecCtrlChange)
        self.Bind(wx.EVT_TEXT      ,self.onP2ChangeText  ,self.scP2     )
        self.Bind(wx.EVT_TEXT_ENTER,self.onXlimChange    ,self.tMaxFreq )
        self.Bind(wx.EVT_CHECKBOX  ,self.onDetrendChange ,self.cbDetrend)
        self.Hide() 

    def onXlimChange(self,event=None):
        self.parent.redraw();
    def onSpecCtrlChange(self,event=None):
        self.parent.redraw();
    def onDetrendChange(self,event=None):
        self.parent.redraw();

    def onP2ChangeText(self,event=None):
        nExp=self.scP2.GetValue()
        self.updateP2(nExp)
        self.parent.redraw();

    def updateP2(self,P2):
        self.lbWinLength.SetLabel("({})".format(2**P2))



class PlotPanel(wx.Panel):
    def __init__(self, parent, selPanel):

        # Superclass constructor
        super(PlotPanel,self).__init__(parent)
        self.SetBackgroundColour('white')
        # data
        self.selPanel = selPanel
        self.parent   = parent
        # GUI
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        self.fig.subplots_adjust(top=0.98,bottom=0.12,left=0.12,right=0.98)
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)

        self.navTB = MyNavigationToolbar2Wx(self.canvas)

        # --- Ctrl Panel
        self.ctrlPanel= wx.Panel(self)
        # Check Boxes
        self.cbScatter = wx.CheckBox(self.ctrlPanel, -1, 'Scatter',(10,10))
        self.cbPDF     = wx.CheckBox(self.ctrlPanel, -1, 'PDF',(10,10))
        self.cbFFT     = wx.CheckBox(self.ctrlPanel, -1, 'FFT',(10,10))
        self.cbSub     = wx.CheckBox(self.ctrlPanel, -1, 'Subplot',(10,10))
        self.cbLogX    = wx.CheckBox(self.ctrlPanel, -1, 'Log-x',(10,10))
        self.cbLogY    = wx.CheckBox(self.ctrlPanel, -1, 'Log-y',(10,10))
        self.cbMinMax  = wx.CheckBox(self.ctrlPanel, -1, 'MinMax',(10,10))
        self.cbSync    = wx.CheckBox(self.ctrlPanel, -1, 'Sync-x',(10,10))
        self.lbCrossHairX = wx.StaticText(self.ctrlPanel, -1, ' x= ...      ')
        self.lbCrossHairY = wx.StaticText(self.ctrlPanel, -1, ' y= ...      ')
        self.lbCrossHairX.SetFont(getMonoFont())
        self.lbCrossHairY.SetFont(getMonoFont())
        #self.cbSub.SetValue(True) # DEFAULT TO SUB?
        self.cbSync.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.scatter_select, self.cbScatter)
        self.Bind(wx.EVT_CHECKBOX, self.pdf_select    , self.cbPDF    )
        self.Bind(wx.EVT_CHECKBOX, self.fft_select    , self.cbFFT    )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event  , self.cbSub    )
        self.Bind(wx.EVT_CHECKBOX, self.log_select    , self.cbLogX   )
        self.Bind(wx.EVT_CHECKBOX, self.log_select    , self.cbLogY   )
        self.Bind(wx.EVT_CHECKBOX, self.minmax_select , self.cbMinMax )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event  , self.cbSync )
        #
        #side_panel = wx.Panel(self,parent)
        # LAYOUT
#         if sys.version_info[0] < 3:
#             cb_sizer = wx.GridSizer(2,5,3)
#         else:
#             cb_sizer = wx.GridSizer(5,2,3)
        cb_sizer  = wx.FlexGridSizer(rows=2, cols=5, hgap=2, vgap=0)
        cb_sizer.Add(self.cbScatter, 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPDF    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFFT    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSub    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.lbCrossHairX   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogX   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogY   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMinMax , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSync   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.lbCrossHairY   , 0, flag=wx.ALL, border=1)

        self.ctrlPanel.SetSizer(cb_sizer)

        # --- Spectral panel
        self.spectralPanel= SpectralCtrlPanel(self)

        # --- layout of panels
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sl3 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        row_sizer.Add(self.navTB        ,0, flag=wx.ALL|wx.CENTER, border=0)
        row_sizer.Add(sl3               ,0, flag=wx.EXPAND|wx.CENTER, border=0)
        #row_sizer.Add(cb_sizer          ,0, flag=wx.ALL, border=5)
        row_sizer.Add(self.ctrlPanel    ,1, flag=wx.ALL|wx.EXPAND|wx.CENTER, border=5)
        #row_sizer.Add(self.lbCrossHair  ,0, flag=wx.ALL, border=5)
        #row_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        #row_sizer2.Add(self.navTB        ,0, flag=wx.ALL, border=5)

        plotsizer = wx.BoxSizer(wx.VERTICAL)
        sl1 = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        sl2 = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        #plotsizer.Add(row_sizer2)
        plotsizer.Add(self.canvas       ,1,flag = wx.EXPAND,border = 5 )
        plotsizer.Add(sl1               ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(row_sizer         ,0,flag = wx.NORTH ,border = 5)
        plotsizer.Add(sl2               ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.spectralPanel,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)

        self.SetSizer(plotsizer)
        self.plotsizer=plotsizer;
        #self.redraw()

    def redraw_event(self, event):
        self.redraw()

    def fft_select(self, event):
        if self.cbFFT.IsChecked():
            self.cbLogY.SetValue(True)
            self.cbPDF.SetValue(False)
            self.cbMinMax.SetValue(False)
            self.spectralPanel.Show();
            self.plotsizer.Layout()
        else:
            self.spectralPanel.Hide();
            self.plotsizer.Layout()
            self.cbLogY.SetValue(False)
        self.redraw()

    def pdf_select(self, event):
        self.cbFFT.SetValue(False)
        self.cbMinMax.SetValue(False)
        self.cbLogX.SetValue(False)
        self.cbLogY.SetValue(False)
        self.redraw()
    def log_select(self, event):
        if self.cbPDF.IsChecked():
            self.cbLogX.SetValue(False)
            self.cbLogY.SetValue(False)
        else:
            self.redraw()
    def scatter_select(self, event):
        if self.cbPDF.IsChecked() or self.cbFFT.IsChecked():
            self.cbScatter.SetValue(False)
        else:
            self.redraw()
    def minmax_select(self, event):
        self.cbFFT.SetValue(False)
        self.cbPDF.SetValue(False)
        self.redraw()

    def empty(self):
        self.cleanPlot()

    def cleanPlot(self):
        for ax in self.fig.axes:
            self.fig.delaxes(ax)
        self.fig.add_subplot(111)
        ax = self.fig.axes[0]
        ax.plot(1,1)
        self.canvas.draw()
        gc.collect()

    def set_subplots(self,nPlots):
        # Creating subplots
        bSubPlots=self.cbSub.IsChecked()
        for ax in self.fig.axes:
            self.fig.delaxes(ax)
        sharex=None
        if bSubPlots:
            for i in range(nPlots):
                # Vertical stack
                if i==0:
                    ax=self.fig.add_subplot(nPlots,1,i+1)
                    if self.cbSync.IsChecked() and (not self.cbPDF.IsChecked()) :
                        sharex=ax
                else:
                    ax=self.fig.add_subplot(nPlots,1,i+1,sharex=sharex)
                # Horizontal stack
                #self.fig.add_subplot(1,nPlots,i+1)
        else:
            self.fig.add_subplot(111)
        
    def draw_tab(self,df,ix,xlabel,I,S,sTab,nTabs,bFirst=True):
        x,xIsString,xIsDate,_=getColumn(df,ix)

        nPlots=len(I)
        bSubPlots=self.cbSub.IsChecked()

        if bFirst:
            self.cursors=[]

        for i in range(nPlots):
            if bSubPlots:
                ax = self.fig.axes[i]
                if bFirst:
                    ax.clear()
            else:
                ax = self.fig.axes[0]

            # Selecting y values
            iy     = I[i]
            ylabel = S[i]
            y,yIsString,yIsDate,c=getColumn(df,iy)
            if nTabs==1:
                if self.cbMinMax.IsChecked():
                    ylabelLeg  = no_unit(ylabel)
                else:
                    ylabelLeg  = ylabel
            else:
                if nPlots==1 or bSubPlots:
                    ylabelLeg  = sTab
                else:
                    if self.cbMinMax.IsChecked():
                        ylabelLeg  = sTab+' - ' + no_unit(ylabel)
                    else:
                        ylabelLeg  = sTab+' - ' + ylabel


            # Scaling
            if self.cbMinMax.IsChecked():
                mi= np.nanmin(y)
                mx= np.nanmax(y)
                if mi == mx:
                    y=y*0
                else:
                    y = (y-np.nanmin(y))/(np.nanmax(y)-np.nanmin(y))
            n = len(y)


            # --- Plotting
            if self.cbPDF.IsChecked():
                if yIsString:
                    if n>100:
                        WarnNow('Dataset has string format and is too large to display')
                    else:
                        value_counts = c.value_counts().sort_index()
                        value_counts.plot(kind='bar', ax=ax)
                elif yIsDate:
                    Warn(self,'Cannot plot PDF of dates')
                else:
                    pdf, xx = np.histogram(y[~np.isnan(y)], bins=min(int(n/10),50))
                    dx  = xx[1] - xx[0]
                    xx  = xx[:-1] + dx/2
                    pdf = pdf / (n*dx)
                    ax.plot(xx, pdf, label=ylabelLeg)
                    if bFirst:
                        ax.set_xlabel(ylabel)
                        ax.set_ylabel('PDF ('+ylabel+')')

            elif self.cbFFT.IsChecked():
                if yIsString or yIsDate:
                    Warn(self,'Cannot plot FFT of dates or strings')
                elif xIsString:
                    Warn(self,'Cannot plot FFT if x axis is string')
                else:
                    #y = np.sin(2*np.pi*2*t)
                    y = np.array(y)
                    y = y[~np.isnan(y)]
                    n = len(y) 
                    if xIsDate:
                        dt = np.timedelta64((x[1]-x[0]),'s').item().total_seconds()
                    else:
                        dt = x[1]-x[0]
                        # Hack to use a constant dt
                        dt = (x[-1]-x[0])/(n-1)
                        #uu,cc= np.unique(np.diff(x), return_counts=True)
                        #print(np.asarray((uu,cc)).T)
                    Fs = 1/dt
                    #print('dt=',dt,'Fs=',Fs)
                    if n%2==0:
                        nhalf = int(n/2+1)
                    else:
                        nhalf = int((n+1)/2)
                    sType    = self.spectralPanel.cbType.GetStringSelection()
                    sAvg     = self.spectralPanel.cbAveraging.GetStringSelection()
                    bDetrend = self.spectralPanel.cbDetrend.IsChecked()
                    if sAvg=='None':
                        if bDetrend:
                            m=np.mean(y);
                        else:
                            m=0;
                        frq = np.arange(nhalf)*Fs/n;
                        Y   = np.fft.rfft(y-m) #Y = np.fft.fft(y) 
                        PSD = abs(Y[range(nhalf)])**2 /(n*Fs) # PSD
                        PSD[1:-1] = PSD[1:-1]*2;
                    elif sAvg=='Welch':
                        # --- Welch - PSD
                        #overlap_frac=0.5
                        nFFTAll=fnextpow2(n)
                        nExp=self.spectralPanel.scP2.GetValue()
                        nPerSeg=2**nExp
                        sAvgMethod = self.spectralPanel.cbAveragingMethod.GetStringSelection()
                        if nPerSeg>n:
                            #Warn(self, 'Power of 2 value was too high and was reduced. Disable averaging to use the full spectrum.');
                            nExp=int(np.log(nFFTAll)/np.log(2))-1
                            nPerSeg=2**nExp
                            self.spectralPanel.scP2.SetValue(nExp)
                            self.spectralPanel.updateP2(nExp)
                            #nPerSeg=n # <<< Possibility to use this with a rectangular window
                        if sAvgMethod=='Hamming':
                           window = hamming(nPerSeg, True)# True=Symmetric, like matlab
                        elif sAvgMethod=='Hann':
                           window = hann(nPerSeg, True)
                        elif sAvgMethod=='Rectangular':
                           window = boxcar(nPerSeg)
                        else:
                            raise NotImplementedError('Contact developer')
                        if bDetrend:
                            frq, PSD = pwelch(y, fs=Fs, window=window, detrend='constant')
                        else:
                            frq, PSD = pwelch(y, fs=Fs, window=window)
                        #print(window)
                        #print(frq)
                        #print(Y)
                    if sType=='Amplitude':
                        deltaf = frq[1]-frq[0]
                        Y = np.sqrt(PSD*2*deltaf)
                        # NOTE: the above should be the same as:Y=abs(Y[range(nhalf)])/n;Y[1:-1]=Y[1:-1]*2;
                    elif sType=='PSD': # One sided
                        Y = PSD
                    elif sType=='f x PSD':
                        Y = PSD*frq
                    else:
                        raise NotImplementedError('Contact developer')
                    if bDetrend:
                        frq=frq[1:]
                        Y  =Y[1:]

                    ax.plot(frq, Y, label=ylabelLeg)
                    if bFirst:
                        ax.set_ylabel('FFT ('+ylabel+')')
                        if self.cbLogX.IsChecked():
                            ax.set_xscale("log", nonposx='clip')
                        if self.cbLogY.IsChecked():
                            if all(Y<=0):
                                pass
                            else:
                                ax.set_yscale("log", nonposy='clip')
                        try:
                            xlim=float(self.spectralPanel.tMaxFreq.GetLineText(0))
                            if xlim>0:
                                ax.set_xlim([0,xlim])
                        except:
                            pass

            else:
                if xIsString and n>100:
                    Warn(self,'Cannot plot large data set since x-axis `{}` has string format. Use `Index` instead for the x-axis.'.format(xlabel))
                elif yIsString and n>100:
                    Warn(self,'Dataset `{}` has string format and is too large to display'.format(ylabel))
                else:
                    if self.cbScatter.IsChecked() or len(x)<2:
                        sty='o'
                    else:
                        sty='-'
                    ax.plot(x,y, sty, label=ylabelLeg, markersize=1)
                    if bFirst:
                        if i==nPlots-1:
                            ax.set_xlabel(xlabel)
                        if bSubPlots or (not bSubPlots and nPlots==1):
                            ax.set_ylabel(ylabel)
                        if self.cbLogX.IsChecked():
                            ax.set_xscale("log", nonposx='clip')
                        if self.cbLogY.IsChecked():
                            if all(y<=0):
                                pass
                            else:
                                ax.set_yscale("log", nonposy='clip')
            # Cross Hair 
            #cursor = Cursor(ax, useblit=True, color='red', linewidth=2)
            if bFirst:
                if bSubPlots or i==0:
                    self.cursors.append(Cursor(ax,horizOn=True, vertOn=True, useblit=True, color='gray', linewidth=0.5, linestyle=':'))

    def onMouseMove(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            #self.lbCrossHairX.SetLabel("x={:.5e}  y={:.5e}".format(x,y))
            self.lbCrossHairX.SetLabel(" x={:10.3e}".format(x))
            self.lbCrossHairY.SetLabel(" y={:10.3e}".format(y))

    def redraw(self):
        self._redraw()

    def _redraw(self):
        #print('>>>>>>> Redraw event')
        ID,ITab,iX1,IY1,iX2,IY2,STab,sX1,SY1,sX2,SY2=self.selPanel.getFullSelection()
        if len(ID)==0:
            #Error(self.parent,'Open a file to plot the data.')
            return
        #print(ID,iX2,ITab,IY1)
        tabs=self.selPanel.tabs
        if iX2 is None or iX2==-1: #iX2==-1 when two table have same columns in mode twocolumns..
            nPlots = len(IY1)
            nTabs = len(ITab)
            self.set_subplots(nPlots)
            for i,sTab in zip(ITab,STab):
                self.draw_tab(tabs[i].data,iX1,sX1,IY1,SY1,sTab,nTabs,bFirst=(i==ITab[0]))
        else:
            nPlots = 1
            self.set_subplots(nPlots)
            if len(IY1)==0:
                xlabel  = sX2
                Ylabels = SY2
            elif len(IY2)==0:
                xlabel  = sX1
                Ylabels = SY1
            else:
                if no_unit(sX1)!=no_unit(sX2):
                    xlabel=sX1+' and '+ sX2
                else:
                    xlabel=sX1
                Ylabels=[]
                for s1,s2 in zip(SY1,SY2):
                    if no_unit(s1)!=no_unit(s2):
                        Ylabels.append(s1+' and '+s2)
                    else:
                        Ylabels.append(s1)
            self.draw_tab(tabs[ITab[0]].data,iX1,xlabel,IY1,Ylabels,STab[0],2,bFirst=True)
            self.draw_tab(tabs[ITab[1]].data,iX2,xlabel,IY2,Ylabels,STab[1],2,bFirst=False)


        bSubPlots=self.cbSub.IsChecked()
        if bSubPlots:
            ax = self.fig.axes[-1]
        else:
            ax = self.fig.axes[0]
        if (not bSubPlots and nPlots!=1) or (len(ITab)>1):
            ax.legend()
        self.canvas.draw()


# --------------------------------------------------------------------------------}
# --- Main Frame  
# --------------------------------------------------------------------------------{
class MainFrame(wx.Frame):
    def __init__(self, filename=None):
        # Parent constructor
        wx.Frame.__init__(self, None, -1, PROG_NAME+' '+PROG_VERSION)
        # Data
        self.tabs=[]
            
        # Hooking exceptions to display them to the user
        sys.excepthook = MyExceptionHook
        # --- Menu
        menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        helpMenu = wx.Menu()
        loadMenuItem  = fileMenu.Append(wx.NewId(),"Open" ,"Open file"           )
        saveMenuItem  = fileMenu.Append(wx.NewId(),"Save figure" ,"Save figure"           )
        exitMenuItem  = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
        aboutMenuItem = helpMenu.Append(wx.NewId(), 'About', 'About')
        menuBar.Append(fileMenu, "&File")
        menuBar.Append(helpMenu, "&Help")
        self.Bind(wx.EVT_MENU,self.onExit ,exitMenuItem )
        self.Bind(wx.EVT_MENU,self.onLoad ,loadMenuItem )
        self.Bind(wx.EVT_MENU,self.onSave ,saveMenuItem )
        self.Bind(wx.EVT_MENU,self.onAbout,aboutMenuItem)
        self.SetMenuBar(menuBar)

        # --- ToolBar
        tb = self.CreateToolBar(wx.TB_HORIZONTAL)
        self.toolBar = tb 
        tb.AddSeparator()
        btOpen   = wx.Button(tb, wx.ID_ANY, "Open"  , wx.DefaultPosition, wx.DefaultSize )
        btReload = wx.Button(tb, wx.ID_ANY, "Reload", wx.DefaultPosition, wx.DefaultSize )
        btAdd    = wx.Button(tb, wx.ID_ANY, "Add"   , wx.DefaultPosition, wx.DefaultSize )
        #btDEBUG  = wx.Button( tb, wx.NewId(), "DEBUG", wx.DefaultPosition, wx.DefaultSize )
        self.comboFormats = wx.ComboBox(tb, choices = FILE_FORMATS_NAMEXT, style=wx.CB_READONLY)  
        self.comboFormats.SetSelection(0)
        self.comboMode = wx.ComboBox(tb, choices = SEL_MODES, style=wx.CB_READONLY)  
        self.comboMode.SetSelection(0)
        self.Bind(wx.EVT_COMBOBOX, self.onModeChange, self.comboMode )
        tb.AddSeparator()
        tb.AddControl( wx.StaticText(tb, -1, 'Mode: ' ) )
        tb.AddControl( self.comboMode ) 
        tb.AddStretchableSpace()
        tb.AddControl( wx.StaticText(tb, -1, 'Format: ' ) )
        tb.AddControl(self.comboFormats ) 
        tb.AddSeparator()
        tb.AddControl(btOpen)
        tb.AddSeparator()
        tb.AddControl(btReload)
        tb.AddSeparator()
        tb.AddControl(btAdd)
        tb.AddStretchableSpace()
        tb.AddSeparator()
        tb.Bind(wx.EVT_BUTTON,self.onLoad  ,btOpen  )
        tb.Bind(wx.EVT_BUTTON,self.onReload,btReload)
        tb.Bind(wx.EVT_BUTTON,self.onAdd   ,btAdd)
        #tb.Bind(wx.EVT_BUTTON,self.onDEBUG,btDEBUG)
        tb.Realize() 

        # --- Status bar
        self.statusbar=self.CreateStatusBar(3, style=0)
        self.statusbar.SetStatusWidths([230, -1, 70])

        # --- Main Panel and Notebook
        self.MainPanel = wx.Panel(self)
        #self.MainPanel = wx.Panel(self, style=wx.RAISED_BORDER)
        #self.MainPanel.SetBackgroundColour((200,0,0))

        self.nb = wx.Notebook(self.MainPanel)
        self.nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_change)


        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, flag=wx.EXPAND)
        self.MainPanel.SetSizer(sizer)

        # --- Drag and drop
        dd = FileDropTarget(self)
        self.SetDropTarget(dd)

        # --- Main Frame (self)
        FrameSizer = wx.BoxSizer(wx.VERTICAL)
        FrameSizer.Add(self.MainPanel,1, flag=wx.EXPAND)
        self.SetSizer(FrameSizer)

        self.SetSize((800, 600))
        self.Center()

        self.Show()

    @property
    def filenames(self):
        filenames=[]
        if hasattr(self,'tabs'):
            for t in self.tabs:
                if t.filename not in filenames:
                    filenames.append(t.filename)
            #filenames=[t.filename for t in self.tabs] 
        return filenames

    def clean_memory(self,bReload=False):
        #print('Clean memory')
        # force Memory cleanup
        if hasattr(self,'tabs'):
            del self.tabs
            self.tabs=[]
        if not bReload:
            if hasattr(self,'selPanel'):
                self.selPanel.clean_memory()
            if hasattr(self,'infoPanel'):
                self.infoPanel.clean()
            if hasattr(self,'plotPanel'):
                self.plotPanel.cleanPlot()
        gc.collect()

    def load_files(self, filenames=[], fileformat=None, bReload=False, bAdd=False):
        """ load multiple files, only trigger the plot at the end """
        if bReload:
            self.selPanel.saveSelection()

        if not bAdd:
            self.clean_memory(bReload=bReload)

        tabs=[]
        for f in filenames:
            if f in self.filenames:
                Error(self,'Cannot add a file already opened')
            else:
                tabs += self._load_file_tabs(f,fileformat=fileformat)
        if len(tabs)>0:
            # Adding tables
            self.load_tabs(tabs,bReload=bReload,bAdd=bAdd,bPlot=True)

    def _load_file_tabs(self,filename,fileformat=None):
        """ load a single file, adds table, and potentially trigger plotting """
        self.statusbar.SetStatusText('');
        self.statusbar.SetStatusText('',1);
        self.statusbar.SetStatusText('',2);

        if not os.path.isfile(filename):
            Error(self,'File not found: '+filename)
            return []
        try:
            F = FILE_READER(filename,fileformat = fileformat)
            dfs = F.toDataFrame()
        except FileNotFoundError as e:
            Error(self, 'A file was not found!\n\n While opening:\n\n {}\n\n the following file was not found:\n\n {}'.format(filename, e.filename))
            return []
        except IOError:
            Error(self, 'IO Error thrown while opening file: '+filename )
            return []
        except MemoryError:
            Error(self,'Insufficient memory!\n\nFile: '+filename+'\n\nTry closing and reopening the program, or use a 64 bit version of this program (i.e. of python).')
            return []
        except weio.FormatNotDetectedError:
            Error(self,'File format not detected!\n\nFile: '+filename+'\n\nUse an explicit file-format from the list')
            return []
        except weio.WrongFormatError as e:
            Error(self,'Wrong file format!\n\nFile: '+filename+'\n\n'   \
                    'The file parser for the selected format failed to open the file.\n\n'+   \
                    'The reported error was:\n'+e.args[0]+'\n\n' +   \
                    'Double-check your file format and report this error if you think it''s a bug.')
            return []
        except weio.BrokenFormatError as e:
            Error(self,'Inconsistency in the file format!\n\nFile: '+filename+'\n\n'   \
                    'The reported error was:\n'+e.args[0]+'\n\n' +   \
                    'Double-check your file format and report this error if you think it''s a bug.')
            return []
        except:
            raise

        #  Creating a list of tables
        tabs=[]
        if not isinstance(dfs,dict):
            if len(dfs)>0:
                tabs=[Table(df=dfs, name='default', filename=filename)]
        else:
            for k in list(dfs.keys()):
                if len(dfs[k])>0:
                    tabs.append(Table(df=dfs[k], name=k, filename=filename))

        self.statusbar.SetStatusText(F.filename,1)
        if fileformat is None:
            self.statusbar.SetStatusText('Detected: '+F.formatName())
        else:
            self.statusbar.SetStatusText('Format: '+F.formatName())
        self.fileformatName = F.formatName()
        if len(tabs)<=0:
            Warn(self,'No dataframe found in file: '+filename)
            return []
        else:
            return tabs
            

    def load_df(self, df):
        tab=[Table(df=df, name='default')]
        self.load_tabs(tab)

    def load_tabs(self, tabs, bReload=False, bAdd=False, bPlot=True):
        if bAdd:
            if not hasattr(self,'selPanel'):
                bAdd=False

        if (not bReload) and (not bAdd):
            self.cleanGUI()

        if bAdd:
            self.tabs=self.tabs+tabs
        else:
            self.tabs=tabs
        ##
        if len(self.tabs)==1:
            self.statusbar.SetStatusText('{}x{}'.format(self.tabs[0].nCols,self.tabs[0].nRows),2)

        if bReload or bAdd:
            self.selPanel.update_tabs(self.tabs)
        else:
            #
            mode = SEL_MODES_ID[self.comboMode.GetSelection()]
            self.vSplitter = wx.SplitterWindow(self.nb)
            self.selPanel = SelectionPanel(self.vSplitter, self.tabs, mode=mode)
            self.tSplitter = wx.SplitterWindow(self.vSplitter)
            #self.tSplitter.SetMinimumPaneSize(20)
            self.plotPanel = PlotPanel(self.tSplitter, self.selPanel)
            self.infoPanel = InfoPanel(self.tSplitter)
            self.tSplitter.SetSashGravity(0.9)
            self.tSplitter.SplitHorizontally(self.plotPanel, self.infoPanel)
            self.tSplitter.SetMinimumPaneSize(55)
            self.tSplitter.SetSashGravity(1)
            self.tSplitter.SetSashPosition(400)

            self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
            self.vSplitter.SetMinimumPaneSize(SIDE_COL[0])
            self.tSplitter.SetSashPosition(SIDE_COL[0])

            self.nb.AddPage(self.vSplitter, "Plot")
            self.nb.SendSizeEvent()

            self.Bind(wx.EVT_COMBOBOX, self.onColSelectionChange, self.selPanel.colPanel1.comboX   )
            self.Bind(wx.EVT_LISTBOX , self.onColSelectionChange, self.selPanel.colPanel1.lbColumns)
            self.Bind(wx.EVT_COMBOBOX, self.onColSelectionChange, self.selPanel.colPanel2.comboX   )
            self.Bind(wx.EVT_LISTBOX , self.onColSelectionChange, self.selPanel.colPanel2.lbColumns)
            self.Bind(wx.EVT_LISTBOX , self.onTabSelectionChange, self.selPanel.tabPanel.lbTab)
            self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.onSashChangeMain, self.vSplitter)

            self.selPanel.tabPanel.lbTab.Bind(wx.EVT_RIGHT_DOWN, self.OnTabPopup)
        

        # plot trigger
        if bPlot:
            self.mainFrameUpdateLayout()
            self.onColSelectionChange(event=None)

    def renameTable(self, iTab, newName):
        oldName = self.tabs[iTab].name
        if newName in [t.name for t in self.tabs]:
            Error(self,'This table already exist, choose a different name.')
            return
        # Renaming table
        self.tabs[iTab].rename(newName)
        # Lowlevel update of GUI
        self.selPanel.renameTable(iTab, oldName, newName)

    def deleteTabs(self, I):
        # removing table slections
        # TODO TODO TODO self.selPanel.tabSelections[t.name]
        # 
        self.tabs = [t for i,t in enumerate(self.tabs) if i not in I]

        # Invalidating selections
        self.selPanel.tabPanel.lbTab.SetSelection(-1)
        # Until we have something better, we empty plot
        self.plotPanel.empty()
        # Updating tables
        self.selPanel.update_tabs(self.tabs)
        # Trigger a replot
        self.onTabSelectionChange()

    def exportTab(self, iTab):
        default_filename=os.path.splitext(os.path.basename(self.tabs[iTab].filename))[0]+'.csv'
        with wx.FileDialog(self, "Save to CSV file",defaultFile=default_filename, wildcard="CSV files (*.csv)|*.csv",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            dlg.CentreOnParent()
            if dlg.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            if isinstance(self.tabs[iTab].data, pd.DataFrame):
                self.tabs[iTab].data.to_csv(dlg.GetPath(),sep=',',index=False)
            else:
                raise NotImplementedError('Export of data that is not a dataframe')

    def onSashChangeMain(self,event=None):
        pass
        # doent work because size is not communicated yet
        #if hasattr(self,'selPanel'):
        #    print('ON SASH')
        #    self.selPanel.setEquiSash(event)

    def OnTabPopup(self,event):
        menu = TablePopup(self,self.selPanel.tabPanel.lbTab)
        self.PopupMenu(menu, event.GetPosition())
        menu.Destroy()

    def onTabSelectionChange(self,event=None):
        # TODO all this can go in TabPanel
        #print('Tab selection change')
        # Storing the previous selection 
        #self.selPanel.printSelection()
        self.selPanel.saveSelection() # 
        #self.selPanel.printSelection()
        ISel=self.selPanel.tabPanel.lbTab.GetSelections()
        if len(ISel)>0:
            if haveSameColumns(self.tabs,ISel):
                # Setting tab
                self.selPanel.setTabForCol(ISel[0],1) 
                self.selPanel.colPanel2.empty()
            else:
                if self.selPanel._mode=='twoColumnsMode':
                    if len(ISel)>2:
                        Error(self,'In this mode, only two tables can be selected. To compare more than two tables, the tables need to have the same columns.')
                        ISel=[ISel[0]]
                        self.selPanel.tabPanel.lbTab.SetSelection(wx.NOT_FOUND)
                        self.selPanel.tabPanel.lbTab.SetSelection(ISel[0])
                        self.selPanel.setTabForCol(ISel[0],1) 
                        self.selPanel.colPanel2.empty()
                    else: # two panels selected
                        self.selPanel.setTabForCol(ISel[0],1) 
                        self.selPanel.setTabForCol(ISel[1],2) 
                else:
                    Error(self,'The two tables have different columns. Chose the "two table mode" to compare them.')
                    # unselect all and select only the first one
                    ISel=[ISel[0]]
                    self.selPanel.tabPanel.lbTab.SetSelection(wx.NOT_FOUND)
                    self.selPanel.tabPanel.lbTab.SetSelection(ISel[0])
                    self.selPanel.setTabForCol(ISel[0],1) 
            #print('>>>Updating tabSelected, from',self.selPanel.tabSelected,'to',self.selPanel.tabPanel.lbTab.GetSelections())
            self.selPanel.tabSelected=self.selPanel.tabPanel.lbTab.GetSelections()

            # Update of status bar
            self.statusbar.SetStatusText('',0)
            self.statusbar.SetStatusText(", ".join([t.filename for (i,t) in enumerate(self.tabs) if i in ISel]),1)
            if len(ISel)==1:
                self.statusbar.SetStatusText('{}x{}'.format(self.tabs[ISel[0]].nCols,self.tabs[ISel[0]].nRows),2)
            else:
                self.statusbar.SetStatusText('',2)

            # Trigger the colSelection Event
            self.onColSelectionChange(event=None)

    def onColSelectionChange(self,event=None):
        if hasattr(self,'plotPanel'):
            if self.selPanel._mode=='twoColumnsMode':
                ISel=self.selPanel.tabPanel.lbTab.GetSelections()
                if haveSameColumns(self.tabs,ISel):
                    pass # NOTE: this test is identical to onTabSelectionChange. Unification.
                elif len(ISel)==2:
                    self.selPanel.colPanel1.forceOneSelection()
                    self.selPanel.colPanel2.forceOneSelection()
            self.plotPanel.redraw()
            #print(self.tabs)
            # --- Stats trigger
            ID,ITab,iX1,IY1,iX2,IY2,STab,sX1,SY1,sX2,SY2=self.selPanel.getFullSelection()
            if sX2 is None:
                self.infoPanel.showStats(self.filenames,self.tabs, ITab,IY1,SY1, iX1 ,erase=True)
            else:                                        
                self.infoPanel.showStats(self.filenames,self.tabs, [ITab[0]],IY1,SY1,iX1,erase=True)
                self.infoPanel.showStats(None          ,self.tabs, [ITab[1]],IY2,SY2,iX2)

    def onExit(self, event):
        self.Close()

    def cleanGUI(self, event=None):
        if hasattr(self,'plotPanel'):
            del self.plotPanel
        if hasattr(self,'selPanel'):
            del self.selPanel
        if hasattr(self,'infoPanel'):
            del self.infoPanel
        self.deletePages()
        gc.collect()

    def onSave(self, event=None):
        # using the navigation toolbar save functionality
        self.plotPanel.navTB.save_figure()

    def onAbout(self, event=None):
        Info(self,PROG_NAME+' '+PROG_VERSION+'\n\nWritten by E. Branlard. \n\nVisit http://github.com/ebranlard/pyDatView for documentation.')

    def onReload(self, event=None):
        filenames = self.filenames
        if len(filenames)>=0:
            iFormat=self.comboFormats.GetSelection()
            if iFormat==0: # auto-format
                Format = None
            else:
                Format = FILE_FORMATS[iFormat-1]
            self.load_files(filenames,fileformat=Format,bReload=True,bAdd=False)
        else:
           Error(self,'Open a file first')

    def onDEBUG(self, event=None):
        #self.clean_memory()
        self.plotPanel.ctrlPanel.Refresh()
        self.plotPanel.cb_sizer.ForceRefresh()


    def onLoad(self, event=None):
        self.selectFile(bAdd=False)

    def onAdd(self, event=None):
        self.selectFile(bAdd=len(self.tabs)>0)

    def selectFile(self,bAdd=False):
        # --- File Format extension
        iFormat=self.comboFormats.GetSelection()
        sFormat=self.comboFormats.GetStringSelection()
        if iFormat==0: # auto-format
            Format = None
            #wildcard = 'all (*.*)|*.*'
            wildcard='|'.join([n+'|*'+';*'.join(e) for n,e in zip(FILE_FORMATS_NAMEXT,FILE_FORMATS_EXTENSIONS)])
            #wildcard = sFormat + extensions+'|all (*.*)|*.*'
        else:
            Format = FILE_FORMATS[iFormat-1]
            extensions = '|*'+';*'.join(FILE_FORMATS[iFormat-1].extensions)
            wildcard = sFormat + extensions+'|all (*.*)|*.*'

        with wx.FileDialog(self, "Open file", wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as dlg:
            #other options: wx.CHANGE_DIR
            #dlg.SetSize((100,100))
            #dlg.Center()
           if dlg.ShowModal() == wx.ID_CANCEL:
               return     # the user changed their mind
           self.load_files(dlg.GetPaths(),fileformat=Format,bAdd=bAdd)


    def onModeChange(self, event=None):
        mode = SEL_MODES_ID[self.comboMode.GetSelection()]
        if hasattr(self,'selPanel'):
            self.selPanel.updateLayout(mode)
        self.mainFrameUpdateLayout()

    def mainFrameUpdateLayout(self, event=None):
        if hasattr(self,'selPanel'):
            nWind=self.selPanel.splitter.nWindows
            self.resizeSideColumn(SIDE_COL[nWind])


    # --- Side column
    def resizeSideColumn(self,width):
        # To force the replot we do an epic unsplit/split...
        #self.vSplitter.Unsplit()
        #self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
        self.vSplitter.SetMinimumPaneSize(width)
        self.vSplitter.SetSashPosition(width)
        #self.selPanel.splitter.setEquiSash()

    # --- NOTEBOOK 
    def deletePages(self):
        for index in reversed(range(self.nb.GetPageCount())):
            self.nb.DeletePage(index)
        self.nb.SendSizeEvent()
        gc.collect()
    def on_tab_change(self, event=None):
        page_to_select = event.GetSelection()
        wx.CallAfter(self.fix_focus, page_to_select)
        event.Skip(True)
    def fix_focus(self, page_to_select):
        page = self.nb.GetPage(page_to_select)
        page.SetFocus()

#----------------------------------------------------------------------
def MyExceptionHook(etype, value, trace):
    """
    Handler for all unhandled exceptions.
    :param `etype`: the exception type (`SyntaxError`, `ZeroDivisionError`, etc...);
    :type `etype`: `Exception`
    :param string `value`: the exception error message;
    :param string `trace`: the traceback header, if any (otherwise, it prints the
     standard Python header: ``Traceback (most recent call last)``.
    """
    # Printing exception
    traceback.print_exception(etype, value, trace)
    # Then showing to user the last error
    frame = wx.GetApp().GetTopWindow()
    tmp = traceback.format_exception(etype, value, trace)
    exception = 'The following exception occured:\n\n'+ tmp[-1]  + '\n'+tmp[-2].strip()
    Error(frame,exception)

# --------------------------------------------------------------------------------}
# --- Tests 
# --------------------------------------------------------------------------------{
def test():
    import time
    import sys
    from .perfmon import PerfMon
    # TODO unit test for #25
    S=ellude_common(['A.txt','A_.txt'])
    if any([len(s)<=1 for s in S]):
        raise Exception('[FAIL] ellude common with underscore difference, Bug #25')

    dt = 3
    # --- Test df
    with PerfMon('Data creation'):
        nRow =10**7;
        nCols=10;
        d={}
        d['col0'] = np.linspace(0,1,nRow);
        for iC in range(1,nCols):
            name='col{}'.format(iC)
            d[name] = np.random.normal(0,1,nRow)+2*iC
        tend = time.time()
        df = pd.DataFrame(data=d)
        del d
    time.sleep(dt) 
    with PerfMon('Plot 1'):
        app = wx.App(False)
        frame = MainFrame()
        frame.load_df(df)
    time.sleep(dt) 
    with PerfMon('Redraw 1'):
        frame.selPanel.colPanel1.lbColumns.SetSelection(-1)
        frame.selPanel.colPanel1.lbColumns.SetSelection(2)
        frame.plotPanel.redraw()
    time.sleep(dt) 
    with PerfMon('Redraw 1 (igen)'):
        frame.selPanel.colPanel1.lbColumns.SetSelection(-1)
        frame.selPanel.colPanel1.lbColumns.SetSelection(2)
        frame.plotPanel.redraw()
    time.sleep(dt) 
    with PerfMon('FFT 1'):
        frame.plotPanel.cbFFT.SetValue(True)
        #frame.plotPanel.cbLogX.SetValue(True)
        #frame.plotPanel.cbLogY.SetValue(True)
        frame.plotPanel.redraw()
        frame.plotPanel.cbFFT.SetValue(False)
    time.sleep(dt) 
    with PerfMon('Plot 3'):
        frame.selPanel.colPanel1.lbColumns.SetSelection(4)
        frame.selPanel.colPanel1.lbColumns.SetSelection(6)
        frame.onColSelectionChange()
    time.sleep(dt) 
    with PerfMon('Redraw 3'):
        frame.plotPanel.redraw()
    time.sleep(dt) 
    with PerfMon('FFT 3'):
        frame.plotPanel.cbFFT.SetValue(True)
        frame.plotPanel.redraw()
        frame.plotPanel.cbFFT.SetValue(False)
    #app.MainLoop()

 
# --------------------------------------------------------------------------------}
# --- Mains 
# --------------------------------------------------------------------------------{
def pydatview(dataframe=None,filenames=[]):
    """
    The main function to start the data frame GUI.
    """
    app = wx.App(False)
    frame = MainFrame()

    if (dataframe is not None) and (len(dataframe)>0):
        #import time
        #tstart = time.time()
        frame.load_df(dataframe)
        #tend = time.time()
        #print('PydatView time: ',tend-tstart)
    elif len(filenames)>0:
        frame.load_files(filenames,fileformat=None)

    app.MainLoop()

def cmdline():
    if len(sys.argv)>1:
        pydatview(filename=sys.argv[1])
    else:
        pydatview()
