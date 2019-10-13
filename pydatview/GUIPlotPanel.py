import numpy as np
import wx
import dateutil # required by matplotlib
#from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('Agg') # Important for Windows version of installer
from matplotlib import rc as matplotlib_rc
try:
    from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
except Exception as e:
    print('')
    print('Error: problem importing `matplotlib.backends.backend_wx`.')
    import platform
    if platform.system()=='Darwin':
        print('')
        print('pyDatView help:')
        print('  This is a typical issue on MacOS, most likely you are')
        print('  using the native MacOS python with the native matplolib')
        print('  library, which is incompatible with `wxPython`.')
        print('')
        print('  You can solve this by either:')
        print('    - using python3, and pip3 e.g. installing it with brew')
        print('    - using a virtual environment with python 2 or 3')
        print('    - using anaconda with python 2 or 3');
        print('')
        import sys
        sys.exit(1)
    else:
        raise e
from matplotlib.figure import Figure
from matplotlib.pyplot import rcParams as pyplot_rc
import gc

try:
    from .spectral import fft_wrap
    from .common import * 
    from .GUICommon import * 
    from .GUIToolBox import MyMultiCursor, MyNavigationToolbar2Wx
    from .GUITools import LogDecToolPanel
except:
    from spectral import fft_wrap
    from common import * #getMonoFont, getColumn, no_unit, unit, inverse_unit getDt
    from GUICommon import * 
    from GUIToolBox import MyMultiCursor, MyNavigationToolbar2Wx
    from GUITools import LogDecToolPanel

font = {'size'   : 8}
matplotlib_rc('font', **font)
pyplot_rc['agg.path.chunksize'] = 20000

def unique(l):
    used=set()
    return [x for x in l if x not in used and (used.add(x) or True)]

class PDFCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(PDFCtrlPanel,self).__init__(parent)
        self.parent   = parent
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
        self.parent.redraw(); # DATA HAS CHANGED

class MinMaxPanel(wx.Panel):
    def __init__(self, parent):
        super(MinMaxPanel,self).__init__(parent)
        self.parent   = parent
        self.cbxMinMax = wx.CheckBox(self, -1, 'xMinMax',(10,10))
        self.cbyMinMax = wx.CheckBox(self, -1, 'yMinMax',(10,10))
        self.cbxMinMax.SetValue(False)
        self.cbyMinMax.SetValue(True)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.cbxMinMax ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(self.cbyMinMax ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_CHECKBOX, self.onMinMaxChange)
        self.Hide() 

    def onMinMaxChange(self,event=None):
        self.parent.redraw(); # DATA HAS CHANGED

class CompCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(CompCtrlPanel,self).__init__(parent)
        self.parent   = parent
        lblList = ['Relative', '|Relative|','Ratio','Absolute','Y-Y'] 
        self.rbType = wx.RadioBox(self, label = 'Type', choices = lblList,
                majorDimension = 1, style = wx.RA_SPECIFY_ROWS) 
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.rbType           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        self.SetSizer(dummy_sizer)
        self.rbType.Bind(wx.EVT_RADIOBOX,self.onTypeChange)
        self.Hide() 

    def onTypeChange(self,e): 
        self.parent.redraw(); # DATA HAS CHANGED


class SpectralCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(SpectralCtrlPanel,self).__init__(parent)
        self.parent   = parent
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
        self.parent.redraw_same_data();
    def onSpecCtrlChange(self,event=None):
        self.parent.redraw() # Data changes
    def onDetrendChange(self,event=None):
        self.parent.redraw() # Data changes

    def onP2ChangeText(self,event=None):
        nExp=self.scP2.GetValue()
        self.updateP2(nExp)
        self.parent.redraw() # Data changes

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
        self.cbRegular = wx.RadioButton(self, -1, 'Regular',style=wx.RB_GROUP)
        self.cbPDF     = wx.RadioButton(self, -1, 'PDF'    ,                 )
        self.cbFFT     = wx.RadioButton(self, -1, 'FFT'    ,                 )
        self.cbMinMax  = wx.RadioButton(self, -1, 'MinMax' ,                 )
        self.cbCompare = wx.RadioButton(self, -1, 'Compare',                 )
        self.cbRegular.SetValue(True)
        self.Bind(wx.EVT_RADIOBUTTON, self.pdf_select    , self.cbPDF    )
        self.Bind(wx.EVT_RADIOBUTTON, self.fft_select    , self.cbFFT    )
        self.Bind(wx.EVT_RADIOBUTTON, self.minmax_select , self.cbMinMax )
        self.Bind(wx.EVT_RADIOBUTTON, self.compare_select, self.cbCompare)
        self.Bind(wx.EVT_RADIOBUTTON, self.regular_select, self.cbRegular)
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)
        cb_sizer.Add(self.cbRegular , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPDF     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFFT     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMinMax  , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbCompare , 0, flag=wx.ALL, border=1)
        self.SetSizer(cb_sizer)

    def plotType(self):
        plotType='Regular'
        if self.cbMinMax.GetValue():
            plotType='MinMax'
        elif self.cbPDF.GetValue():
            plotType='PDF'
        elif self.cbFFT.GetValue():
            plotType='FFT'
        elif self.cbCompare.GetValue():
            plotType='Compare'
        return plotType



    def regular_select(self, event=None):
        self.parent.cbLogY.SetValue(False)
        # 
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.slCtrl.Hide();
        self.parent.plotsizer.Layout()
        #
        self.parent.redraw() # Data changes

    def compare_select(self, event=None):
        self.parent.cbLogY.SetValue(False)
        self.parent.show_hide(self.parent.cmpPanel, self.cbCompare.GetValue())
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.redraw() # Data changes


    def fft_select(self, event=None):
        self.parent.show_hide(self.parent.spcPanel, self.cbFFT.GetValue())
        self.parent.cbLogY.SetValue(self.cbFFT.GetValue())
        self.parent.pdfPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.redraw() # Data changes

    def pdf_select(self, event=None):
        self.parent.cbLogX.SetValue(False)
        self.parent.cbLogY.SetValue(False)
        self.parent.show_hide(self.parent.pdfPanel, self.cbPDF.GetValue())
        self.parent.spcPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.redraw() # Data changes

    def minmax_select(self, event):
        self.parent.cbLogY.SetValue(False)
        self.parent.show_hide(self.parent.mmxPanel, self.cbMinMax.GetValue())
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.redraw() # Data changes

