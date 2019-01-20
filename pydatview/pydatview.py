from __future__ import division, unicode_literals, print_function, absolute_import
from builtins import map, range, chr, str
from io import open
from future import standard_library
standard_library.install_aliases()

import numpy as np
import os.path 
import pandas as pd
import sys
import traceback 
import gc

#  GUI
import wx
from .GUIPlotPanel import PlotPanel
from .GUISelectionPanel import SelectionPanel,SEL_MODES,SEL_MODES_ID
from .GUISelectionPanel import ColumnPopup,TablePopup
from .GUIInfoPanel import InfoPanel
from .Tables import Table, haveSameColumns
# Helper
from .common import *
# Librairies
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
BOT_PANL =85

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
      if len(filenames)>0:
          # If Ctrl is pressed we add
          bAdd= wx.GetKeyState(wx.WXK_CONTROL);
          self.parent.load_files(filenames,fileformat=None,bAdd=bAdd)
      return True




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
        # --- GUI
        #font = self.GetFont()
        #print(font.GetFamily(),font.GetStyle(),font.GetPointSize())
        #font.SetFamily(wx.FONTFAMILY_DEFAULT)
        #font.SetFamily(wx.FONTFAMILY_MODERN)
        #font.SetFamily(wx.FONTFAMILY_SWISS)
        #font.SetPointSize(8)
        #print(font.GetFamily(),font.GetStyle(),font.GetPointSize())
        #self.SetFont(font) 
        # --- Menu
        menuBar = wx.MenuBar()

        fileMenu = wx.Menu()
        loadMenuItem  = fileMenu.Append(wx.ID_NEW,"Open file" ,"Open file"           )
        saveMenuItem  = fileMenu.Append(wx.ID_SAVE,"Save figure" ,"Save figure"           )
        exitMenuItem  = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
        menuBar.Append(fileMenu, "&File")
        self.Bind(wx.EVT_MENU,self.onExit ,exitMenuItem )
        self.Bind(wx.EVT_MENU,self.onLoad ,loadMenuItem )
        self.Bind(wx.EVT_MENU,self.onSave ,saveMenuItem )

        toolMenu = wx.Menu()
        dmpDecayMenuItem  = toolMenu.Append(wx.ID_ANY, 'Damping from decay')
        menuBar.Append(toolMenu, "&Tools")
        self.Bind(wx.EVT_MENU,self.onDamping,dmpDecayMenuItem)

        helpMenu = wx.Menu()
        aboutMenuItem = helpMenu.Append(wx.NewId(), 'About', 'About')
        menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU,self.onAbout,aboutMenuItem)

        # --- ToolBar
        tb = self.CreateToolBar(wx.TB_HORIZONTAL|wx.TB_TEXT|wx.TB_HORZ_LAYOUT)
        self.toolBar = tb 
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
        #bmp = wx.Bitmap('help.png') #wx.Bitmap("NEW.BMP", wx.BITMAP_TYPE_BMP) 
        self.AddTBBitmapTool(tb,"Open"  ,wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN),self.onLoad)
        self.AddTBBitmapTool(tb,"Reload",wx.ArtProvider.GetBitmap(wx.ART_REDO),self.onReload)
        try:
            self.AddTBBitmapTool(tb,"Add"   ,wx.ArtProvider.GetBitmap(wx.ART_PLUS),self.onAdd)
        except:
            self.AddTBBitmapTool(tb,"Add"   ,wx.ArtProvider.GetBitmap(wx.FILE_OPEN),self.onAdd)
        #self.AddTBBitmapTool(tb,"Debug" ,wx.ArtProvider.GetBitmap(wx.ART_ERROR),self.onAdd)
        tb.AddStretchableSpace()
        tb.Realize() 

        # --- Status bar
        self.statusbar=self.CreateStatusBar(3, style=0)
        self.statusbar.SetStatusWidths([230, -1, 70])

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
        self.SetSizer(self.FrameSizer)

        self.SetSize((800, 600))
        self.Center()

        self.Show()

    def AddTBBitmapTool(self,tb,label,bitmap,callback=None,Type=None):
        """ Adding a toolbar tool, safe depending on interface"""
        # Modern API
        if Type is None or Type==0:
            try:
                tl = tb.AddTool( -1, bitmap=bitmap, label=label )
                if callback is not None:
                    tb.Bind(wx.EVT_TOOL, callback, tl)
                return tl
            except:
                Type=None
        # Old fashion API
        if Type is None or Type==1:
            try:
                tl = tb.AddLabelTool( -1, bitmap=bitmap, label=label )
                if callback is not None:
                    tb.Bind(wx.EVT_TOOL, callback, tl)
                return tl
            except:
                Type=None
        # Using a Bitmap 
        if Type is None or Type==2:
            try:
                bt=wx.Button(tb,wx.ID_ANY, " "+label+" ", style=wx.BU_EXACTFIT)
                bt.SetBitmapLabel(bitmap)
                tl=tb.AddControl(bt)
                if callback is not None:
                    tb.Bind(wx.EVT_BUTTON, callback, bt)
                return tl
            except:
                Type=None
        # Last resort, we add a button only
        bt=wx.Button(tb,wx.ID_ANY, label)
        tl=tb.AddControl(bt)
        if callback is not None:
            tb.Bind(wx.EVT_BUTTON, callback, bt)
        return tl


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
            if hasattr(self,'selPanel'):
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
        except weio.FileNotFoundError as e:
            Error(self, 'A file was not found!\n\n While opening:\n\n {}\n\n the following file was not found:\n\n {}'.format(filename, e.filename))
            return []
        except IOError:
            Error(self, 'IO Error thrown while opening file: '+filename )
            return []
        except MemoryError:
            Error(self,'Insufficient memory!\n\nFile: '+filename+'\n\nTry closing and reopening the program, or use a 64 bit version of this program (i.e. of python).')
            return []
        except weio.EmptyFileError:
            Error(self,'File empty!\n\nFile is empty: '+filename+'\n\nOpen a different file.')
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
            #self.vSplitter = wx.SplitterWindow(self.nb)
            self.vSplitter = wx.SplitterWindow(self.MainPanel)
            self.selPanel = SelectionPanel(self.vSplitter, self.tabs, mode=mode, mainframe=self)
            self.tSplitter = wx.SplitterWindow(self.vSplitter)
            #self.tSplitter.SetMinimumPaneSize(20)
            self.infoPanel = InfoPanel(self.tSplitter)
            self.plotPanel = PlotPanel(self.tSplitter, self.selPanel, self.infoPanel)
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
        self.infoPanel.empty()
        self.selPanel.clean_memory()
        # Updating tables
        self.selPanel.update_tabs(self.tabs)
        # Trigger a replot
        self.onTabSelectionChange()

    def exportTab(self, iTab):
        default_filename=os.path.splitext(os.path.basename(self.tabs[iTab].filename))[0]+'.csv'
        with wx.FileDialog(self, "Save to CSV file",defaultFile=default_filename,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
                #, wildcard="CSV files (*.csv)|*.csv",
            dlg.CentreOnParent()
            if dlg.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            if isinstance(self.tabs[iTab].data, pd.DataFrame):
                try:
                    self.tabs[iTab].data.to_csv(dlg.GetPath(),sep=',',index=False) #python3
                except:
                    self.tabs[iTab].data.to_csv(dlg.GetPath(),sep=str(u',').encode('utf-8'),index=False) #python 2.
            else:
                raise NotImplementedError('Export of data that is not a dataframe')

    def onDamping(self, event=None):
        if not hasattr(self,'plotPanel'):
            Error(self,'Plot some data first')
            return
        self.plotPanel.showTool('LogDec')

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
            #self.showStats()

#     def showStats(self):
#         self.infoPanel.showStats(self.plotPanel.plotData,self.plotPanel.pltTypePanel.plotType())

    def onExit(self, event):
        self.Close()

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
        Info(self,PROG_NAME+' '+PROG_VERSION+'\n\nWritten by E. Branlard. \n\nVisit http://github.com/ebranlard/pyDatView for documentation.')

    def onReload(self, event=None):
        filenames = self.filenames
        if len(filenames)>0:
            iFormat=self.comboFormats.GetSelection()
            if iFormat==0: # auto-format
                Format = None
            else:
                Format = FILE_FORMATS[iFormat-1]
            self.load_files(filenames,fileformat=Format,bReload=True,bAdd=False)
        else:
           Error(self,'Open one or more file first.')

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
def test(filenames=None):
    if filenames is not None:
        app = wx.App(False)
        frame = MainFrame()
        frame.load_files(filenames,fileformat=None)
        return

    import time
    import sys
    from .perfmon import PerfMon
    from .GUISelectionPanel import ellude_common
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
        frame.plotPanel.pltTypePanel.cbFFT.SetValue(True)
        #frame.plotPanel.cbLogX.SetValue(True)
        #frame.plotPanel.cbLogY.SetValue(True)
        frame.plotPanel.redraw()
        frame.plotPanel.pltTypePanel.cbFFT.SetValue(False)
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
        frame.plotPanel.pltTypePanel.cbFFT.SetValue(True)
        frame.plotPanel.redraw()
        frame.plotPanel.pltTypePanel.cbFFT.SetValue(False)
    #app.MainLoop()

 
# --------------------------------------------------------------------------------}
# --- Mains 
# --------------------------------------------------------------------------------{
def pydatview(dataframe=None,filenames=[]):
    """
    The main function to start the data frame GUI.
    """
    try:
        app = wx.App(False)
    except:
        print("MacOS Error:")
        print("   This program needs access to the screen. Please run with a")
        print("   Framework build of python, and only when you are logged in")
        print("   on the main display of your Mac.")
        print("")
        print("pyDatView help:")
        print("   You see the error above because you are using a Mac and ")
        print("   the python executable you are using does not have access to")
        print("   your screen. This is a Mac issue, not a pyDatView issue.")
        print("   Instead of calling 'python pyDatView.py', you need to find")
        print("   another python and do '/path/python pyDatView.py'")
        print("   You can try './pythonmac pyDatView.py', a script provided")
        print("   in this repository to detect the path (in some cases)")
        print("   ")
        print("   You can find additional help in the file 'README.md'.")
        print("   ")
        print("   For quick reference, here are some typical cases:")
        print("   - Your python was installed with 'brew', then likely use   ")
        print("        /usr/lib/Cellar/python/XXXXX/Frameworks/python.framework/Versions/XXXX/bin/pythonXXX");
        print("   - Your python is an anaconda python, use something like:");
        print("        /anaconda3/bin/python.app   (NOTE: the '.app'!")
        print("   - You are using a python 2 version, you can use the system one:")
        print("        /Library/Frameworks/Python.framework/Versions/XXX/bin/pythonXXX")
        print("        /System/Library/Frameworks/Python.framework/Versions/XXX/bin/pythonXXX")
        return

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
