import numpy as np
import os
import os.path
import sys
import traceback
import gc
import json
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
#from wx.lib.agw.flatnotebook import FlatNotebook
from wx import Notebook

from pydatview.GUIFileInfo import FileInfoPanel
from pydatview.GUIFields1D import Fields1DPanel
from pydatview.GUIFields2D import Fields2DPanel

from pydatview.GUISelectionPanel import SEL_MODES,SEL_MODES_ID
from pydatview.GUISelectionPanel import ColumnPopup,TablePopup
from pydatview.GUISelectionPanel import _tab_shortname
from pydatview.GUIPipelinePanel import PipelinePanel
from pydatview.GUIToolBox import GetKeyString, TBAddTool
from pydatview.Tables import TableList, Table
# Helper
from pydatview.common import exception2string, PyDatViewException
from pydatview.common import *
from pydatview.GUICommon import *
import pydatview.io as weio # File Formats and File Readers
# Pluggins
from pydatview.plugins import DATA_PLUGINS_WITH_EDITOR, DATA_PLUGINS_SIMPLE, TOOLS
from pydatview.plugins import OF_DATA_PLUGINS_WITH_EDITOR, OF_DATA_PLUGINS_SIMPLE
from pydatview.appdata import loadAppData, saveAppData, configFilePath, defaultAppData

