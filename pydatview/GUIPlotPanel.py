import os
import numpy as np
import wx
import wx.lib.buttons  as  buttons
import dateutil # required by matplotlib
#from matplotlib import pyplot as plt
import matplotlib
# Backends:
#  ['GTK3Agg', 'GTK3Cairo', 'GTK4Agg', 'GTK4Cairo', 'MacOSX', 'nbAgg', 'QtAgg', 'QtCairo', 'Qt5Agg', 'Qt5Cairo', 'TkAgg', 'TkCairo', 'WebAgg', 'WX', 'WXAgg', 'WXCairo', 'agg', 'cairo', 'pdf', 'pgf', 'ps', 'svg', 'template']
matplotlib.use('WX') # Important for Windows version of installer. NOTE: changed from Agg to wxAgg, then to WX
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
        print('    - using a virtual environment with python 3')
        print('    - using anaconda with python 3');
        print('')
        import sys
        sys.exit(1)
    else:
        raise e
from matplotlib.figure import Figure
from matplotlib.pyplot import rcParams as pyplot_rc
from matplotlib import font_manager
from pandas.plotting import register_matplotlib_converters

import gc

from pydatview.common import * # unique, CHAR
from pydatview.plotdata import PlotData, compareMultiplePD
from pydatview.GUICommon import * 
from pydatview.GUIToolBox import MyMultiCursor, MyNavigationToolbar2Wx, TBAddTool, TBAddCheckTool
from pydatview.GUIMeasure import GUIMeasure
import pydatview.icons as icons

font = {'size'   : 8}
matplotlib_rc('font', **font)
pyplot_rc['agg.path.chunksize'] = 20000


class PDFCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(PDFCtrlPanel,self).__init__(parent)
        self.parent   = parent
        lb = wx.StaticText( self, -1, 'Number of bins:')
        self.scBins = wx.SpinCtrl(self, value='51',size=wx.Size(70,-1), style=wx.TE_RIGHT)
        self.scBins.SetRange(3, 10000)
        self.cbSmooth = wx.CheckBox(self, -1, 'Smooth',(10,10))
        self.cbSmooth.SetValue(False)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(lb                    ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.scBins           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.cbSmooth         ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_TEXT    , self.onPDFOptionChange, self.scBins)
        self.Bind(wx.EVT_CHECKBOX, self.onPDFOptionChange)
        self.Hide() 

    def onPDFOptionChange(self,event=None):
        self.parent.load_and_draw(); # DATA HAS CHANGED

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
        self.parent.load_and_draw(); # DATA HAS CHANGED

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
        self.parent.load_and_draw(); # DATA HAS CHANGED


class SpectralCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(SpectralCtrlPanel,self).__init__(parent)
        self.parent   = parent
        # --- GUI widgets
        lb = wx.StaticText( self, -1, 'Type:')
        self.cbType            = wx.ComboBox(self, choices=['PSD','f x PSD','Amplitude'] , style=wx.CB_READONLY)
        self.cbType.SetSelection(0)
        lbAveraging            = wx.StaticText( self, -1, 'Avg.:')
        self.cbAveraging       = wx.ComboBox(self, choices=['None','Welch','Binning'] , style=wx.CB_READONLY)
        self.cbAveraging.SetSelection(1)
        self.lbAveragingMethod = wx.StaticText( self, -1, 'Window:')
        self.cbAveragingMethod = wx.ComboBox(self, choices=['Hamming','Hann','Rectangular'] , style=wx.CB_READONLY)
        self.cbAveragingMethod.SetSelection(0)
        self.lbP2 = wx.StaticText( self, -1, '2^n:')
        self.scP2 = wx.SpinCtrl(self, value='11',size=wx.Size(40,-1))
        self.lbWinLength = wx.StaticText( self, -1, '(2048) ')
        self.scP2.SetRange(3, 50)
        self.previousNExp = 8
        self.previousNDec = 20
        lbMaxFreq     = wx.StaticText( self, -1, 'Xlim:')
        self.tMaxFreq = wx.TextCtrl(self,size = (30,-1),style=wx.TE_PROCESS_ENTER)
        self.tMaxFreq.SetValue("-1")
        self.cbDetrend = wx.CheckBox(self, -1, 'Detrend',(10,10))
        lbX = wx.StaticText( self, -1, 'x:')
        self.cbTypeX = wx.ComboBox(self, choices=['1/x','2pi/x','x'] , style=wx.CB_READONLY)
        self.cbTypeX.SetSelection(0)
        # Layout
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
        dummy_sizer.Add(lbX                   ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.cbTypeX          ,0, flag = wx.CENTER|wx.LEFT,border = 1)
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
        if self.cbAveraging.GetStringSelection()=='None':
            self.scP2.Enable(False)
            self.cbAveragingMethod.Enable(False)
            self.lbP2.SetLabel('')
            self.lbWinLength.SetLabel('')
        elif self.cbAveraging.GetStringSelection()=='Binning':
            self.previousNExp= self.scP2.GetValue()
            self.scP2.SetValue(self.previousNDec)
            self.scP2.Enable(True)
            self.cbAveragingMethod.Enable(False)
            self.lbP2.SetLabel('n:')
            self.lbWinLength.SetLabel('')
        else:
            self.previousDec= self.scP2.GetValue()
            self.scP2.SetValue(self.previousNExp)
            self.lbP2.SetLabel('2^n:')
            self.scP2.Enable(True)
            self.cbAveragingMethod.Enable(True)
            self.onP2ChangeText(event=None)
        self.parent.load_and_draw() # Data changes

    def onDetrendChange(self,event=None):
        self.parent.load_and_draw() # Data changes

    def onP2ChangeText(self,event=None):
        if self.cbAveraging.GetStringSelection()=='Binning':
            pass
        else:
            nExp=self.scP2.GetValue()
            self.updateP2(nExp)
        self.parent.load_and_draw() # Data changes

    def updateP2(self,P2):
        self.lbWinLength.SetLabel("({})".format(2**P2))




