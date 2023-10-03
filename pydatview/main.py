import numpy as np
import os.path 
import sys
import traceback 
import gc
try:
    import pandas as pd
except:
    print('')
    print('')
    print('Error: problem loading pandas package:')
    print('  - Check if this package is installed ( e.g. type: `pip install pandas`)')
    print('  - If you are using anaconda, try `conda update python.app`')
    print('  - If none of the above work, contact the developer.')
    print('')
    print('')
    sys.exit(-1)
    #raise


#  GUI
import wx
from .GUIPlotPanel import PlotPanel
from .GUISelectionPanel import SelectionPanel,SEL_MODES,SEL_MODES_ID
from .GUISelectionPanel import ColumnPopup,TablePopup
from .GUIInfoPanel import InfoPanel
from .GUIPipelinePanel import PipelinePanel
from .GUIToolBox import GetKeyString, TBAddTool
from .Tables import TableList, Table
# Helper
from .common import *
from .GUICommon import *
import pydatview.io as weio # File Formats and File Readers
# Pluggins
from .plugins import DATA_PLUGINS_WITH_EDITOR, DATA_PLUGINS_SIMPLE, TOOLS
from .plugins import OF_DATA_PLUGINS_WITH_EDITOR, OF_DATA_PLUGINS_SIMPLE
from .appdata import loadAppData, saveAppData, configFilePath, defaultAppData

# --------------------------------------------------------------------------------}
# --- GLOBAL 
# --------------------------------------------------------------------------------{
PROG_NAME='pyDatView'
PROG_VERSION='v0.3-local'
SIDE_COL       = [160,160,300,420,530]
SIDE_COL_LARGE = [200,200,360,480,600]
BOT_PANL =85
ISTAT = 0 # Index of Status bar where main status info is provided

#matplotlib.rcParams['text.usetex'] = False
# matplotlib.rcParams['font.sans-serif'] = 'DejaVu Sans'
#matplotlib.rcParams['font.family'] = 'Arial'
#matplotlib.rcParams['font.sans-serif'] = 'Arial'
# matplotlib.rcParams['font.family'] = 'sans-serif'





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
      filenames.sort()
      if len(filenames)>0:
          # If Ctrl is pressed we add
          bAdd= wx.GetKeyState(wx.WXK_CONTROL);
          iFormat=self.parent.comboFormats.GetSelection()
          if iFormat==0: # auto-format
              Format = None
          else:
              Format = self.parent.FILE_FORMATS[iFormat-1]
          self.parent.load_files(filenames, fileformats=[Format]*len(filenames), bAdd=bAdd, bPlot=True)
      return True


# --------------------------------------------------------------------------------}
# --- Loader Menu 
# --------------------------------------------------------------------------------{
class LoaderMenuPopup(wx.Menu):
    def __init__(self, parent, data):
        wx.Menu.__init__(self)
        self.parent = parent 
        self.data = data 

        # Populate menu
        item = wx.MenuItem(self, -1, "Date format: dayfirst", kind=wx.ITEM_CHECK)
        self.Append(item)
        self.Bind(wx.EVT_MENU, lambda ev: self.setCheck(ev, 'dayfirst') )
        self.Check(item.GetId(), self.data['dayfirst']) # Checking the menu box

    def setCheck(self, event, label):
        self.data['dayfirst'] = not self.data['dayfirst']


