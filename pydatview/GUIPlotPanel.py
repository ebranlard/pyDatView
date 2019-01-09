
import numpy as np
import wx
import dateutil # required by matplotlib
#from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg') # Important for Windows version of installer
from matplotlib import rc as matplotlib_rc
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.figure import Figure
from matplotlib.pyplot import rcParams as pyplot_rc
from matplotlib.widgets import Cursor
import gc

try:
    from .spectral import pwelch, hamming , boxcar, hann, fnextpow2
    # TODO get rid of that:
    from .common import getMonoFont, getColumn, no_unit, unit
except:
    from spectral import pwelch, hamming , boxcar, hann, fnextpow2
    from common import getMonoFont, getColumn, no_unit, unit

font = {'size'   : 8}
matplotlib_rc('font', **font)
pyplot_rc['agg.path.chunksize'] = 20000

def getMonoFont():
    return wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Monospace')

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
        #self.SetBackgroundColour('white')
        #self.SetToolBitmapSize((22,22))

class PDFCtrlPanel(wx.Panel):
    def __init__(self, parent):
        # Superclass constructor
        super(PDFCtrlPanel,self).__init__(parent)
        # data
        self.parent   = parent
        # GUI
        lb = wx.StaticText( self, -1, 'Number of bins:')
        self.scBins = wx.SpinCtrl(self, value='50',size=wx.Size(70,-1))
        self.scBins.SetRange(3, 10000)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(lb                    ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.scBins           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_TEXT      ,self.onBinsChange  ,self.scBins     )
        self.Hide() 

    def onBinsChange(self,event=None):
        self.parent.redraw();

class CompCtrlPanel(wx.Panel):
    def __init__(self, parent):
        # Superclass constructor
        super(CompCtrlPanel,self).__init__(parent)
        # data
        self.parent   = parent
        # GUI
        #lb = wx.StaticText( self, -1, ' NOTE: this feature is beta.')
        lblList = ['Relative', '|Relative|','Absolute','Y-Y'] 
        self.rbType = wx.RadioBox(self, label = 'Type', choices = lblList,
             majorDimension = 1, style = wx.RA_SPECIFY_ROWS) 
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.rbType           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        #dummy_sizer.Add(lb                    ,0, flag = wx.CENTER|wx.LEFT,border = 2)
        self.SetSizer(dummy_sizer)
        self.rbType.Bind(wx.EVT_RADIOBOX,self.onTypeChange)
        self.Hide() 

    def onTypeChange(self,e): 
        self.parent.redraw();


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


