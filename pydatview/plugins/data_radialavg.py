import numpy as np
from pydatview.plugins.base_plugin import GUIToolPanel, TOOL_BORDER
from pydatview.plugins.base_plugin import ActionEditor

# from pydatview.common import CHAR, Error, Info, pretty_num_short
# from pydatview.common import DummyMainFrame
from pydatview.pipeline import AdderAction


# --------------------------------------------------------------------------------}
# --- Radial
# --------------------------------------------------------------------------------{
sAVG_METHODS = ['Last `n` seconds','Last `n` periods']
AVG_METHODS  = ['constantwindow','periods']

# --------------------------------------------------------------------------------}
# --- Data
# --------------------------------------------------------------------------------{
_DEFAULT_DICT={
    'active':False, 
    'avgMethod':'constantwindow', 
    'avgParam': '2'
}

# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def radialAvgAction(label, mainframe, data=None):
    """
    Return an "action" for the current plugin, to be used in the pipeline.
    The action is also edited and created by the GUI Editor
    """
    if data is None:
        # NOTE: if we don't do copy below, we will end up remembering even after the action was deleted
        #       its not a bad feature, but we might want to think it through
        #       One issue is that "active" is kept in memory
        data=_DEFAULT_DICT
        data['active'] = False #<<< Important

    #guiCallback = mainframe.redraw
    if mainframe is not None:
        # TODO TODO TODO Clean this up
        def guiCallback():
            if hasattr(mainframe,'selPanel'):
                mainframe.selPanel.colPanel1.setColumns()
                mainframe.selPanel.colPanel2.setColumns()
                mainframe.selPanel.colPanel3.setColumns()
                mainframe.onTabSelectionChange()             # trigger replot
            if hasattr(mainframe,'pipePanel'):
                pass

    action = AdderAction(
            name=label,
            tableFunctionAdd   = radialAvg,
#             tableFunctionApply = applyMask,
#             tableFunctionCancel = removeMask,
            guiEditorClass = RadialToolPanel,
            guiCallback = guiCallback,
            data = data,
            mainframe=mainframe
            )
    return action


# --------------------------------------------------------------------------------}
# --- Main methods
# --------------------------------------------------------------------------------{
# add method  
def radialAvg(tab, data=None):
    """ NOTE: radial average may return several dataframe"""
    #print('>>> RadialAvg',data)
    dfs_new, names_new = tab.radialAvg(data['avgMethod'],data['avgParam'])
    return dfs_new, names_new

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class RadialToolPanel(ActionEditor):
    def __init__(self, parent, action=None):
        import wx # avoided at module level for unittests
        super(RadialToolPanel,self).__init__(parent, action=action)

        # --- Creating "Fake data" for testing only!
        if action is None:
            print('[WARN] Calling GUI without an action! Creating one.')
            action = maskAction(label='dummyAction', mainframe=DummyMainFrame(parent))

        # --- GUI elements
        self.btClose = self.getBtBitmap(self,'Close'  ,'close'  , self.destroy)
        self.btAdd  = self.getBtBitmap(self,'Average','compute', self.onAdd) # ART_PLUS

        self.lb         = wx.StaticText( self, -1, """Select tables, averaging method and average parameter (`Period` methods uses the `azimuth` signal) """)
        self.cbTabs     = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        self.cbTabs.Enable(False) # <<< Cancelling until we find a way to select tables and action better
       
        self.cbMethod   = wx.ComboBox(self, choices=sAVG_METHODS, style=wx.CB_READONLY)
        
        self.textAverageParam = wx.TextCtrl(self, wx.ID_ANY, '', size = (36,-1), style=wx.TE_PROCESS_ENTER)

        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=2, cols=1, hgap=0, vgap=0)
        #btSizer  = wx.BoxSizer(wx.VERTICAL)
        btSizer.Add(self.btClose   ,0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btAdd    ,0, flag = wx.ALL|wx.EXPAND, border = 1)

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

        # --- Events
        # NOTE: getBtBitmap and getToggleBtBitmap already specify the binding
        self.cbTabs.Bind   (wx.EVT_COMBOBOX, self.onTabChange)

        # --- Init triggers
        self._Data2GUI()
        #self.onToggleApply(init=True)
        self.updateTabList()

    # --- Implementation specific
    

    # --- Table related
    def onTabChange(self,event=None):
        tabList = self.parent.selPanel.tabList

    def updateTabList(self,event=None):
        tabListNames = ['All opened tables']+self.tabList.getDisplayTabNames()
        #try:
        iSel=np.min([self.cbTabs.GetSelection(),len(tabListNames)])
        self.cbTabs.Clear()
        [self.cbTabs.Append(tn) for tn in tabListNames]
        self.cbTabs.SetSelection(iSel)
        #except RuntimeError:
        #    pass

    # --- Fairly generic
    def _GUI2Data(self):
        try:
            self.data['avgParam'] = float(self.textAverageParam.GetLineText(0))
        except:
            raise Exception('Error: the averaging parameter needs to be an integer or a float')
        self.data['avgMethod'] = AVG_METHODS[self.cbMethod.GetSelection()]
        #iSel         = self.cbTabs.GetSelection()
        #iSel         = self.cbTabs.GetSelection()
        #tabList      = self.parent.selPanel.tabList

    def _Data2GUI(self):
        iSel = AVG_METHODS.index(self.data['avgMethod'])
        self.cbMethod.SetSelection(iSel)
        self.textAverageParam.SetValue(str(self.data['avgParam']))



if __name__ == '__main__':
    from pydatview.plugins.base_plugin import demoGUIPlugin
    demoGUIPlugin(RadialToolPanel, actionCreator=radialAvgAction, mainLoop=False, title='Radial Avg')