# --------------------------------------------------------------------------------}
# --- GLOBAL 
# --------------------------------------------------------------------------------{
PROG_NAME='pyDatView'
PROG_VERSION='v0.5-local'
ISTAT = 0 # Index of Status bar where main status info is provided
VIEW_FILE_EXT = '.pdvview'  # Extension for exported view files

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
      if len(filenames) == 0:
          return True
      # View files are handled separately
      view_files = [f for f in filenames if f.lower().endswith(VIEW_FILE_EXT)]
      data_files  = [f for f in filenames if not f.lower().endswith(VIEW_FILE_EXT)]
      if view_files:
          self.parent.load_view_file(view_files[0])
      elif data_files:
          bAdd = wx.GetKeyState(wx.WXK_CONTROL)
          iFormat = self.parent.comboFormats.GetSelection()
          Format = None if iFormat == 0 else self.parent.FILE_FORMATS[iFormat-1]
          self.parent.load_files(data_files, fileformats=[Format]*len(data_files), bAdd=bAdd, bPlot=True)
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
        loadMenuItem  = fileMenu.Append(wx.ID_NEW,"&Open file\tCtrl+O" ,"Open file"           )
        reloadMenuItem= fileMenu.Append(wx.ID_ANY,"&Reload\tCtrl+R"    ,"Reload current files" )
        addMenuItem   = fileMenu.Append(wx.ID_ANY,"&Add file\tCtrl+A"  ,"Add file to current data" )
        self.recentFilesMenu = wx.Menu()
        fileMenu.AppendSubMenu(self.recentFilesMenu, 'Recent Files')
        fileMenu.AppendSeparator()
        scrpMenuItem  = fileMenu.Append(-1        ,"Export script" ,"Export script"           )
        exptMenuItem  = fileMenu.Append(-1        ,"Export table" ,"Export table"           )
        saveMenuItem  = fileMenu.Append(wx.ID_SAVE,"Save figure" ,"Save figure"           )
        exitMenuItem  = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
        menuBar.Append(fileMenu, "&File")
        self.Bind(wx.EVT_MENU,self.onExit   ,exitMenuItem)
        self.Bind(wx.EVT_MENU,self.onLoad   ,loadMenuItem)
        self.Bind(wx.EVT_MENU,self.onReload ,reloadMenuItem)
        self.Bind(wx.EVT_MENU,self.onAdd    ,addMenuItem)
        self.Bind(wx.EVT_MENU,self.onScript ,scrpMenuItem)
        self.Bind(wx.EVT_MENU,self.onExport ,exptMenuItem)
        self.Bind(wx.EVT_MENU,self.onSave   ,saveMenuItem)

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

        # --- Views Menu
        self.viewsMenu = wx.Menu()
        saveViewMenuItem   = self.viewsMenu.Append(wx.ID_ANY, '&Save current view...\tCtrl+S',   'Save the current selection and plot settings as a named view')
        exportViewMenuItem = self.viewsMenu.Append(wx.ID_ANY, 'Export view to file...', 'Export the current view to a .pdvview file (includes file list and settings)')
        importViewMenuItem = self.viewsMenu.Append(wx.ID_ANY, 'Import view from file...', 'Load a .pdvview file, open its data files, and restore the view')
        self.viewsMenu.AppendSeparator()
        menuBar.Append(self.viewsMenu, "&Views")
        self.Bind(wx.EVT_MENU, self.onSaveView,    saveViewMenuItem)
        self.Bind(wx.EVT_MENU, self.onExportView,  exportViewMenuItem)
        self.Bind(wx.EVT_MENU, self.onImportView,  importViewMenuItem)

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
        self.comboMode.SetToolTip("How to handle column matching when multiple tables are selected")
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
        tb.AddStretchableSpace()
        tb.Realize()
        self.toolBar = tb
        # Set short-help tooltips on named toolbar tools
        try:
            _tb_tooltips = {
                'Open':   'Open file (Ctrl+O)',
                'Reload': 'Reload current files (Ctrl+R)',
                'Add':    'Add file to current data set (Ctrl+A)',
            }
            for i in range(tb.GetToolsCount()):
                t = tb.GetToolByPos(i)
                lbl = t.GetLabel()
                if lbl in _tb_tooltips:
                    tb.SetToolShortHelp(t.GetId(), _tb_tooltips[lbl])
        except Exception:
            pass
        # Bind Toolbox Events
        self.Bind(wx.EVT_COMBOBOX, self.onModeChange, self.comboMode )
        self.Bind(wx.EVT_COMBOBOX, self.onFormatChange, self.comboFormats )
        tb.Bind(wx.EVT_BUTTON, self.onShowLoaderMenu, self.btLoaderMenu)
        tb.Bind(wx.EVT_CHECKBOX, self.onLivePlotChange, self.cbLivePlot)
        # Populate the views combobox and menu from saved data
        self._populateViewsUI()
        self._populateRecentFilesMenu()

        # --- Status bar
        self.statusbar=self.CreateStatusBar(3, style=0)
        self.statusbar.SetStatusWidths([150, -1, 70])

        # --- Pipeline
        self.pipePanel = PipelinePanel(self, data=self.data['pipeline'], tabList=self.tabList)

        # --- Main Panel and Notebook
        self.nb = Notebook(self, id=wx.ID_ANY, style=wx.BK_DEFAULT|wx.NB_LEFT)
        #self.nb = FlatNotebook(self, id=wx.ID_ANY, style=wx.VERTICAL)

        # --- Drag and drop
        dd = FileDropTarget(self)
        self.SetDropTarget(dd)

        # --- Main Frame (self)
        self.FrameSizer = wx.BoxSizer(wx.VERTICAL)
        slSep = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.FrameSizer.Add(slSep         ,0, flag=wx.EXPAND|wx.BOTTOM,border=0)
        self.FrameSizer.Add(self.nb ,1, flag=wx.EXPAND, border=0)
        self.FrameSizer.Add(self.pipePanel,0, flag=wx.EXPAND,border=0)
        self.SetSizer(self.FrameSizer)

        self.SetSize(self.data['windowSize'])
        self.Center()
        self.Show()
        self.Bind(wx.EVT_SIZE, self.OnResizeWindow)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Shortcuts
        idFilter = wx.NewId()
        self.Bind(wx.EVT_MENU, self.onFilter, id=idFilter)
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('F'), idFilter),
        ])
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
            self.statusbar.SetStatusText('Reloading...', ISTAT)
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

        # --- Load the tables
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
        # Track recent files (only for fresh loads, not reloads)
        if not bReload and filenames:
            for p in reversed(filenames):
                self._track_recent(p)
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
        if self.nb.GetPageCount()==0:
            self.createNotebookPages()

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
            self.selPanel.setTables(self.tabList)
        # Filenames trigger 
        self.onTabListChangeLowLevel()

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


    def createNotebookPages(self):
        nb = self.nb

        self.Freeze()
        nb.file_info_tab = FileInfoPanel(nb, mainframe = self)
        nb.fields_1d_tab = Fields1DPanel(nb, mainframe = self)
        nb.fields_2d_tab = Fields2DPanel(nb, mainframe = self)
        nb.AddPage(nb.file_info_tab, "File info (beta)")
        nb.AddPage(nb.fields_1d_tab, "1D plot")
        nb.AddPage(nb.fields_2d_tab, "2D plot (beta)")
        nb.SetSelection(1)
        #nb.fields_1d_tab.SetFocus()