class PlotTypePanel(wx.Panel):
    def __init__(self, parent):
        # Superclass constructor
        super(PlotTypePanel,self).__init__(parent)
        #self.SetBackgroundColour('gray')
        # data
        self.parent   = parent
        # --- Ctrl Panel
        self.cbRegular = wx.CheckBox(self, -1, 'Regular',(10,10))
        self.cbPDF     = wx.CheckBox(self, -1, 'PDF'    ,(10,10))
        self.cbFFT     = wx.CheckBox(self, -1, 'FFT'    ,(10,10))
        self.cbMinMax  = wx.CheckBox(self, -1, 'MinMax' ,(10,10))
        self.cbCompare = wx.CheckBox(self, -1, 'Compare',(10,10))
        self.cbRegular.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.pdf_select    , self.cbPDF    )
        self.Bind(wx.EVT_CHECKBOX, self.fft_select    , self.cbFFT    )
        self.Bind(wx.EVT_CHECKBOX, self.minmax_select , self.cbMinMax )
        self.Bind(wx.EVT_CHECKBOX, self.compare_select, self.cbCompare)
        self.Bind(wx.EVT_CHECKBOX, self.regular_select, self.cbRegular)
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)
        cb_sizer.Add(self.cbRegular , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPDF     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFFT     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMinMax  , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbCompare , 0, flag=wx.ALL, border=1)
        self.SetSizer(cb_sizer)

    def regular_select(self, event=None):
        self.cbFFT.SetValue(False)
        self.cbMinMax.SetValue(False)
        self.cbPDF.SetValue(False)
        self.cbCompare.SetValue(False)
        self.parent.cbLogY.SetValue(False)
        # 
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.slCtrl.Hide();
        self.parent.plotsizer.Layout()
        #
        self.parent.redraw()

    def compare_select(self, event=None):
        self.cbRegular.SetValue(False)
        self.cbFFT.SetValue(False)
        self.cbMinMax.SetValue(False)
        self.cbPDF.SetValue(False)
        self.parent.show_hide(self.parent.cmpPanel, self.cbCompare.IsChecked())
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.plotsizer.Layout()
        #
        self.parent.redraw()

    def fft_select(self, event=None):
        self.cbPDF.SetValue(False)
        self.cbMinMax.SetValue(False)
        self.cbRegular.SetValue(False)
        self.cbCompare.SetValue(False)
        self.parent.show_hide(self.parent.spcPanel, self.cbFFT.IsChecked())
        if self.cbFFT.IsChecked():
            self.parent.cbLogY.SetValue(True)
        else:
            self.parent.cbLogY.SetValue(False)

        self.parent.pdfPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.redraw()

    def pdf_select(self, event=None):
        self.cbFFT.SetValue(False)
        self.cbMinMax.SetValue(False)
        self.cbCompare.SetValue(False)
        self.cbRegular.SetValue(False)
        self.parent.cbLogX.SetValue(False)
        self.parent.cbLogY.SetValue(False)
        self.parent.show_hide(self.parent.pdfPanel, self.cbPDF.IsChecked())
        self.parent.spcPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.redraw()

    def minmax_select(self, event):
        self.cbFFT.SetValue(False)
        self.cbPDF.SetValue(False)
        self.cbCompare.SetValue(False)
        self.cbRegular.SetValue(False)
        # 
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.slCtrl.Hide();
        self.parent.plotsizer.Layout()
        #
        self.parent.redraw()

