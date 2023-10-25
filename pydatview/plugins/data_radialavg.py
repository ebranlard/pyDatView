import numpy as np
from pydatview.common import PyDatViewException
from pydatview.plugins.base_plugin import GUIToolPanel, TOOL_BORDER
from pydatview.plugins.base_plugin import ActionEditor

# from pydatview.common import CHAR, Error, Info, pretty_num_short
# from pydatview.common import DummyMainFrame
from pydatview.pipeline import AdderAction

_HELP = """Nodal/Radial averaging

Nodal averaging is useful to extract OpenFAST/FAST.Farm outputs as function 
of a given nodal variable(typically: the radial position along the blade span, or
the tower height, or downstream wake locations).

OpenFAST outputs these nodal variables in different channels such as: 
   B1N001Alpha(t), B1N002Alpha(t), etc.

The nodal averaging tool perform a time average of these channels, so that they can 
be plotted as function of their spatial variable (e.g. the radial position).
For the example above, the nodal averaging would return Alpha(r), with r the radial
position.

Two methods are available to perform the time averaging:
 - Last `n` seconds: average over the `n` last seconds of the time series, where `n` is, 
                     the user input parameter value. Setting `n` > tmax will correspond
                     to the entire time series.
 - Last `n` periods: average the time series over the last `n` rotor revolutions. 
                     This is the recommend approach for quasi-periodic signals
                     (such as wind turbines outputs), with a rotor.
                     The script will need a column named "Azimuth" to perform correctly.
                     
Behind the scene, the script:
 - Determines whether it is an OpenFAST or FAST.Farm output.
 - Attempts to open the OpenFAST input files to find out the nodal locations (
    (e.g., by opening the AeroDyn blade file, the ElastoDyn file, etc.)
   If the files can't be read the variables will be plotted as function of "index"
   instead of the spatial coordinates (e.g., r). 
   Better results are therefore obtained if the input files are accessible by pyDatView. 

Requirements:
  - A column named "time" (case and unit incensitive) need to be present.
  - For the period averaging, a column named "azimuth" need to be present.
  - For better results, OpenFAST inputs files should be accessible (i.e. the output file
    should not have been moved or renamed)


NOTE: 
 - The action "nodal time concatenation" takes all the time series of a given variable
   and concatenate them into one channel.
      B1Alpha =  [B1N001Alpha(t), B1N002Alpha(t), etc. ] 

"""

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
    'avgParam': 2
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
            mainframe=mainframe,
            imports  = _imports,
            data_var = _data_var,
            code     = _code
            )
    return action


# --------------------------------------------------------------------------------}
# --- Main methods
# --------------------------------------------------------------------------------{
_imports = ["from pydatview.fast.postpro import radialAvg"]
_data_var='dataRadialAvg'
_code = """dfs_new, names_new = radialAvg(filename, avgMethod=dataRadialAvg['avgMethod'], avgParam=dataRadialAvg['avgParam'], df=df, raiseException=False)"""

# add method  
def radialAvg(tab, data=None):
    """ NOTE: radial average may return several dataframe"""
    from pydatview.fast.postpro import radialAvg as radialAvgPostPro
    #print('>>> RadialAvg',data)
    dfs_new, names_new = radialAvgPostPro(filename=tab.filename, df=tab.data, avgMethod=data['avgMethod'],avgParam=data['avgParam'])
    if all(df is None for df in dfs_new):
        raise PyDatViewException('No OpenFAST radial data found for table: '+tab.nickname)

    return dfs_new, names_new

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class RadialToolPanel(ActionEditor):
    def __init__(self, parent, action=None):
        import wx # avoided at module level for unittests
        super(RadialToolPanel,self).__init__(parent, action=action, help_string=_HELP)

        # --- Creating "Fake data" for testing only!
        if action is None:
            print('[WARN] Calling GUI without an action! Creating one.')
            action = maskAction(label='dummyAction', mainframe=DummyMainFrame(parent))

        # --- GUI elements
        self.btClose = self.getBtBitmap(self,'Close'  ,'close'  , self.destroy)
        self.btAdd  = self.getBtBitmap(self,'Average','compute', self.onAdd) # ART_PLUS
        self.btHelp  = self.getBtBitmap(self, 'Help','help', self.onHelp)

        self.lb         = wx.StaticText( self, -1, """Select averaging method and average parameter (`Period` methods uses the `azimuth` signal) """)
        #self.cbTabs     = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        #self.cbTabs.Enable(False) # <<< Cancelling until we find a way to select tables and action better
       
        self.cbMethod   = wx.ComboBox(self, choices=sAVG_METHODS, style=wx.CB_READONLY)
        
        self.textAverageParam = wx.TextCtrl(self, wx.ID_ANY, '', size = (36,-1), style=wx.TE_PROCESS_ENTER)

        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=2, cols=2, hgap=0, vgap=0)
        #btSizer  = wx.BoxSizer(wx.VERTICAL)
        btSizer.Add(self.btClose   ,0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btAdd     ,0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btHelp    ,0, flag = wx.ALL|wx.EXPAND, border = 1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #row_sizer.Add(wx.StaticText(self, -1, 'Tab:')   , 0, wx.CENTER|wx.LEFT, 0)
        #row_sizer.Add(self.cbTabs                       , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Method:'), 0, wx.ALIGN_LEFT|wx.CENTER|wx.LEFT, 0)
        row_sizer.Add(self.cbMethod                     , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Param:') , 0, wx.CENTER|wx.LEFT, 5)
        row_sizer.Add(self.textAverageParam             , 0, wx.CENTER|wx.LEFT|wx.RIGHT, 2)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.lb     ,0, flag =wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM,border = 4)
        vert_sizer.Add(row_sizer   ,0, flag =wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM,border = 4)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT          ,border = 5)
        self.sizer.Add(vert_sizer   ,0, flag = wx.LEFT|wx.EXPAND,border = TOOL_BORDER)
        self.SetSizer(self.sizer)

        # --- Events
        # NOTE: getBtBitmap and getToggleBtBitmap already specify the binding
        #self.cbTabs.Bind   (wx.EVT_COMBOBOX, self.onTabChange)

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
        #iSel=np.min([self.cbTabs.GetSelection(),len(tabListNames)])
        #self.cbTabs.Clear()
        #[self.cbTabs.Append(tn) for tn in tabListNames]
        #self.cbTabs.SetSelection(iSel)
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