#         nb.SendSizeEvent()
#         self.nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_change)
        try:
            self.Thaw()
        except:
            pass
#     def update_file_list(self, filenames):
#         self.file_info_tab.lb.Set(filenames)
#         self.fields_2d_tab.lb_files.Set(filenames)



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
        # Update window title to show loaded file names
        base = PROG_NAME + ' ' + PROG_VERSION
        try:
            unique_files = list(dict.fromkeys(
                os.path.basename(self.tabList.filenames[i]) for i in range(nTabs)
                if self.tabList.filenames[i]))
            if len(unique_files) == 0:
                self.SetTitle(base)
            elif len(unique_files) <= 3:
                self.SetTitle('{} \u2014 {}'.format(base, ', '.join(unique_files)))
            else:
                self.SetTitle('{} \u2014 {} \u2026 ({} files)'.format(base, unique_files[0], len(unique_files)))
        except Exception:
            self.SetTitle(base)

    # --- Table Actions - TODO consider a table handler, or doing only the triggers
    def onTabListChangeLowLevel(self):
        fileobjects = self.tabList.unique_fileobjects
        filenames   = [fo.filename for fo in fileobjects]
        if hasattr(self, 'nb'):
            self.nb.file_info_tab.cleanGUI()
            self.nb.fields_2d_tab.cleanGUI()
            self.nb.file_info_tab.updateFiles(filenames, fileobjects) 
            self.nb.fields_2d_tab.updateFiles(filenames, fileobjects) 

    def renameTable(self, iTab, newName):
        oldName = self.tabList.renameTable(iTab, newName)
        self.selPanel.renameTable(iTab, oldName, newName)

    def deleteTabs(self, I):
        self.tabList.deleteTabs(I)
        if len(self.tabList)==0:
            self.cleanGUI()
            return
        
        self.onTabListChangeLowLevel()

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
            self._track_recent(path)

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
                self.statusbar.SetStatusText('', ISTAT)
                self.redrawCallback()
        else:
            self.statusbar.SetStatusText('Live plot OFF \u2014 press Ctrl+R to update', ISTAT)
            if hasattr(self,'plotPanel'):
                for ax in self.plotPanel.fig.axes:
                    ax.annotate('Live Plot Disabled', xy=(0.5, 0.5), size=20, xycoords='axes fraction', ha='center', va='center',)
                    self.plotPanel.canvas.draw()


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
        #if hasattr(self,'plotPanel'):
        #    del self.plotPanel
        #if hasattr(self,'selPanel'):
        #    del self.selPanel
        #if hasattr(self,'infoPanel'):
        #    del self.infoPanel
        #self.deletePages()
        #self.nb.fields_1d_tab.cleanGUI()
        self.nb.fields_2d_tab.cleanGUI()
        self.nb.file_info_tab.cleanGUI()
        self.FrameSizer.Layout()
        gc.collect()

    def onSave(self, event=None):
        # using the navigation toolbar save functionality
        if hasattr(self, 'plotPanel'):
            self.plotPanel.navTBBottom.save_figure()
        else:
            Error(self,'Open one or more file first.')

    def onAbout(self, event=None):
        import matplotlib
        io_userpath = os.path.join(weio.defaultUserDataDir(), 'pydatview_io')
        matplotlibrc = matplotlib.matplotlib_fname()
        startedpath= os.getcwd()
        aboutMsg = ' - Version:\n     {}\n'.format(PROG_NAME+' '+PROG_VERSION)
        aboutMsg += '- Started in:\n     {}\n'.format(startedpath)
        aboutMsg += '- Config file:\n     {}\n'.format(configFilePath())
        aboutMsg += '- IO data directory:\n     {}\n'.format(io_userpath)
        aboutMsg += '- matplolibrc file:\n     {}\n'.format(matplotlibrc)
        aboutMsg += '\nVisit http://github.com/ebranlard/pyDatView for documentation.'

        About(self, aboutMsg)

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
        # Check CTRL state: if held, add to existing tables (same as CTRL+drag-drop)
        bAdd = wx.GetKeyState(wx.WXK_CONTROL) and self.tabList.len() > 0
        self.selectFile(bAdd=bAdd)

    def onAdd(self, event=None):
        self.selectFile(bAdd=self.tabList.len()>0)

    def selectFile(self, bAdd=False):
        # --- File Format extension
        iFormat=self.comboFormats.GetSelection()
        sFormat=self.comboFormats.GetStringSelection()
        if iFormat==0: # auto-format
            Format = None
            view_wc = 'pyDatView views (*{})|*{}'.format(VIEW_FILE_EXT, VIEW_FILE_EXT)
            wildcard = '|'.join([n+'|*'+';*'.join(e) for n,e in zip(self.FILE_FORMATS_NAMEXT,self.FILE_FORMATS_EXTENSIONS)])
            wildcard = view_wc + '|' + wildcard
        else:
            Format = self.FILE_FORMATS[iFormat-1]
            extensions = '|*'+';*'.join(self.FILE_FORMATS[iFormat-1].extensions)
            wildcard = sFormat + extensions+'|all (*.*)|*.*'

        with wx.FileDialog(self, "Open file", wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as dlg:
            #other options: wx.CHANGE_DIR
            if dlg.ShowModal() == wx.ID_CANCEL:
               return     # the user changed their mind
            filenames = dlg.GetPaths()
            # Route view files the same way as drag-and-drop does
            view_files = [f for f in filenames if f.lower().endswith(VIEW_FILE_EXT)]
            data_files = [f for f in filenames if not f.lower().endswith(VIEW_FILE_EXT)]
            if view_files:
                self.load_view_file(view_files[0])
            elif data_files:
                self.load_files(data_files, fileformats=[Format]*len(data_files), bAdd=bAdd, bPlot=True)

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


    # --- Views: save / restore
    def _populateViewsUI(self):
        """Rebuild the Views menu items from saved views list"""
        views = self.data.get('views', [])
        # Rebuild dynamic menu items (keep Save/Export/Import + separator at top, positions 0-3)
        while self.viewsMenu.GetMenuItemCount() > 4:
            item = self.viewsMenu.FindItemByPosition(4)
            self.viewsMenu.Delete(item)
        for v in views:
            subMenu = wx.Menu()
            applyItem    = subMenu.Append(wx.ID_ANY, 'Apply view')
            applyTabItem = subMenu.Append(wx.ID_ANY, 'Apply view to current table')
            deleteItem   = subMenu.Append(wx.ID_ANY, 'Delete view')
            self.viewsMenu.AppendSubMenu(subMenu, v['name'])
            self.Bind(wx.EVT_MENU, lambda e, n=v['name']: self.onRestoreView(n),               applyItem)
            self.Bind(wx.EVT_MENU, lambda e, n=v['name']: self.onRestoreViewCurrentTable(n), applyTabItem)
            self.Bind(wx.EVT_MENU, lambda e, n=v['name']: self.onDeleteView(n),               deleteItem)

    def _track_recent(self, path):
        """Insert *path* at the top of recentFiles (capped at 30) and refresh the menu."""
        recent = self.data.get('recentFiles', [])
        abs_path = os.path.abspath(path)
        if abs_path in recent:
            recent.remove(abs_path)
        recent.insert(0, abs_path)
        self.data['recentFiles'] = recent[:30]
        self._populateRecentFilesMenu()

    def _populateRecentFilesMenu(self):
        """Rebuild the Recent Files submenu from saved recentFiles list."""
        while self.recentFilesMenu.GetMenuItemCount() > 0:
            item = self.recentFilesMenu.FindItemByPosition(0)
            self.recentFilesMenu.Delete(item)
        recent = self.data.get('recentFiles', [])
        if not recent:
            emptyItem = self.recentFilesMenu.Append(wx.ID_ANY, '(empty)')
            emptyItem.Enable(False)
        else:
            for path in recent:
                item = self.recentFilesMenu.Append(wx.ID_ANY, path)
                if path.endswith(VIEW_FILE_EXT):
                    self.Bind(wx.EVT_MENU, lambda e, p=path: self.load_view_file(p), item)
                else:
                    self.Bind(wx.EVT_MENU, lambda e, p=path: self.load_files([p]), item)

    def _capturePipelineState(self):
        """Return {action_name: data_dict} for every action currently in the pipeline."""
        if not hasattr(self, 'pipePanel'):
            return {}
        state = {}
        for action in list(self.pipePanel.actionsData) + list(self.pipePanel.actionsPlotFilters):
            state[action.name] = dict(action.data)
        return state

    def _restorePipelineState(self, pipeline_state):
        """Restore pipeline actions from a saved state dict.

        Strategy
        --------
        * PlotDataActions (Filter, Remove Outliers, Resample, Bin data):
          Non-destructive — safe to cancel and re-apply at any time.
        * ReversibleTableAction (Mask):
          cancel() calls clearMask() on each table, so the original rows
          are recovered before the saved mask is re-applied.
        * IrreversibleTableAction (Standardize Units etc.):
          Cannot be undone — left in place, not overwritten.
        """
        if not hasattr(self, 'pipePanel') or not pipeline_state:
            return
        from pydatview.plugins import DATA_PLUGINS_WITH_EDITOR, OF_DATA_PLUGINS_WITH_EDITOR
        from pydatview.pipeline import IrreversibleTableAction, AdderAction
        all_restorable = {}
        all_restorable.update(DATA_PLUGINS_WITH_EDITOR)
        all_restorable.update(OF_DATA_PLUGINS_WITH_EDITOR)

        # Step 1 – remove every restorable action that is currently active.
        # IrreversibleTableAction and AdderAction are excluded: they can't
        # be undone without a data reload so we leave them untouched.
        for name in list(all_restorable.keys()):
            existing = self.pipePanel.find(name)
            if existing is not None and not isinstance(existing, (IrreversibleTableAction, AdderAction)):
                self.pipePanel.remove(existing, cancel=True, tabList=self.tabList, updateGUI=False)

        # Step 2 – recreate each action that was active when the view was saved
        for name, saved_data in pipeline_state.items():
            if name not in all_restorable:
                continue  # Unknown or irreversible plugin — skip
            if not saved_data.get('active', False):
                continue  # Only restore actions that were active
            constructor = all_restorable[name]
            action = constructor(label=name, mainframe=self)
            # Skip AdderAction and IrreversibleTableAction — restoring these
            # without a data reload would produce duplicate or inconsistent tables.
            if isinstance(action, (IrreversibleTableAction, AdderAction)):
                continue
            action.data.update(saved_data)
            self.pipePanel.append(action, overwrite=False, apply=True,
                                  updateGUI=True, tabList=self.tabList)

    def onSaveView(self, event=None):
        """Prompt for a view name and save current state"""
        if not hasattr(self, 'selPanel') or not hasattr(self, 'plotPanel'):
            from .GUICommon import Error
            Error(self, 'Load some data and plot it before saving a view.')
            return
        dlg = wx.TextEntryDialog(self, 'Enter a name for this view:', 'Save View', '')
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        name = dlg.GetValue().strip()
        dlg.Destroy()
        if not name:
            return
        view = {
            'name':         name,
            'selection':    self.selPanel.captureViewState(),
            'plotPanel':    self.plotPanel.captureViewData(),
            'modeIndex':    self.comboMode.GetSelection(),
            'loaderOptions': dict(self.data['loaderOptions']),
            'pipeline':     self._capturePipelineState(),
        }
        # Replace existing view with same name, otherwise append
        views = self.data.get('views', [])
        for i, v in enumerate(views):
            if v['name'] == name:
                views[i] = view
                break
        else:
            views.append(view)
        self.data['views'] = views
        self._populateViewsUI()
        self.statusbar.SetStatusText('View "{}" saved.'.format(name), ISTAT)

    def onRestoreViewFromCombo(self, event=None):
        """Restore the view selected in the toolbar combobox"""
        name = self.comboViews.GetStringSelection()
        if name:
            self.onRestoreView(name)

    def onRestoreView(self, name):
        """Restore the named view"""
        if not hasattr(self, 'selPanel') or not hasattr(self, 'plotPanel'):
            return
        views = self.data.get('views', [])
        view = next((v for v in views if v['name'] == name), None)
        if view is None:
            return
        # R9 – Restore loader options (e.g. dayfirst) stored in the view
        loader_opts = view.get('loaderOptions', {})
        if loader_opts:
            self.data['loaderOptions'].update(loader_opts)
        # Restore selection mode
        modeIndex = view.get('modeIndex', 0)
        self.comboMode.SetSelection(modeIndex)
        self.selPanel.updateLayout(SEL_MODES_ID[modeIndex])
        # Restore selection state (tables + columns); collect any warnings
        warnings = self.selPanel.restoreViewState(view.get('selection', {}))
        # Restore plot settings
        self.plotPanel.restoreViewData(view.get('plotPanel', {}))
        # Restore pipeline actions (Mask, Filter, Resample, Bin data, etc.)
        self._restorePipelineState(view.get('pipeline', {}))
        # Trigger a full redraw
        self.plotPanel.load_and_draw()
        if warnings:
            Warn(self, 'View "{}" was partially restored:\n\n{}'.format(name, '\n'.join(warnings)))
            self.statusbar.SetStatusText('View "{}" partially restored.'.format(name), ISTAT)
        else:
            self.statusbar.SetStatusText('View "{}" restored.'.format(name), ISTAT)

    def onRestoreViewCurrentTable(self, name):
        """Restore view's column selections + plot settings on the currently selected table(s).

        Keeps the current table selection but resolves the view's saved column
        names (x, y, z) against each currently selected table.  If a table's
        shortname matches a saved entry that is used directly; otherwise the
        first saved selection is tried.
        """
        if not hasattr(self, 'selPanel') or not hasattr(self, 'plotPanel'):
            return
        views = self.data.get('views', [])
        view = next((v for v in views if v['name'] == name), None)
        if view is None:
            return

        selection = view.get('selection', {})
        saved_tabs = selection.get('tabSelections', {})

        # Apply formulas from the view so added columns exist before name lookup
        saved_formulas = selection.get('formulas', {})
        if saved_formulas:
            from pydatview.GUISelectionPanel import _find_tab_by_key
            full_formulas = {}
            for short_k, flist in saved_formulas.items():
                matched = _find_tab_by_key(self.tabList, short_k)
                full_formulas[matched.raw_name if matched else short_k] = flist
            self.tabList.applyFormulas(full_formulas)

        # Restore plot settings (3D mode, style, etc.)
        self.plotPanel.restoreViewData(view.get('plotPanel', {}))

        warnings = []
        ISel = self.selPanel.tabPanel.lbTab.GetSelections()
        if len(ISel) == 0 or not saved_tabs:
            self.plotPanel.load_and_draw()
            self.statusbar.SetStatusText('View "{}" settings applied.'.format(name), ISTAT)
            return

        # Collect a fallback selection (first saved entry)
        fallback_sel = next(iter(saved_tabs.values()))

        for iTab in ISel:
            if iTab >= self.tabList.len():
                continue
            tab = self.tabList[iTab]
            cols = list(tab.columns)
            full_k = tab.name
            short = _tab_shortname(tab)

            # Match by shortname first, then fall back to first saved entry
            matched_sel = saved_tabs.get(short, fallback_sel)

            # Resolve X column by name
            xName = matched_sel.get('xName')
            xSel = matched_sel.get('xSel', -1)
            if xName is not None:
                xSel = cols.index(xName) if xName in cols else -1
                if xName not in cols:
                    warnings.append('Table "{}": x-column "{}" not found'.format(short, xName))
            elif xSel >= len(cols):
                xSel = -1

            # Resolve Y columns by name
            yNames = matched_sel.get('yNames', [])
            if yNames:
                ySel = [cols.index(yn) for yn in yNames if yn in cols]
                missing = [yn for yn in yNames if yn not in cols]
                if missing:
                    warnings.append('Table "{}": column(s) not found: {}'.format(
                        short, ', '.join('"{}"'.format(n) for n in missing)))
            else:
                ySel_raw = matched_sel.get('ySel', [])
                ySel = [iy for iy in ySel_raw if 0 <= iy < len(cols)]

            # Resolve Z column by name (comboZ: 0=None, 1+=col)
            zName = matched_sel.get('zName')
            zSel = matched_sel.get('zSel', 0)
            if zName is not None:
                zSel = (cols.index(zName) + 1) if zName in cols else 0
                if zName not in cols:
                    warnings.append('Table "{}": z-column "{}" not found'.format(short, zName))
            elif zSel > len(cols):
                zSel = 0

            if full_k in self.selPanel.tabSelections:
                self.selPanel.tabSelections[full_k] = {
                    'xSel': xSel, 'ySel': tuple(ySel), 'zSel': zSel,
                }

        # Refresh column panels from the updated selections (without overwriting)
        self.selPanel.tabSelectionChanged(save=False)
        self.plotPanel.load_and_draw()
        if warnings:
            Warn(self, 'View "{}" partially applied:\n\n{}'.format(name, '\n'.join(warnings)))
            self.statusbar.SetStatusText('View "{}" partially applied.'.format(name), ISTAT)
        else:
            self.statusbar.SetStatusText('View "{}" applied to current table.'.format(name), ISTAT)

    def onDeleteView(self, name):
        """Delete the named view from the saved views list"""
        views = self.data.get('views', [])
        self.data['views'] = [v for v in views if v['name'] != name]
        self._populateViewsUI()
        self.statusbar.SetStatusText('View "{}" deleted.'.format(name), ISTAT)

    def onExportView(self, event=None):
        """Export the current view (files + selection + plot settings) to a .pdvview file"""
        if not hasattr(self, 'selPanel') or not hasattr(self, 'plotPanel'):
            Error(self, 'Load some data and plot it before exporting a view.')
            return
        if self.tabList.len() == 0:
            Error(self, 'No files are loaded.')
            return
        wildcard = 'pyDatView view (*{})|*{}'.format(VIEW_FILE_EXT, VIEW_FILE_EXT)
        with wx.FileDialog(self, 'Export view to file', wildcard=wildcard,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        if not path.lower().endswith(VIEW_FILE_EXT):
            path += VIEW_FILE_EXT
        base_dir = os.path.dirname(os.path.abspath(path))
        # Build file list with relative paths
        filenames, fileformats = self.tabList.filenames_and_formats
        files = []
        for fn, ff in zip(filenames, fileformats):
            try:
                rel = os.path.relpath(fn, base_dir)
            except ValueError:
                rel = fn  # Different drive on Windows: fall back to absolute
            files.append({'path': rel, 'format': ff.name if ff is not None else ''})
        view_data = {
            'version':       1,
            'name':          os.path.splitext(os.path.basename(path))[0],
            'files':         files,
            'loaderOptions': dict(self.data['loaderOptions']),
            'modeIndex':     self.comboMode.GetSelection(),
            'selection':     self.selPanel.captureViewState(),
            'plotPanel':     self.plotPanel.captureViewData(),
            'pipeline':      self._capturePipelineState(),
        }
        try:
            with open(path, 'w') as f:
                json.dump(view_data, f, indent=2)
            self.statusbar.SetStatusText('View exported to: {}'.format(path), ISTAT)
            self._track_recent(path)
        except Exception as e:
            Error(self, 'Failed to export view:\n{}'.format(str(e)))

    def onImportView(self, event=None):
        """Open a file dialog to pick a .pdvview file and load it"""
        wildcard = 'pyDatView view (*{})|*{}|All files (*.*)|*.*'.format(VIEW_FILE_EXT, VIEW_FILE_EXT)
        with wx.FileDialog(self, 'Import view from file', wildcard=wildcard,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        self.load_view_file(path)

    def load_view_file(self, path):
        """Load a .pdvview file: open its data files then restore the saved view state"""
        try:
            with open(path, 'r') as f:
                view_data = json.load(f)
        except Exception as e:
            Error(self, 'Failed to read view file:\n{}'.format(str(e)))
            return
        base_dir = os.path.dirname(os.path.abspath(path))
        # Resolve file paths (relative to the view file) and match formats
        filenames   = []
        fileformats = []
        missing     = []
        for entry in view_data.get('files', []):
            rel   = entry.get('path', '')
            abs_path = os.path.normpath(os.path.join(base_dir, rel))
            if not os.path.isfile(abs_path):
                missing.append(abs_path)
                continue
            fmt_name = entry.get('format', '')
            ff = next((f for f in self.FILE_FORMATS if f.name == fmt_name), None)
            filenames.append(abs_path)
            fileformats.append(ff)
        if missing:
            Warn(self, 'The following file(s) from the view could not be found:\n\n'
                       + '\n'.join(missing))
        if not filenames:
            Error(self, 'No loadable files found in the view.')
            return
        # Restore loader options stored in the view
        loader_opts = view_data.get('loaderOptions', {})
        if loader_opts:
            self.data['loaderOptions'].update(loader_opts)
        # Load the data files (bPlot=False so we can restore settings first)
        self.load_files(filenames, fileformats=fileformats, bAdd=False, bPlot=False)
        if not hasattr(self, 'selPanel') or not hasattr(self, 'plotPanel'):
            return
        # Restore view state
        modeIndex = view_data.get('modeIndex', 0)
        self.comboMode.SetSelection(modeIndex)
        self.selPanel.updateLayout(SEL_MODES_ID[modeIndex])
        warnings = self.selPanel.restoreViewState(view_data.get('selection', {}))
        self.plotPanel.restoreViewData(view_data.get('plotPanel', {}))
        # Restore pipeline actions (Mask, Filter, Resample, Bin data, etc.)
        self._restorePipelineState(view_data.get('pipeline', {}))
        self.plotPanel.load_and_draw()
        view_name = view_data.get('name', os.path.basename(path))
        if warnings:
            Warn(self, 'View "{}" was partially restored:\n\n{}'.format(view_name, '\n'.join(warnings)))
            self.statusbar.SetStatusText('View "{}" partially restored.'.format(view_name), ISTAT)
        else:
            self.statusbar.SetStatusText('View "{}" loaded from file.'.format(view_name), ISTAT)
        self._track_recent(path)

    def mainFrameUpdateLayout(self, event=None):
        if hasattr(self.nb,'fields_1d_tab'):
            try:
                self.nb.fields_1d_tab.updateSashLayout()
            except:
                print('[Fail] An error occured in mainFrameUpdateLayout')

    def OnIdle(self, event):
        if self.resized:
            self.resized = False
            if hasattr(self,'plotPanel'):
                self.plotPanel.setSubplotTight()
            #self.Thaw() # Commented see #166

    def OnResizeWindow(self, event):
        self.resized = True
        #self.Freeze() # Commented see #166
        self.Layout()


    # --- NOTEBOOK 
#     def deletePages(self):
#         for index in reversed(range(self.nb.GetPageCount())):
#             self.nb.DeletePage(index)
#         self.nb.SendSizeEvent()
#         gc.collect()
# 
#     def on_tab_change(self, event=None):
#         page_to_select = event.GetSelection()
#         wx.CallAfter(self.fix_focus, page_to_select)
#         event.Skip(True)
# 
#     def fix_focus(self, page_to_select):
#         page = self.nb.GetPage(page_to_select)
#         page.SetFocus()

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
    # Printing exception to screen
    traceback.print_exception(etype, value, trace)
    if etype==wxAssertionError:
        if wx.Platform == '__WXMAC__':
            # We skip these exceptions on macos (likely bitmap size 0)
            return
    # Then showing to user the last error
    frame = wx.GetApp().GetTopWindow()
    tmp = traceback.format_exception(etype, value, trace)
    sException=''
    if tmp[-1].find('Exception: Error:')==0:
        sException = tmp[-1][18:]
    elif tmp[-1].find('Exception: Warn:')==0:
        Warn(frame,tmp[-1][17:])
    else:
        sException = 'The following exception occured:\n\n'
        #sException += tmp[-1]  + '\n'
        #sException += tmp[-2].strip()
        #if len(tmp)>2:
        #    sException += '\n'+tmp[-3].strip()
        ## TODO make this a custom dialog where the user can copy paste the error more easily...
        sException += exception2string(value, prevStack=False)

    try:
        frame.Thaw() # Make sure any freeze event is stopped
    except:
        pass
    if len(sException)>0:
        Error(frame, sException)

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
            #print('[INFO] Setting locale to C')
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
    err = None
    # NOTE: any exceptions occurring before MainLoop will result in the window to close
    try:
        if (dataframes is not None) and (len(dataframes)>0):
            if names is None:
                names=['df{}'.format(i+1) for i in range(len(dataframes))]
            frame.load_dfs(dataframes, names)
        elif len(filenames)>0:
            frame.load_files(filenames, fileformats=None, bPlot=True)
    except Exception as e:
        try:
            frame.Thaw()
        except:
            pass
        # Print to screen:
        traceback.print_exc()
        # Store it to display it later in App
        err = 'Errors occured while loading files:\n\n'
        err += exception2string(e)

    #frame.onShowTool(toolName='Curve fitting')
    #frame.onDataPlugin(toolName='Radial Average')
    #frame.onDataPlugin(toolName='Resample')
    #frame.onScript()
    if err is not None:
        wx.FutureCall(100,  Error, frame, err)
    app.MainLoop()
    # Nothing will be reached here until the window is opened


def cmdline():
    if len(sys.argv)>1:
        pydatview(filename=sys.argv[1])
    else:
        pydatview()
