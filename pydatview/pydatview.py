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
from matplotlib.figure import Figure
from matplotlib.pyplot import rcParams as pyplot_rc
#from matplotlib import pyplot as plt
import numpy as np
import os.path 
import pandas as pd
import sys
import traceback 
from dateutil import parser
import gc
import pdb

from .GUIMultiSplit import MultiSplit
import weio # File Formats and File Readers



# --------------------------------------------------------------------------------}
# --- GLOBAL 
# --------------------------------------------------------------------------------{
PROG_NAME='pyDatView'
PROG_VERSION='v0.1-local'
FILE_FORMATS            = weio.fileFormats()
FILE_FORMATS_EXTENSIONS = [['.*']]+[f.extensions for f in FILE_FORMATS]
FILE_FORMATS_NAMES      = ['auto (any supported file)'] + [f.name for f in FILE_FORMATS]
FILE_FORMATS_NAMEXT     =['{} ({})'.format(n,','.join(e)) for n,e in zip(FILE_FORMATS_NAMES,FILE_FORMATS_EXTENSIONS)]
FILE_READER             = weio.read

SIDE_COL = [150,150,250,350]

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
        x = range(len(df.iloc[:, 1]))
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
    ss = common_start(strings)
    se = common_end(strings)
    iu = ss[:-1].rfind('_')
    if iu > 0:
        ss=ss[:iu+1]
    iu = se[:-1].find('_')
    if iu > 0:
        se=se[iu:]
    iu = se[:-1].find('.')
    if iu > 0:
        se=se[iu:]

    ns=len(ss)     
    ne=len(se)     

    strings = [s[ns:] for s in strings] 
    if ne>0:
        strings = [s[:-ne] for s in strings] 
    for i,s in enumerate(strings):
        if len(s)==0:
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
            self.columns = df.columns.values
        else: 
            # ndarray??
            raise Exception('Implementation of tables with ndarray dropped for now')
            self.name=name
            self.data=data
            self.columns=columns
        self.filename = filename
        self.name=os.path.splitext(os.path.basename(self.filename))[0]+'|'+ self.name
        
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
        B=[all(tabs[i].columns==tabs[I[0]].columns) for i in I ]
        return all(B)
    else:
        return False

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

    def showStats(self,tabs,ITab,ColIndexes,ColNames,erase=False):
        if erase:
            self.tInfo.SetValue("")
        for iTab in ITab:
            tab = tabs[iTab]
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
                    self.tInfo.AppendText('{:15s} mean:{:10.3e}  std:{:10.3e}  min:{:10.3e}  max:{:10.3e}\n'.format(s,np.nanmean(y),np.nanstd(y),np.nanmin(y),np.nanmax(y)))
        self.tInfo.ShowPosition(0)

        
# --------------------------------------------------------------------------------}
# --- SelectionPanel:  
# --------------------------------------------------------------------------------{
class ColumnPanel(wx.Panel):
    """ A list of columns for x and y axis """
    def __init__(self, parent):
        # Superclass constructor
        super(ColumnPanel,self).__init__(parent)
        #lbX = wx.StaticText( self, -1, 'x: ')
        self.comboX = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        self.comboX.SetFont(getMonoFont())
        self.lbColumns=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED )
        self.lbColumns.SetFont(getMonoFont())
        #self.SetBackgroundColour('blue')

        sizerX = wx.BoxSizer(wx.HORIZONTAL)
        #sizerX.Add(lbX           ,0,wx.ALL | wx.ALIGN_CENTER,5)
        sizerX.Add(self.comboX   , 0, flag=wx.TOP | wx.BOTTOM | wx.EXPAND, border=5)

        sizerCol = wx.BoxSizer(wx.VERTICAL)
        sizerCol.Add(sizerX        , 0, border=5)
        sizerCol.Add(self.lbColumns, 2, flag=wx.EXPAND, border=0)

        self.SetSizer(sizerCol)

    def selectDefaultColumns(self,tab):
        df=tab.data
        # Selecting the first column for x-axis
        iSelect = min(1,self.comboX.GetCount())
        _,isString,_,_=getColumn(df,iSelect)
        if isString:
            iSelect = 0 # we roll back and select the index
        self.comboX.SetSelection(iSelect)

        # Selecting the second column for y-axis
        iSelect=min(2,self.lbColumns.GetCount())
        _,isString,_,_=getColumn(df,iSelect)
        if isString:
            iSelect=0 # we roll back to selecting the index
        self.lbColumns.SetSelection(iSelect)

    def updateColumnNames(self,tab):
        """ Update of column names """
        # Backup of selection first
        ISel=self.lbColumns.GetSelections()
        iSel = self.comboX.GetSelection()
        # ..then empty
        self.empty()
        # ..then replace
        columns=['Index']+list(tab.columns[:])
        columns=[s.replace('_',' ') for s in columns]
        for c in columns:
            self.lbColumns.Append(c)
        for i in ISel:
            if i<len(columns):
                self.lbColumns.SetSelection(i)
                self.lbColumns.EnsureVisible(i)
        for c in columns:
            self.comboX.Append(c)
        if iSel<0:
            self.selectDefaultColumns(tab) # not pretty
        elif iSel<len(columns):
            self.comboX.SetSelection(iSel)

    def forceOneSelection(self):
        ISel=self.lbColumns.GetSelections()
        self.lbColumns.SetSelection(-1)
        if len(ISel)>0:
            self.lbColumns.SetSelection(ISel[0])

    def empty(self):
        for i in reversed(range(self.lbColumns.GetCount())):
            self.lbColumns.Delete(i)
        for i in reversed(range(self.comboX.GetCount())):
            self.comboX.Delete(i)

    def getColumnSelection(self):
        iX = self.comboX.GetSelection()
        sX = self.comboX.GetStringSelection()
        IY = self.lbColumns.GetSelections()
        SY = [self.lbColumns.GetString(i) for i in IY]
        return iX,IY,sX,SY

