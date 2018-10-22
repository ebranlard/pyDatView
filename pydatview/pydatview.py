from __future__ import division, print_function

#import pdb
import wx
import dateutil # required by matplotlib
from matplotlib import rc as matplotlib_rc
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
#from matplotlib import pyplot as plt
import numpy as np
import os.path 
import pandas as pd
import sys
import traceback 
from dateutil import parser

import weio # File Formats and File Readers



# --------------------------------------------------------------------------------}
# --- GLOBAL 
# --------------------------------------------------------------------------------{
PROG_NAME='pyDatView'
FILE_FORMATS            = weio.fileFormats()
FILE_FORMATS_EXTENSIONS = [f.extensions for f in FILE_FORMATS]
FILE_FORMATS_NAMES      = ['auto (any supported file)'] + [f.name for f in FILE_FORMATS]
FILE_READER             = weio.read

SIDE_COL_SMALL = 130
SIDE_COL_LARGE = 230

font = {'size'   : 9}
matplotlib_rc('font', **font)
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
        s='{:2d}.{:2d}s'.format(0,int(c))
    elif(t<60) :
        s=nb.floor(t);
        c=nb.floor((t-s)*100);
        s='{:2d}.{:2d}s'.format(int(s),int(c))
    elif(t<3600) :
        m=np.floor(t/60);
        s=np.mod( np.floor(t), 60);
        s='{:2d}m{:2d}s'.format(int(m),int(s))
    elif(t<86400) :
        h=np.floor(t/3600);
        m=np.floor(( np.mod( np.floor(t) , 3600))/60);
        s='{:2d}h{:2d}m'.format(int(h),int(m))
    elif(t<8553600) : #below 3month
        d=np.floor(t/86400);
        h=np.floor( np.mod(np.floor(t), 86400)/3600);
        s='{:2d}d{:2d}h'.format(int(d),int(h))
    elif(t<31536000):
        m=t/(3600*24*30.5);
        s='{:4.1f}mh'.format(m)
        #s='+3mon.';
    else:
        y=t/(3600*24*365.25);
        s='{:.1f}y'.format(y)
    return s