class PlotPanel(wx.Panel):
    def __init__(self, parent, selPanel):

        # Superclass constructor
        super(PlotPanel,self).__init__(parent)
        # data
        self.selPanel = selPanel
        self.parent   = parent
        if selPanel is not None:
            bg=selPanel.BackgroundColour
            self.SetBackgroundColour(bg) # sowhow, our parent has a wrong color
        # GUI
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        self.fig.subplots_adjust(top=0.98,bottom=0.12,left=0.12,right=0.98)
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)

        self.navTB = MyNavigationToolbar2Wx(self.canvas)

        # --- PlotType Panel
        self.pltTypePanel= PlotTypePanel(self);
        # --- Plot type specific options
        self.spcPanel = SpectralCtrlPanel(self)
        self.pdfPanel      = PDFCtrlPanel(self)
        self.cmpPanel     = CompCtrlPanel(self)

        # --- Ctrl Panel
        self.ctrlPanel= wx.Panel(self)
        # Check Boxes
        self.cbScatter = wx.CheckBox(self.ctrlPanel, -1, 'Scatter',(10,10))
        self.cbSub     = wx.CheckBox(self.ctrlPanel, -1, 'Subplot',(10,10))
        self.cbLogX    = wx.CheckBox(self.ctrlPanel, -1, 'Log-x',(10,10))
        self.cbLogY    = wx.CheckBox(self.ctrlPanel, -1, 'Log-y',(10,10))
        self.cbSync    = wx.CheckBox(self.ctrlPanel, -1, 'Sync-x',(10,10))
        #self.cbSub.SetValue(True) # DEFAULT TO SUB?
        self.cbSync.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.scatter_select, self.cbScatter)
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event  , self.cbSub    )
        self.Bind(wx.EVT_CHECKBOX, self.log_select    , self.cbLogX   )
        self.Bind(wx.EVT_CHECKBOX, self.log_select    , self.cbLogY   )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event  , self.cbSync )
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=2, cols=3, hgap=2, vgap=0)
        cb_sizer.Add(self.cbScatter, 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSub    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSync   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogX   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogY   , 0, flag=wx.ALL, border=1)
        self.ctrlPanel.SetSizer(cb_sizer)
        # --- Ctrl Panel
        crossHairPanel= wx.Panel(self)
        self.lbCrossHairX = wx.StaticText(crossHairPanel, -1, 'x= ...      ')
        self.lbCrossHairY = wx.StaticText(crossHairPanel, -1, 'y= ...      ')
        self.lbCrossHairX.SetFont(getMonoFont())
        self.lbCrossHairY.SetFont(getMonoFont())
        cbCH  = wx.FlexGridSizer(rows=2, cols=1, hgap=2, vgap=0)
        cbCH.Add(self.lbCrossHairX   , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbCrossHairY   , 0, flag=wx.ALL, border=1)
        crossHairPanel.SetSizer(cbCH)


        # --- layout of panels
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sl2 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        sl3 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        sl4 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        row_sizer.Add(self.pltTypePanel , 0 , flag=wx.ALL|wx.CENTER           , border=2)
        row_sizer.Add(sl2               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(self.navTB        , 0 , flag=wx.ALL|wx.CENTER           , border=0)
        row_sizer.Add(sl3               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(self.ctrlPanel    , 1 , flag=wx.ALL|wx.EXPAND|wx.CENTER , border=2)
        row_sizer.Add(sl4               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(crossHairPanel,0, flag=wx.EXPAND|wx.CENTER|wx.LEFT    , border=2)

        plotsizer = wx.BoxSizer(wx.VERTICAL)
        self.slCtrl = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.slCtrl.Hide()
        sl1 = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        plotsizer.Add(self.canvas       ,1,flag = wx.EXPAND,border = 5 )
        plotsizer.Add(sl1               ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.spcPanel,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.pdfPanel     ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.cmpPanel    ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slCtrl       ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(row_sizer         ,0,flag = wx.NORTH ,border = 5)

        self.show_hide(self.spcPanel, self.pltTypePanel.cbFFT.IsChecked())
        self.show_hide(self.cmpPanel, self.pltTypePanel.cbCompare.IsChecked())
        self.show_hide(self.pdfPanel, self.pltTypePanel.cbPDF.IsChecked())

        self.SetSizer(plotsizer)
        self.plotsizer=plotsizer;
        #self.redraw()

    def redraw_event(self, event):
        self.redraw()

    def log_select(self, event):
        if self.pltTypePanel.cbPDF.IsChecked():
            self.cbLogX.SetValue(False)
            self.cbLogY.SetValue(False)
        else:
            self.redraw()
    def scatter_select(self, event):
        if self.pltTypePanel.cbPDF.IsChecked() or self.pltTypePanel.cbFFT.IsChecked():
            self.cbScatter.SetValue(False)
        else:
            self.redraw()

    def show_hide(self,panel,bShow):
        if bShow:
            panel.Show()
            self.slCtrl.Show()
        else:
            panel.Hide()
            self.slCtrl.Hide()


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
        for ax in self.fig.axes:
            self.fig.delaxes(ax)
        sharex=None
        bSubPlots = self.cbSub.IsChecked() and (not self.pltTypePanel.cbCompare.IsChecked())
        if bSubPlots:
            for i in range(nPlots):
                # Vertical stack
                if i==0:
                    ax=self.fig.add_subplot(nPlots,1,i+1)
                    if self.cbSync.IsChecked() and (not self.pltTypePanel.cbPDF.IsChecked()) :
                        sharex=ax
                else:
                    ax=self.fig.add_subplot(nPlots,1,i+1,sharex=sharex)
                # Horizontal stack
                #self.fig.add_subplot(1,nPlots,i+1)
        else:
            self.fig.add_subplot(111)
        
    def draw_tab(self,df,ix,xlabel,I,S,sTab,nTabs,bFirst=True):
        x,xIsString,xIsDate,_=getColumn(df,ix)

        #if self.pltTypePanel.cbCompare.IsChecked():
        #    iRef=I[0]
        #    yRef,_,_,_=getColumn(df,iRef)
        #    I=I[1:]
            
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
                if self.pltTypePanel.cbMinMax.IsChecked():
                    ylabelLeg  = no_unit(ylabel)
                else:
                    ylabelLeg  = ylabel
            else:
                if nPlots==1 or bSubPlots:
                    ylabelLeg  = sTab
                else:
                    if self.pltTypePanel.cbMinMax.IsChecked():
                        ylabelLeg  = sTab+' - ' + no_unit(ylabel)
                    else:
                        ylabelLeg  = sTab+' - ' + ylabel


            # Scaling
            if self.pltTypePanel.cbMinMax.IsChecked():
                mi= np.nanmin(y)
                mx= np.nanmax(y)
                if mi == mx:
                    y=y*0
                else:
                    y = (y-np.nanmin(y))/(np.nanmax(y)-np.nanmin(y))
            n = len(y)


            # --- Plotting
            if self.pltTypePanel.cbPDF.IsChecked():
                # ---PDF
                if yIsString:
                    if n>100:
                        WarnNow('Dataset has string format and is too large to display')
                    else:
                        value_counts = c.value_counts().sort_index()
                        value_counts.plot(kind='bar', ax=ax)
                elif yIsDate:
                    Warn(self,'Cannot plot PDF of dates')
                else:
                    nBins=self.pdfPanel.scBins.GetValue()
                    #min(int(n/10),50)
                    if nBins>=n:
                        nBins=n
                        self.pdfPanel.scBins.SetValue(nBins)
                    pdf, xx = np.histogram(y[~np.isnan(y)], bins=nBins)
                    dx  = xx[1] - xx[0]
                    xx  = xx[:-1] + dx/2
                    pdf = pdf / (n*dx)
                    ax.plot(xx, pdf, label=ylabelLeg)
                    if bFirst:
                        ax.set_xlabel(ylabel)
                        ax.set_ylabel('PDF ('+ylabel+')')

            elif self.pltTypePanel.cbFFT.IsChecked():
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
                        dt = (np.max(x)-np.min(x))/(n-1)
                        #uu,cc= np.unique(np.diff(x), return_counts=True)
                        #print(np.asarray((uu,cc)).T)
                    Fs = 1/dt
                    #print('dt=',dt,'Fs=',Fs)
                    #print(x[0:5])
                    if n%2==0:
                        nhalf = int(n/2+1)
                    else:
                        nhalf = int((n+1)/2)
                    sType    = self.spcPanel.cbType.GetStringSelection()
                    sAvg     = self.spcPanel.cbAveraging.GetStringSelection()
                    bDetrend = self.spcPanel.cbDetrend.IsChecked()
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
                        nExp=self.spcPanel.scP2.GetValue()
                        nPerSeg=2**nExp
                        sAvgMethod = self.spcPanel.cbAveragingMethod.GetStringSelection()
                        if nPerSeg>n:
                            #Warn(self, 'Power of 2 value was too high and was reduced. Disable averaging to use the full spectrum.');
                            nExp=int(np.log(nFFTAll)/np.log(2))-1
                            nPerSeg=2**nExp
                            self.spcPanel.scP2.SetValue(nExp)
                            self.spcPanel.updateP2(nExp)
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
                            xlim=float(self.spcPanel.tMaxFreq.GetLineText(0))
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


    def draw_tab_comp(self,tabs,ITab,ix,xlabel,I,S,STab):
        def getError(y,yref,method):
            if sComp=='Relative':
                Error=(y-yRef)/yRef*100
            elif sComp=='|Relative|':
                Error=abs(y-yRef)/yRef*100
            elif sComp=='Absolute':
                Error=y-yRef
            else:
                raise Exception('Something wrong '+sComp)
            return Error


        self.cursors=[]
        ax=None
        sComp = self.cmpPanel.rbType.GetStringSelection()
        xlabelAll=xlabel
        if sComp=='Relative':
            ylabelAll='Relative error [%]';
        elif sComp=='|Relative|':
            ylabelAll='Abs. relative error [%]';
        elif sComp=='Absolute':
            ylabelAll='Absolute error';
        elif sComp=='Y-Y':
            if len(I)<=3:
                ylabelAll=' and '.join(S[1:]);
            xlabelAll=S[0];

        if self.cbScatter.IsChecked():
            sty='o'
        else:
            sty='-'

        yunits=[]
        if isinstance(ix,list):
            # --- Compare different tables - different columns
            #print('Several Tabs, 2 different columns')
            if len(ix)!=2 or len(I)!=2:
                raise NotImplementedError('Comparison of more than 2 table not implemented')
            if len(I[0])!=1:
                raise NotImplementedError('Comparison of 2 table with different columns not implemented')
            IY1=I[0]
            IY2=I[1]
            iy1 =IY1[0]
            iy2 =IY2[0]
            ix1= ix[0]
            ix2= ix[1]
            if S[0].find(' and ')>0:
                SS=' wrt. '.join(S[0].split(' and ')[::-1])
                yunits=[unit(lb) for lb in S[0].split(' and ')]
                if sComp=='Y-Y':
                    xlabelAll=S[0].split(' and ')[0]
                    ylabelAll=S[0].split(' and ')[1]
                    yunit=unit(S[0].split(' and ')[1])
            else:
                SS=S[0] + ', '+ ' wrt. '.join(STab[::-1])
                if sComp=='Y-Y':
                    xlabelAll=STab[0]+', '+S[0]
                    ylabelAll=STab[1]+', '+S[0]
                yunits=[unit(S[0])]

            xRef,_,_,_=getColumn(tabs[ITab[0]].data,ix1)
            yRef,_,_,_=getColumn(tabs[ITab[0]].data,iy1)
            for iTab,sTab in zip(ITab[1:],STab[1:]):
                tab=tabs[iTab]
                df=tabs[iTab].data;
                x,_,_,_=getColumn(df,ix2)
                ax = self.fig.axes[0]
                # Selecting y values
                ylabel = SS
                y,yIsString,yIsDate,c=getColumn(df,iy2)
                if sComp=='Y-Y':
                    ax.plot(yRef,y, sty, label=ylabel, markersize=1)
                else:
                    Error = getError(y,yRef,sComp)
                    ax.plot(xRef,Error, sty, label=ylabel, markersize=1)

        elif len(ITab)==1:
            # --- Compare one table - different columns
            #print('One Tab, different columns')
            xRef,_,_,_=getColumn(tabs[ITab[0]].data,ix)
            yRef,_,_,_=getColumn(tabs[ITab[0]].data,I[0])
            iTab=ITab[0]
            tab=tabs[iTab]
            df=tabs[iTab].data;
            x,_,_,_=getColumn(df,ix)
            yunits.append(unit(S[0]))
            for i in range(len(I)-1):
                ax = self.fig.axes[0]
                # Selecting y values
                iy     = I[i+1]
                if sComp=='Y-Y':
                    ylabel = no_unit(S[i+1])+' wrt. '+no_unit(S[0])
                else:
                    ylabel = no_unit(S[i+1])+' wrt. '+no_unit(S[0])
                yunits.append(unit(S[i+1]))
                y,yIsString,yIsDate,c=getColumn(df,iy)
                if sComp=='Y-Y':
                    ax.plot(yRef,y, sty, label=ylabel, markersize=1)
                else:
                    Error = getError(y,yRef,sComp)
                    ax.plot(xRef,Error, sty, label=ylabel, markersize=1)
                #cursor = Cursor(ax, useblit=True, color='red', linewidth=2)
        else:
            # --- Compare different tables, same column
            #print('Several Tabs, same columns')
            xRef,_,_,_=getColumn(tabs[ITab[0]].data,ix)
            yunits=[]
            for i in range(len(I)):
                iy= I[i]
                yRef,_,_,_=getColumn(tabs[ITab[0]].data,iy)

                for iTab,sTab in zip(ITab[1:],STab[1:]):
                    tab=tabs[iTab]
                    df=tabs[iTab].data;
                    x,_,_,_=getColumn(df,ix)
                    ax = self.fig.axes[0]
                    # Selecting y values
                    ylabel = sTab+'|'+S[i]
                    yunits.append(unit(S[i]))
                    y,yIsString,yIsDate,c=getColumn(df,iy)
                    if sComp=='Y-Y':
                        ax.plot(yRef,y, sty, label=ylabel, markersize=1.5)
                    else:
                        Error = getError(y,yRef,sComp)
                        ax.plot(xRef,Error, sty, label=ylabel, markersize=1.5)
                    #cursor = Cursor(ax, useblit=True, color='red', linewidth=2)
        yunits=set(yunits)
        if len(yunits)==1:
            yunit=next(iter(yunits))
        else:
            yunit=''
        if ax is not None:
            if sComp=='Y-Y':
                xmin,xmax=ax.get_xlim()
                ax.plot([xmin,xmax],[xmin,xmax],'k--',linewidth=0.5)
            ax.set_xlabel(xlabelAll)
            if sComp=='Absolute':
                ax.set_ylabel(ylabelAll+' '+yunit)
            else:
                ax.set_ylabel(ylabelAll)
            self.cursors.append(Cursor(ax,horizOn=True, vertOn=True, useblit=True, color='gray', linewidth=0.5, linestyle=':'))



    def onMouseMove(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            self.lbCrossHairX.SetLabel("x={:10.3e}".format(x))
            self.lbCrossHairY.SetLabel("y={:10.3e}".format(y))

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
            # --- Same X 
            nPlots = len(IY1)
            nTabs = len(ITab)
            self.set_subplots(nPlots)
            if self.pltTypePanel.cbCompare.IsChecked():
                self.draw_tab_comp(tabs,ITab,iX1,sX1,IY1,SY1,STab)
            else:
                for i,sTab in zip(ITab,STab):
                    self.draw_tab(tabs[i].data,iX1,sX1,IY1,SY1,sTab,nTabs,bFirst=(i==ITab[0]))
        else:
            # --- Different X 
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
            if self.pltTypePanel.cbCompare.IsChecked():
                self.draw_tab_comp(tabs,ITab,[iX1,iX2],sX1,[IY1,IY2],Ylabels,STab)
            else:
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



if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table

    app = wx.App(False)
    self=wx.Frame(None,-1,"Title")
    self.SetSize((800, 600))
    #self.SetBackgroundColour('red')
    class FakeSelPanel(wx.Panel):
        def __init__(self, parent):
            super(FakeSelPanel,self).__init__(parent)
            d ={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+1,'ColC':np.random.normal(0,1,100)+2}
            df = pd.DataFrame(data=d)
            self.tabs=[Table(df=df)]

        def getFullSelection(self):
            ID=['a']
            ITab=[0]
            return ID,[0],0,[2,3],None,None,['tab'],'x',['ColB','ColC'],None,None

    selpanel=FakeSelPanel(self)
    #     selpanel.SetBackgroundColour('blue')
    p1=PlotPanel(self,selpanel)
    p1.redraw()
    #p1=SpectralCtrlPanel(self)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(selpanel,0, flag = wx.EXPAND|wx.ALL,border = 10)
    sizer.Add(p1,1, flag = wx.EXPAND|wx.ALL,border = 10)
    self.SetSizer(sizer)

    self.Center()
    self.Layout()
    self.SetSize((800, 600))
    self.Show()
    self.SendSizeEvent()

    #p1.showStats(None,[tab],[0],[0,1],tab.columns,0,erase=False)

    app.MainLoop()