# --------------------------------------------------------------------------------}
# --- Main Frame  
# --------------------------------------------------------------------------------{
class MainFrame(wx.Frame):
    def __init__(self, data=None):
        # Parent constructor
        wx.Frame.__init__(self, None, -1, PROG_NAME+' '+PROG_VERSION)
        # Hooking exceptions to display them to the user
        sys.excepthook = MyExceptionHook
        # --- Data
        self.restore_formulas = []
        self.systemFontSize = self.GetFont().GetPointSize()
        self.data = loadAppData(self)
        self.tabList=TableList(options=self.data['loaderOptions'])
        self.datareset = False
        self.resized = False # used to trigger a tight layout after resize event
        # Global variables...
        setFontSize(self.data['fontSize'])
        setMonoFontSize(self.data['monoFontSize'])

        # --- GUI
        #font = self.GetFont()
        #print(font.GetFamily(),font.GetStyle(),font.GetPointSize())
        #font.SetFamily(wx.FONTFAMILY_DEFAULT)
        #font.SetFamily(wx.FONTFAMILY_MODERN)
        #font.SetFamily(wx.FONTFAMILY_SWISS)
        #font.SetPointSize(8)
        #print(font.GetFamily(),font.GetStyle(),font.GetPointSize())
        #self.SetFont(font) 
        self.SetFont(getFont(self))
        # --- Menu
        menuBar = wx.MenuBar()

        fileMenu = wx.Menu()
        loadMenuItem  = fileMenu.Append(wx.ID_NEW,"Open file" ,"Open file"           )
        scrpMenuItem  = fileMenu.Append(-1        ,"Export script" ,"Export script"           )
        exptMenuItem  = fileMenu.Append(-1        ,"Export table" ,"Export table"           )
        saveMenuItem  = fileMenu.Append(wx.ID_SAVE,"Save figure" ,"Save figure"           )
        exitMenuItem  = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
        menuBar.Append(fileMenu, "&File")
        self.Bind(wx.EVT_MENU,self.onExit  ,exitMenuItem)
        self.Bind(wx.EVT_MENU,self.onLoad  ,loadMenuItem)
        self.Bind(wx.EVT_MENU,self.onScript,scrpMenuItem)
        self.Bind(wx.EVT_MENU,self.onExport,exptMenuItem)
        self.Bind(wx.EVT_MENU,self.onSave  ,saveMenuItem)

        # --- Data Plugins
        # NOTE: very important, need "s_loc" otherwise the lambda function take the last toolName
        dataMenu = wx.Menu()
        menuBar.Append(dataMenu, "&Data")
        for toolName in DATA_PLUGINS_WITH_EDITOR.keys():
            self.Bind(wx.EVT_MENU, lambda e, s_loc=toolName: self.onDataPlugin(e, s_loc), dataMenu.Append(wx.ID_ANY, toolName))

        for toolName in DATA_PLUGINS_SIMPLE.keys():
            self.Bind(wx.EVT_MENU, lambda e, s_loc=toolName: self.onDataPlugin(e, s_loc), dataMenu.Append(wx.ID_ANY, toolName))

        # --- Tools Plugins
        toolMenu = wx.Menu()
        menuBar.Append(toolMenu, "&Tools")
        for toolName in TOOLS.keys():
            self.Bind(wx.EVT_MENU, lambda e, s_loc=toolName: self.onShowTool(e, s_loc), toolMenu.Append(wx.ID_ANY, toolName))

        # --- OpenFAST Plugins
        ofMenu = wx.Menu()
        menuBar.Append(ofMenu, "&OpenFAST")
        #for toolName in OF_DATA_TOOLS.keys(): # TODO remove me, should be an action
        #    self.Bind(wx.EVT_MENU, lambda e, s_loc=toolName: self.onShowTool(e, s_loc), ofMenu.Append(wx.ID_ANY, toolName))
        for toolName in OF_DATA_PLUGINS_WITH_EDITOR.keys():
            self.Bind(wx.EVT_MENU, lambda e, s_loc=toolName: self.onDataPlugin(e, s_loc), ofMenu.Append(wx.ID_ANY, toolName))

        for toolName in OF_DATA_PLUGINS_SIMPLE.keys():
            self.Bind(wx.EVT_MENU, lambda e, s_loc=toolName: self.onDataPlugin(e, s_loc), ofMenu.Append(wx.ID_ANY, toolName))


        # --- Help Menu
        helpMenu = wx.Menu()
        aboutMenuItem = helpMenu.Append(wx.NewId(), 'About', 'About')
        resetMenuItem = helpMenu.Append(wx.NewId(), 'Reset options', 'Rest options')
        menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU,self.onAbout, aboutMenuItem)
        self.Bind(wx.EVT_MENU,self.onReset, resetMenuItem)


        io_userpath = os.path.join(weio.defaultUserDataDir(), 'pydatview_io')
        self.FILE_FORMATS, errors= weio.fileFormats(userpath=io_userpath, ignoreErrors=True, verbose=False)
        if len(errors)>0:
            for e in errors:
                Warn(self, e)

        self.FILE_FORMATS_EXTENSIONS = [['.*']]+[f.extensions for f in self.FILE_FORMATS]
        self.FILE_FORMATS_NAMES      = ['auto (any supported file)'] + [f.name for f in self.FILE_FORMATS]
        self.FILE_FORMATS_NAMEXT     =['{} ({})'.format(n,','.join(e)) for n,e in zip(self.FILE_FORMATS_NAMES,self.FILE_FORMATS_EXTENSIONS)]

        # --- ToolBar
        tb = self.CreateToolBar(wx.TB_HORIZONTAL|wx.TB_TEXT|wx.TB_HORZ_LAYOUT)
        tb.AddSeparator()
        self.comboMode = wx.ComboBox(tb, choices = SEL_MODES, style=wx.CB_READONLY)  
        self.comboMode.SetSelection(0)
        #tb.AddStretchableSpace()
        tb.AddControl( wx.StaticText(tb, -1, 'Mode: ' ) )
        tb.AddControl( self.comboMode ) 
        self.cbLivePlot = wx.CheckBox(tb, -1, 'Live Plot') #,(10,10))
        self.cbLivePlot.SetValue(True)
        tb.AddControl( self.cbLivePlot ) 
        tb.AddStretchableSpace()
        tb.AddControl( wx.StaticText(tb, -1, 'Format: ' ) )
        self.comboFormats = wx.ComboBox(tb, choices = self.FILE_FORMATS_NAMEXT, style=wx.CB_READONLY)  
        self.comboFormats.SetSelection(0)
        tb.AddControl(self.comboFormats ) 
        # Menu for loader options
        self.btLoaderMenu = wx.Button(tb, wx.ID_ANY, CHAR['menu'], style=wx.BU_EXACTFIT)
        tb.AddControl(self.btLoaderMenu)
        self.loaderMenu = LoaderMenuPopup(tb, self.data['loaderOptions'])
        tb.AddSeparator()
        TBAddTool(tb, "Open"  , 'ART_FILE_OPEN', self.onLoad)
        TBAddTool(tb, "Reload", 'ART_REDO'     , self.onReload)
        TBAddTool(tb, "Add"   , 'ART_PLUS'     , self.onAdd)
        #bmp = wx.Bitmap('help.png') #wx.Bitmap("NEW.BMP", wx.BITMAP_TYPE_BMP) 
        #self.AddTBBitmapTool(tb,"Debug" ,wx.ArtProvider.GetBitmap(wx.ART_ERROR),self.onDEBUG)
        tb.AddStretchableSpace()
        tb.Realize() 
        self.toolBar = tb 
        # Bind Toolbox Events
        self.Bind(wx.EVT_COMBOBOX, self.onModeChange, self.comboMode )
        self.Bind(wx.EVT_COMBOBOX, self.onFormatChange, self.comboFormats )
        tb.Bind(wx.EVT_BUTTON, self.onShowLoaderMenu, self.btLoaderMenu)
        tb.Bind(wx.EVT_CHECKBOX, self.onLivePlotChange, self.cbLivePlot)

        # --- Status bar
        self.statusbar=self.CreateStatusBar(3, style=0)
        self.statusbar.SetStatusWidths([150, -1, 70])

        # --- Pipeline
        self.pipePanel = PipelinePanel(self, data=self.data['pipeline'], tabList=self.tabList)

        # --- Main Panel and Notebook
        self.MainPanel = wx.Panel(self)
        #self.MainPanel = wx.Panel(self, style=wx.RAISED_BORDER)
        #self.MainPanel.SetBackgroundColour((200,0,0))

        #self.nb = wx.Notebook(self.MainPanel)
        #self.nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_change)


        sizer = wx.BoxSizer()
        #sizer.Add(self.nb, 1, flag=wx.EXPAND)
        self.MainPanel.SetSizer(sizer)

        # --- Drag and drop
        dd = FileDropTarget(self)
        self.SetDropTarget(dd)

        # --- Main Frame (self)
        self.FrameSizer = wx.BoxSizer(wx.VERTICAL)
        slSep = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.FrameSizer.Add(slSep         ,0, flag=wx.EXPAND|wx.BOTTOM,border=0)
        self.FrameSizer.Add(self.MainPanel,1, flag=wx.EXPAND,border=0)
        self.FrameSizer.Add(self.pipePanel,0, flag=wx.EXPAND,border=0)
        self.SetSizer(self.FrameSizer)

        self.SetSize(self.data['windowSize'])
        self.Center()
        self.Show()
        self.Bind(wx.EVT_SIZE, self.OnResizeWindow)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Shortcuts
        idFilter=wx.NewId()
        self.Bind(wx.EVT_MENU, self.onFilter, id=idFilter)

        accel_tbl = wx.AcceleratorTable(
                [(wx.ACCEL_CTRL,  ord('F'), idFilter )]
                )
        self.SetAcceleratorTable(accel_tbl)

    def onFilter(self,event):
        if hasattr(self,'selPanel'):
            self.selPanel.colPanel1.tFilter.SetFocus()
        event.Skip()

    def clean_memory(self,bReload=False):
        #print('Clean memory')
        # force Memory cleanup
        self.tabList.clean()
        if hasattr(self,'plotPanel'):
            self.plotPanel.markers = []
        if not bReload:
            if hasattr(self,'selPanel'):
                self.selPanel.clean_memory()
            if hasattr(self,'infoPanel'):
                self.infoPanel.clean()
            if hasattr(self,'plotPanel'):
                self.plotPanel.cleanPlot()
        gc.collect()

    def load_files(self, filenames=[], fileformats=None, bReload=False, bAdd=False, bPlot=True):
        """ load multiple files, only trigger the plot at the end """
        if bReload:
            if hasattr(self,'selPanel'):
                self.selPanel.saveSelection() # TODO move to tables
        else:
            self.statusbar.SetStatusText('Loading files...', ISTAT)

        # A function to update the status bar while we load files
        statusFunction = lambda i: self.statusbar.SetStatusText('Loading files {}/{}'.format(i+1,len(filenames)), ISTAT)

        if not bAdd:
            self.clean_memory(bReload=bReload)


        if fileformats is None:
            fileformats=[None]*len(filenames)
        assert type(fileformats)==list, 'fileformats must be a list'
        assert len(fileformats)==len(filenames), 'fileformats and filenames must have the same lengths'

        # Sorting files in alphabetical order in base_filenames order
        base_filenames = [os.path.basename(f) for f in filenames]
        I = np.argsort(base_filenames)
        filenames   = list(np.array(filenames)[I])
        fileformats = list(np.array(fileformats)[I])
        #filenames = [f for __, f in sorted(zip(base_filenames, filenames))]

        # Load the tables
        newTabs, warnList = self.tabList.load_tables_from_files(filenames=filenames, fileformats=fileformats, bAdd=bAdd, bReload=bReload, statusFunction=statusFunction)

        # Apply postLoad pipeline
        if bReload:
            self.applyPipeline(self.tabList, force=True) # we force on reload
        else:
            self.applyPipeline(newTabs, force=True, applyToAll=True) # we apply only on newTabs

        if bReload:
            # Restore formulas that were previously added
            self.tabList.applyFormulas(self.formulas_backup)
            self.formulas_backup = {}
        # Display warnings
        for warn in warnList: 
            Warn(self,warn)
        # Load tables into the GUI
        if self.tabList.len()>0:
            self.load_tabs_into_GUI(bReload=bReload, bAdd=bAdd, bPlot=bPlot)

    def load_dfs(self, dfs, names=None, bAdd=False, bPlot=True):
        """ Load one or multiple dataframes intoGUI """
        # 
        if not isinstance(dfs,list):
            dfs=[dfs]
        if names is None:
            names = ['tab{}'.format(i) for i in range(len(dfs))]
        if not isinstance(names,list):
            names=[names]
        self.tabList.from_dataframes(dataframes=dfs, names=names, bAdd=bAdd)
        self.load_tabs_into_GUI(bAdd=bAdd, bPlot=bPlot)
        if hasattr(self,'selPanel'):
            self.selPanel.updateLayout(SEL_MODES_ID[self.comboMode.GetSelection()])

    def load_tabs_into_GUI(self, bReload=False, bAdd=False, bPlot=True):
        if bAdd:
            if not hasattr(self,'selPanel'):
                bAdd=False

        if (not bReload) and (not bAdd):
            self.cleanGUI()
        if (bReload):
            self.statusbar.SetStatusText('Done reloading.', ISTAT)
        self.Freeze()
        # Setting status bar
        self.setStatusBar()

        if bReload or bAdd:
            self.selPanel.update_tabs(self.tabList)
        else:
            # --- Create a selPanel, plotPanel and infoPanel
            mode = SEL_MODES_ID[self.comboMode.GetSelection()]
            #self.vSplitter = wx.SplitterWindow(self.nb)
            self.vSplitter = wx.SplitterWindow(self.MainPanel)
            self.selPanel = SelectionPanel(self.vSplitter, self.tabList, mode=mode, mainframe=self)
            self.tSplitter = wx.SplitterWindow(self.vSplitter)
            #self.tSplitter.SetMinimumPaneSize(20)
            self.infoPanel = InfoPanel(self.tSplitter, data=self.data['infoPanel'])
            self.plotPanel = PlotPanel(self.tSplitter, self.selPanel, infoPanel=self.infoPanel, pipeLike=self.pipePanel, data=self.data['plotPanel'])
            self.livePlotFreezeUnfreeze() # Dont enable panels if livePlot is not allowed
            self.tSplitter.SetSashGravity(0.9)
            self.tSplitter.SplitHorizontally(self.plotPanel, self.infoPanel)
            self.tSplitter.SetMinimumPaneSize(BOT_PANL)
            self.tSplitter.SetSashGravity(1)
            self.tSplitter.SetSashPosition(400)

            self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
            self.vSplitter.SetMinimumPaneSize(SIDE_COL[0])
            self.tSplitter.SetSashPosition(SIDE_COL[0])

            #self.nb.AddPage(self.vSplitter, "Plot")
            #self.nb.SendSizeEvent()

            sizer = self.MainPanel.GetSizer()
            sizer.Add(self.vSplitter, 1, flag=wx.EXPAND,border=0)
            self.MainPanel.SetSizer(sizer)
            self.FrameSizer.Layout()


            # --- Bind 
            # The selPanel does the binding, but the callback is stored here because it involves plotPanel... TODO, rethink it
            #self.selPanel.bindColSelectionChange(self.onColSelectionChangeCallBack)
            self.selPanel.setTabSelectionChangeCallback(self.onTabSelectionChangeTrigger)
            self.selPanel.setRedrawCallback(self.redrawCallback)
            self.selPanel.setUpdateLayoutCallback(self.mainFrameUpdateLayout)
            self.plotPanel.setAddTablesCallback(self.load_dfs)

            self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.onSashChangeMain, self.vSplitter)

        # plot trigger
        if bPlot:
            self.mainFrameUpdateLayout()
            self.onColSelectionChange(event=None)
        try:
            self.Thaw()
        except:
            pass
        # Hack
        #self.onShowTool(tool='Filter')
        #self.onShowTool(tool='Resample')
        #self.onDataPlugin(toolName='Mask')
        #self.onDataPlugin(toolName='Bin data')
        #self.onDataPlugin(toolName='Remove Outliers')
        #self.onDataPlugin(toolName='Filter')

    def setStatusBar(self, ISel=None):
        nTabs=self.tabList.len()
        if ISel is None:
            ISel = list(np.arange(nTabs))
        if nTabs<0:
            self.statusbar.SetStatusText('', ISTAT) # Format
            self.statusbar.SetStatusText('', ISTAT+1) # Filenames
            self.statusbar.SetStatusText('', ISTAT+2) # Shape
        elif nTabs==1:
            self.statusbar.SetStatusText(self.tabList[0].fileformat_name, ISTAT+0)
            self.statusbar.SetStatusText(self.tabList[0].filename       , ISTAT+1)
            self.statusbar.SetStatusText(self.tabList[0].shapestring    , ISTAT+2)
        elif len(ISel)==1:
            self.statusbar.SetStatusText(self.tabList[ISel[0]].fileformat_name , ISTAT+0)
            self.statusbar.SetStatusText(self.tabList[ISel[0]].filename        , ISTAT+1)
            self.statusbar.SetStatusText(self.tabList[ISel[0]].shapestring     , ISTAT+2)
        else:
            self.statusbar.SetStatusText('{} tables loaded'.format(nTabs)                                                     ,ISTAT+0) 
            self.statusbar.SetStatusText(", ".join(list(set([self.tabList.filenames[i] for i in ISel]))),ISTAT+1)
            self.statusbar.SetStatusText(''                                                             ,ISTAT+2)

    # --- Table Actions - TODO consider a table handler, or doing only the triggers
    def renameTable(self, iTab, newName):
        oldName = self.tabList.renameTable(iTab, newName)
        self.selPanel.renameTable(iTab, oldName, newName)

    def deleteTabs(self, I):
        self.tabList.deleteTabs(I)
        if len(self.tabList)==0:
            self.cleanGUI()
            return

        # Invalidating selections
        self.selPanel.tabPanel.lbTab.SetSelection(-1)
        # Until we have something better, we empty plot
        self.plotPanel.empty()
        self.infoPanel.empty()
        self.selPanel.clean_memory()
        # Updating tables
        self.selPanel.update_tabs(self.tabList)
        # Trigger a replot
        self.onTabSelectionChange()

    def exportTab(self, iTab):
        tab=self.tabList[iTab]
        default_filename=tab.basename +'.csv'

        # --- Set list of allowed formats
        # NOTE: this needs to be in harmony with io.converters
        fformat= ['auto'   ]; wildcard ='auto (based on extension, default to CSV) (.*)|*.*|'
        fformat+=['csv'    ]; wildcard+='CSV file (.csv,.txt)|*.csv;*.txt|'
        fformat+=['outb'   ]; wildcard+='FAST output file (.outb)|*.outb|'
        fformat+=['parquet']; wildcard+='Parquet file (.parquet)|*.parquet'
        #fformat= ['excel'  ];wildcard+='Excel file (.xls,.xlsx)|*.xls;*.xlsx|'
        #fformat+=['pkl'    ];wildcard+='Pickle file (.pkl)|*.pkl|'
        #fformat+=['tecplot'];wildcard+='Tecplot ASCII file (.dat)|*.dat|'

        with wx.FileDialog(self, "Save to CSV file", defaultFile=default_filename,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard=wildcard) as dlg:
            dlg.CentreOnParent()
            if dlg.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            path = dlg.GetPath()
            fformat = fformat[dlg.GetFilterIndex()]
            tab.export(path=path, fformat=fformat)

    def onShowTool(self, event=None, toolName=''):
        """ 
        Show tool See pydatview.plugins.__init__.py
        tool in 'Outlier', 'Filter', 'LogDec','Radial Average', 'Mask', 'CurveFitting'
        """
        if not hasattr(self,'plotPanel'):
            Error(self,'Plot some data first')
            return
        self.plotPanel.showTool(toolName)

    def onDataPlugin(self, event=None, toolName=''):
        """ 
        Dispatcher to apply plugins to data:
          - simple plugins are directly exectued
          - plugins that are panels are sent over to plotPanel to show them
        TODO merge with onShowTool

        See pydatview.plugins.__init__.py for list of toolNames
        """
        if not hasattr(self,'plotPanel'):
            Error(self,'Plot some data first')
            return

        if toolName in DATA_PLUGINS_WITH_EDITOR.keys():
            # Check to see if the pipeline already contains this action
            action = self.pipePanel.find(toolName) # old action to edit
            if action is None:
                function = DATA_PLUGINS_WITH_EDITOR[toolName]
                action = function(label=toolName, mainframe=self) # getting brand new action
            else:
                print('>>> The action already exists, we use it for the GUI')
            self.plotPanel.showToolAction(action)
            # The panel will have the responsibility to apply/delete the action, updateGUI, etc

        elif toolName in OF_DATA_PLUGINS_WITH_EDITOR.keys():
            # Check to see if the pipeline already contains this action
            action = self.pipePanel.find(toolName) # old action to edit
            if action is None:
                function = OF_DATA_PLUGINS_WITH_EDITOR[toolName]
                action = function(label=toolName, mainframe=self) # getting brand new action
            else:
                print('>>> The action already exists, we use it for the GUI')
            self.plotPanel.showToolAction(action)
            # The panel will have the responsibility to apply/delete the action, updateGUI, etc

        elif toolName in DATA_PLUGINS_SIMPLE.keys():
            function = DATA_PLUGINS_SIMPLE[toolName]
            action = function(label=toolName, mainframe=self) # calling the data function
            # Here we apply the action directly
            # We can't overwrite, so we'll delete by name..
            self.addAction(action, overwrite=False, apply=True, tabList=self.tabList, updateGUI=True)

        elif toolName in OF_DATA_PLUGINS_SIMPLE.keys(): # TODO merge with DATA_PLUGINS_SIMPLE
            function = OF_DATA_PLUGINS_SIMPLE[toolName]
            action = function(label=toolName, mainframe=self) # calling the data function
            # Here we apply the action directly
            # We can't overwrite, so we'll delete by name..
            self.addAction(action, overwrite=False, apply=True, tabList=self.tabList, updateGUI=True)
        else:
            raise NotImplementedError('Tool: ',toolName)

    # --- Pipeline
    def addAction(self, action, **kwargs):
        self.pipePanel.append(action, **kwargs)
    def removeAction(self, action, **kwargs):
        self.pipePanel.remove(action, **kwargs)
    def applyPipeline(self, *args, **kwargs):
        self.pipePanel.apply(*args, **kwargs)
    def checkErrors(self):
        # TODO this should be done at a given point in the GUI
        nErr = len(self.pipePanel.errorList)
        if nErr>0:
            if not self.pipePanel.user_warned:
                if nErr>=len(self.tabList):
                    if nErr==1:
                        sErr='\n'+'\n'.join(self.pipePanel.errorList)
                        Warn(self, message=sErr, caption = 'The following error occured when applying the pipeline actions:')
                    else:
                        sErr = '\n\nCheck `Errors` in the bottom right side of the window.'
                        Warn(self, 'Errors occured on all tables.'+sErr)
                #elif nErr<len(self.tabList):
                #    Warn(self, 'Errors occured on some tables.'+sErr)
                self.pipePanel.user_warned = True

    def onSashChangeMain(self, event=None):
        pass
        # doent work because size is not communicated yet
        #if hasattr(self,'selPanel'):
        #    print('ON SASH')
        #    self.selPanel.setEquiSash(event)


    def onTabSelectionChange(self, event=None):
        self.checkErrors()
        # TODO get rid of me
        self.selPanel.onTabSelectionChange()

    def onColSelectionChange(self, event=None):
        # TODO get rid of me
        self.selPanel.onColSelectionChange()

    def redraw(self):
        self.checkErrors()
        # TODO get rid of me
        self.redrawCallback()

    # --- CallBacks sent to panels
    def onTabSelectionChangeTrigger(self, event=None):
        # Update of status bar
        ISel=self.selPanel.tabPanel.lbTab.GetSelections()
        if len(ISel)>0:
            self.setStatusBar(ISel)

    def onColSelectionChangeTrigger(self, event=None):
        pass

    def onLivePlotChange(self, event=None):
        if self.cbLivePlot.IsChecked():
            if hasattr(self,'plotPanel'):
                #print('[INFO] Reenabling live plot')
                #self.plotPanel.Enable(True)
                #self.infoPanel.Enable(True)
                self.redrawCallback()
        else:
            if hasattr(self,'plotPanel'):
                #print('[INFO] Disabling live plot')
                for ax in self.plotPanel.fig.axes:
                    ax.annotate('Live Plot Disabled', xy=(0.5, 0.5), size=20, xycoords='axes fraction', ha='center', va='center',)
                    self.plotPanel.canvas.draw()
                #self.plotPanel.Enable(False)
                #self.infoPanel.Enable(False)

    def livePlotFreezeUnfreeze(self):
        pass
        #if self.cbLivePlot.IsChecked():
        #    if hasattr(self,'plotPanel'):
        #        #print('[INFO] Enabling live plot')
        #        #self.plotPanel.Enable(True)
        #        self.infoPanel.Enable(True)
        #else:
        #    if hasattr(self,'plotPanel'):
        #        #print('[INFO] Disabling live plot')
        #        #self.plotPanel.Enable(False)
        #        self.infoPanel.Enable(False)

    def redrawCallback(self):
        if hasattr(self,'plotPanel'):
            if self.cbLivePlot.IsChecked():
                self.plotPanel.load_and_draw()
            else:
                pass
                #print('[INFO] Drawing event skipped, live plot is not checked.')

