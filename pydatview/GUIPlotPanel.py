import os
import numpy as np
import wx
import wx.lib.buttons  as  buttons
import dateutil # required by matplotlib
#from matplotlib import pyplot as plt
import matplotlib
import matplotlib.dates as mdates
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
# from matplotlib.figure import Figure
from pydatview.figure import SwappyFigure as Figure
from matplotlib.pyplot import rcParams as pyplot_rc
from matplotlib import font_manager
from pandas.plotting import register_matplotlib_converters

import gc

from pydatview.common import * # unique, CHAR, pretty_date
from pydatview.plotdata import PlotData, compareMultiplePD 
from pydatview.plotdata import PDL_xlabel
from pydatview.GUICommon import * 
from pydatview.GUIToolBox import MyMultiCursor, MyNavigationToolbar2Wx, TBAddTool, TBAddCheckTool
from pydatview.GUIMeasure import GUIMeasure, find_closest_i
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

    def _GUI2Data(self):
        data = {'nBins':  self.scBins.GetValue(),
                'smooth': self.cbSmooth.GetValue()}
        return data

class MinMaxPanel(wx.Panel):
    def __init__(self, parent):
        super(MinMaxPanel,self).__init__(parent)
        # Data
        self.parent = parent
        self.yRef = None
        self.cbxMinMax = wx.CheckBox(self, -1, 'xMinMax',(10,10))
        self.cbyMinMax = wx.CheckBox(self, -1, 'yMinMax',(10,10))
        self.cbxMinMax.SetValue(False)
        self.cbyMinMax.SetValue(True)
        lbCentering  = wx.StaticText( self, -1, 'Y-centering:')
        self.lbyRef  = wx.StaticText( self, -1, '            ')
        self.cbyMean  = wx.ComboBox(self, choices=['None', 'Mid=0', 'Mid=ref', 'Mean=0', 'Mean=ref'], style=wx.CB_READONLY)
        #self.cbyMean  = wx.ComboBox(self, choices=['None', '0', 'Mean of means'] , style=wx.CB_READONLY)
        self.cbyMean.SetSelection(0)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.cbxMinMax ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(self.cbyMinMax ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(lbCentering    ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbyMean   ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(self.lbyRef    ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_CHECKBOX, self.onMinMaxChange)
        self.cbyMean.Bind(wx.EVT_COMBOBOX, self.onMeanChange)
        self.Hide() 

    def setYRef(self, yRef=None):
        self.yRef = yRef
        if yRef is None:
            self.lbyRef.SetLabel('')
        else:
            self.lbyRef.SetLabel('Y-ref: '+pretty_num(yRef))


    def onMinMaxChange(self, event=None):
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def onMeanChange(self, event=None):
        self.setYRef(None)
        if self.cbyMean.GetValue()=='None':
            self.cbyMinMax.Enable(True)
        else:
            self.cbyMinMax.Enable(False)
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def _GUI2Data(self):
        data={'yScale':self.cbyMinMax.IsChecked(),
              'xScale':self.cbxMinMax.IsChecked(),
              'yCenter':self.cbyMean.GetValue(),
              'yRef':self.yRef,
              }
        return data

class PolarPanel(wx.Panel):
    def __init__(self, parent):
        super(PolarPanel,self).__init__(parent)
        # Data
        self.parent = parent
        self.rRef = None
        self.cbPolarDeg      = wx.CheckBox(self, -1, 'Theta [deg]',(10,10))
        self.cbPolarBins = wx.ComboBox(self, choices=['None', '12', '36', '60', '180', '360'], style=wx.CB_READONLY)
        self.cbPolarAbout = wx.ComboBox(self, choices=['x (from z, y hori flip, z vert)', 'z (from x, x hori, y vert)'], style=wx.CB_READONLY)
        self.cbPolarSameMean = wx.CheckBox(self, -1, 'Same Mean',(10,10))
#         self.cbPolarCenter   = wx.CheckBox(self, -1, 'Center',(10,10))
        self.lbrRef  = wx.StaticText( self, -1, '            ')
        self.cbPolarDeg.SetValue(True)
        lbBins  = wx.StaticText( self, -1, 'Bins:')
        lbAbout = wx.StaticText( self, -1, 'About:')
        self.cbPolarBins.SetSelection(0)
        self.cbPolarAbout.SetSelection(0)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.cbPolarDeg      ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(lbBins               ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbPolarBins     ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(lbAbout               ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbPolarAbout     ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbPolarSameMean ,0, flag=wx.CENTER|wx.LEFT, border = 2)
#         dummy_sizer.Add(self.cbPolarCenter   ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(self.lbrRef          ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_CHECKBOX, self.onParamChange)
        self.Bind(wx.EVT_COMBOBOX, self.onParamChange)
        self.Hide() 

    def onParamChange(self, event=None):
        self.setRRef(None)
        if self.cbPolarAbout.GetValue().startswith('x'): # TODO
            self.parent.cbFlipX.SetValue(True)
        else:
            self.parent.cbFlipX.SetValue(False)
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def setRRef(self, rRef=None):
        self.rRef = rRef
        if rRef is None:
            self.lbrRef.SetLabel('')
        else:
            self.lbrRef.SetLabel('R-ref: '+pretty_num(rRef))

    def _GUI2Data(self):
        data={'Bins':self.cbPolarBins.GetValue(),
              'Deg':self.cbPolarDeg.IsChecked(),
              'About':self.cbPolarAbout.GetValue(),
              'SameMean':self.cbPolarSameMean.IsChecked(),
#               'Center':self.cbPolarCenter.IsChecked(),
              'rRef':self.rRef,
              }
        return data


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

    def _GUI2Data(self):
        data = {'type':  self.rbType.GetString(self.rbType.GetSelection())}
        return data

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


    def _GUI2Data(self):
        data = {}
        data['xType']      = self.cbTypeX.GetStringSelection()
        data['yType']      = self.cbType.GetStringSelection()
        data['avgMethod']  = self.cbAveraging.GetStringSelection()
        data['avgWindow']  = self.cbAveragingMethod.GetStringSelection()
        data['bDetrend']   = self.cbDetrend.IsChecked()
        data['nExp']       = self.scP2.GetValue()
        data['nPerDecade'] = self.scP2.GetValue()
        return data



class PlotTypePanel(wx.Panel):
    def __init__(self, parent):
        # Superclass constructor
        super(PlotTypePanel,self).__init__(parent)
        #self.SetBackgroundColour('yellow')
        # data
        self.parent   = parent # PlotPanel is parent
        # --- Ctrl Panel
        self.cbRegular = wx.RadioButton(self, -1, 'Regular',style=wx.RB_GROUP)
        self.cbPDF     = wx.RadioButton(self, -1, 'PDF'    ,                 )
        self.cbFFT     = wx.RadioButton(self, -1, 'FFT'    ,                 )
        self.cbMinMax  = wx.RadioButton(self, -1, 'MinMax' ,                 )
        self.cbCompare = wx.RadioButton(self, -1, 'Compare',                 )
        self.cbPolar   = wx.RadioButton(self, -1, 'Polar (beta)',            )
        self.cbRegular.SetValue(True)
        # BIND
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbPDF    )
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbFFT    )
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbMinMax )
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbCompare)
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbRegular)
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbPolar)
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=6, cols=1, hgap=0, vgap=0)
        cb_sizer.Add(self.cbRegular , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPDF     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFFT     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMinMax  , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbCompare , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPolar   , 0, flag=wx.ALL, border=1)
        self.SetSizer(cb_sizer)
        # Link Panels and Comboboxes 
        PTDict = {}
        PTDict['Regular']= {'opt_panel': None           ,  'cb':self.cbRegular}
        PTDict['FFT']    = {'opt_panel': parent.spcPanel,  'cb':self.cbFFT}
        PTDict['PDF']    = {'opt_panel': parent.pdfPanel,  'cb':self.cbPDF}
        PTDict['Compare']= {'opt_panel': parent.cmpPanel,  'cb':self.cbCompare}
        PTDict['MinMax'] = {'opt_panel': parent.mmxPanel,  'cb':self.cbMinMax}
        PTDict['Polar']  = {'opt_panel': parent.polPanel,  'cb':self.cbPolar}
        self.PTDict = PTDict

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
        elif self.cbPolar.GetValue():
            plotType='Polar'
        return plotType

    def plotTypeChange(self, event=None):
        self.clear_measures()
        self.parent.cleanMarkers()
        self.parent.Freeze()
        # --- Show and hide panels based on check box values
        currentPlotType=''
        for plotType, d in self.PTDict.items():
            if d['cb'].GetValue():
                currentPlotType=plotType
                if d['opt_panel'] is not None:
                    d['opt_panel'].Show()
                    d['opt_panel'].Refresh()
                    self.parent.slEsth.Show()
                else:
                    self.parent.slEsth.Hide()
            else:
                if d['opt_panel'] is not None:
                    d['opt_panel'].Hide()
        #plotType = self.plotType()
        plotType = currentPlotType
        # --- Special cases
        # Default
        self.parent.cbFlipX.SetValue(False)
        self.parent.cbLogY.SetValue(False)
        if plotType == 'Regular':
            pass
        elif plotType == 'MinMax':
            pass
        elif plotType == 'PDF':
            self.parent.cbLogX.SetValue(False)
            pass
        elif plotType == 'FFT':
            self.parent.cbLogY.SetValue(True)
        elif plotType == 'Compare':
            pass
        elif plotType == 'Polar':
            self.parent.cbLogX.SetValue(False)
            if self.parent.polPanel.cbPolarAbout.GetValue().startswith('x'): # TODO
                self.parent.cbFlipX.SetValue(True)

        self.parent.plotsizer.Layout()
        self.parent.Thaw()
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
        LWChoices = ['0.5','1.0','1.25','1.5','1.75','2.0','2.5','3.0']
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

        # Store data
        self.data={}
        self._GUI2Data()

    def onAnyEsthOptionChange(self,event=None):
        self.parent.redraw_same_data()

    def onFontOptionChange(self,event=None):
        matplotlib_rc('font', **{'size':int(self.cbFont.Value) }) # affect all (including ticks)
        self.onAnyEsthOptionChange()

    def _GUI2Data(self):
        """ data['plotStyle'] """
        self.data['Font']           = int(self.cbFont.GetValue())
        self.data['LegendFont']     = int(self.cbLgdFont.GetValue())
        self.data['LegendPosition'] = self.cbLegend.GetValue()
        self.data['LineWidth']      = float(self.cbLW.GetValue())
        self.data['MarkerSize']     = float(self.cbMS.GetValue())
        return self.data


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
        self.subplotsPar=None
        self.plotDone=False
        if data is not None:
            self.data  = data
        else:
            self.data = self.defaultData()
        if self.selPanel is not None:
            bg=self.selPanel.BackgroundColour
            self.SetBackgroundColour(bg) # sowhow, our parent has a wrong color
        #self.SetBackgroundColour('red')
        self.leftMeasure = GUIMeasure(1, 'firebrick')
        self.rightMeasure = GUIMeasure(2, 'darkgreen')
        self.markers = [] # List of GUIMeasures
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

        self.navTBTop    = MyNavigationToolbar2Wx(self.canvas, ['Home', 'Pan'], plotPanel=self)
        self.navTBBottom = MyNavigationToolbar2Wx(self.canvas, ['Subplots', 'Save'], plotPanel=self)
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
        # --- Plot type specific options
        self.spcPanel = SpectralCtrlPanel(self)
        self.pdfPanel = PDFCtrlPanel(self)
        self.cmpPanel = CompCtrlPanel(self)
        self.mmxPanel = MinMaxPanel(self)
        self.polPanel = PolarPanel(self)
        # --- PlotType Panel (Needs the different pansel above)
        self.pltTypePanel= PlotTypePanel(self);

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
        self.cbMarkPt     = wx.CheckBox(self.ctrlPanel, -1, 'Mark Points',(10,10))
        self.cbSwapXY     = wx.CheckBox(self.ctrlPanel, -1, 'Swap XY',(10,10))
        self.cbFlipX      = wx.CheckBox(self.ctrlPanel, -1, 'Flip X',(10,10))
        self.cbFlipY      = wx.CheckBox(self.ctrlPanel, -1, 'Flip Y',(10,10))
        #self.cbSub.SetValue(True) # DEFAULT TO SUB?
        self.cbSync.SetValue(True)
        self.cbXHair.SetValue(self.data['CrossHair']) # Have cross hair by default
        self.cbAutoScale.SetValue(True)
        self.cbGrid.SetValue(self.data['Grid'])
        # BIND - Callbacks
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSub    )
        self.Bind(wx.EVT_COMBOBOX, self.redraw_event     , self.cbCurveType)
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogX   )
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogY   )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSync )
        self.Bind(wx.EVT_CHECKBOX, self.crosshair_event  , self.cbXHair )
        self.Bind(wx.EVT_CHECKBOX, self.plot_matrix_event, self.cbPlotMatrix )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbAutoScale )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbGrid )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbStepPlot )
        self.Bind(wx.EVT_CHECKBOX, self.measure_event    , self.cbMeasure )
        self.Bind(wx.EVT_CHECKBOX, self.markpt_event     , self.cbMarkPt )
        self.Bind(wx.EVT_CHECKBOX, self.swap_event       , self.cbSwapXY )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbFlipX )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbFlipY )
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=5, cols=3, hgap=0, vgap=0)
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
        cb_sizer.Add(self.cbMarkPt    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSwapXY    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFlipX     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFlipY     , 0, flag=wx.ALL, border=1)

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
        plotsizer.Add(self.polPanel ,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slEsth   ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.esthPanel,0,flag = wx.EXPAND|wx.CENTER|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slCtrl   ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(row_sizer     ,0,flag = wx.EXPAND|wx.NORTH ,border = 2)

        self.SetSizer(plotsizer)
        self.plotsizer=plotsizer;
#         self.setSubplotSpacing(init=True)

    # --- Bindings/callback
    def setAddTablesCallback(self, callback):
        self.addTablesCallback = callback

    def addTables(self, *args, **kwargs):
        if self.addTablesCallback is not None:
            self.addTablesCallback(*args, **kwargs)
        else:
            print('[WARN] callback to add tables to parent was not set. (call setAddTablesCallback)')


    # --- GUI DATA
    def saveData(self, data):
        data['Grid']      = self.cbGrid.IsChecked()
        data['CrossHair'] = self.cbXHair.IsChecked()
        self.esthPanel._GUI2Data()
        data['plotStyle']= self.esthPanel.data
        
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
        self.Freeze()
        if self.esthToggle:
            self.slCtrl.Show()
            self.esthPanel.Show()
        else:
            self.slCtrl.Hide()
            self.esthPanel.Hide()
        self.plotsizer.Layout()
        self.Thaw()
        event.Skip()

    def setSubplotSpacing(self, init=False, tight=False):
        """ 
        Handle default subplot spacing

        NOTE:
           - Tight fails when the ylabel is too long, especially for fft with multiplt signals
           - might need to change depending on window size/resizing
           - need to change if right axis needed 
           - this will override the user settings
        """
        if tight: 
            self.setSubplotTight(draw=False)
            return

        if init: 
            subplotsParLoc={'bottom':0.12, 'top':0.97, 'left':0.12, 'right':0.98}
            self.fig.subplots_adjust(**subplotsParLoc)
            return

        if self.subplotsPar is not None:
            if self.cbPlotMatrix.GetValue(): # TODO detect it
                self.subplotsPar['right'] = 0.98 - self.subplotsPar['left']
            # See GUIToolBox.py configure_toolbar
            self.fig.subplots_adjust(**self.subplotsPar)
            return
        else:
            self.setSubplotTight(draw=False)

    def setSubplotTight(self, draw=True):
        self.fig.tight_layout()
        self.subplotsPar = self.getSubplotSpacing()

        # --- Ensure some minimum spacing based on panel size
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

        self.subplotsPar['left']   = max(self.subplotsPar['left']  , left)
        self.subplotsPar['bottom'] = max(self.subplotsPar['bottom'], bottom)
        self.subplotsPar['top']    = min(self.subplotsPar['top']   , 0.97)
        self.subplotsPar['right']  = min(self.subplotsPar['right'] , 0.995)
        self.fig.subplots_adjust(**self.subplotsPar)
        if draw:
            self.canvas.draw()

    def getSubplotSpacing(self):
        try:
            params = self.fig.subplotpars
            paramsD= {}
            for key in ['left', 'bottom', 'right', 'top', 'wspace', 'hspace']:
                paramsD[key]=getattr(params, key)
            return paramsD
        except:
            return None # At Init we don't have a figure

    def plot_matrix_event(self, event):
        if self.cbSwapXY.IsChecked():
            print('[WARN] Cant have plot Matrix and Swap XY for now')
            self.cbSwapXY.SetValue(False)

        if self.infoPanel is not None:
            self.infoPanel.togglePlotMatrix(self.cbPlotMatrix.GetValue())
        self.redraw_same_data()

    def swap_event(self, event):
        if self.cbPlotMatrix.IsChecked():
            print('[WARN] Cant have plot Matrix and Swap XY for now')
            self.cbPlotMatrix.SetValue(False)
            self.infoPanel.togglePlotMatrix(False)

        self.redraw_same_data()

    def measure_event(self, event):
        if self.cbMeasure.IsChecked():
            # Can't measure and Mark points at the same time
            self.cbMarkPt.SetValue(False) 
            self.cleanMarkers()
            # We do nothing, onMouseRelease will trigger the plot and setting
        else:
            self.cleanMeasures()
        # We redraw after cleaning (measures or markers)
        self.redraw_same_data()

    def setAndPlotMeasures(self, ax, x, y, which=None):
        if which is None:
            which=[1,2]
        if not hasattr(ax, 'PD'):
            print('[WARN] Cannot measure on an empty plot')
            return
        if 1 in which:
            # Left click, measure 1 - set values, compute all intersections and plot
            self.leftMeasure.set(ax, x, y) 
            if self.infoPanel is not None:
                self.infoPanel.showMeasure1()
        if 2 in which:
            # Right click, measure 2 - set values, compute all intersections and plot
            self.rightMeasure.set(ax, x, y)
            if self.infoPanel is not None:
                self.infoPanel.showMeasure2()
        self.plotMeasures(which=which)

    def plotMeasures(self, which=None):
        if which is None:
            which=[1,2]
        ## plot them
        if 1 in which:
            self.leftMeasure.plot (self.fig.axes, self.plotData)
        if 2 in which:
            self.rightMeasure.plot(self.fig.axes, self.plotData)
        ## Update dx,dy label
        self.lbDeltaX.SetLabel(self.rightMeasure.sDeltaX(self.leftMeasure))
        self.lbDeltaY.SetLabel(self.rightMeasure.sDeltaY(self.leftMeasure))

        #if not self.cbAutoScale.IsChecked():
        #    print('>>> On Mouse Release Restore LIMITS')
        #    self._restore_limits()
        #else:
        #    print('>>> On Mouse Release Not Restore LIMITS')
        # Update label

    def cleanMeasures(self):
        # We clear
        for measure in [self.leftMeasure, self.rightMeasure]:
            measure.clear()
        if self.infoPanel is not None:
            self.infoPanel.clearMeasurements()
        # Update dx,dy label
        self.lbDeltaX.SetLabel('')
        self.lbDeltaY.SetLabel('')

    def markpt_event(self, event):

        if self.cbMarkPt.IsChecked():
            # Can't measure and Mark points at the same time
            self.cbMeasure.SetValue(False) 
            self.cleanMeasures()
            # We do nothing, onMouseRelease will trigger the plot and setting
            self.markers = [] 
        else:
            self.cleanMarkers()
        # We redraw after cleaning markesr or measures
        self.redraw_same_data()

    def plotMarkers(self):
        for marker in self.markers:
            marker.plot (self.fig.axes, self.plotData)

    def cleanMarkers(self):
        # We clear
        for marker in self.markers:
            marker.clear()
        self.markers=[]

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
                # Store first axis to share with other
                if self.sharex:
                    sharex=ax
            else:
                if self.cbSwapXY.IsChecked():
                    ax=self.fig.add_subplot(nPlots,1,i+1, sharey=sharex)
                else:
                    ax=self.fig.add_subplot(nPlots,1,i+1, sharex=sharex)
            # Horizontal stack
            #self.fig.add_subplot(1,nPlots,i+1)

    def onMouseMove(self, event):
        if event.inaxes and len(self.plotData)>0:
            x, y = event.xdata, event.ydata
            self.lbCrossHairX.SetLabel('x =' + self.formatLabelValue(x,self.plotData[0].xIsDate))
            self.lbCrossHairY.SetLabel('y =' + self.formatLabelValue(y,self.plotData[0].yIsDate))

    def onMouseClick(self, event):
        self.clickLocation = (event.inaxes, event.xdata, event.ydata)

    def onMouseRelease(self, event):
        if self.cbMeasure.GetValue():
            # --- Measures
            # Loop on axes
            for iax, ax in enumerate(self.fig.axes):
                if event.inaxes == ax:
                    x, y = event.xdata, event.ydata
                    if self.clickLocation != (ax, x, y):
                        # Ignore measurements for zoom-actions. Possibly add small tolerance.
                        # Zoom-actions disable autoscale
                        #self.cbAutoScale.SetValue(False)
                        return
                    if self.cbSwapXY.IsChecked():
                        x, y = y, x
                    if event.button == 1:
                        which =[1] # Left click, measure 1
                    elif event.button == 3:
                        which =[2] # Right click, measure 2
                    else:
                        return
                    self.setAndPlotMeasures(ax, x, y, which)
                    return # We return as soon as one ax match the click location
        elif self.cbMarkPt.GetValue():
            # --- Markers
            for iax, ax in enumerate(self.fig.axes):
                if event.inaxes == ax:
                    x, y = event.xdata, event.ydata
                    if self.clickLocation != (ax, x, y):
                        return
                    if self.cbSwapXY.IsChecked():
                        x, y = y, x
                    if event.button == 1:
                        # We add a marker
                        from pydatview.tools.colors import fColrs, python_colors
                        n = len(self.markers)
                        IDs = set([m.ID for m in self.markers])
                        All = set(np.arange(1,n+2))
                        ID = list(All.difference(IDs))[0] # Should be only of size 1
                        #marker = GUIMeasure(1, python_colors(n+1), ID=ID)
                        marker = GUIMeasure(1, fColrs(ID, cmap='darker'), ID=ID)
                        #marker = GUIMeasure(1, 'firebrick', ID=ID)
                        #GUIMeasure(2, 'darkgreen')
                        self.markers.append(marker)
                        marker.setAndPlot(self.fig.axes, ax, x, y, self.plotData)
                    elif event.button == 3:
                        # find the closest marker
                        XY = np.array([m.P_target_raw for m in self.markers])
                        i = find_closest_i(XY, (x,y))
                        # We clear it fomr the plot
                        self.markers[i].clear()
                        # We delete it
                        del self.markers[i]
                    else:
                        return

    def onDraw(self, event):
        self._store_limits()

    def formatLabelValue(self, value, isdate):
        try:
            if isdate:
                s = pretty_date(mdates.num2date(value))
            elif abs(value)<1000 and abs(value)>1e-4:
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
        if toolName in TOOLS.keys():
            self.showToolPanel(panelClass=TOOLS[toolName])
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
        data = self.pdfPanel._GUI2Data()
        nBins_out= PD.toPDF(**data)
        if nBins_out != data['nBins']:
            self.pdfPanel.scBins.SetValue(data['nBins'])

    def setPD_MinMax(self, PD, firstCall=False):
        """ Convert plot data to MinMax data based on GUI options"""
        data = self.mmxPanel._GUI2Data()
        if data['yCenter'] in ['Mean=ref', 'Mid=ref']:
            if firstCall:
                try:
                    data['yRef'] = PD._y0Mean[0] # Will fail for strings
                    if np.isnan(data['yRef']): # Will fail for datetimes
                        data['yRef'] = 0
                except:
                    data['yRef'] = 0
                    print('[WARN] Fail to get yRef, setting it to 0')
                self.mmxPanel.setYRef(data['yRef']) # Update GUI
        try:
            PD.toMinMax(**data)
        except Exception as e:
            self.mmxPanel.cbxMinMax.SetValue(False)
            raise e # Used to be Warn

    def setPD_FFT(self, PD):
        """ Convert plot data to FFT data based on GUI options"""
        data = self.spcPanel._GUI2Data()
        # Convert plotdata to FFT data
        try:
            Info = PD.toFFT(**data) 
            # Trigger
            if hasattr(Info,'nExp') and Info.nExp!=data['nExp']:
                self.spcPanel.scP2.SetValue(Info.nExp)
                self.spcPanel.updateP2(Info.nExp)
        except Exception as e:
            self.spcPanel.Hide();
            self.plotsizer.Layout()
            raise e

    def setPD_Polar(self, PD, firstCall=False):
        """ Convert plot data to Polar data based on GUI options"""
        data = self.polPanel._GUI2Data()
        if data['SameMean'] and firstCall:
            try:
                data['rRef'] = PD._y0Mean[0] # Will fail for strings
                if np.isnan(data['rRef']): # Will fail for datetimes
                    data['rRef'] = 0
            except:
                data['rRef'] = 0
                print('[WARN] Fail to get yRef, setting it to 0')
            self.polPanel.setRRef(data['rRef']) # Update GUI

        PD.toPolar(**data)


    def transformPlotData(self, PD, firstCall=False):
        """" 
        Apply MinMax, PDF or FFT transform to plot based on GUI data
        """
        plotType=self.pltTypePanel.plotType()
        if plotType=='MinMax':
            self.setPD_MinMax(PD, firstCall=firstCall) 
        elif plotType=='PDF':
            self.setPD_PDF(PD, PD.c)  
        elif plotType=='FFT':
            self.setPD_FFT(PD) 
        elif plotType=='Polar':
            self.setPD_Polar(PD, firstCall=firstCall) 

    def getPlotData(self, plotType=None):
        if plotType is None:
            plotType = self.pltTypePanel.plotType()

        ID,SameCol,selMode=self.selPanel.getPlotDataSelection()

        self.selMode=selMode # we store the selection mode
        del self.plotData
        self.plotData=[]
        tabs=self.selPanel.tabList

        try:
            for i,idx in enumerate(ID):
                # Initialize each plotdata based on selected table and selected id channels
                PD = PlotData();
                PD.fromIDs(tabs, i, idx, SameCol, pipeline=self.pipeLike) 
                self.transformPlotData(PD, firstCall=i==0)
                self.plotData.append(PD)
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

    def set_axes_lim(self, PDs, axis, plotType='Regular'):
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
        def getDelta(xMin, xMax):
            delta = xMax-xMin
            if delta==0:
                delta=1
            else:
            #    if tight:
            #        delta=0
            #    else:
                delta = delta*pyplot_rc['axes.xmargin']
            return delta

        tight=False
        if plotType in ['FFT','Compare']:
            axis.autoscale(True, axis='both', tight=tight)
            return
        elif plotType =='Polar':
            axis.set_aspect('equal', adjustable='box')
            xMin=np.min([PDs[i]._xMin[0] for i in axis.iPD])
            xMax=np.max([PDs[i]._xMax[0] for i in axis.iPD])
            yMin=np.min([PDs[i]._yMin[0] for i in axis.iPD])
            yMax=np.max([PDs[i]._yMax[0] for i in axis.iPD])
            xMax =  max (abs(xMin), abs(xMax))
            yMax =  max (abs(yMin), abs(yMax))
            Max  =  max (abs(xMax), abs(yMax))
            Min = -Max
            delta = getDelta(Min, Max)
            axis.set_xlim_(Min-delta, Max+delta)
            axis.set_ylim_(Min-delta, Max+delta)
            axis.autoscale(False, axis='x', tight=False)
            axis.autoscale(False, axis='y', tight=False)
            return 

        vXString=[PDs[i].xIsString for i in axis.iPD]
        vYString=[PDs[i].yIsString for i in axis.iPD]
        if not any(vXString) and not self.cbLogX.IsChecked():
            try:
                xMin=np.min([PDs[i]._xMin[0] for i in axis.iPD])
                xMax=np.max([PDs[i]._xMax[0] for i in axis.iPD])
                delta = getDelta(xMin, xMax)
                axis.set_xlim_(xMin-delta,xMax+delta)
                axis.autoscale(False, axis='x', tight=False)
            except:
                pass
        if not any(vYString) and not self.cbLogY.IsChecked(): 
            try:
                yMin=np.min([PDs[i]._yMin[0] for i in axis.iPD])
                yMax=np.max([PDs[i]._yMax[0] for i in axis.iPD])
                delta = (yMax-yMin)
                # Old behavior
                if np.isclose(yMin,yMax): 
                    # NOTE: by using 10% of yMax we usually avoid having the "mean" written at
                    #   the top of the script
                    delta=1 if np.isclose(yMax,0) else 0.1*yMax
                else:
                    delta = delta*pyplot_rc['axes.xmargin']
#                 if delta==0:
#                     # If delta is zero, we extend the bounds to "readable" values
#                     yMean = (yMax+yMin)/2
#                     if abs(yMean)>1e-6:
#                         delta = 0.05*yMean
#                     else:
#                         delta = 1
#                 elif abs(yMin)>1e-6:
#                     delta_rel = delta/abs(yMin)
#                     if delta<1e-5:
#                         delta = 0.1
#                     elif delta_rel<1e-5:
#                         # we set a delta such that the numerical fluctuations are visible but
#                         # it's obvious that it's still a "constant" signal
#                         delta = 100*delta 
#                     else:
#                         delta = delta*pyplot_rc['axes.xmargin']
#                 else:
#                     if delta<1e-5:
#                         delta = 1
#                     else:
#                         delta = delta*pyplot_rc['axes.xmargin']
                axis.set_ylim_(yMin-delta,yMax+delta)
                axis.autoscale(False, axis='y', tight=False)
            except:
                pass

    def getPlotOptions(self, PD=None):
        # --- PlotStyles
        plotStyle = self.esthPanel._GUI2Data()

        # --- Plot options
        plot_options = dict()
        plot_options['step'] = self.cbStepPlot.IsChecked()
        plot_options['swapXY'] = self.cbSwapXY.IsChecked()
        plot_options['flipX'] = self.cbFlipX.IsChecked()
        plot_options['flipY'] = self.cbFlipY.IsChecked()
        plot_options['logX'] = self.cbLogX.IsChecked()
        plot_options['logY'] = self.cbLogY.IsChecked()
        if self.cbGrid.IsChecked():
            plot_options['grid'] = {'visible': self.cbGrid.IsChecked(), 'linestyle':'-', 'linewidth':0.5, 'color':'#b0b0b0'}
        else:
            plot_options['grid'] = {'visible': False}
        #plot_options['tick_params'] = {'direction':'in', 'top':True, 'right':True, 'labelright':False, 'labeltop':False, 'which':'both'}
        plot_options['tick_params'] = {}

        plot_options['lw']=plotStyle['LineWidth']
        plot_options['ms']=plotStyle['MarkerSize']
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
        font_options['size']          = plotStyle['Font']
        font_options_legd['fontsize'] = plotStyle['LegendFont']
        if PD is not None:
            needChineseFont = any([pd.needChineseFont for pd in PD])
            if needChineseFont and self.specialFont is not None:
                font_options['fontproperties']=  self.specialFont
                font_options_legd['prop']     =  self.specialFont 

        return plotStyle, plot_options, font_options, font_options_legd



    def plot_all(self, autoscale=True):
        """ 
        autoscale: if True, find the limits based on the data.
                  Otherwise, the limits are restored using:
                     self._restore_limits and the variables: self.xlim_prev, self.ylim_prev
        """
        self.multiCursors=[]

        axes=self.fig.axes
        PD=self.plotData

        # --- PlotStyles
        plotType = self.pltTypePanel.plotType()
        plotStyle, plot_options, font_options, font_options_legd = self.getPlotOptions()

        # --- Loop on axes. Either use ax.iPD to chose the plot data, or rely on plotmatrix
        for axis_idx, ax_left in enumerate(axes):
            ax_right = None
            # Swap XY
            ax_left.setSwap(plot_options['swapXY'])
            # Checks
            vDate=[PD[i].yIsDate for i in ax_left.iPD]
            if any(vDate) and len(vDate)>1:
                Error(self,'Cannot plot date and other value on the same axis')
                return

            # Set limit before plot when possible, for optimization
            self.set_axes_lim(PD, ax_left, plotType)

            # Actually plot
            if self.infoPanel is not None:
                pm = self.infoPanel.getPlotMatrix(PD, self.cbSub.IsChecked())
            else:
                pm = None
            __, bAllNegLeft        = self.plotSignals(ax_left, axis_idx, PD, pm, 1, plot_options)
            ax_right, bAllNegRight = self.plotSignals(ax_left, axis_idx, PD, pm, 2, plot_options)

            # Log Axes
            if plot_options['logX']:
                try:
                    ax_left.set_xscale("log", nonpositive='clip') # latest
                except:
                    ax_left.set_xscale("log", nonposx='clip') # legacy

            if plot_options['logY']:
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

            if not autoscale:
                # We force the limits to be the same as before
                self._restore_limits()
            elif self.pltTypePanel.cbFFT.GetValue():
                # XLIM - TODO FFT ONLY NASTY
                try:
                    xlim=float(self.spcPanel.tMaxFreq.GetLineText(0))
                    if xlim>0:
                            ax_left.set_xlim_([0,xlim])
                            pd=PD[ax_left.iPD[0]]
                            I=pd.x<xlim
                            ymin = np.min([np.min(PD[ipd].y[I]) for ipd in ax_left.iPD])
                            ax_left.set_ylim_(bottom=ymin/2)
                    if self.spcPanel.cbTypeX.GetStringSelection()=='x':
                        ax_left.invert_xaxis()
                except:
                    pass

            # --- Grid
            if plotType=='Polar':
                if plot_options['grid']['visible']:
                    vr = np.unique(np.abs(ax_left.get_xticks()))
                    grid_opts = plot_options['grid'].copy()
                    del grid_opts['visible']
                    # Temporary grid, might use a Polar plot in the future...
                    th = np.linspace(0,2*np.pi, 60)
                    for r in vr:
                        ax_left.plot(r*np.cos(th), r*np.sin(th), **grid_opts)
                    ax_left.plot([-r,r],[0,0], **grid_opts)
                    ax_left.plot([0,0],[-r,r], **grid_opts)
            else:
                ax_left.grid(**plot_options['grid'])
                if ax_right is not None:
                    l = ax_left.get_ylim_()
                    l2 = ax_right.get_ylim_()
                    f = lambda x : l2[0]+(x-l[0])/(l[1]-l[0])*(l2[1]-l2[0])
                    ticks = f(ax_left.get_yticks())
                    ax_right.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
                    if len(ax_left.lines) == 0:
                        ax_left.set_yticks(ax_right.get_yticks())
                        ax_left.yaxis.set_visible(False)
                        ax_right.grid(**plot_options['grid'])
            # Flip
            if plot_options['flipX']:
                ax_left.invert_xaxis()
            if plot_options['flipY']:
                ax_left.invert_yaxis()

            # TODO put this in set_axes_lim
            if plotType=='Compare':
                if self.cmpPanel.rbType.GetStringSelection()=='Y-Y':
                    xmin,xmax=ax_left.get_xlim_()

            # Ticks
            ax_left.tick_params(**plot_options['tick_params'])
            if ax_right is not None:
                ax_right.tick_params(**plot_options['tick_params'])

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
            lgdLoc = plotStyle['LegendPosition'].lower()
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

        # --- End loop on axes
        # --- Measure: Done as an overlay in plotMeasures

        # --- xlabel
        #axes[-1].set_xlabel(PD[axes[-1].iPD[0]].sx, **font_options)
        axes[-1].set_xlabel(PDL_xlabel(PD), **font_options)

        #print('sy :',[pd.sy for pd in PD])
        #print('syl:',[pd.syl for pd in PD])

        # --- Cursors for each individual plot
        # NOTE: cursors needs to be stored in the object!
        #for ax_left in self.fig.axes:
        #    self.cursors.append(MyCursor(ax_left,horizOn=True, vertOn=False, useblit=True, color='gray', linewidth=0.5, linestyle=':'))
        # Vertical cusor for all, commonly
        bXHair = self.cbXHair.GetValue()
        self.multiCursors = MyMultiCursor(self.canvas, tuple(self.fig.axes), useblit=True, horizOn=bXHair, vertOn=bXHair, color='gray', linewidth=0.5, linestyle=':')

    def plotSignals(self, ax, axis_idx, PD, pm, left_right, opts):
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
                if opts['step']:
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
        # Use PD
        for ax in axes:
            ax.PD=[self.plotData[i] for i in ax.iPD]

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
        if self.plotDone:
            self.subplotsPar = self.getSubplotSpacing()
        else:
            self.subplotsPar = None
        self.clean_memory()
        self.getPlotData()
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
        self.plotDone=True

    def redraw_same_data(self, force_autoscale=False):
        """ 
         - force_autoscale: if True, for the plot area to autoscale
                This is used when the user click on "Home"

        """
        if len(self.plotData)==0: 
            self.cleanPlot();
            return
        elif len(self.plotData) == 1:
            if self.plotData[0].xIsString or self.plotData[0].yIsString: 
                # or self.plotData[0].xIsDate or self.plotData[0].yIsDate:
                self.cbAutoScale.SetValue(True)
            else:
                if len(self.xlim_prev)==0: # Might occur if some date didn't plot before (e.g. strings)
                    self.cbAutoScale.SetValue(True)
                # KEEP ME below, check if plot data is within a given rectangle
                # If no plot data is present in the window 
                #elif not rectangleOverlap(self.plotData[0]._xMin[0], self.plotData[0]._yMin[0], 
                #            self.plotData[0]._xMax[0], self.plotData[0]._yMax[0],
                #            self.xlim_prev[0][0], self.ylim_prev[0][0], 
                #            self.xlim_prev[0][1], self.ylim_prev[0][1]):
                #    self.cbAutoScale.SetValue(True)

        mode=self.findPlotMode(self.plotData)
        nPlots,spreadBy=self.findSubPlots(self.plotData,mode)

        self.clean_memory_plot()
        self.set_subplots(nPlots)
        self.distributePlots(mode,nPlots,spreadBy)
        self.setSubplotSpacing()

        if not self.pltTypePanel.cbCompare.GetValue():
            self.setLegendLabels(mode)

        autoscale = (self.cbAutoScale.IsChecked()) or (force_autoscale)
        self.plot_all(autoscale=autoscale)
        self.plotMarkers()
        self.canvas.draw()


    def _store_limits(self):
        self.xlim_prev = []
        self.ylim_prev = []
        for ax in self.fig.axes:
            self.xlim_prev.append(ax.get_xlim_())
            self.ylim_prev.append(ax.get_ylim_())

    def _restore_limits(self):
        for ax, xlim, ylim in zip(self.fig.axes, self.xlim_prev, self.ylim_prev):
            ax.set_xlim_(xlim)
            ax.set_ylim_(ylim)

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