class PlotTypePanel(wx.Panel):
    def __init__(self, parent):
        # Superclass constructor
        super(PlotTypePanel,self).__init__(parent)
        #self.SetBackgroundColour('yellow')
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
        cb_sizer  = wx.FlexGridSizer(rows=5, cols=1, hgap=0, vgap=0)
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
        self.clear_measures()
        self.parent.cbLogY.SetValue(False)
        # 
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.slEsth.Hide();
        self.parent.plotsizer.Layout()
        #
        self.parent.load_and_draw() # Data changes

    def compare_select(self, event=None):
        self.clear_measures()
        self.parent.cbLogY.SetValue(False)
        self.parent.show_hide(self.parent.cmpPanel, self.cbCompare.GetValue())
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.load_and_draw() # Data changes

    def fft_select(self, event=None):
        self.clear_measures()
        self.parent.show_hide(self.parent.spcPanel, self.cbFFT.GetValue())
        self.parent.cbLogY.SetValue(self.cbFFT.GetValue())
        self.parent.pdfPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.load_and_draw() # Data changes

    def pdf_select(self, event=None):
        self.clear_measures()
        self.parent.cbLogX.SetValue(False)
        self.parent.cbLogY.SetValue(False)
        self.parent.show_hide(self.parent.pdfPanel, self.cbPDF.GetValue())
        self.parent.spcPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.mmxPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.load_and_draw() # Data changes

    def minmax_select(self, event):
        self.clear_measures()
        self.parent.cbLogY.SetValue(False)
        self.parent.show_hide(self.parent.mmxPanel, self.cbMinMax.GetValue())
        self.parent.spcPanel.Hide();
        self.parent.pdfPanel.Hide();
        self.parent.cmpPanel.Hide();
        self.parent.plotsizer.Layout()
        self.parent.load_and_draw() # Data changes

    def clear_measures(self):
        self.parent.rightMeasure.clear()
        self.parent.leftMeasure.clear()
        self.parent.lbDeltaX.SetLabel('')
        self.parent.lbDeltaY.SetLabel('')