#     def showStats(self):
#         self.infoPanel.showStats(self.plotPanel.plotData,self.plotPanel.pltTypePanel.plotType())

    def onExit(self, event):
        self.Close() 

    def onClose(self, event):
        saveAppData(self, self.data)
        event.Skip()

    def cleanGUI(self, event=None):
        if hasattr(self,'plotPanel'):
            del self.plotPanel
        if hasattr(self,'selPanel'):
            del self.selPanel
        if hasattr(self,'infoPanel'):
            del self.infoPanel
        #self.deletePages()
        try:
            self.MainPanel.GetSizer().Clear(delete_windows=True) # Delete Windows
        except:
            self.MainPanel.GetSizer().Clear()
        self.FrameSizer.Layout()
        gc.collect()

    def onSave(self, event=None):
        # using the navigation toolbar save functionality
        self.plotPanel.navTB.save_figure()

    def onAbout(self, event=None):
        io_userpath = os.path.join(weio.defaultUserDataDir(), 'pydatview_io')
        About(self,PROG_NAME+' '+PROG_VERSION+'\n\n'
                'pyDatView config file:\n     {}\n'.format(configFilePath())+
                'pyDatView io data directory:\n     {}\n'.format(io_userpath)+
                '\n\nVisit http://github.com/ebranlard/pyDatView for documentation.')

    def onReset (self, event=None):
        configFile = configFilePath()
        result = YesNo(self,
                'The options of pyDatView will be reset to default.\nThe changes will be noticeable the next time you open pyDatView.\n\n'+
                'This action will overwrite the user settings file:\n   {}\n\n'.format(configFile)+
                'pyDatView will then close.\n\n'
                'Are you sure you want to continue?', caption = 'Reset settings?')
        if result:
            try:
                os.remove(configFile)
            except:
                pass
            self.data = defaultAppData(self)
            self.datareset = True
            self.onExit(event=None)

    def onReload(self, event=None):
        filenames, fileformats = self.tabList.filenames_and_formats
        self.statusbar.SetStatusText('Reloading...', ISTAT)
        if len(filenames)>0:
            # If only one file, use the comboBox to decide which fileformat to use
            if len(filenames)==1:
                iFormat=self.comboFormats.GetSelection()
                if iFormat==0: # auto-format
                    fileformats = [None]
                else:
                    fileformats = [self.FILE_FORMATS[iFormat-1]]

            # Save formulas to restore them after reload with sorted tabs
            self.formulas_backup = self.tabList.storeFormulas()
            # Actually load files (read and add in GUI)
            self.load_files(filenames, fileformats=fileformats, bReload=True, bAdd=False, bPlot=True)
        else:
           Error(self,'Open one or more file first.')

    def onDEBUG(self, event=None):
        #self.clean_memory()
        self.plotPanel.ctrlPanel.Refresh()
        self.plotPanel.cb_sizer.ForceRefresh()

    def onExport(self, event=None):
        ISel=[]
        try:
            ISel = self.selPanel.tabPanel.lbTab.GetSelections()
        except:
            pass
        if len(ISel)>0:
            self.exportTab(ISel[0])
        else:
           Error(self,'Open a file and select a table first.')

    def onScript(self, event=None):
        from pydatview.GUIScripter import GUIScripterFrame
        GUIScripterFrame
        pop = GUIScripterFrame(parent=None, mainframe=self, pipeLike=self.pipePanel, title="pyDatView - Script export")
        pop.Show()
