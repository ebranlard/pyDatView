import wx
import numpy as np
from pydatview.plugins.base_plugin import GUIToolPanel, TOOL_BORDER
# --------------------------------------------------------------------------------}
# --- Radial
# --------------------------------------------------------------------------------{
sAVG_METHODS = ['Last `n` seconds','Last `n` periods']
AVG_METHODS  = ['constantwindow','periods']

class RadialToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(RadialToolPanel,self).__init__(parent)

        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()

        # --- GUI
        btClose = self.getBtBitmap(self,'Close'  ,'close'  , self.destroy)
        btComp  = self.getBtBitmap(self,'Average','compute', self.onApply) # ART_PLUS

        self.lb         = wx.StaticText( self, -1, """Select tables, averaging method and average parameter (`Period` methods uses the `azimuth` signal) """)
        self.cbTabs     = wx.ComboBox(self, choices=tabListNames, style=wx.CB_READONLY)
        self.cbMethod   = wx.ComboBox(self, choices=sAVG_METHODS, style=wx.CB_READONLY)
        self.cbTabs.SetSelection(0)
        self.cbMethod.SetSelection(0)

        self.textAverageParam = wx.TextCtrl(self, wx.ID_ANY, '2',size = (36,-1), style=wx.TE_PROCESS_ENTER)

        btSizer  = wx.FlexGridSizer(rows=2, cols=1, hgap=0, vgap=0)
        #btSizer  = wx.BoxSizer(wx.VERTICAL)
        btSizer.Add(btClose   ,0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btComp    ,0, flag = wx.ALL|wx.EXPAND, border = 1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(wx.StaticText(self, -1, 'Tab:')   , 0, wx.CENTER|wx.LEFT, 0)
        row_sizer.Add(self.cbTabs                       , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Method:'), 0, wx.CENTER|wx.LEFT, 5)
        row_sizer.Add(self.cbMethod                     , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Param:') , 0, wx.CENTER|wx.LEFT, 5)
        row_sizer.Add(self.textAverageParam             , 0, wx.CENTER|wx.LEFT|wx.RIGHT| wx.EXPAND, 2)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.lb     ,0, flag =wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM,border = 5)
        vert_sizer.Add(row_sizer   ,0, flag =wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM,border = 5)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT          ,border = 5)
        self.sizer.Add(vert_sizer   ,0, flag = wx.LEFT|wx.EXPAND,border = TOOL_BORDER)
        self.SetSizer(self.sizer)
        self.Bind(wx.EVT_COMBOBOX, self.onTabChange, self.cbTabs )

    def onTabChange(self,event=None):
        tabList = self.parent.selPanel.tabList

    def onApply(self,event=None):
        try:
            avgParam     = float(self.textAverageParam.GetLineText(0))
        except:
            raise Exception('Error: the averaging parameter needs to be an integer or a float')
        iSel         = self.cbTabs.GetSelection()
        avgMethod   = AVG_METHODS[self.cbMethod.GetSelection()]
        tabList      = self.parent.selPanel.tabList
        if iSel==0:
            dfs, names, errors = tabList.radialAvg(avgMethod,avgParam)
            self.parent.addTables(dfs,names,bAdd=True)
            if len(errors)>0:
                raise Exception('Error: The filtering failed on some tables:\n\n'+'\n'.join(errors))
        else:
            dfs, names = tabList[iSel-1].radialAvg(avgMethod,avgParam)
            self.parent.addTables([dfs],[names], bAdd=True)

        self.updateTabList()

    def updateTabList(self,event=None):
        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()
        iSel=np.min([self.cbTabs.GetSelection(),len(tabListNames)])
        self.cbTabs.Clear()
        [self.cbTabs.Append(tn) for tn in tabListNames]
        self.cbTabs.SetSelection(iSel)

