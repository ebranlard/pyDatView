""" 
"""
import wx
from pydatview.GUIPlotPanel import PlotPanel
from pydatview.GUIInfoPanel import InfoPanel
from pydatview.GUISelectionPanel import SelectionPanel, SEL_MODES_ID
# from pydatview.GUISelectionPanel import SelectionPanel,SEL_MODES,SEL_MODES_ID
# from pydatview.GUISelectionPanel import ColumnPopup,TablePopup
# from pydatview.GUIPipelinePanel import PipelinePanel
# from pydatview.GUIToolBox import GetKeyString, TBAddTool
# from pydatview.Tables import TableList, Table


SIDE_COL       = [160,160,300,420,530]
SIDE_COL_LARGE = [200,200,360,480,600]
BOT_PANL =85

class Fields1DPanel(wx.SplitterWindow): # TODO Panel

    def __init__(self, parent, mainframe):
        # Superclass constructor
        super(Fields1DPanel, self).__init__(parent)
        # Data
        self.parent = parent
        self.mainframe = mainframe

        self.vSplitter = self # Backward compatibility

        # --- Create a selPanel, plotPanel and infoPanel
        mode = SEL_MODES_ID[mainframe.comboMode.GetSelection()]
        self.selPanel = SelectionPanel(self.vSplitter, mainframe.tabList, mode=mode, mainframe=mainframe)
        self.tSplitter = wx.SplitterWindow(self.vSplitter)
        #self.tSplitter.SetMinimumPaneSize(20)
        self.infoPanel = InfoPanel(self.tSplitter, data=mainframe.data['infoPanel'])
        self.plotPanel = PlotPanel(self.tSplitter, self.selPanel, infoPanel=self.infoPanel, pipeLike=mainframe.pipePanel, data=mainframe.data['plotPanel'])
        self.livePlotFreezeUnfreeze() # Dont enable panels if livePlot is not allowed
        self.tSplitter.SetSashGravity(0.9)
        self.tSplitter.SplitHorizontally(self.plotPanel, self.infoPanel)
        self.tSplitter.SetMinimumPaneSize(BOT_PANL)
        self.tSplitter.SetSashGravity(1)
        self.tSplitter.SetSashPosition(400)

        self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
        self.vSplitter.SetMinimumPaneSize(SIDE_COL[0])
        self.tSplitter.SetSashPosition(SIDE_COL[0])


        # --- Bind 
        # The selPanel does the binding, but the callback is stored here because it involves plotPanel... TODO, rethink it
        #self.selPanel.bindColSelectionChange(self.onColSelectionChangeCallBack)
        self.selPanel.setTabSelectionChangeCallback(mainframe.onTabSelectionChangeTrigger)
        self.selPanel.setRedrawCallback(mainframe.redrawCallback)
        self.selPanel.setUpdateLayoutCallback(mainframe.mainFrameUpdateLayout)
        self.plotPanel.setAddTablesCallback(mainframe.load_dfs)

        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, mainframe.onSashChangeMain, self.vSplitter)

        # --- Mainframe backward compatibility
        mainframe.selPanel  = self.selPanel
        mainframe.plotPanel = self.plotPanel
        mainframe.infoPanel = self.infoPanel


    def updateSashLayout(self, event=None):
#         try:
        nWind = self.selPanel.splitter.nWindows
        if self.Size[0]<=800:
            sash=SIDE_COL[nWind]
        else:
            sash=SIDE_COL_LARGE[nWind]
        self.resizeSideColumn(sash)
#         except:
#             print('[Fail] An error occured in mainFrameUpdateLayout')


    # --- Side column
    def resizeSideColumn(self,width):
        # To force the replot we do an epic unsplit/split...
        #self.vSplitter.Unsplit()
        #self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
        self.vSplitter.SetMinimumPaneSize(width)
        self.vSplitter.SetSashPosition(width)
        #self.selPanel.splitter.setEquiSash()

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