class TablePanel(wx.Panel):
    """ Display list of tables """
    def __init__(self, parent):
        # Superclass constructor
        super(TablePanel,self).__init__(parent)
        # DATA
        label = wx.StaticText( self, -1, 'Tables: ')
        self.lbTab=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED)
        self.lbTab.SetFont(getMonoFont())
        #self.lbTab.Hide()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, border=5)
        sizer.Add(self.lbTab, 2, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)
        


SEL_MODES    = ['auto','Same tables'    ,'Different tables'  ]
SEL_MODES_ID = ['auto','sameColumnsMode','twoColumnsMode']

class SelectionPanel(wx.Panel):
    """ Display options for the user to select data """
    def __init__(self, parent, tabs, mode='auto'):
        # Superclass constructor
        super(SelectionPanel,self).__init__(parent)
        # DATA
        self.tabs       = []
        self.itabForCol = None
        self.parent     = parent

        # GUI DATA
        self.splitter  = MultiSplit(self, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(70)
        self.tabPanel  = TablePanel (self.splitter);
        self.colPanel1 = ColumnPanel(self.splitter);
        self.colPanel2 = ColumnPanel(self.splitter);
        self.tabPanel.Hide()
        self.colPanel1.Hide()
        self.colPanel2.Hide()
        # Layout
        self.updateLayout(mode)
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

    def updateLayout(self,mode):
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
        if len(self.tabs)>1:
            self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel1) 

    def twoColumnsMode(self):
        self._mode='twoColumnsMode'
        self.splitter.removeAll()
        self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel2) 
        self.splitter.AppendWindow(self.colPanel1) 
        #self.parent.GetParent().GetParent().GetParent().resizeSideColumn(SIDE_COL_LARGE)

    def updateTables(self,tabs):
        """ Update the list of tables, while keeping the selection if any """
        self.tabs = tabs
        ISel=self.tabPanel.lbTab.GetSelections()
        tabnames=[t.name for t in tabs]
        etabnames=ellude_common(tabnames)
        for i in reversed(range(self.tabPanel.lbTab.GetCount())):
            self.tabPanel.lbTab.Delete(i)

        for t in etabnames:
            self.tabPanel.lbTab.Append(t)

        # Reselecting
        if len(ISel)>0:        
            if not haveSameColumns(tabs,ISel):
                ISel=[ISel[0]]
            for i in ISel:
                if i<len(tabs):
                    self.tabPanel.lbTab.SetSelection(i)
        #
        if len(self.tabPanel.lbTab.GetSelections())==0:
            self.selectDefaultTable()

        # Trigger - updating columns and layout
        ISel=self.tabPanel.lbTab.GetSelections()
        # TODO
        self.setTabForCol(ISel[0],1) # TODO
        self.updateLayout(self.modeRequested)

    def setTabForCol(self,iTabSel,iPanel):
        if iPanel==1:
            self.colPanel1.updateColumnNames(self.tabs[iTabSel])
        elif iPanel==2:
            self.colPanel2.updateColumnNames(self.tabs[iTabSel])
        else:
            raise Exception('Wrong ipanel')

    def selectDefaultTable(self):
        # Selecting the first table
        if self.tabPanel.lbTab.GetCount()>0:
            self.tabPanel.lbTab.SetSelection(0)


    def update_tabs(self, tabs):
        self.updateTables(tabs)

    def getFullSelection(self):
        ITab,STab = self.getSelectedTables()
        iX1,IY1,sX1,SY1 = self.colPanel1.getColumnSelection()
        ID = []
        if self._mode =='sameColumnsMode':
            for i,itab in enumerate(ITab):
                for j,iy in enumerate(IY1):
                    ID.append([itab,iX1,iy])
            iX2=None
            IY2=None
            sX2=None
            SY2=None
        elif self._mode =='twoColumnsMode':
            if len(ITab)>=1:
                for j,iy in enumerate(IY1):
                    ID.append([ITab[0],iX1,iy])
                iX2=None
                IY2=None
                sX2=None
                SY2=None
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
        if hasattr(self,'tabs'):
            del self.tabs