#         if hasattr(self,'selPanel') and hasattr(self,'plotPanel'):
#             script = pythonScript(self.tabList, self.selPanel, self.plotPanel)
#         else:
#             Error(self,'Open a file and generate a plot before exporting.')
#         tab=self.tabList.get(iTab)
#         default_filename=tab.basename +'.csv'
#         with wx.FileDialog(self, "Save to CSV file",defaultFile=default_filename,
#                 style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
#                 #, wildcard="CSV files (*.csv)|*.csv",
#             dlg.CentreOnParent()
#             if dlg.ShowModal() == wx.ID_CANCEL:
#                 return     # the user changed their mind
#             tab.export(dlg.GetPath())


    def onLoad(self, event=None):
        self.selectFile(bAdd=False)

    def onAdd(self, event=None):
        self.selectFile(bAdd=self.tabList.len()>0)

    def selectFile(self,bAdd=False):
        # --- File Format extension
        iFormat=self.comboFormats.GetSelection()
        sFormat=self.comboFormats.GetStringSelection()
        if iFormat==0: # auto-format
            Format = None
            #wildcard = 'all (*.*)|*.*'
            wildcard='|'.join([n+'|*'+';*'.join(e) for n,e in zip(self.FILE_FORMATS_NAMEXT,self.FILE_FORMATS_EXTENSIONS)])
            #wildcard = sFormat + extensions+'|all (*.*)|*.*'
        else:
            Format = self.FILE_FORMATS[iFormat-1]
            extensions = '|*'+';*'.join(self.FILE_FORMATS[iFormat-1].extensions)
            wildcard = sFormat + extensions+'|all (*.*)|*.*'

        with wx.FileDialog(self, "Open file", wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as dlg:
            #other options: wx.CHANGE_DIR
            #dlg.SetSize((100,100))
            #dlg.Center()
           if dlg.ShowModal() == wx.ID_CANCEL:
               return     # the user changed their mind
           filenames = dlg.GetPaths()
           self.load_files(filenames,fileformats=[Format]*len(filenames),bAdd=bAdd, bPlot=True)

    def onModeChange(self, event=None):
        if hasattr(self,'selPanel'):
            self.selPanel.updateLayout(SEL_MODES_ID[self.comboMode.GetSelection()])
        self.mainFrameUpdateLayout()
        # --- Trigger to check number of columns
        self.onTabSelectionChange()

    def onFormatChange(self, event=None):
        """ The user changed the format """
        #if hasattr(self,'selPanel'):
        #    ISel=self.selPanel.tabPanel.lbTab.GetSelections()
        pass


    def onShowLoaderMenu(self, event=None):
        #pos = (self.btLoaderMenu.GetPosition()[0], self.btLoaderMenu.GetPosition()[1] + self.btLoaderMenu.GetSize()[1])
        self.PopupMenu(self.loaderMenu) #, pos)


    def mainFrameUpdateLayout(self, event=None):
        try:
            if hasattr(self,'selPanel'):
                nWind=self.selPanel.splitter.nWindows
                if self.Size[0]<=800:
                    sash=SIDE_COL[nWind]
                else:
                    sash=SIDE_COL_LARGE[nWind]
                self.resizeSideColumn(sash)
        except:
            print('[Fail] An error occured in mainFrameUpdateLayout')

    def OnIdle(self, event):
        if self.resized:
            self.resized = False
            self.mainFrameUpdateLayout()
            if hasattr(self,'plotPanel'):
                self.plotPanel.setSubplotTight()
            self.Thaw()

    def OnResizeWindow(self, event):
        self.resized = True
        self.Freeze()
        self.Layout()

    # --- Side column
    def resizeSideColumn(self,width):
        # To force the replot we do an epic unsplit/split...
        #self.vSplitter.Unsplit()
        #self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
        self.vSplitter.SetMinimumPaneSize(width)
        self.vSplitter.SetSashPosition(width)
        #self.selPanel.splitter.setEquiSash()

    # --- NOTEBOOK 
    #def deletePages(self):
    #    for index in reversed(range(self.nb.GetPageCount())):
    #        self.nb.DeletePage(index)
    #    self.nb.SendSizeEvent()
    #    gc.collect()
    #def on_tab_change(self, event=None):
    #    page_to_select = event.GetSelection()
    #    wx.CallAfter(self.fix_focus, page_to_select)
    #    event.Skip(True)
    #def fix_focus(self, page_to_select):
    #    page = self.nb.GetPage(page_to_select)
    #    page.SetFocus()

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
    from wx._core import wxAssertionError
    # Printing exception
    traceback.print_exception(etype, value, trace)
    if etype==wxAssertionError:
        if wx.Platform == '__WXMAC__':
            # We skip these exceptions on macos (likely bitmap size 0)
            return
    # Then showing to user the last error
    frame = wx.GetApp().GetTopWindow()
    tmp = traceback.format_exception(etype, value, trace)
    if tmp[-1].find('Exception: Error:')==0:
        Error(frame,tmp[-1][18:])
    elif tmp[-1].find('Exception: Warn:')==0:
        Warn(frame,tmp[-1][17:])
    else:
        exception = 'The following exception occured:\n\n'+ tmp[-1]  + '\n'+tmp[-2].strip()
        Error(frame,exception)
    try:
        frame.Thaw() # Make sure any freeze event is stopped
    except:
        pass

# --------------------------------------------------------------------------------}
# --- Tests 
# --------------------------------------------------------------------------------{
def test(filenames=None):
    if filenames is not None:
        app = wx.App(False)
        frame = MainFrame()
        frame.load_files(filenames,fileformats=None, bPlot=True)
        return
 
# --------------------------------------------------------------------------------}
# --- Wrapped WxApp
# --------------------------------------------------------------------------------{
class MyWxApp(wx.App):
    def __init__(self, redirect=False, filename=None):
        try:
            wx.App.__init__(self, redirect, filename)
        except:
            if wx.Platform == '__WXMAC__':
                #msg = """This program needs access to the screen.
                #          Please run with 'pythonw', not 'python', and only when you are logged
                #          in on the main display of your Mac."""
               msg= """
MacOS Error:
  This program needs access to the screen. Please run with a
  Framework build of python, and only when you are logged in
  on the main display of your Mac.

pyDatView help:
  You see the error above because you are using a Mac and 
  the python executable you are using does not have access to
  your screen. This is a Mac issue, not a pyDatView issue.
  Instead of calling 'python pyDatView.py', you need to find
  another python and do '/path/python pyDatView.py'
  You can try './pythonmac pyDatView.py', a script provided
  in this repository to detect the path (in some cases)
  
  You can find additional help in the file 'README.md'.
  
  For quick reference, here are some typical cases:
  - Your python was installed with 'brew', then likely use   
       /usr/lib/Cellar/python/XXXXX/Frameworks/python.framework/Versions/XXXX/bin/pythonXXX;
  - Your python is an anaconda python, use something like:;
       /anaconda3/bin/python.app   (NOTE: the '.app'!
"""

            elif wx.Platform == '__WXGTK__':
                msg ="""
Error:
  Unable to access the X Display, is $DISPLAY set properly?

pyDatView help:
  You are probably running this application on a server accessed via ssh.
  Use `ssh -X` or `ssh -Y` to access the server. 
  Else, try setting up $DISPLAY before doing the ssh connection.
"""
            else:
                msg = 'Unable to create GUI' # TODO: more description is needed for wxMSW...
            raise SystemExit(msg)
    def InitLocale(self):
        if sys.platform.startswith('win') and sys.version_info > (3,8):
            # See Bug #128 - Issue with wxPython 4.1 on Windows
            import locale
            locale.setlocale(locale.LC_ALL, "C")
            print('[INFO] Setting locale to C')
            #self.SetAssertMode(wx.APP_ASSERT_SUPPRESS) # Try this

# --------------------------------------------------------------------------------}
# --- Mains 
# --------------------------------------------------------------------------------{
def showApp(firstArg=None, dataframes=None, filenames=[], names=None):
    """
    The main function to start the pyDatView GUI and loads
    Call this function with:
      - filenames : list of filenames or a single filename (string)
      OR
      - dataframes: list of dataframes or a single dataframe
      - names: list of names to be used for the multiple dataframes
    """
    app = MyWxApp(False)
    frame = MainFrame()
    # Optional first argument
    if firstArg is not None:
        if isinstance(firstArg,list):
            if isinstance(firstArg[0],str):
                filenames=firstArg
            else:
                dataframes=firstArg
        elif isinstance(firstArg,str):
            filenames=[firstArg]
        elif isinstance(firstArg, pd.DataFrame):
            dataframes=[firstArg]
    # Load files or dataframe depending on interface
    if (dataframes is not None) and (len(dataframes)>0):
        if names is None:
            names=['df{}'.format(i+1) for i in range(len(dataframes))]
        frame.load_dfs(dataframes, names)
    elif len(filenames)>0:
        frame.load_files(filenames, fileformats=None, bPlot=True)

    #frame.onShowTool(toolName='')
    #frame.onDataPlugin(toolName='Radial Average')
    #frame.onDataPlugin(toolName='Resample')
    #frame.onScript()

    app.MainLoop()


def cmdline():
    if len(sys.argv)>1:
        pydatview(filename=sys.argv[1])
    else:
        pydatview()
