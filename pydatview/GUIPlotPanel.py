import os
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
from matplotlib import font_manager
import gc

from .spectral import fft_wrap
from .common import * 
from .GUICommon import * 
from .GUIToolBox import MyMultiCursor, MyNavigationToolbar2Wx
from .GUITools import LogDecToolPanel, MaskToolPanel, RadialToolPanel, CurveFitToolPanel
from .GUIMeasure import GUIMeasure
#     from spectral import fft_wrap

font = {'size'   : 8}
matplotlib_rc('font', **font)
pyplot_rc['agg.path.chunksize'] = 20000

def unique(l):
    used=set()
    return [x for x in l if x not in used and (used.add(x) or True)]

class PlotData():
    def __init__(s):
        s.id=-1
        s.it=-1
        s.ix=-1 # column index
        s.iy=-1 # column index
        s.sx=''
        s.sy=''
        s.st=''
        s.syl=''
        s.filename = ''
        s.tabname = ''
        #d.x,d.xIsString,d.xIsDate,_ = tabs[d.it].getColumn(d.ix)
        #d.y,d.yIsString,d.yIsDate,c = tabs[d.it].getColumn(d.iy)
        pass

    def __repr__(s):
        s1='id:{}, it:{}, ix:{}, iy:{}, sx:"{}", sy:"{}", st:{}, syl:{}'.format(s.id,s.it,s.ix,s.iy,s.sx,s.sy,s.st,s.syl)
        return s1


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
    def __init__(self, parent, selPanel,infoPanel=None, mainframe=None):

        # Superclass constructor
        super(PlotPanel,self).__init__(parent)

        # Font handling
        font = parent.GetFont()
        font.SetPointSize(font.GetPointSize()-1)
        self.SetFont(font) 
        # Preparing a special font manager for chinese characters
        self.specialFont=None
        CH_F_PATHS = [
                os.path.join(pyplot_rc['datapath'], 'fonts/ttf/SimHei.ttf'),
                os.path.join(os.path.dirname(__file__),'../SimHei.ttf')]
        for fpath in CH_F_PATHS:
            if os.path.exists(fpath):
                fontP = font_manager.FontProperties(fname=fpath)
                fontP.set_size(font.GetPointSize())
                self.specialFont=fontP
                break
        # data
        self.selPanel = selPanel
        self.infoPanel=infoPanel
        self.infoPanel.setPlotMatrixCallbacks(self._onPlotMatrixLeftClick, self._onPlotMatrixRightClick)
        self.parent   = parent
        self.mainframe= mainframe
        self.plotData = []
        if self.selPanel is not None:
            bg=self.selPanel.BackgroundColour
            self.SetBackgroundColour(bg) # sowhow, our parent has a wrong color
        self.leftMeasure = GUIMeasure(1, 'firebrick')
        self.rightMeasure = GUIMeasure(2, 'darkgreen')
        self.xlim_prev = [[0, 1]]
        self.ylim_prev = [[0, 1]]
        # GUI
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        #self.fig.set_tight_layout(True) 
        self.fig.subplots_adjust(top=0.98,bottom=0.12,left=0.12,right=0.88)
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)
        self.canvas.mpl_connect('button_press_event', self.onMouseClick)
        self.canvas.mpl_connect('button_release_event', self.onMouseRelease)
        self.clickLocation = (None, 0, 0)

        self.navTBTop = MyNavigationToolbar2Wx(self.canvas, 1)
        self.navTBBottom = MyNavigationToolbar2Wx(self.canvas, 2)

        self.toolbar_sizer  = wx.BoxSizer(wx.VERTICAL)
        self.toolbar_sizer.Add(self.navTBTop)
        self.toolbar_sizer.Add(self.navTBBottom)


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
        self.cbScatter    = wx.CheckBox(self.ctrlPanel, -1, 'Scatter',(10,10))
        self.cbSub        = wx.CheckBox(self.ctrlPanel, -1, 'Subplot',(10,10))
        self.cbLogX       = wx.CheckBox(self.ctrlPanel, -1, 'Log-x',(10,10))
        self.cbLogY       = wx.CheckBox(self.ctrlPanel, -1, 'Log-y',(10,10))
        self.cbSync       = wx.CheckBox(self.ctrlPanel, -1, 'Sync-x',(10,10))
        self.cbXHair      = wx.CheckBox(self.ctrlPanel, -1, 'CrossHair',(10,10))
        self.cbPlotMatrix = wx.CheckBox(self.ctrlPanel, -1, 'Matrix',(10,10))
        self.cbAutoScale  = wx.CheckBox(self.ctrlPanel, -1, 'AutoScale',(10,10))
        self.cbGrid       = wx.CheckBox(self.ctrlPanel, -1, 'Grid',(10,10))
        self.cbStepPlot   = wx.CheckBox(self.ctrlPanel, -1, 'StepPlot',(10,10))
        self.cbMeasure    = wx.CheckBox(self.ctrlPanel, -1, 'Measure',(10,10))
        #self.cbSub.SetValue(True) # DEFAULT TO SUB?
        self.cbSync.SetValue(True)
        self.cbXHair.SetValue(True) # Have cross hair by default
        self.cbAutoScale.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.scatter_select   , self.cbScatter)
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSub    )
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogX   )
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogY   )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSync )
        self.Bind(wx.EVT_CHECKBOX, self.crosshair_event  , self.cbXHair )
        self.Bind(wx.EVT_CHECKBOX, self.plot_matrix_select, self.cbPlotMatrix )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbAutoScale )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbGrid )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbStepPlot )
        self.Bind(wx.EVT_CHECKBOX, self.measure_select   , self.cbMeasure )
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=4, cols=3, hgap=2, vgap=0)
        cb_sizer.Add(self.cbScatter   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSub       , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbAutoScale , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogX      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogY      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbStepPlot  , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSync      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbXHair     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbGrid      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPlotMatrix, 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMeasure   , 0, flag=wx.ALL, border=1)

        self.ctrlPanel.SetSizer(cb_sizer)
        # --- Ctrl Panel
        crossHairPanel= wx.Panel(self)
        self.lbCrossHairX = wx.StaticText(crossHairPanel, -1, 'x = ...       ')
        self.lbCrossHairY = wx.StaticText(crossHairPanel, -1, 'y = ...       ')
        self.lbDeltaX = wx.StaticText(crossHairPanel,     -1, '              ')
        self.lbDeltaY = wx.StaticText(crossHairPanel,     -1, '              ')
        self.lbCrossHairX.SetFont(getMonoFont(self))
        self.lbCrossHairY.SetFont(getMonoFont(self))
        self.lbDeltaX.SetFont(getMonoFont(self))
        self.lbDeltaY.SetFont(getMonoFont(self))
        cbCH  = wx.FlexGridSizer(rows=4, cols=1, hgap=0, vgap=0)
        cbCH.Add(self.lbCrossHairX   , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbCrossHairY   , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbDeltaX       , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbDeltaY       , 0, flag=wx.ALL, border=1)
        crossHairPanel.SetSizer(cbCH)

        # --- layout of panels
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sl2 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        sl3 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        sl4 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        row_sizer.Add(self.pltTypePanel , 0 , flag=wx.ALL|wx.CENTER           , border=2)
        row_sizer.Add(sl2               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(self.toolbar_sizer, 0 , flag=wx.LEFT|wx.RIGHT|wx.CENTER , border=2)
        row_sizer.Add(sl3               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(self.ctrlPanel    , 1 , flag=wx.ALL|wx.EXPAND|wx.CENTER , border=2)
        row_sizer.Add(sl4               , 0 , flag=wx.EXPAND|wx.CENTER        , border=0)
        row_sizer.Add(crossHairPanel    , 0 , flag=wx.EXPAND|wx.CENTER|wx.LEFT, border=2)

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
        plotsizer.Add(row_sizer     ,0,flag = wx.EXPAND|wx.NORTH ,border = 5)

        self.show_hide(self.spcPanel, self.pltTypePanel.cbFFT.GetValue())
        self.show_hide(self.cmpPanel, self.pltTypePanel.cbCompare.GetValue())
        self.show_hide(self.pdfPanel, self.pltTypePanel.cbPDF.GetValue())
        self.show_hide(self.mmxPanel, self.pltTypePanel.cbMinMax.GetValue())

        self.SetSizer(plotsizer)
        self.plotsizer=plotsizer;

    def plot_matrix_select(self, event):
        self.infoPanel.togglePlotMatrix(self.cbPlotMatrix.GetValue())
        self.redraw_same_data()

    def measure_select(self, event):
        if self.cbMeasure.IsChecked():
            self.cbAutoScale.SetValue(False)
        self.redraw_same_data()

    def redraw_event(self, event):
        self.redraw_same_data()

    def log_select(self, event):
        if self.pltTypePanel.cbPDF.GetValue():
            self.cbLogX.SetValue(False)
            self.cbLogY.SetValue(False)
        else:
            self.redraw_same_data()

    def crosshair_event(self, event):
        try:
            self.multiCursors.vertOn =self.cbXHair.GetValue()
            self.multiCursors.horizOn=self.cbXHair.GetValue()
            self.multiCursors._update()
        except:
            pass

    def scatter_select(self, event):
        self.cbScatter.SetValue(self.cbScatter.GetValue())
        self.redraw_same_data()

    def show_hide(self,panel,bShow):
        if bShow:
            panel.Show()
            self.slCtrl.Show()
        else:
            panel.Hide()
            self.slCtrl.Hide()

    @property
    def sharex(self):
        return self.cbSync.IsChecked() and (not self.pltTypePanel.cbPDF.GetValue())

    def set_subplots(self,nPlots):
        # Creating subplots
        for ax in self.fig.axes:
            self.fig.delaxes(ax)
        sharex=None
        for i in range(nPlots):
            # Vertical stack
            if i==0:
                ax=self.fig.add_subplot(nPlots,1,i+1)
                if self.sharex:
                    sharex=ax
            else:
                ax=self.fig.add_subplot(nPlots,1,i+1,sharex=sharex)
            # Horizontal stack
            #self.fig.add_subplot(1,nPlots,i+1)

    def onMouseMove(self, event):
        if event.inaxes:
            x, y = event.xdata, event.ydata
            self.lbCrossHairX.SetLabel('x =' + self.formatLabelValue(x))
            self.lbCrossHairY.SetLabel('y =' + self.formatLabelValue(y)) 
        self._store_limits()

    def onMouseClick(self, event):
        self.clickLocation = (event.inaxes, event.xdata, event.ydata)

    def onMouseRelease(self, event):
        if self.cbMeasure.GetValue():
            for ax, ax_idx in zip(self.fig.axes, range(len(self.fig.axes))):
                if event.inaxes == ax:
                    x, y = event.xdata, event.ydata
                    if self.clickLocation != (ax, x, y):
                        # Ignore measurements for zoom-actions. Possibly add small tolerance.
                        # Zoom-actions disable autoscale
                        self.cbAutoScale.SetValue(False)
                        return
                    if event.button == 1:
                        self.infoPanel.setMeasurements((x, y), None)
                        self.leftMeasure.set(ax_idx, x, y)
                        self.leftMeasure.plot(ax, ax_idx)
                    elif event.button == 3:
                        self.infoPanel.setMeasurements(None, (x, y))
                        self.rightMeasure.set(ax_idx, x, y)
                        self.rightMeasure.plot(ax, ax_idx)
                    else:
                        return
                    if self.cbAutoScale.IsChecked() is False:
                        self._restore_limits()
                        
                    if self.leftMeasure.axis_idx == self.rightMeasure.axis_idx and self.leftMeasure.axis_idx != -1:
                        self.lbDeltaX.SetLabel('dx=' + self.formatLabelValue(self.rightMeasure.x - self.leftMeasure.x))
                        self.lbDeltaY.SetLabel('dy=' + self.formatLabelValue(self.rightMeasure.y - self.leftMeasure.y))
                    else:
                        self.lbDeltaX.SetLabel('')
                        self.lbDeltaY.SetLabel('')
                    return

    def formatLabelValue(self, value):
        try:
            if abs(value)<1000 and abs(value)>1e-4:
                s = '{:10.5f}'.format(value)
            else:
                s = '{:10.3e}'.format(value)
        except TypeError:
            s = '            '
        return s

    def removeTools(self,event=None,Layout=True):
        try:
            # Python3
            self.toolSizer.Clear(delete_windows=True) # Delete Windows
        except:
            # Python2
            if hasattr(self,'toolPanel'):
                self.toolSizer.Remove(self.toolPanel)
                self.toolPanel.Destroy()
                del self.toolPanel
            self.toolSizer.Clear() # Delete Windows
        if Layout:
            self.plotsizer.Layout()

    def showTool(self,toolName=''):
        self.removeTools(Layout=False)
        # TODO dictionary
        if toolName=='LogDec':
            self.toolPanel=LogDecToolPanel(self)
        elif toolName=='Mask':
            self.toolPanel=MaskToolPanel(self)
        elif toolName=='FASTRadialAverage':
            self.toolPanel=RadialToolPanel(self)
        elif toolName=='CurveFitting':
            self.toolPanel=CurveFitToolPanel(self)
        else:
            raise Exception('Unknown tool {}'.format(toolName))
        self.toolSizer.Add(self.toolPanel, 0, wx.EXPAND|wx.ALL, 5)
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
        ID,SameCol=self.selPanel.getPlotDataSelection()
        del self.plotData
        self.plotData=[]
        tabs=self.selPanel.tabList.getTabs() # TODO
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
            d.x,d.xIsString,d.xIsDate,_ = tabs[d.it].getColumn(d.ix)
            d.y,d.yIsString,d.yIsDate,c = tabs[d.it].getColumn(d.iy)
            n=len(d.y)
            if n>1000 and (d.xIsString):
                self.plotData=[]
                raise Exception('Error: x values contain more than 1000 string. This is not suitable for plotting.\n\nPlease select another column for table: {}\nProblematic column: {}\n'.format(d.st,d.sx))

            if n>1000 and (d.yIsString):
                self.plotData=[]
                raise Exception('Error: y values contain more than 1000 string. This is not suitable for plotting.\n\nPlease select another column for table: {}\nProblematic column: {}\n'.format(d.st,d.sy))

            d.needChineseFont = has_chinese_char(d.sy) or has_chinese_char(d.sx)
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
                if np.mean(np.abs(yref))<1e-7:
                    Error=(y-yRef)/(yRef+1)*100
                else:
                    Error=(y-yRef)/yRef*100
            elif sComp=='|Relative|':
                if np.mean(np.abs(yref))<1e-7:
                    Error=abs((y-yRef)/(yRef+1))*100
                else:
                    Error=abs((y-yRef)/yRef)*100
            elif sComp=='Ratio':
                if np.mean(np.abs(yref))<1e-7:
                    Error=(y+1)/(yRef+1)
                else:
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
        elif mode =='nTabs_SimCols':
            # --- Compare different tables, similar columns
            print('Several Tabs, similar columns, TODO')
            self.plotData=[]

    def _onPlotMatrixLeftClick(self, event):
        """Toggle plot-states from None, to left-axis, to right-axis.
            Left-click goes forwards, right-click goes backwards.
            IndexError to avoid "holes" in matrix with outer adjacent populated entries
        """
        btn = event.GetEventObject()
        label = btn.GetLabelText()
        if label == '-':
            btn.SetLabel('1')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('-')
        elif label == '1':
            btn.SetLabel('2')
        else:
            btn.SetLabel('-')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('1')
        self.redraw_same_data()

    def _onPlotMatrixRightClick(self, event):
        btn = event.GetEventObject()
        label = btn.GetLabelText()
        if label == '-':
            btn.SetLabel('2')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('-')
        elif label == '1':
            btn.SetLabel('-')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('2')
        else:
            btn.SetLabel('1')
        self.redraw_same_data()

    def plot_all(self, keep_limits=True):
        self.multiCursors=[]

        if self.cbMeasure.GetValue() is False:
            for measure in [self.leftMeasure, self.rightMeasure]:
                measure.clear()
                self.infoPanel.setMeasurements(None, None)
                self.lbDeltaX.SetLabel('')
                self.lbDeltaY.SetLabel('')

        axes=self.fig.axes

        bScatter=self.cbScatter.IsChecked()
        bStep=self.cbStepPlot.IsChecked()

        PD=self.plotData

        needChineseFont = any([pd.needChineseFont for pd in PD])
        if needChineseFont and self.specialFont is not None:
            font_options      = {'fontproperties': self.specialFont}
            font_options_legd = {'prop': self.specialFont}
        else:
            font_options      = {}
            font_options_legd = {}

        for ax_left, axis_idx in zip(axes, range(len(axes))):
            ax_right = None
            # Plot data
            vDate=[PD[i].yIsDate for i in ax_left.iPD]
            if any(vDate) and len(vDate)>1:
                Error(self,'Cannot plot date and other value on the same axis')
                return

            #Keep me - tight axis, attempt to optimize
            #try:
            #    xMin=np.min([PD[i].x0Min[0] for i in ax_left.iPD])
            #    xMax=np.max([PD[i].x0Max[0] for i in ax_left.iPD])
            #    ax_left.set_xlim(xMin,xMax)
            #    ax_left.autoscale(False)
            #except:
            #    pass
            #try:
            #    yMin=np.min([PD[i].y0Min[0] for i in ax_left.iPD])
            #    yMax=np.max([PD[i].y0Max[0] for i in ax_left.iPD])
            #    ax_left.set_ylim(yMin,yMax)
            #    ax_left.autoscale(False)
            #except:
            #    pass

            pm = self.infoPanel.getPlotMatrix(PD, self.cbSub.IsChecked())
            __, bAllNegLeft        = self.plotSignals(ax_left, axis_idx, PD, pm, 1, bScatter, bStep)
            ax_right, bAllNegRight = self.plotSignals(ax_left, axis_idx, PD, pm, 2, bScatter, bStep)

            self.infoPanel.setMeasurements(self.leftMeasure.get_xydata(), self.rightMeasure.get_xydata())
            for measure in [self.leftMeasure, self.rightMeasure]:
                measure.plot(ax_left, axis_idx)

            # Log Axes
            if self.cbLogX.IsChecked():
                ax_left.set_xscale("log", nonposx='clip')
            if self.cbLogY.IsChecked():
                if bAllNegLeft is False:
                    ax_left.set_yscale("log", nonposy='clip')
                if bAllNegRight is False and ax_right is not None:
                    ax_right.set_yscale("log", nonposy='clip')

            # XLIM - TODO FFT ONLY NASTY
            if self.pltTypePanel.cbFFT.GetValue():
                try:
                    xlim=float(self.spcPanel.tMaxFreq.GetLineText(0))
                    if xlim>0:
                        ax_left.set_xlim([0,xlim])
                        pd=PD[ax_left.iPD[0]]
                        I=pd.x<xlim
                        ymin = np.min([np.min(PD[ipd].y[I]) for ipd in ax_left.iPD])
                        ax_left.set_ylim(bottom=ymin/2)
                except:
                    pass
            elif self.cbAutoScale.IsChecked() is False and keep_limits:
                self._restore_limits()

            ax_left.grid(self.cbGrid.IsChecked())

            # Special Grids
            if self.pltTypePanel.cbCompare.GetValue():
                if self.cmpPanel.rbType.GetStringSelection()=='Y-Y':
                    xmin,xmax=ax_left.get_xlim()
                    ax_left.plot([xmin,xmax],[xmin,xmax],'k--',linewidth=0.5)

            # Labels
            yleft_labels = []
            yright_labels = []
            yleft_legends = []
            yright_legends = []
            if pm is None:
                yleft_labels = unique([PD[i].sy for i in ax_left.iPD])
                if axis_idx == 0:
                    yleft_legends = unique([PD[i].syl for i in ax_left.iPD])
            else:
                for signal_idx in range(len(PD)):
                    if pm[signal_idx][axis_idx] == 1:
                        yleft_labels.append(PD[signal_idx].sy)
                        yleft_legends.append(PD[signal_idx].syl)
                    elif pm[signal_idx][axis_idx] == 2:
                        yright_labels.append(PD[signal_idx].sy)
                        yright_legends.append(PD[signal_idx].syl)
                yleft_labels = unique(yleft_labels)
                yright_labels = unique(yright_labels)
                yleft_legends = unique(yleft_legends)
                yright_legends = unique(yright_legends)

            if len(yleft_labels) > 0 and len(yleft_labels) <= 3:
                ax_left.set_ylabel(' and '.join(yleft_labels), **font_options)
            elif ax_left is not None:
                ax_left.set_ylabel('')
            if len(yright_labels) > 0 and len(yright_labels) <= 3:
                ax_right.set_ylabel(' and '.join(yright_labels), **font_options)
            elif ax_right is not None:
                ax_right.set_ylabel('')

            # Legends
            if (self.pltTypePanel.cbCompare.GetValue() or 
                ((len(yleft_legends) + len(yright_legends)) > 1)):
                if len(yleft_legends) > 0:
                    ax_left.legend(fancybox=False, loc=1, **font_options_legd)
                if ax_right is not None and len(yright_legends) > 0:
                    ax_right.legend(fancybox=False, loc=4, **font_options_legd)
            elif len(axes)>1 and len(axes)==len(PD):
                # TODO: can this be removed? If there is only one unique signal
                # per subplot, normally only ylabel is displayed and no legend.
                # Special case when we have subplots and all plots have the same label
                usy = unique([pd.sy for pd in PD])
                if len(usy)==1:
                    for ax in axes:
                        ax.legend(fancybox=False, loc=1, **font_options_legd)

        axes[-1].set_xlabel(PD[axes[-1].iPD[0]].sx, **font_options)

        #print('sy :',[pd.sy for pd in PD])
        #print('syl:',[pd.syl for pd in PD])

        # --- Cursors for each individual plot
        # NOTE: cursors needs to be stored in the object!
        #for ax_left in self.fig.axes:
        #    self.cursors.append(MyCursor(ax_left,horizOn=True, vertOn=False, useblit=True, color='gray', linewidth=0.5, linestyle=':'))
        # Vertical cusor for all, commonly
        bXHair = self.cbXHair.GetValue()
        self.multiCursors = MyMultiCursor(self.canvas, tuple(self.fig.axes), useblit=True, horizOn=bXHair, vertOn=bXHair, color='gray', linewidth=0.5, linestyle=':')

    def plotSignals(self, ax, axis_idx, PD, pm, left_right, is_scatter, is_step):
        axis = None
        bAllNeg = True
        if pm is None:
            loop_range = ax.iPD
        else:
            loop_range = range(len(PD))
        for signal_idx in loop_range:
            do_plot = False
            if left_right == 1 and (pm is None or pm[signal_idx][axis_idx] == left_right):
                do_plot = True
                axis = ax
            elif left_right == 2 and pm is not None and pm[signal_idx][axis_idx] == left_right:
                do_plot = True
                if axis is None:
                    axis = ax.twinx()
                    ax.set_zorder(axis.get_zorder()+1)
                    ax.patch.set_visible(False)
                    axis._get_lines.prop_cycler = ax._get_lines.prop_cycler
            pd=PD[signal_idx]
            if is_scatter or len(pd.x)==1:
                sty='o'
            else:
                sty='-'
            if do_plot:
                if is_step:
                    plot = axis.step
                else:
                    plot = axis.plot
                plot(pd.x,pd.y,sty,label=pd.syl,markersize=1)
                bAllNeg = bAllNeg and all(pd.y<=0)
        return axis, bAllNeg
            
    def findPlotMode(self,PD):
        uTabs = unique([pd.it for pd in PD])
        usy   = unique([pd.sy for pd in PD])
        uiy   = unique([pd.iy for pd in PD])
        if len(uTabs)<=0:
            raise Exception('No Table. Contact developer')
        elif len(uTabs)==1:
            mode='1Tab_nCols'
        else:
            if PD[0].SameCol:
                mode='nTabs_SameCols'
            else:
                if len(uTabs) == len(PD):
                    mode='nTabs_1Col'
                else:
                    mode='nTabs_SimCols'
        return mode

    def findSubPlots(self,PD,mode):
        uTabs = unique([pd.it for pd in PD])
        usy   = unique([pd.sy for pd in PD])
        bSubPlots = self.cbSub.IsChecked()
        bCompare  = self.pltTypePanel.cbCompare.GetValue() # NOTE bCompare somehow always 1Tab_nCols
        nSubPlots=1
        spreadBy='none'
        self.infoPanel.setTabMode(mode)
        if mode=='1Tab_nCols':
            if bSubPlots:
                if bCompare or len(uTabs)==1:
                    nSubPlots = self.infoPanel.getNumberOfSubplots(PD, self.cbSub.IsChecked())
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
        elif mode=='nTabs_SimCols':
            if bSubPlots:
                if bCompare:
                    print('>>>TODO ',mode,len(usy),len(uTabs))
                else:
                    nSubPlots=int(len(PD)/len(uTabs))
                    spreadBy='mod-ip'
        elif mode=='nTabs_1Col':
            if bSubPlots:
                if bCompare:
                    print('>>> TODO',mode,len(uTabs))
                else:
                    nSubPlots=len(uTabs)
                    spreadBy='it'
        else:
            raise Exception('Unknown mode, contact developer.')
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
                    if i < len(axes):
                        axes[i].iPD.append(ipd)
            elif spreadBy=='it':
                for ipd,pd in enumerate(PD):
                    i=uTabs.index(pd.it)
                    axes[i].iPD.append(ipd)
            elif spreadBy=='mod-ip':
                for ipd,pd in enumerate(PD):
                    i=np.mod(ipd, nSubPlots)
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
        elif mode=='nTabs_SimCols':
            bSubPlots = self.cbSub.IsChecked()
            if bSubPlots: # spread by table name
                for pd in self.plotData:
                    pd.syl=pd.st
            else:
                for pd in self.plotData:
                    pd.syl=pd.st + ' - '+pd.sy
        else:
            raise Exception('Unknown mode {}'.format(mode))


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

    def redraw_same_data(self, keep_limits=True):
        self._redraw_same_data(keep_limits)

    def _redraw_same_data(self, keep_limits=True):
        if len(self.plotData)==0: 
            self.cleanPlot();
            return
        elif len(self.plotData) == 1:
            # If single signal view is out of range, enable autoscale (could be regardless of cbMeasure?)
            for (x, y) in np.array([self.plotData[0].x, self.plotData[0].y]).transpose():
                if (self.xlim_prev[0][0] < x and x < self.xlim_prev[0][1] and
                    self.ylim_prev[0][0] < y and y < self.ylim_prev[0][1]):
                    break
            else:
                self.cbAutoScale.SetValue(True)

        mode=self.findPlotMode(self.plotData)
        nPlots,spreadBy=self.findSubPlots(self.plotData,mode)

        self.clean_memory_plot()
        self.set_subplots(nPlots)
        self.distributePlots(mode,nPlots,spreadBy)

        if not self.pltTypePanel.cbCompare.GetValue():
            self.setLegendLabels(mode)

        self.plot_all(keep_limits)
        self.canvas.draw()
        self._store_limits()

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

    def _store_limits(self):
        self.xlim_prev = []
        self.ylim_prev = []
        for ax in self.fig.axes:
            self.xlim_prev.append(ax.get_xlim())
            self.ylim_prev.append(ax.get_ylim())

    def _restore_limits(self):
        for ax, xlim, ylim in zip(self.fig.axes, self.xlim_prev, self.ylim_prev):
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)


if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table,TableList

    app = wx.App(False)
    self=wx.Frame(None,-1,"Title")
    self.SetSize((800, 600))
    #self.SetBackgroundColour('red')
    class FakeSelPanel(wx.Panel):
        def __init__(self, parent):
            super(FakeSelPanel,self).__init__(parent)
            d ={'ColA': np.linspace(0,1,100)+1,'ColB': np.random.normal(0,1,100)+0,'ColC':np.random.normal(0,1,100)+1}
            df = pd.DataFrame(data=d)
            self.tabList=TableList([Table(data=df)])

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