# --------------------------------------------------------------------------------}
# --- Table 
# --------------------------------------------------------------------------------{
class Table(object):
    def __init__(self,data=[],columns=[],name='',df=None):
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

    def showStats(self,tabs,ITab,ColIndexes,ColNames):
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
class SelectionPanel(wx.Panel):
    """ Display options for the user to select data """
    def __init__(self, parent, tabs):
        # Superclass constructor
        super(SelectionPanel,self).__init__(parent)
        self.parent = parent
        # GUI
        #self.lbTab=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED )
        self.lbTab=wx.ListBox(self, -1, choices=[])
        self.lbTab.SetFont(getMonoFont())
        #self.lbTab.Hide()

        lbX = wx.StaticText( self, -1, 'x: ')
        self.comboX = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        self.lbColumns=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED )
        self.lbColumns.SetFont(getMonoFont())

        sizerX = wx.BoxSizer(wx.HORIZONTAL)
        sizerX.Add(lbX           ,0,wx.ALL | wx.ALIGN_CENTER,5)
        sizerX.Add(self.comboX   ,0,wx.ALL | wx.ALIGN_CENTER,5)

        sizerCol = wx.BoxSizer(wx.VERTICAL)
        sizerCol.Add(sizerX       , 0, border=5)
        sizerCol.Add(self.lbColumns, 2, flag=wx.EXPAND, border=5)

        self.MainSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.MainSizer.Add(self.lbTab, 2, flag=wx.EXPAND, border=5)
        self.MainSizer.Add(sizerCol  , 2, flag=wx.EXPAND, border=5)
        self.SetSizer(self.MainSizer)

        #
        self.tabs=tabs
        if len(tabs)>0:
            #print(tabs)
            self.updateTables(tabs)
            self.selectDefaultTable()
            self.selectDefaultColumns(self.tabForCol)

    def updateTables(self,tabs):
        """ Update the list of tables, while keeping the selection if any """
        self.tabs = tabs
        ISel=self.lbTab.GetSelections()
        tabnames=[t.name for t in tabs]
        #print('Updating tables with:')
        #print(tabs)
        for i in reversed(range(self.lbTab.GetCount())):
            self.lbTab.Delete(i)
        for t in tabnames:
            self.lbTab.Append(t)
        for i in ISel:
            if i<len(tabnames):
                self.lbTab.SetSelection(i)
        if len(ISel)==0:        
            self.selectDefaultTable()
        # Trigger - updating columns
        ISel=self.lbTab.GetSelections()
        self.setTabForCol(ISel[0])
        # Trigger 
        if len(tabs)>1:
            self.lbTab.Show()
        else:
            self.lbTab.Hide()

    def setTabForCol(self,iSel):
        self.tabForCol = self.tabs[iSel]
        self.updateColumnNames(self.tabForCol)

    def selectDefaultTable(self):
        # Selecting the first table
        if self.lbTab.GetCount()>0:
            self.lbTab.SetSelection(0)

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

    def updateColumnNames(self,df):
        """ Update of column names """
        ISel=self.lbColumns.GetSelections()
        self.columns=['Index']+list(df.columns[:])
        for i in reversed(range(self.lbColumns.GetCount())):
            self.lbColumns.Delete(i)
        for c in self.columns:
            self.lbColumns.Append(c)
        for i in ISel:
            if i<len(self.columns):
                self.lbColumns.SetSelection(i)

        iSel    = self.comboX.GetSelection()
        for i in reversed(range(self.comboX.GetCount())):
            self.comboX.Delete(i)
        for c in self.columns:
            self.comboX.Append(c)
        if iSel<len(self.columns):
            self.comboX.SetSelection(iSel)

    def update_tabs(self, tabs):
        self.updateTables(tabs)

    def getSelectedColumns(self):
        I=self.lbColumns.GetSelections()
        S=[self.lbColumns.GetString(i) for i in I]
        return I,S

    def getSelectedTables(self):
        I=self.lbTab.GetSelections()
        S=[self.lbTab.GetString(i) for i in I]
        return I,S

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
        cb_sizer.Add(self.cbScatter,0,wx.ALL                  ,1)
        cb_sizer.Add(self.cbPDF    ,0,wx.ALL                  ,1)
        cb_sizer.Add(self.cbFFT    ,0,wx.ALL                  ,1)
        cb_sizer.Add(self.cbSub    ,0,wx.ALL                  ,1)
        cb_sizer.Add(self.cbLogX   ,0,wx.ALL                  ,1)
        cb_sizer.Add(self.cbLogY   ,0,wx.ALL                  ,1)
        cb_sizer.Add(self.cbMinMax ,0,wx.ALL                  ,1)
        cb_sizer.Add(self.cbSync   ,0,wx.ALL                  ,1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #row_sizer.Add(lbX           ,0,wx.ALL | wx.ALIGN_CENTER,5)
        #row_sizer.Add(self.comboX   ,0,wx.ALL | wx.ALIGN_CENTER,5)
        row_sizer.Add(self.navTB    ,0,wx.ALL                  ,5)
        row_sizer.Add(cb_sizer      ,0,wx.ALL                  ,5)

        plotsizer = wx.BoxSizer(wx.VERTICAL)
        plotsizer.Add(self.canvas, 1, flag=wx.EXPAND, border=5)
        plotsizer.Add(row_sizer)

        self.SetSizer(plotsizer)

        self.redraw()

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

    def redraw(self):
        tabs=self.selPanel.tabs
        if len(tabs) <= 0:
            return

        # TODO TODO GETDATA FROM SOMETHING ELSE
        ITab,STab= self.selPanel.getSelectedTables()
        if len(ITab)<=0 or len(ITab)>1:
            return
        self.df = tabs[ITab[0]].data


        I,S = self.selPanel.getSelectedColumns()
        nPlots=len(I)
        if nPlots<0:
            return


        # Selecting x values
        ix     = self.selPanel.comboX.GetSelection()
        xlabel = self.selPanel.comboX.GetStringSelection()
        #import pdb
        #pdb.set_trace()
        x,xIsString,xIsDate,_=getColumn(self.df,ix)

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

        for i in range(nPlots):
            if bSubPlots:
                ax = self.fig.axes[i]
                ax.clear()
            else:
                ax = self.fig.axes[0]

            # Selecting y values
            iy = I[i]
            ylabel  = S[i]
            y,yIsString,yIsDate,c=getColumn(self.df,iy)

            # Scaling
            if self.cbMinMax.IsChecked():
                mi= np.min(y)
                mx= np.max(y)
                if mi == mx:
                    y=y*0
                else:
                    y = (y-np.min(y))/(max(y)-min(y))
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
                    #n=1000
                    #y = np.random.normal(size=n) 
                    pdf, xx = np.histogram(y[~np.isnan(y)], bins=min(int(n/10),50))
                    dx  = xx[1] - xx[0]
                    xx  = xx[:-1] + dx/2
                    pdf = pdf / (n*dx)
                    ax.plot(xx, pdf, label=ylabel)
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
                    ax.plot(frq, abs(Y), label=ylabel)
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
                    if self.cbScatter.IsChecked():
                        sty='o'
                    else:
                        sty='-'
                    ax.plot(x,y, sty, label=ylabel, markersize=1)
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

        if (not bSubPlots and nPlots!=1):
            ax.legend()
        self.canvas.draw()


# --------------------------------------------------------------------------------}
# --- Main Frame  
# --------------------------------------------------------------------------------{
class MainFrame(wx.Frame):
    def __init__(self, df=None, filename=None):
        # Parent constructor
        wx.Frame.__init__(self, None, -1, PROG_NAME)
        # Data
        self.df=df
        self.filename=filename
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
        btOpen   = wx.Button( tb, wx.NewId(), "Open", wx.DefaultPosition, wx.DefaultSize )
        btReload = wx.Button( tb, wx.NewId(), "Reload", wx.DefaultPosition, wx.DefaultSize )
        #btDEBUG  = wx.Button( tb, wx.NewId(), "DEBUG", wx.DefaultPosition, wx.DefaultSize )
        self.comboFormats = wx.ComboBox( tb, choices = FILE_FORMATS_NAMES  , style=wx.CB_READONLY)  
        self.comboFormats.SetSelection(0)
        tb.AddStretchableSpace()
        tb.AddControl( wx.StaticText( tb, -1, 'File format: ' ) )
        tb.AddControl(self.comboFormats ) 
        tb.AddSeparator()
        tb.AddControl(btOpen)
        tb.AddSeparator()
        tb.AddControl(btReload)
        tb.AddStretchableSpace()
        tb.AddSeparator()
        tb.Bind(wx.EVT_BUTTON,self.onLoad  ,btOpen  )
        tb.Bind(wx.EVT_BUTTON,self.onReload,btReload)
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

    def load_file(self,filename,fileformat=None,bReload=False):
        if not os.path.isfile(filename):
            Error(self,'File not found: '+filename)
            return
        self.filename=filename
        try:
            F = FILE_READER(filename,fileformat = fileformat)
            dfs = F.toDataFrame()
            self.statusbar.SetStatusText(F.filename,1)
            if fileformat is None:
                self.statusbar.SetStatusText('Detected: '+F.formatName())
            else:
                self.statusbar.SetStatusText('Format: '+F.formatName())
            if len(dfs)<=0:
                Warn(self,'No dataframe found while converting file:'+filename)
            else:
                self.load_df(dfs,bReload=bReload)
        except IOError:
            self.statusbar.SetStatusText('FAIL: '+filename,1)
            wx.LogError("Cannot open file:"+filename )

    def load_df(self, dfs, bReload=False):
        if not bReload:
            self.cleanGUI()

        #  Creating a list of tables
        if not isinstance(dfs,dict):
            tabs=[Table(df=dfs, name='default')]
        else:
            tabs=[]
            for k in list(dfs.keys()):
                tabs.append(Table(df=dfs[k], name=k))

        ##
        self.tabs=tabs
        if len(tabs)==1:
            self.statusbar.SetStatusText('{}x{}'.format(tabs[0].nCols,tabs[0].nRows),2)

        if bReload:
            self.selPanel.update_tabs(tabs)
            # trigger
            self.onColSelectionChange(event=None)
            ## NOTE: stat trigger here is misplaced
            #I,S = self.selPanel.getSelectedColumns()
            #self.infoPanel.showStats(df,I,S)
        else:
            #
            self.vSplitter = wx.SplitterWindow(self.nb)
            self.selPanel = SelectionPanel(self.vSplitter, tabs)

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
            self.vSplitter.SetMinimumPaneSize(SIDE_COL_SMALL)
            self.tSplitter.SetSashPosition(SIDE_COL_SMALL)

            self.nb.AddPage(self.vSplitter, "Plot")
            self.nb.SendSizeEvent()

            self.Bind(wx.EVT_COMBOBOX, self.onColSelectionChange, self.selPanel.comboX   )
            self.Bind(wx.EVT_LISTBOX , self.onColSelectionChange, self.selPanel.lbColumns)
            self.Bind(wx.EVT_LISTBOX , self.onTabSelectionChange, self.selPanel.lbTab)
            self.onColSelectionChange(event=None)
        # Trigger 
        if len(tabs)>1:
            #self.selPanel.lbTab.Show()
            self.resizeSideColumn(SIDE_COL_LARGE)
        else:
            #self.lbTab.Hide()
            self.resizeSideColumn(SIDE_COL_SMALL)

    def onTabSelectionChange(self,event):
        ISel=self.selPanel.lbTab.GetSelections()
        if len(ISel)>0:
            # Setting tab
            self.selPanel.setTabForCol(ISel[0])
            #print('Selected: '+str(self.selPanel.tabForCol))
            self.plotPanel.redraw()
            # --- Stats
            ITab,STab = self.selPanel.getSelectedTables()
            I,S = self.selPanel.getSelectedColumns()
            self.infoPanel.showStats(self.tabs,ITab,I,S)

    def onColSelectionChange(self,event):
        self.plotPanel.redraw()
        #print(self.tabs)
        # --- Stats
        ITab,STab = self.selPanel.getSelectedTables()
        I,S = self.selPanel.getSelectedColumns()
        self.infoPanel.showStats(self.tabs,ITab,I,S)

    def onExit(self, event):
        self.Close()

    def cleanGUI(self, event=None):
        self.deletePages()

    def onSave(self, event):
        # using the navigation toolbar save functionality
        self.plotPanel.navTB.save_figure()

    def onAbout(self, event):
        Info(self,'For authors/help/revision/license visit http://github.com/ebranlard/pyDatView')

    def onReload(self, event):
        if (self.filename is not None) and len(self.filename)>0:
           self.load_file(self.filename,fileformat=None,bReload=True)
        else:
           Error(self,'Open a file first')

    def onDEBUG(self, event):
        ptr = self.selPanel.lbTab
        if ptr.IsShown():
            ptr.Hide()
            self.resizeSideColumn(SIDE_COL_SMALL)
        else:
            ptr.Show()
            self.resizeSideColumn(SIDE_COL_LARGE)

    def onLoad(self, event):
        # --- File Format extension
        iFormat=self.comboFormats.GetSelection()
        sFormat=self.comboFormats.GetStringSelection()
        if iFormat==0: # auto-format
            Format = None
            wildcard = 'all (*.*)|*.*'
        else:
            Format = FILE_FORMATS[iFormat-1]
            extensions='|*'+';*'.join(FILE_FORMATS[iFormat-1].extensions)
            wildcard = sFormat + extensions+'|all (*.*)|*.*'

        with wx.FileDialog(self, "Open file", wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            #other options: | wx.MULTIPLE | wx.CHANGE_DIR
            #dlg.SetSize((100,100))
            #dlg.Center()
           if dlg.ShowModal() == wx.ID_CANCEL:
               return     # the user changed their mind
           self.load_file(dlg.GetPath(),fileformat=Format)

    # --- Side column
    def resizeSideColumn(self,width):
        # To force the replot we do an epic unsplit/split...
        self.vSplitter.Unsplit()
        self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
        self.vSplitter.SetMinimumPaneSize(width)
        self.vSplitter.SetSashPosition(width)

    # --- NOTEBOOK 
    def deletePages(self):
        for index in reversed(range(self.nb.GetPageCount())):
            self.nb.DeletePage(index)
        self.nb.SendSizeEvent()
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

 
def pydatview(dataframe=None,filename=''):
    """
    The main function to start the data frame GUI.
    """
    app = wx.App(False)
    frame = MainFrame()

    if (dataframe is not None) and (len(dataframe)>0):
        frame.load_df(dataframe)
    elif len(filename)>0:
        frame.load_file(filename,fileformat=None)

    app.MainLoop()

def cmdline():
    if len(sys.argv)>1:
        pydatview(filename=sys.argv[1])
    else:
        pydatview()