class PlotPanel(wx.Panel):
    def __init__(self, parent, selPanel,infoPanel=None):

        # Superclass constructor
        super(PlotPanel,self).__init__(parent)
        font = parent.GetFont()
        font.SetPointSize(font.GetPointSize()-1)
        self.SetFont(font) 
        # data
        self.selPanel = selPanel
        self.infoPanel=infoPanel
        self.parent   = parent
        self.plotData = []
        if self.selPanel is not None:
            bg=self.selPanel.BackgroundColour
            self.SetBackgroundColour(bg) # sowhow, our parent has a wrong color
        # GUI
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        self.fig.subplots_adjust(top=0.98,bottom=0.12,left=0.12,right=0.98)
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)

        self.navTB = MyNavigationToolbar2Wx(self.canvas)


        # --- Tool Panel
        self.toolSizer= wx.BoxSizer(wx.VERTICAL)
        # --- PlotType Panel
        self.pltTypePanel= PlotTypePanel(self);
        # --- Plot type specific options
        self.spcPanel = SpectralCtrlPanel(self)
        self.pdfPanel = PDFCtrlPanel(self)
        self.cmpPanel = CompCtrlPanel(self)
        self.mmxPanel = MinMaxPanel(self)

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
        cb_sizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)
        cb_sizer.Add(self.cbScatter, 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSub    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogX   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogY   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSync   , 0, flag=wx.ALL, border=1)
        self.ctrlPanel.SetSizer(cb_sizer)
        # --- Ctrl Panel
        crossHairPanel= wx.Panel(self)
        self.lbCrossHairX = wx.StaticText(crossHairPanel, -1, 'x= ...      ')
        self.lbCrossHairY = wx.StaticText(crossHairPanel, -1, 'y= ...      ')
        self.lbCrossHairX.SetFont(getMonoFont(self))
        self.lbCrossHairY.SetFont(getMonoFont(self))
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
        row_sizer.Add(self.navTB        , 0 , flag=wx.LEFT|wx.RIGHT|wx.CENTER , border=2)
        row_sizer.Add(sl3               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(self.ctrlPanel    , 1 , flag=wx.ALL|wx.EXPAND|wx.CENTER , border=2)
        row_sizer.Add(sl4               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(crossHairPanel,0, flag=wx.EXPAND|wx.CENTER|wx.LEFT    , border=2)

        plotsizer = wx.BoxSizer(wx.VERTICAL)
        self.slCtrl = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.slCtrl.Hide()
        sl1 = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        plotsizer.Add(self.toolSizer,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.canvas   ,1,flag = wx.EXPAND,border = 5 )
        plotsizer.Add(sl1           ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.spcPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.pdfPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.cmpPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.mmxPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slCtrl   ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(row_sizer     ,0,flag = wx.NORTH ,border = 5)

        self.show_hide(self.spcPanel, self.pltTypePanel.cbFFT.GetValue())
        self.show_hide(self.cmpPanel, self.pltTypePanel.cbCompare.GetValue())
        self.show_hide(self.pdfPanel, self.pltTypePanel.cbPDF.GetValue())
        self.show_hide(self.mmxPanel, self.pltTypePanel.cbMinMax.GetValue())

        self.SetSizer(plotsizer)
        self.plotsizer=plotsizer;

    def redraw_event(self, event):
        self.redraw_same_data()

    def log_select(self, event):
        if self.pltTypePanel.cbPDF.GetValue():
            self.cbLogX.SetValue(False)
            self.cbLogY.SetValue(False)
        else:
            self.redraw_same_data()
    def scatter_select(self, event):
        if self.pltTypePanel.cbPDF.GetValue() or self.pltTypePanel.cbFFT.GetValue():
            self.cbScatter.SetValue(False)
        else:
            self.redraw_same_data()

    def show_hide(self,panel,bShow):
        if bShow:
            panel.Show()
            self.slCtrl.Show()
        else:
            panel.Hide()
            self.slCtrl.Hide()


    def set_subplots(self,nPlots):
        # Creating subplots
        for ax in self.fig.axes:
            self.fig.delaxes(ax)
        sharex=None
        bSubPlots = self.cbSub.IsChecked()
        if bSubPlots:
            for i in range(nPlots):
                # Vertical stack
                if i==0:
                    ax=self.fig.add_subplot(nPlots,1,i+1)
                    if self.cbSync.IsChecked() and (not self.pltTypePanel.cbPDF.GetValue()) :
                        sharex=ax
                else:
                    ax=self.fig.add_subplot(nPlots,1,i+1,sharex=sharex)
                # Horizontal stack
                #self.fig.add_subplot(1,nPlots,i+1)
        else:
            self.fig.add_subplot(111)

    def onMouseMove(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            if abs(x)<1000 and abs(x)>1e-4:
                self.lbCrossHairX.SetLabel("x={:10.5f}".format(x))
            else:
                self.lbCrossHairX.SetLabel("x={:10.3e}".format(x))
            if abs(y)<1000 and abs(y)>1e-4:
                self.lbCrossHairY.SetLabel("y={:10.5f}".format(y))
            else:
                self.lbCrossHairY.SetLabel("y={:10.3e}".format(y))

    def removeTools(self,event=None):
        self.toolSizer.Clear(delete_windows=True) # Delete Windows
        self.plotsizer.Layout()

    def showTool(self,toolName=''):
        self.toolSizer.Clear(delete_windows=True) # Delete Windows
        if toolName=='LogDec':
            panel = LogDecToolPanel(self)
            self.toolSizer.Add(panel, 0, wx.EXPAND|wx.ALL, 5)

        else:
            raise Exception('Unknown tool {}'.format(toolName))
        self.plotsizer.Layout()

    def setPD_PDF(self,d,c):
        # ---PDF
        n=len(d.y)
        if d.yIsString:
            if n>100:
                Warn(self,'Dataset has string format and is too large to display')
                self.pltTypePanel.cbRegular.SetValue(True)
                return
            else:
                vc = c.value_counts().sort_index()
                d.x = vc.keys().tolist()
                d.y = vc/n # TODO counts/PDF option
                d.yIsString=False
                d.xIsString=True
        elif d.yIsDate:
            Warn(self,'Cannot plot PDF of dates')
            self.pltTypePanel.cbRegular.SetValue(True)
            return
        else:
            nBins=self.pdfPanel.scBins.GetValue()
            #min(int(n/10),50)
            if nBins>=n:
                nBins=n
                self.pdfPanel.scBins.SetValue(nBins)
            d.y, d.x = np.histogram(d.y[~np.isnan(d.y)], bins=nBins)
            dx   = d.x[1] - d.x[0]
            d.x  = d.x[:-1] + dx/2
            d.y  = d.y / (n*dx) # TODO counts /PDF option
        d.sx = d.sy;
        d.sy = 'PDF('+no_unit(d.sy)+')'
        iu = inverse_unit(d.sy)
        if len(iu)>0:
            d.sy += ' ['+ iu +']'

    def setPD_MinMax(self,d):
        if self.mmxPanel.cbyMinMax.IsChecked():
            if d.yIsString:
                Warn(self,'Cannot compute min-max for strings')
                self.mmxPanel.cbyMinMax.SetValue(False)
                #self.pltTypePanel.cbRegular.SetValue(True)
                return
            mi= np.nanmin(d.y)
            mx= np.nanmax(d.y)
            if mi == mx:
                d.y=d.y*0
            else:
                d.y = (d.y-mi)/(mx-mi)
        if self.mmxPanel.cbxMinMax.IsChecked():
            if d.xIsString:
                Warn(self,'Cannot compute min-max for strings')
                self.mmxPanel.cbxMinMax.SetValue(False)
                #self.pltTypePanel.cbRegular.SetValue(True)
                return
            mi= np.nanmin(d.x)
            mx= np.nanmax(d.x)
            if mi == mx:
                d.x=d.x*0
            else:
                d.x = (d.x-mi)/(mx-mi)

    def setPD_FFT(self,d):
        if d.yIsString or d.yIsDate:
            Warn(self,'Cannot plot FFT of dates or strings')
            self.pltTypePanel.cbRegular.SetValue(True)
        elif d.xIsString:
            Warn(self,'Cannot plot FFT if x axis is string')
            self.pltTypePanel.cbRegular.SetValue(True)
        else:
            output_type      = self.spcPanel.cbType.GetStringSelection()
            averaging        = self.spcPanel.cbAveraging.GetStringSelection()
            averaging_window = self.spcPanel.cbAveragingMethod.GetStringSelection()
            bDetrend         = self.spcPanel.cbDetrend.IsChecked()
            nExp             = self.spcPanel.scP2.GetValue()
            dt=None
            if d.xIsDate:
                dt = getDt(d.x)
            # --- Computing fft - x is freq, y is Amplitude
            d.x, d.y, Info = fft_wrap(d.x, d.y, dt=dt, output_type=output_type,averaging=averaging,averaging_window=averaging_window,detrend=bDetrend,nExp=nExp)
            # --- Setting plot options
            d.Info=Info
            d.xIsDate=False
            d.sy= 'FFT('+no_unit(d.sy)+')'
            if unit(d.sx)=='s':
                d.sx= 'Frequency [Hz]'
            else:
                d.sx= ''
            if hasattr(Info,'nExp') and Info.nExp!=nExp:
                self.spcPanel.scP2.SetValue(Info.nExp)
                self.spcPanel.updateP2(Info.nExp)


    def getPlotData(self,plotType):
        class PlotData():
            def __repr__(s):
                s1='id:{}, it:{}, ix:{}, iy:{}, sx:"{}", sy:"{}", st:{}, syl:{}'.format(s.id,s.it,s.ix,s.iy,s.sx,s.sy,s.st,s.syl)
                return s1

        ID,SameCol=self.selPanel.getPlotDataSelection()
        del self.plotData
        self.plotData=[]
        tabs=self.selPanel.tabs
        for i,idx in enumerate(ID):
            d=PlotData();
            d.id = i
            d.it = idx[0]
            d.ix = idx[1]
            d.iy = idx[2]
            d.sx = idx[3]
            d.sy = idx[4]
            d.syl = ''
            d.st = idx[5]
            d.filename = tabs[d.it].filename
            d.tabname = tabs[d.it].active_name
            d.SameCol = SameCol
            d.x,d.xIsString,d.xIsDate,_=getColumn(tabs[d.it].data,d.ix)
            d.y,d.yIsString,d.yIsDate,c=getColumn(tabs[d.it].data,d.iy)
            n=len(d.y)
            # Stats of the raw data
            #d.x0Min  = xMin(d)
            #d.x0Max  = xMax(d)
            d.y0Min  = yMin(d)
            d.y0Max  = yMax(d)
            d.y0Std  = yStd(d)
            d.y0Mean = yMean(d)
            d.n0     = (n,'{:d}'.format(n))
            # Possible change of data
            if plotType=='MinMax':
                self.setPD_MinMax(d) 
            elif plotType=='PDF':
                self.setPD_PDF(d,c)  
            elif plotType=='FFT':
                self.setPD_FFT(d) 
            self.plotData.append(d)

    def PD_Compare(self,mode):
        # --- Comparison
        PD=self.plotData
        sComp = self.cmpPanel.rbType.GetStringSelection()

        def getError(y,yref,method):
            if len(y)!=len(yref):
                raise NotImplementedError('Cannot compare signals of different lengths')
            if sComp=='Relative':
                Error=(y-yRef)/yRef*100
            elif sComp=='|Relative|':
                Error=abs((y-yRef)/yRef)*100
            elif sComp=='Ratio':
                Error=y/yRef
            elif sComp=='Absolute':
                Error=y-yRef
            else:
                raise Exception('Something wrong '+sComp)
            return Error

        def getErrorLabel(ylab=''):
            if len(ylab)>0:
                ylab=no_unit(ylab)
                ylab='in '+ylab+' '
            if sComp=='Relative':
                return 'Relative error '+ylab+'[%]';
            elif sComp=='|Relative|':
                return 'Abs. relative error '+ylab+'[%]';
            if sComp=='Ratio':
                return 'Ratio '+ylab.replace('in','of')+'[-]';
            elif sComp=='Absolute':
                usy   = unique([pd.sy for pd in PD])
                yunits= unique([unit(sy) for sy in usy])
                if len(yunits)==1 and len(yunits[0])>0:
                    return 'Absolute error '+ylab+'['+yunits[0]+']'
                else:
                    return 'Absolute error '+ylab;
            elif sComp=='Y-Y':
                return PD[0].sy

        xlabelAll=PD[0].sx

        
        if any([pd.yIsString for pd in PD]):
            Warn(self,'Cannot compare strings')
            self.pltTypePanel.cbRegular.SetValue(True)
            return
        if any([pd.yIsDate for pd in PD]):
            Warn(self,'Cannot compare dates with other values')
            self.pltTypePanel.cbRegular.SetValue(True)
            return


        if mode=='nTabs_1Col':
            ylabelAll=getErrorLabel(PD[1].sy)
            usy   = unique([pd.sy for pd in PD])
            #print('Compare - different tabs - 1 col')
            st  = [pd.st for pd in PD]
            if len(usy)==1:
               SS=usy[0] + ', '+ ' wrt. '.join(st[::-1])
               if sComp=='Y-Y':
                   xlabelAll=PD[0].st+', '+PD[0].sy
                   ylabelAll=PD[1].st+', '+PD[1].sy
            else:
                SS=' wrt. '.join(usy[::-1])
                if sComp=='Y-Y':
                    xlabelAll=PD[0].sy
                    ylabelAll=PD[1].sy

            xRef = PD[0].x
            yRef = PD[0].y
            PD[1].syl=SS
            y=np.interp(xRef,PD[1].x,PD[1].y)
            if sComp=='Y-Y':
                PD[1].x=yRef
                PD[1].y=y
            else:
                Error = getError(y,yRef,sComp)
                PD[1].x=xRef
                PD[1].y=Error
            PD[1].sx=xlabelAll
            PD[1].sy=ylabelAll
            self.plotData=[PD[1]]

        elif mode=='1Tab_nCols':
            # --- Compare one table - different columns
            #print('One Tab, different columns')
            ylabelAll=getErrorLabel()
            xRef = PD[0].x
            yRef = PD[0].y
            pdRef=PD[0]
            for pd in PD[1:]:
                if sComp=='Y-Y':
                    pd.syl = no_unit(pd.sy)+' wrt. '+no_unit(pdRef.sy)
                    pd.x   = yRef
                    pd.sx  = PD[0].sy
                else:
                    pd.syl = no_unit(pd.sy)+' wrt. '+no_unit(pdRef.sy)
                    pd.sx  = xlabelAll
                    pd.sy  = ylabelAll
                    Error  = getError(pd.y,yRef,sComp)
                    pd.x=xRef
                    pd.y=Error
            self.plotData=PD[1:]
        elif mode =='nTabs_SameCols':
            # --- Compare different tables, same column
            #print('Several Tabs, same columns')
            uiy=unique([pd.iy for pd in PD])
            uit=unique([pd.it for pd in PD])
            self.plotData=[]
            for iy in uiy:
                PD_SameCol=[pd for pd in PD if pd.iy==iy]
                xRef = PD_SameCol[0].x
                yRef = PD_SameCol[0].y
                ylabelAll=getErrorLabel(PD_SameCol[0].sy)
                for pd in PD_SameCol[1:]:
                    if pd.xIsString:
                        if len(xRef)==len(pd.x):
                            pass # fine able to interpolate
                        else:
                            Error(self,'X values have different length and are strings, cannot interpolate string. Use `Index` for x instead.')
                    else:
                        pd.y=np.interp(xRef,pd.x,pd.y)
                    if sComp=='Y-Y':
                        pd.x=yRef
                        pd.sx=PD_SameCol[0].st+', '+PD_SameCol[0].sy
                        if len(PD_SameCol)==1:
                            pd.sy =pd.st+', '+pd.sy
                        else:
                            pd.syl= pd.st
                    else:
                        if len(uit)<=2:
                            pd.syl = pd.st+' wrt. '+PD_SameCol[0].st+', '+pd.sy
                        else:
                            pd.syl = pd.st+'|'+pd.sy
                        pd.sx  = xlabelAll
                        pd.sy  = ylabelAll
                        Error = getError(pd.y,yRef,sComp)
                        pd.x=xRef
                        pd.y=Error
                    self.plotData.append(pd)




    def plot_all(self):
        self.multiCursors=[]
        axes=self.fig.axes

        bScatter=self.cbScatter.IsChecked()

        PD=self.plotData

        bAllNeg=True
        for ax in axes:
            # Plot data
            vDate=[PD[i].yIsDate for i in ax.iPD]
            if any(vDate) and len(vDate)>1:
                Error(self,'Cannot plot date and other value on the same axis')
                return

            #Keep me - tight axis, attempt to optimize
            #try:
            #    xMin=np.min([PD[i].x0Min[0] for i in ax.iPD])
            #    xMax=np.max([PD[i].x0Max[0] for i in ax.iPD])
            #    ax.set_xlim(xMin,xMax)
            #    ax.autoscale(False)
            #except:
            #    pass
            #try:
            #    yMin=np.min([PD[i].y0Min[0] for i in ax.iPD])
            #    yMax=np.max([PD[i].y0Max[0] for i in ax.iPD])
            #    ax.set_ylim(yMin,yMax)
            #    ax.autoscale(False)
            #except:
            #    pass


            for ipd in ax.iPD:
                pd=PD[ipd]
                if bScatter or len(pd.x)==1:
                    sty='o'
                else:
                    sty='-'
                ax.plot(pd.x,pd.y,sty,label=pd.syl,markersize=1)
                try:
                    bAllNeg=bAllNeg and  all(pd.y<=0)
                except:
                    pass # Dates

            # Log Axes
            if self.cbLogX.IsChecked():
                ax.set_xscale("log", nonposx='clip')
            if self.cbLogY.IsChecked():
                if bAllNeg:
                    pass
                else:
                    ax.set_yscale("log", nonposy='clip')

            # XLIM - TODO FFT ONLY NASTY
            if self.pltTypePanel.cbFFT.GetValue():
                try:
                    xlim=float(self.spcPanel.tMaxFreq.GetLineText(0))
                    if xlim>0:
                        ax.set_xlim([0,xlim])
                        pd=PD[ax.iPD[0]]
                        I=pd.x<xlim
                        ymin = np.min([np.min(PD[ipd].y[I]) for ipd in ax.iPD])
                        ax.set_ylim(bottom=ymin/2)
                except:
                    pass
            # Special Grids
            if self.pltTypePanel.cbCompare.GetValue():
                if self.cmpPanel.rbType.GetStringSelection()=='Y-Y':
                    xmin,xmax=ax.get_xlim()
                    ax.plot([xmin,xmax],[xmin,xmax],'k--',linewidth=0.5)

        # Labels
        axes[-1].set_xlabel(PD[axes[-1].iPD[0]].sx)
        for ax in axes:
            usy = unique([PD[i].sy for i in ax.iPD])
            if len(usy)<=3:
                ax.set_ylabel(' and '.join(usy)) # consider legend
            else:
                ax.set_ylabel('')
        # Legend
        #print('sy :',[pd.sy for pd in PD])
        #print('syl:',[pd.syl for pd in PD])
        usyP0 = unique([PD[i].syl for i in axes[0].iPD])
        if  self.pltTypePanel.cbCompare.GetValue():
            for ax in axes:
                ax.legend(fancybox=False, loc=1)
        elif len(usyP0)>1:
            #axes[0].legend(fancybox=False, framealpha=1, loc=1, shadow=None)
            axes[0].legend(fancybox=False, loc=1)
        elif len(axes)>1 and len(axes)==len(PD):
            # Special case when we have subplots and all plots have the same label
            usy = unique([pd.sy for pd in PD])
            if len(usy)==1:
                for ax in axes:
                    ax.legend(fancybox=False, loc=1)
            
        # --- Cursors for each individual plot
        # NOTE: cursors needs to be stored in the object!
        #for ax in self.fig.axes:
        #    self.cursors.append(MyCursor(ax,horizOn=True, vertOn=False, useblit=True, color='gray', linewidth=0.5, linestyle=':'))
        # Vertical cusor for all, commonly
        self.multiCursors = MyMultiCursor(self.canvas, tuple(self.fig.axes), useblit=True, horizOn = True, vertOn=True, color='gray', linewidth=0.5, linestyle=':')

    def findPlotMode(self,PD):
        uTabs=unique([pd.it for pd in PD])
        usy=unique([pd.sy for pd in PD])
        uiy=unique([pd.iy for pd in PD])
        if len(uTabs)<=0:
            raise Exception('No Table. Contact developer')
        elif len(uTabs)==1:
            mode='1Tab_nCols'
        else:
            if PD[0].SameCol:
                mode='nTabs_SameCols'
            else:
                mode='nTabs_1Col'
        return mode

    def findSubPlots(self,PD,mode):
        uTabs=unique([pd.it for pd in PD])
        usy=unique([pd.sy for pd in PD])
        bSubPlots = self.cbSub.IsChecked()
        bCompare  = self.pltTypePanel.cbCompare.GetValue() # NOTE bCompare somehow always 1Tab_nCols
        nSubPlots=1
        spreadBy='none'
        if mode=='1Tab_nCols':
            if bSubPlots:
                if bCompare:
                    nSubPlots=len(PD)
                    spreadBy='iy'
                else:
                    nSubPlots=len(usy)
                    spreadBy='iy'
        elif mode=='nTabs_SameCols':
            if bSubPlots:
                if bCompare:
                    print('>>>TODO ',mode,len(usy),len(uTabs))
                else:
                    if len(usy)==1:
                        # Temporary hack until we have an option for spread by tabs or col
                        nSubPlots=len(uTabs)
                        spreadBy='it'
                    else:
                        nSubPlots=len(usy)
                        spreadBy='iy'
        else:
            mode='nTabs_1Col'
            if bSubPlots:
                if bCompare:
                    print('>>> TODO',mode,len(uTabs))
                else:
                    nSubPlots=len(uTabs)
                    spreadBy='it'
        return nSubPlots,spreadBy

    def distributePlots(self,mode,nSubPlots,spreadBy):
        """ Assigns plot data to axes and axes to plot data """
        axes=self.fig.axes

        # Link plot data to axes
        if nSubPlots==1 or spreadBy=='none':
            axes[0].iPD=[i for i in range(len(self.plotData))]
        else:
            for ax in axes:
                ax.iPD=[]
            PD=self.plotData
            uTabs=unique([pd.it for pd in PD])
            uiy=unique([pd.iy for pd in PD])
            if spreadBy=='iy':
                for ipd,pd in enumerate(PD):
                    i=uiy.index(pd.iy)
                    axes[i].iPD.append(ipd)
            elif spreadBy=='it':
                for ipd,pd in enumerate(PD):
                    i=uTabs.index(pd.it)
                    axes[i].iPD.append(ipd)
            else:
                raise Exception('Wrong spreadby value')

    def setLegendLabels(self,mode):
        """ Set labels for legend """
        if mode=='1Tab_nCols':
            for pd in self.plotData:
                if self.pltTypePanel.cbMinMax.GetValue():
                    pd.syl = no_unit(pd.sy)
                else:
                    pd.syl = pd.sy

        elif mode=='nTabs_SameCols':
            for pd in self.plotData:
                pd.syl=pd.st

        elif mode=='nTabs_1Col':
            usy=unique([pd.sy for pd in self.plotData])
            if len(usy)==1:
                for pd in self.plotData:
                    pd.syl=pd.st
            else:
                for pd in self.plotData:
                    if self.pltTypePanel.cbMinMax.GetValue():
                        pd.syl=no_unit(pd.sy)
                    else:
                        pd.syl=pd.sy #pd.syl=pd.st + ' - '+pd.sy



    def empty(self):
        self.cleanPlot()

    def clean_memory(self):
        if hasattr(self,'plotData'):
            del self.plotData
            self.plotData=[]
            for ax in self.fig.axes:
                ax.iPD=[]
                self.fig.delaxes(ax)
            gc.collect()

    def clean_memory_plot(self):
        pass

    def cleanPlot(self):
        for ax in self.fig.axes:
            if hasattr(ax,'iPD'):
                del ax.iPD
            self.fig.delaxes(ax)
        gc.collect()
        self.fig.add_subplot(111)
        ax = self.fig.axes[0]
        ax.set_axis_off()
        #ax.plot(1,1)
        self.canvas.draw()
        gc.collect()

    def redraw(self):
        self._redraw()
        if self.infoPanel is not None:
            self.infoPanel.showStats(self.plotData,self.pltTypePanel.plotType())

    def redraw_same_data(self):
        self._redraw_same_data()

    def _redraw_same_data(self):
        if len(self.plotData)==0: 
            self.cleanPlot();
            return

        mode=self.findPlotMode(self.plotData)
        nPlots,spreadBy=self.findSubPlots(self.plotData,mode)

        self.clean_memory_plot()
        self.set_subplots(nPlots)
        self.distributePlots(mode,nPlots,spreadBy)

        if not self.pltTypePanel.cbCompare.GetValue():
            self.setLegendLabels(mode)

        self.plot_all()
        self.canvas.draw()

    def _redraw(self):
        self.clean_memory()
        self.getPlotData(self.pltTypePanel.plotType())
        if len(self.plotData)==0: 
            self.cleanPlot();
            return

        mode=self.findPlotMode(self.plotData)
        if self.pltTypePanel.cbCompare.GetValue():
            self.PD_Compare(mode)
            if len(self.plotData)==0: 
                self.cleanPlot();
                return
        self._redraw_same_data()

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
            d ={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0,'ColC':np.random.normal(0,1,100)+1}
            df = pd.DataFrame(data=d)
            self.tabs=[Table(df=df)]

        def getPlotDataSelection(self):
            ID=[]
            ID.append([0,0,2,'x','ColB','tab'])
            ID.append([0,0,3,'x','ColC','tab'])
            return ID,True

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