# --------------------------------------------------------------------------------}
# --- Plot Panel 
# --------------------------------------------------------------------------------{
class MyNavigationToolbar2Wx(NavigationToolbar2Wx): 
    def __init__(self, plotCanvas):
        NavigationToolbar2Wx.__init__(self, plotCanvas)
        self.DeleteToolByPos(1)
        self.DeleteToolByPos(1)
        #self.SetToolBitmapSize((22,22))

class PlotPanel(wx.Panel):
    def __init__(self, parent, selPanel):

        # Superclass constructor
        super(PlotPanel,self).__init__(parent)
        # data
        self.selPanel=selPanel
        self.parent=parent
        # GUI
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        self.fig.subplots_adjust(top=0.98,bottom=0.12,left=0.12,right=0.98)
        self.canvas = FigureCanvas(self, -1, self.fig)

        self.navTB = MyNavigationToolbar2Wx(self.canvas)

        #lbX = wx.StaticText( self, -1, 'x-axis: ')
        # Check Boxes
        self.cbScatter = wx.CheckBox(self, -1, 'Scatter',(10,10))
        self.cbPDF     = wx.CheckBox(self, -1, 'PDF',(10,10))
        self.cbFFT     = wx.CheckBox(self, -1, 'FFT',(10,10))
        self.cbSub     = wx.CheckBox(self, -1, 'Subplot',(10,10))
        self.cbLogX    = wx.CheckBox(self, -1, 'Log-x',(10,10))
        self.cbLogY    = wx.CheckBox(self, -1, 'Log-y',(10,10))
        self.cbMinMax  = wx.CheckBox(self, -1, 'MinMax',(10,10))
        self.cbSync    = wx.CheckBox(self, -1, 'Sync-x',(10,10))
        #self.cbSub.SetValue(True) # DEFAULT TO SUB?
        self.cbSync.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.scatter_select  , self.cbScatter)
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
        if sys.version_info[0] < 3:
            cb_sizer = wx.GridSizer(2,4,3)
        else:
            cb_sizer = wx.GridSizer(4,2,3)
        cb_sizer.Add(self.cbScatter, 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPDF    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFFT    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSub    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogX   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogY   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMinMax , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSync   , 0, flag=wx.ALL, border=1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #row_sizer.Add(lbX           ,0,wx.ALL | wx.ALIGN_CENTER,5)
        #row_sizer.Add(self.colPanel1.comboX   ,0,wx.ALL | wx.ALIGN_CENTER,5)
        row_sizer.Add(self.navTB    ,0, flag=wx.ALL, border=5)
        row_sizer.Add(cb_sizer      ,0, flag=wx.ALL, border=5)

        plotsizer = wx.BoxSizer(wx.VERTICAL)
        plotsizer.Add(self.canvas, 1, flag=wx.EXPAND, border=5)
        plotsizer.Add(row_sizer)

        self.SetSizer(plotsizer)
        #self.redraw()

    def redraw_event(self, event):
        self.redraw()
    def fft_select(self, event):
        self.cbPDF.SetValue(False)
        self.cbMinMax.SetValue(False)
        self.cbLogY.SetValue(True)
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
        #import pdb
        #pdb.set_trace()
        x,xIsString,xIsDate,_=getColumn(df,ix)

        nPlots=len(I)
        bSubPlots=self.cbSub.IsChecked()

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
                    if xIsDate:
                        dt = np.timedelta64((x[1]-x[0]),'s').item().total_seconds()
                    else:
                        dt = x[1]-x[0]
                    y = np.array(y)
                    y = y[~np.isnan(y)]
                    n = len(y) 
                    Fs = 1/dt
                    k = np.arange(n)
                    T = n/Fs
                    frq = k/T # two sides frequency range
                    frq = frq[range(int(n/2))] # one side frequency range
                    Y = np.fft.fft(y)/n # fft computing and normalization
                    Y = Y[range(int(n/2))]
                    ax.plot(frq, abs(Y), label=ylabelLeg)
                    if bFirst:
                        ax.set_ylabel('FFT ('+ylabel+')')
                        if self.cbLogX.IsChecked():
                            ax.set_xscale("log", nonposx='clip')
                        if self.cbLogY.IsChecked():
                            if all(Y<=0):
                                pass
                            else:
                                ax.set_yscale("log", nonposy='clip')

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
    def redraw(self):
        self._redraw()

    def _redraw(self):
        #print('Redraw event')

        ID,ITab,iX1,IY1,iX2,IY2,STab,sX1,SY1,sX2,SY2=self.selPanel.getFullSelection()
        if len(ID)==0:
            #Error(self.parent,'Open a file to plot the data.')
            return

        tabs=self.selPanel.tabs
        if iX2 is None:
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
                if sX1!=sX2:
                    xlabel=sX1+' and '+ sX2
                else:
                    xlabel=sX1
                Ylabels = [s1+' and '+s2 for s1,s2 in zip(SY1,SY2)]
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
        if filename is not None:
            self.filenames=[filename]
        else:
            self.filenames=[]
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

        # --- Main Frame (self)
        FrameSizer = wx.BoxSizer(wx.VERTICAL)
        FrameSizer.Add(self.MainPanel,1, flag=wx.EXPAND)
        self.SetSizer(FrameSizer)

        self.SetSize((800, 600))
        self.Center()

        self.Show()

    def clean_memory(self,bReload=False):
        #print('Clean memory')
        # force Memory cleanup
        if hasattr(self,'dfs'):
            del self.dfs
        if hasattr(self,'tabs'):
            del self.tabs
        if hasattr(self,'selPanel'):
            self.selPanel.clean_memory()

        if hasattr(self,'plotPanel'):
            self.plotPanel.cleanPlot()
        gc.collect()

    def load_files(self,filenames=[],fileformat=None, bReload=False,bAdd=False):
        """ load multiple files, only trigger the plot at the end """
        for i,f in enumerate(filenames):
            if i>0:
                bAdd = True
            if bAdd and (f in self.filenames):
                Error(self,'Cannot add a file already opened')
            else:
                self.load_file(f,fileformat=fileformat,bAdd=bAdd,bPlot=False)
        # Trigger a plot event at the end, in case an error occured
        self.updateLayout()
        self.onColSelectionChange(event=None)

    def load_file(self,filename,fileformat=None,bReload=False,bAdd=False,bPlot=True):
        """ load a single file, adds table, and potentially trigger plotting """
        if not os.path.isfile(filename):
            Error(self,'File not found: '+filename)
            return
        if bAdd:
            self.filenames.append(filename)
        else:
            # Cleaning memory
            self.clean_memory(bReload=bReload)
            self.filenames=[filename]
        try:
            #
            F = FILE_READER(filename,fileformat = fileformat)
            dfs = F.toDataFrame()
        except IOError:
            Error(self, 'IO Error,  cannot open file: '+filename )
            return
        except MemoryError:
            Error(self,'Insufficient memory!\n\nTry closing and reopening the program, or use a 64 bit version of this program (i.e. of python).')
            return
        except weio.FormatNotDetectedError:
            Error(self,'File format not detected!\n\nUse an explicit file-format from the list')
            return
        except weio.WrongFormatError as e:
            Error(self,'Wrong file format!\n\n'+   \
                    'The file parser for the selected format failed to open the file.\n\n'+   \
                    'The reported error was:\n'+e.args[0]+'\n\n' +   \
                    'Double-check your file format and report this error if you think it''s a bug.')
            return
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
        else:
            self.load_tabs(tabs,bReload=bReload,bAdd=bAdd,bPlot=bPlot)
        del dfs
        del F
            

    def load_df(self, df):
        tab=[Table(df=df, name='default')]
        self.load_tabs(tab)

    def load_tabs(self, tabs, bReload=False, bAdd=False, bPlot=True):
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
        # plot trigger
        if bPlot:
            self.updateLayout()
            self.onColSelectionChange(event=None)

    def onSashChangeMain(self,event):
        pass
        # doent work because size is not communicated yet
        #if hasattr(self,'selPanel'):
        #    print('ON SASH')
        #    self.selPanel.setEquiSash(event)

    def onTabSelectionChange(self,event):
        # TODO all this can go in TabPanel
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
                        self.selPanel.tabPanel.lbTab.SetSelection(wx.NOT_FOUND)
                        self.selPanel.tabPanel.lbTab.SetSelection(ISel[0])
                        self.selPanel.setTabForCol(ISel[0],1) 
                    else:
                        self.selPanel.setTabForCol(ISel[0],1) 
                        self.selPanel.setTabForCol(ISel[1],2) 
                else:
                    Error(self,'The two tables have different columns. Chose the "two table mode" to compare them.')
                    # unselect all and select only the first one
                    self.selPanel.tabPanel.lbTab.SetSelection(wx.NOT_FOUND)
                    self.selPanel.tabPanel.lbTab.SetSelection(ISel[0])
                    self.selPanel.setTabForCol(ISel[0],1) 


            # Trigger the colSelection Event
            self.onColSelectionChange(event=None)

    def onColSelectionChange(self,event):
        if hasattr(self,'plotPanel'):
            if self.selPanel._mode=='twoColumnsMode':
                if len(self.selPanel.tabPanel.lbTab.GetSelections())==2:
                    self.selPanel.colPanel1.forceOneSelection()
                    self.selPanel.colPanel2.forceOneSelection()
            self.plotPanel.redraw()
            #print(self.tabs)
            # --- Stats trigger
            ID,ITab,iX1,IY1,iX2,IY2,STab,sX1,SY1,sX2,SY2=self.selPanel.getFullSelection()
            if sX2 is None:
                self.infoPanel.showStats(self.tabs,ITab,IY1,SY1,erase=True)
            else:
                self.infoPanel.showStats(self.tabs,[ITab[0]],IY1,SY1,erase=True)
                self.infoPanel.showStats(self.tabs,[ITab[1]],IY2,SY2)

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

    def onSave(self, event):
        # using the navigation toolbar save functionality
        self.plotPanel.navTB.save_figure()

    def onAbout(self, event):
        Info(self,PROG_NAME+' '+PROG_VERSION+'\n\nWritten by E. Branlard. \n\nVisit http://github.com/ebranlard/pyDatView for documentation.')

    def onReload(self, event):
        if (self.filenames is not None) and len(self.filenames)==1 and len(self.filenames[0])>0:
            iFormat=self.comboFormats.GetSelection()
            if iFormat==0: # auto-format
                Format = None
            else:
                Format = FILE_FORMATS[iFormat-1]
            self.load_file(self.filenames[0],fileformat=Format,bReload=True)
        elif len(self.filenames)>=1 :
           Error(self,'Reloading only implemented for one file for now.')
        else:
           Error(self,'Open a file first')

    def onDEBUG(self, event):
        self.clean_memory()
        #del self.plotPanel.fig
        #del self.plotPanel.canvas
        #del self.plotPanel.navTB
        #del self.plotPanel
        #del self.selPanel
        #gc.collect()
        #self.cleanGUI()
        #gc.collect()
        #ptr = self.selPanel.tabPanel.lbTab
        #if ptr.IsShown():
        #    ptr.Hide()
        #    self.resizeSideColumn(SIDE_COL_SMALL)
        #else:
        #    ptr.Show()
        #    self.resizeSideColumn(SIDE_COL_LARGE)
    def onLoad(self, event):
        self.selectFile(bAdd=False)

    def onAdd(self, event):
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
        self.updateLayout()

    def updateLayout(self, event=None):
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
    def on_tab_change(self, event):
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
    # --- Test df
    tstart = time.time()
    nRow =10**7;
    nCols=10;
    d={}
    d['col0'] = np.linspace(0,1,nRow);
    for iC in range(1,nCols):
        name='col{}'.format(iC)
        d[name] = np.random.normal(0,1,nRow)+2*iC
#     df = pd.DataFrame(data={'col1':np.linspace(0,1,size) , 'col2': np.random.normal(0,1,size)})
    tend = time.time()
    df = pd.DataFrame(data=d)
    print('Size:',sys.getsizeof(df)/10**6)
    print('Creation time: ',tend-tstart)
    pydatview(df)

 
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