class EstheticsPanel(wx.Panel):
    def __init__(self, parent, data):
        wx.Panel.__init__(self, parent)
        self.parent=parent
        #self.SetBackgroundColour('red')

        # Font
        lbFont = wx.StaticText( self, -1, 'Font:')
        fontChoices = ['6','7','8','9','10','11','12','13','14','15','16','17','18']
        self.cbFont = wx.ComboBox(self, choices=fontChoices , style=wx.CB_READONLY)
        try:
            i = fontChoices.index(str(data['Font']))
        except ValueError:
            i = 2
        self.cbFont.SetSelection(i)
        # Legend
        # NOTE: we don't offer "best" since best is slow
        lbLegend = wx.StaticText( self, -1, 'Legend:')
        lbChoices = ['None','Upper right','Upper left','Lower left','Lower right','Right','Center left','Center right','Lower center','Upper center','Center']
        self.cbLegend = wx.ComboBox(self, choices=lbChoices, style=wx.CB_READONLY)
        try:
            i = lbChoices.index(str(data['LegendPosition']))
        except ValueError:
            i=1
        self.cbLegend.SetSelection(i)
        # Legend Font
        lbLgdFont = wx.StaticText( self, -1, 'Legend font:')
        self.cbLgdFont = wx.ComboBox(self, choices=fontChoices, style=wx.CB_READONLY)
        try:
            i = fontChoices.index(str(data['LegendFont']))
        except ValueError:
            i = 2
        self.cbLgdFont.SetSelection(i)
        # Line Width Font
        lbLW = wx.StaticText( self, -1, 'Line width:')
        LWChoices = ['0.5','1.0','1.25','1.5','2.0','2.5','3.0']
        self.cbLW = wx.ComboBox(self, choices=LWChoices , style=wx.CB_READONLY)
        try:
            i = LWChoices.index(str(data['LineWidth']))
        except ValueError:
            i = 3
        self.cbLW.SetSelection(i)
        #  Marker Size
        lbMS = wx.StaticText( self, -1, 'Marker size:')
        MSChoices = ['0.5','1','2','3','4','5','6','7','8']
        self.cbMS= wx.ComboBox(self, choices=MSChoices, style=wx.CB_READONLY)
        try:
            i = MSChoices.index(str(data['MarkerSize']))
        except ValueError:
            i = 2
        self.cbMS.SetSelection(i)

        # Layout
        #dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer = wx.WrapSizer(orient=wx.HORIZONTAL)
        dummy_sizer.Add(lbFont                ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.cbFont           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbLW                  ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        dummy_sizer.Add(self.cbLW             ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbMS                  ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        dummy_sizer.Add(self.cbMS             ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbLegend              ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        dummy_sizer.Add(self.cbLegend         ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbLgdFont             ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        dummy_sizer.Add(self.cbLgdFont        ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        self.SetSizer(dummy_sizer)
        self.Hide()
        # Callbacks
        self.Bind(wx.EVT_COMBOBOX  ,self.onAnyEsthOptionChange)
        self.cbFont.Bind(wx.EVT_COMBOBOX  ,self.onFontOptionChange)

    def onAnyEsthOptionChange(self,event=None):
        self.parent.redraw_same_data()

    def onFontOptionChange(self,event=None):
        matplotlib_rc('font', **{'size':int(self.cbFont.Value) }) # affect all (including ticks)
        self.onAnyEsthOptionChange()


class PlotPanel(wx.Panel):
    def __init__(self, parent, selPanel, pipeLike=None, infoPanel=None, data=None):

        # Superclass constructor
        super(PlotPanel,self).__init__(parent)

        # Font handling
        font = parent.GetFont()
        font.SetPointSize(font.GetPointSize()-1)
        self.SetFont(font) 
        # Preparing a special font manager for chinese characters
        self.specialFont=None
        try:
            pyplot_path = matplotlib.get_data_path()
        except:
            pyplot_path = pyplot_rc['datapath']
        CH_F_PATHS = [
                os.path.join(pyplot_path, 'fonts/ttf/SimHei.ttf'),
                os.path.join(os.path.dirname(__file__),'../SimHei.ttf')]
        for fpath in CH_F_PATHS:
            if os.path.exists(fpath):
                fontP = font_manager.FontProperties(fname=fpath)
                fontP.set_size(font.GetPointSize())
                self.specialFont=fontP
                break
        # data
        self.selPanel = selPanel # <<< dependency with selPanel should be minimum
        self.pipeLike = pipeLike #
        self.selMode  = '' 
        self.infoPanel=infoPanel
        if self.infoPanel is not None:
            self.infoPanel.setPlotMatrixCallbacks(self._onPlotMatrixLeftClick, self._onPlotMatrixRightClick)
        self.parent   = parent
        self.plotData = []
        self.toolPanel=None
        if data is not None:
            self.data  = data
        else:
            print('>>> Using default settings for plot panel')
            self.data = self.defaultData()
        if self.selPanel is not None:
            bg=self.selPanel.BackgroundColour
            self.SetBackgroundColour(bg) # sowhow, our parent has a wrong color
        #self.SetBackgroundColour('red')
        self.leftMeasure = GUIMeasure(1, 'firebrick')
        self.rightMeasure = GUIMeasure(2, 'darkgreen')
        self.xlim_prev = [[0, 1]]
        self.ylim_prev = [[0, 1]]
        self.addTablesCallback = None

        # --- GUI
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        register_matplotlib_converters()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)
        self.canvas.mpl_connect('button_press_event', self.onMouseClick)
        self.canvas.mpl_connect('button_release_event', self.onMouseRelease)
        self.canvas.mpl_connect('draw_event', self.onDraw)
        self.clickLocation = (None, 0, 0)

        self.navTBTop    = MyNavigationToolbar2Wx(self.canvas, ['Home', 'Pan'])
        self.navTBBottom = MyNavigationToolbar2Wx(self.canvas, ['Subplots', 'Save'])
        TBAddCheckTool(self.navTBBottom,'', icons.chart.GetBitmap(), self.onEsthToggle)
        self.esthToggle=False

        self.navTBBottom.Realize()

        #self.navTB = wx.ToolBar(self, style=wx.TB_HORIZONTAL|wx.TB_HORZ_LAYOUT|wx.TB_NODIVIDER|wx.TB_FLAT)
        #self.navTB.SetMargins(0,0)
        #self.navTB.SetToolPacking(0)
        #self.navTB.AddCheckTool(-1, label='', bitmap1=icons.chart.GetBitmap())
        #self.navTB.Realize()

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
        # --- Esthetics panel
        self.esthPanel = EstheticsPanel(self, data=self.data['plotStyle'])


        # --- Ctrl Panel
        self.ctrlPanel= wx.Panel(self)
        #self.ctrlPanel.SetBackgroundColour('blue')
        # Check Boxes
        self.cbCurveType = wx.ComboBox(self.ctrlPanel, choices=['Plain','LS','Markers','Mix'] , style=wx.CB_READONLY)
        self.cbCurveType.SetSelection(1)
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
        self.cbXHair.SetValue(self.data['CrossHair']) # Have cross hair by default
        self.cbAutoScale.SetValue(True)
        self.cbGrid.SetValue(self.data['Grid'])
        # Callbacks
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSub    )
        self.Bind(wx.EVT_COMBOBOX, self.redraw_event     , self.cbCurveType)
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogX   )
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogY   )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSync )
        self.Bind(wx.EVT_CHECKBOX, self.crosshair_event  , self.cbXHair )
        self.Bind(wx.EVT_CHECKBOX, self.plot_matrix_select, self.cbPlotMatrix )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbAutoScale )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbGrid )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbStepPlot )
        self.Bind(wx.EVT_CHECKBOX, self.measure_select   , self.cbMeasure )
        self.Bind(wx.EVT_CHECKBOX, self.measure_select   , self.cbMeasure )
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=4, cols=3, hgap=0, vgap=0)
        cb_sizer.Add(self.cbCurveType , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSub       , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbAutoScale , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogX      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogY      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbStepPlot  , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbXHair     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbGrid      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSync      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPlotMatrix, 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMeasure   , 0, flag=wx.ALL, border=1)

        self.ctrlPanel.SetSizer(cb_sizer)

        # --- Crosshair Panel
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
        row_sizer.Add(self.pltTypePanel , 0 , flag=wx.LEFT|wx.RIGHT|wx.CENTER          , border=1)
        row_sizer.Add(sl2               , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(self.toolbar_sizer, 0 , flag=wx.LEFT|wx.RIGHT|wx.CENTER          , border=1)
        row_sizer.Add(sl3               , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(self.ctrlPanel    , 1 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(sl4               , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(crossHairPanel    , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=1)

        plotsizer = wx.BoxSizer(wx.VERTICAL)
        self.slCtrl = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.slCtrl.Hide()
        self.slEsth = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.slEsth.Hide()
        sl1 = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        plotsizer.Add(self.toolSizer,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.canvas   ,1,flag = wx.EXPAND,border = 5 )
        plotsizer.Add(sl1           ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.spcPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.pdfPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.cmpPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.mmxPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slEsth   ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.esthPanel,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slCtrl   ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(row_sizer     ,0,flag = wx.EXPAND|wx.NORTH ,border = 2)

        self.show_hide(self.spcPanel, self.pltTypePanel.cbFFT.GetValue())
        self.show_hide(self.cmpPanel, self.pltTypePanel.cbCompare.GetValue())
        self.show_hide(self.pdfPanel, self.pltTypePanel.cbPDF.GetValue())
        self.show_hide(self.mmxPanel, self.pltTypePanel.cbMinMax.GetValue())

        self.SetSizer(plotsizer)
        self.plotsizer=plotsizer;
        self.set_subplot_spacing(init=True)

    # --- Bindings/callback
    def setAddTablesCallback(self, callback):
        self.addTablesCallback = callback

    def addTables(self, *args, **kwargs):
        if self.addTablesCallback is not None:
            self.addTablesCallback(*args, **kwargs)
        else:
            print('[WARN] callback to add tables to parent was not set.')


    # --- GUI DATA
    def saveData(self, data):
        data['Grid']      = self.cbGrid.IsChecked()
        data['CrossHair'] = self.cbXHair.IsChecked()
        data['plotStyle']['Font']           = self.esthPanel.cbFont.GetValue()
        data['plotStyle']['LegendFont']     = self.esthPanel.cbLgdFont.GetValue()
        data['plotStyle']['LegendPosition'] = self.esthPanel.cbLegend.GetValue()
        data['plotStyle']['LineWidth']      = self.esthPanel.cbLW.GetValue()
        data['plotStyle']['MarkerSize']     = self.esthPanel.cbMS.GetValue()
        
    @staticmethod
    def defaultData():
        data={}
        data['CrossHair']=True
        data['Grid']=False
        plotStyle = dict()
        plotStyle['Font']           = '11'
        plotStyle['LegendFont']     = '11'
        plotStyle['LegendPosition'] = 'Upper right'
        plotStyle['LineWidth']      = '1.5'
        plotStyle['MarkerSize']     = '2'
        data['plotStyle']= plotStyle
        return data

    def onEsthToggle(self,event):
        self.esthToggle=not self.esthToggle
        if self.esthToggle:
            self.slCtrl.Show()
            self.esthPanel.Show()
        else:
            self.slCtrl.Hide()
            self.esthPanel.Hide()
        self.plotsizer.Layout()
        event.Skip()

    def set_subplot_spacing(self, init=False):
        """ 
        Handle default subplot spacing

        NOTE:
           - Tight fails when the ylabel is too long, especially for fft with multiplt signals
           - might need to change depending on window size/resizing
           - need to change if right axis needed 
           - this will override the user settings
        """
        #self.fig.set_tight_layout(True)  # NOTE: works almost fine, but problem with FFT multiple
        # TODO this is definitely not generic, but tight fails..
        if init: 
            # NOTE: at init size is (20,20) because sizer is not initialized yet
            bottom = 0.12
            left   = 0.12
        else:
            if self.Size[1]<300:
                bottom=0.20
            elif self.Size[1]<350:
                bottom=0.18
            elif self.Size[1]<430:
                bottom=0.16
            elif self.Size[1]<600:
                bottom=0.13
            elif self.Size[1]<800:
                bottom=0.09
            else:
                bottom=0.07
            if self.Size[0]<300:
                left=0.22
            elif self.Size[0]<450:
                left=0.20
            elif self.Size[0]<950:
                left=0.12
            else:
                left=0.06
        #print(self.Size,'bottom', bottom, 'left',left)
        if self.cbPlotMatrix.GetValue(): # TODO detect it
            self.fig.subplots_adjust(top=0.97,bottom=bottom,left=left,right=0.98-left)
        else:
            self.fig.subplots_adjust(top=0.97,bottom=bottom,left=left,right=0.98)

    def plot_matrix_select(self, event):
        if self.infoPanel is not None:
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

    def show_hide(self,panel,bShow):
        if bShow:
            panel.Show()
            self.slEsth.Show()
        else:
            self.slEsth.Hide()
            panel.Hide()

    @property
    def sharex(self):
        return self.cbSync.IsChecked() and (not self.pltTypePanel.cbPDF.GetValue())

    def set_subplots(self,nPlots):
        self.set_subplot_spacing()
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
                        if self.infoPanel is not None:
                            self.infoPanel.setMeasurements((x, y), None)
                        self.leftMeasure.set(ax_idx, x, y)
                        self.leftMeasure.plot(ax, ax_idx)
                    elif event.button == 3:
                        if self.infoPanel is not None:
                            self.infoPanel.setMeasurements(None, (x, y))
                        self.rightMeasure.set(ax_idx, x, y)
                        self.rightMeasure.plot(ax, ax_idx)
                    else:
                        return
                    if not self.cbAutoScale.IsChecked():
                        self._restore_limits()
                        
                    if self.leftMeasure.axis_idx == self.rightMeasure.axis_idx and self.leftMeasure.axis_idx != -1:
                        self.lbDeltaX.SetLabel('dx=' + self.formatLabelValue(self.rightMeasure.x - self.leftMeasure.x))
                        self.lbDeltaY.SetLabel('dy=' + self.formatLabelValue(self.rightMeasure.y - self.leftMeasure.y))
                    else:
                        self.lbDeltaX.SetLabel('')
                        self.lbDeltaY.SetLabel('')
                    return

    def onDraw(self, event):
        self._store_limits()

    def formatLabelValue(self, value):
        try:
            if abs(value)<1000 and abs(value)>1e-4:
                s = '{:10.5f}'.format(value)
            else:
                s = '{:10.3e}'.format(value)
        except TypeError:
            s = '            '
        return s

    def removeTools(self, event=None, Layout=True):
        if self.toolPanel is not None:
            self.toolPanel.destroyData() # clean destroy of data (action callbacks)
        self.toolSizer.Clear(delete_windows=True) # Delete Windows
        if Layout:
            self.plotsizer.Layout()

    def showTool(self, toolName=''):
        from pydatview.plugins import TOOLS
        from pydatview.plugins import DATA_TOOLS # TODO remove me
        if toolName in TOOLS.keys():
            self.showToolPanel(panelClass=TOOLS[toolName])
        elif toolName in DATA_TOOLS.keys():
            self.showToolPanel(panelClass=DATA_TOOLS[toolName])
        else:
            raise Exception('Unknown tool {}'.format(toolName))

    def showToolAction(self, action):
        """ Show a tool panel based on an action"""
        self.showToolPanel(panelClass=action.guiEditorClass, action=action)

    def showToolPanel(self, panelClass=None, panel=None, action=None):
        """ Show a tool panel based on a panel class (should inherit from GUIToolPanel)"""
        self.Freeze()
        self.removeTools(Layout=False)
        if panel is not None:
            self.toolPanel=panel # use the panel directly
        else:
            if action is None:
                print('NOTE: calling a panel without action')
                self.toolPanel=panelClass(parent=self) # calling the panel constructor
            else:
                self.toolPanel=panelClass(parent=self, action=action) # calling the panel constructor
                action.guiEditorObj = self.toolPanel
        self.toolSizer.Add(self.toolPanel, 0, wx.EXPAND|wx.ALL, 5)
        self.plotsizer.Layout()
        self.Thaw()


    def setPD_PDF(self,PD,c):
        """ Convert plot data to PDF data based on GUI options"""
        # ---PDF
        nBins   = self.pdfPanel.scBins.GetValue()
        bSmooth = self.pdfPanel.cbSmooth.GetValue()
        nBins_out= PD.toPDF(nBins,bSmooth)
        if nBins_out!=nBins:
            self.pdfPanel.scBins.SetValue(nBins)

    def setPD_MinMax(self,PD):
        """ Convert plot data to MinMax data based on GUI options"""
        yScale=self.mmxPanel.cbyMinMax.IsChecked()
        xScale=self.mmxPanel.cbxMinMax.IsChecked()
        try:
            PD.toMinMax(xScale,yScale)
        except Exception as e:
            self.mmxPanel.cbxMinMax.SetValue(False)
            raise e # Used to be Warn

    def setPD_FFT(self,pd):
        """ Convert plot data to FFT data based on GUI options"""
        yType      = self.spcPanel.cbType.GetStringSelection()
        xType      = self.spcPanel.cbTypeX.GetStringSelection()
        avgMethod  = self.spcPanel.cbAveraging.GetStringSelection()
        avgWindow  = self.spcPanel.cbAveragingMethod.GetStringSelection()
        bDetrend   = self.spcPanel.cbDetrend.IsChecked()
        nExp       = self.spcPanel.scP2.GetValue()
        nPerDecade = self.spcPanel.scP2.GetValue()
        # Convert plotdata to FFT data
        try:
            Info = pd.toFFT(yType=yType, xType=xType, avgMethod=avgMethod, avgWindow=avgWindow, bDetrend=bDetrend, nExp=nExp, nPerDecade=nPerDecade) 
            # Trigger
            if hasattr(Info,'nExp') and Info.nExp!=nExp:
                self.spcPanel.scP2.SetValue(Info.nExp)
                self.spcPanel.updateP2(Info.nExp)
        except Exception as e:
            self.spcPanel.Hide();
            self.plotsizer.Layout()
            raise e


    def transformPlotData(self,PD):
        """" 
        Apply MinMax, PDF or FFT transform to plot based on GUI data
        """
        plotType=self.pltTypePanel.plotType()
        if plotType=='MinMax':
            self.setPD_MinMax(PD) 
        elif plotType=='PDF':
            self.setPD_PDF(PD,PD.c)  
        elif plotType=='FFT':
            self.setPD_FFT(PD) 

    def getPlotData(self,plotType):

        ID,SameCol,selMode=self.selPanel.getPlotDataSelection()

        self.selMode=selMode # we store the selection mode
        del self.plotData
        self.plotData=[]
        tabs=self.selPanel.tabList

        try:
            for i,idx in enumerate(ID):
                # Initialize each plotdata based on selected table and selected id channels
                pd=PlotData();
                pd.fromIDs(tabs, i, idx, SameCol, pipeline=self.pipeLike) 
                # Possible change of data
                if plotType=='MinMax':
                    self.setPD_MinMax(pd) 
                elif plotType=='PDF':
                    self.setPD_PDF(pd,pd.c)  
                elif plotType=='FFT':
                    self.setPD_FFT(pd) 
                self.plotData.append(pd)
        except Exception as e:
            self.plotData=[]
            raise e

    def PD_Compare(self,mode):
        """ Perform comparison of the selected PlotData, returns new plotData with the comparison. """
        sComp = self.cmpPanel.rbType.GetStringSelection()
        try:
            self.plotData = compareMultiplePD(self.plotData,mode, sComp)
        except Exception as e:
            self.pltTypePanel.cbRegular.SetValue(True)
            raise e

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

    def set_axes_lim(self, PDs, axis):
        """ 
        It's usually faster to set the axis limits first (before plotting) 
        and disable autoscaling. This way the limits are not recomputed when plot data are added.
        Also, we already have computed the min and max, so we leverage that. 
        NOTE: 
          doesnt not work with strings
          doesnt not work for FFT and compare 

        INPUTS:
            PDs: list of plot data
        """
        # TODO option for tight axes
        tight=False

        plotType=self.pltTypePanel.plotType()
        if plotType in ['FFT','Compare']:
            axis.autoscale(True, axis='both', tight=tight)
            return
        vXString=[PDs[i].xIsString for i in axis.iPD]
        vYString=[PDs[i].yIsString for i in axis.iPD]
        if not any(vXString) and not self.cbLogX.IsChecked():
            try:
                xMin=np.min([PDs[i]._xMin[0] for i in axis.iPD])
                xMax=np.max([PDs[i]._xMax[0] for i in axis.iPD])
                if np.isclose(xMin,xMax): 
                    delta=1 if np.isclose(xMax,0) else 0.1*xMax
                else:
                    if tight:
                        delta=0
                    else:
                        delta = (xMax-xMin)*pyplot_rc['axes.xmargin']
                axis.set_xlim(xMin-delta,xMax+delta)
                axis.autoscale(False, axis='x', tight=False)
            except:
                pass
        if not any(vYString) and not self.cbLogY.IsChecked(): 
            try:
                yMin=np.min([PDs[i]._yMin[0] for i in axis.iPD])
                yMax=np.max([PDs[i]._yMax[0] for i in axis.iPD])
                delta = (yMax-yMin)*pyplot_rc['axes.ymargin'] 
                if np.isclose(yMin,yMax): 
                    delta=1 if np.isclose(yMax,0) else 0.1*yMax
                else:
                    if tight:
                        delta=0
                    else:
                        delta = (yMax-yMin)*pyplot_rc['axes.xmargin']
                axis.set_ylim(yMin-delta,yMax+delta)
                axis.autoscale(False, axis='y', tight=False)
            except:
                pass

    def plot_all(self, keep_limits=True):
        self.multiCursors=[]

        if self.cbMeasure.GetValue() is False:
            for measure in [self.leftMeasure, self.rightMeasure]:
                measure.clear()
                if self.infoPanel is not None:
                    self.infoPanel.setMeasurements(None, None)
                self.lbDeltaX.SetLabel('')
                self.lbDeltaY.SetLabel('')

        axes=self.fig.axes
        PD=self.plotData


        # --- Plot options
        bStep    = self.cbStepPlot.IsChecked()
        plot_options = dict()
        plot_options['lw']=float(self.esthPanel.cbLW.Value)
        plot_options['ms']=float(self.esthPanel.cbMS.Value)
        if self.cbCurveType.Value=='Plain':
            plot_options['LineStyles'] = ['-']
            plot_options['Markers']    = ['']
        elif self.cbCurveType.Value=='LS':
            plot_options['LineStyles'] = ['-','--','-.',':']
            plot_options['Markers']    = ['']
        elif self.cbCurveType.Value=='Markers':
            plot_options['LineStyles'] = ['']
            plot_options['Markers']    = ['o','d','v','^','s']
        elif self.cbCurveType.Value=='Mix': # NOTE, can be improved
            plot_options['LineStyles'] = ['-','--', '-','-','-']
            plot_options['Markers']    = ['' ,''   ,'o','^','s']
        else:
            # Combination of linestyles markers, colors, etc.
            # But at that stage, if the user really want this, then we can implement an option to set styles per plot. Not high priority.
            raise Exception('Not implemented')



        # --- Font options
        font_options      = dict()
        font_options_legd = dict()
        font_options['size']          = int(self.esthPanel.cbFont.Value)  # affect labels
        font_options_legd['fontsize'] = int(self.esthPanel.cbLgdFont.Value)
        needChineseFont = any([pd.needChineseFont for pd in PD])
        if needChineseFont and self.specialFont is not None:
            font_options['fontproperties']=  self.specialFont
            font_options_legd['prop']     =  self.specialFont 

        # --- Loop on axes. Either use ax.iPD to chose the plot data, or rely on plotmatrix
        for axis_idx, ax_left in enumerate(axes):
            ax_right = None
            # Checks
            vDate=[PD[i].yIsDate for i in ax_left.iPD]
            if any(vDate) and len(vDate)>1:
                Error(self,'Cannot plot date and other value on the same axis')
                return

            # Set limit before plot when possible, for optimization
            self.set_axes_lim(PD, ax_left)

            # Actually plot
            if self.infoPanel is not None:
                pm = self.infoPanel.getPlotMatrix(PD, self.cbSub.IsChecked())
            else:
                pm = None
            __, bAllNegLeft        = self.plotSignals(ax_left, axis_idx, PD, pm, 1, bStep, plot_options)
            ax_right, bAllNegRight = self.plotSignals(ax_left, axis_idx, PD, pm, 2, bStep, plot_options)

            if self.infoPanel is not None:
                self.infoPanel.setMeasurements(self.leftMeasure.get_xydata(), self.rightMeasure.get_xydata())
            for measure in [self.leftMeasure, self.rightMeasure]:
                measure.plot(ax_left, axis_idx)

            # Log Axes
            if self.cbLogX.IsChecked():
                try:
                    ax_left.set_xscale("log", nonpositive='clip') # latest
                except:
                    ax_left.set_xscale("log", nonposx='clip') # legacy

            if self.cbLogY.IsChecked():
                if bAllNegLeft is False:
                    try:
                        ax_left.set_yscale("log", nonpositive='clip') # latest
                    except:
                        ax_left.set_yscale("log", nonposy='clip')
                if bAllNegRight is False and ax_right is not None:
                    try:
                        ax_right.set_yscale("log", nonpositive='clip') # latest
                    except:
                        ax_left.set_yscale("log", nonposy='clip') # legacy

            # XLIM - TODO FFT ONLY NASTY
            if self.pltTypePanel.cbFFT.GetValue():
                try:
                    if self.cbAutoScale.IsChecked():
                        xlim=float(self.spcPanel.tMaxFreq.GetLineText(0))
                        if xlim>0:
                                ax_left.set_xlim([0,xlim])
                                pd=PD[ax_left.iPD[0]]
                                I=pd.x<xlim
                                ymin = np.min([np.min(PD[ipd].y[I]) for ipd in ax_left.iPD])
                                ax_left.set_ylim(bottom=ymin/2)
                        if self.spcPanel.cbTypeX.GetStringSelection()=='x':
                            ax_left.invert_xaxis()
                    else:
                        self._restore_limits()
                except:
                    pass
            elif not self.cbAutoScale.IsChecked() and keep_limits:
                self._restore_limits()

            ax_left.grid(self.cbGrid.IsChecked())
            if ax_right is not None:
                l = ax_left.get_ylim()
                l2 = ax_right.get_ylim()
                f = lambda x : l2[0]+(x-l[0])/(l[1]-l[0])*(l2[1]-l2[0])
                ticks = f(ax_left.get_yticks())
                ax_right.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
                if len(ax_left.lines) == 0:
                    ax_left.set_yticks(ax_right.get_yticks())
                    ax_left.yaxis.set_visible(False)
                    ax_right.grid(self.cbGrid.IsChecked())

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
            lgdLoc = self.esthPanel.cbLegend.Value.lower()
            if (self.pltTypePanel.cbCompare.GetValue() or 
                ((len(yleft_legends) + len(yright_legends)) > 1)):
                if lgdLoc !='none':
                    if len(yleft_legends) > 0:
                        ax_left.legend(fancybox=False, loc=lgdLoc, **font_options_legd)
                if ax_right is not None and len(yright_legends) > 0:
                    ax_right.legend(fancybox=False, loc=4, **font_options_legd)
            elif len(axes)>1 and len(axes)==len(PD):
                # TODO: can this be removed? If there is only one unique signal
                # per subplot, normally only ylabel is displayed and no legend.
                # Special case when we have subplots and all plots have the same label
                if lgdLoc !='none':
                    usy = unique([pd.sy for pd in PD])
                    if len(usy)==1:
                        for ax in axes:
                            ax.legend(fancybox=False, loc=lgdLoc, **font_options_legd)

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

    def plotSignals(self, ax, axis_idx, PD, pm, left_right, is_step, opts):
        axis = None
        bAllNeg = True
        if pm is None:
            loop_range = ax.iPD
        else:
            loop_range = range(len(PD))

        iPlot=-1
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
            if do_plot:
                iPlot+=1 
                # --- styling per plot 
                if len(pd.x)==1:
                    marker='o'; ls=''
                else:
                    # TODO allow PlotData to override for "per plot" options in the future
                    marker = opts['Markers'][np.mod(iPlot,len(opts['Markers']))]
                    ls     = opts['LineStyles'][np.mod(iPlot,len(opts['LineStyles']))]
                if is_step:
                    plot = axis.step
                else:
                    plot = axis.plot
                plot(pd.x,pd.y,label=pd.syl,ms=opts['ms'], lw=opts['lw'], marker=marker, ls=ls)
                try:
                    bAllNeg = bAllNeg and all(pd.y<=0)
                except:
                    pass # Dates or strings
        return axis, bAllNeg
            
    def findPlotMode(self,PD):
        uTabs = unique([pd.it for pd in PD])
        usy   = unique([pd.sy for pd in PD])
        uiy   = unique([pd.iy for pd in PD])
        if len(uTabs)<=0:
            raise Exception('No Table. Contact developer')
        if len(uTabs)==1:
            mode='1Tab_nCols'
        else:
            if PD[0].SameCol:
                mode='nTabs_SameCols'
            else:
                # Now that we allow multiple selections detecting "simColumns" is more difficult 
                if len(uTabs) == len(PD):
                    mode='nTabs_1Col'
                elif self.selMode=='simColumnsMode':
                    mode='nTabs_SimCols'
                else:
                    mode='nTabs_mCols'
        return mode

    def findSubPlots(self,PD,mode):
        uTabs = unique([pd.it for pd in PD])
        usy   = unique([pd.sy for pd in PD])
        bSubPlots = self.cbSub.IsChecked()
        bCompare  = self.pltTypePanel.cbCompare.GetValue() # NOTE bCompare somehow always 1Tab_nCols
        nSubPlots=1
        spreadBy='none'
        if self.infoPanel is not None:
            self.infoPanel.setTabMode(mode) # TODO get rid of me
        if mode=='1Tab_nCols':
            if bSubPlots:
                if bCompare or len(uTabs)==1:
                    if self.infoPanel is not None:
                        nSubPlots = self.infoPanel.getNumberOfSubplots(PD, bSubPlots)
                    else:
                        nSubPlots=len(usy)
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
        elif mode=='nTabs_mCols':
            if bSubPlots:
                if bCompare:
                    print('>>>TODO ',mode,len(usy),len(uTabs))
                else:
                    if bCompare or len(uTabs)==1:
                        nSubPlots = self.infoPanel.getNumberOfSubplots(PD, bSubPlots)
                    else:
                        nSubPlots=len(PD)
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
        elif mode=='nTabs_mCols':
            usy=unique([pd.sy for pd in self.plotData])
            bSubPlots = self.cbSub.IsChecked()
            if bSubPlots and len(usy)==1: # spread by table name
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

    def load_and_draw(self):
        """ Full draw event: 
          - Get plot data based on selection
          - Plot them
          - Trigger changes to infoPanel
            
        """
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
        self.redraw_same_data()
        if self.infoPanel is not None:
            self.infoPanel.showStats(self.plotData,self.pltTypePanel.plotType())

    def redraw_same_data(self, keep_limits=True):
        if len(self.plotData)==0: 
            self.cleanPlot();
            return
        elif len(self.plotData) == 1:
            if self.plotData[0].xIsString or self.plotData[0].yIsString or self.plotData[0].xIsDate or self.plotData[0].yIsDate:
                self.cbAutoScale.SetValue(True)
            else:
                if len(self.xlim_prev)==0: # Might occur if some date didn't plot before (e.g. strings)
                    self.cbAutoScale.SetValue(True)
                elif rectangleOverlap(self.plotData[0]._xMin[0], self.plotData[0]._yMin[0], 
                            self.plotData[0]._xMax[0], self.plotData[0]._yMax[0],
                            self.xlim_prev[0][0], self.ylim_prev[0][0], 
                            self.xlim_prev[0][1], self.ylim_prev[0][1]):
                        pass
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
    from pydatview.Tables import TableList
    from pydatview.GUISelectionPanel import SelectionPanel

    # --- Data
    tabList   = TableList.createDummy(1)
    app = wx.App(False)
    self=wx.Frame(None,-1,"GUI Plot Panel Demo")

    # --- Panels
    self.selPanel  = SelectionPanel(self, tabList, mode='auto')
    self.plotPanel = PlotPanel(self, self.selPanel)
    self.plotPanel.load_and_draw() # <<< Important
    self.selPanel.setRedrawCallback(self.plotPanel.load_and_draw) #  Binding the two

    # --- Finalize GUI
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(self.selPanel ,0, flag = wx.EXPAND|wx.ALL,border = 5)
    sizer.Add(self.plotPanel,1, flag = wx.EXPAND|wx.ALL,border = 5)
    self.SetSizer(sizer)
    self.Center()
    self.SetSize((900, 600))
    self.Show()
    app.MainLoop()


