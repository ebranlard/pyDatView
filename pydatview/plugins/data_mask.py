import wx
import numpy as np
from pydatview.plugins.base_plugin import ActionEditor, TOOL_BORDER
from pydatview.common import CHAR, Error, Info, pretty_num_short
from pydatview.common import DummyMainFrame
from pydatview.pipeline import ReversibleTableAction
# --------------------------------------------------------------------------------}
# --- Data
# --------------------------------------------------------------------------------{
_DEFAULT_DICT={
    'active':False, 
    'maskString': ''
    # 'nBins':50
}

# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def maskAction(label, mainframe, data=None):
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

    guiCallback = mainframe.redraw

    action = ReversibleTableAction(
            name=label,
            tableFunctionAdd   = addTabMask,
            tableFunctionApply = applyMask,
            tableFunctionCancel = removeMask,
            guiEditorClass = MaskToolPanel,
            guiCallback = guiCallback,
            data = data,
            mainframe=mainframe
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main methods
# --------------------------------------------------------------------------------{
def applyMask(tab, data):
    #    dfs, names, errors = tabList.applyCommonMaskString(maskString, bAdd=False)
    dfs, name = tab.applyMaskString(data['maskString'], bAdd=False)

def removeMask(tab, data):
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> CLEAR MASK')
    tab.clearMask()
    #    tabList.clearCommonMask()

def addTabMask(tab, opts):
    """ Apply action on a a table and return a new one with a new name 
    df_new, name_new = f(t, opts)
    """
    df_new, name_new = tab.applyMaskString(opts['maskString'], bAdd=True)
    return df_new, name_new 

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the mask action
# --------------------------------------------------------------------------------{
class MaskToolPanel(ActionEditor):
    def __init__(self, parent, action):
        ActionEditor.__init__(self, parent, action=action)

        # --- Creating "Fake data" for testing only!
        if action is None:
            print('[WARN] Calling GUI without an action! Creating one.')
            action = maskAction(label='dummyAction', mainframe=DummyMainFrame(parent))

        # --- GUI elements
        self.btClose = self.getBtBitmap(self, 'Close','close', self.destroy)
        self.btAdd   = self.getBtBitmap(self, u'Mask (add)','add'  , self.onAdd)
        self.btApply = self.getToggleBtBitmap(self, 'Apply','cloud', self.onToggleApply)

        self.cbTabs     = wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
        self.cbTabs.Enable(False) # <<< Cancelling until we find a way to select tables and action better

        self.lb         = wx.StaticText( self, -1, """(Example of mask: "({Time}>100) && ({Time}<50) && ({WS}==5)"    or    "{Date} > '2018-10-01'")""")
        self.textMask = wx.TextCtrl(self, wx.ID_ANY, 'Dummy', style = wx.TE_PROCESS_ENTER)
        #self.textMask.SetValue('({Time}>100) & ({Time}<400)')
        #self.textMask.SetValue("{Date} > '2018-10-01'")

        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=2, cols=2, hgap=2, vgap=0)
        btSizer.Add(self.btClose                ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(wx.StaticText(self, -1, '') ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btAdd                  ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btApply                ,0,flag = wx.ALL|wx.EXPAND, border = 1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(wx.StaticText(self, -1, 'Tab:')   , 0, wx.CENTER|wx.LEFT, 0)
        row_sizer.Add(self.cbTabs                       , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Mask:'), 0, wx.CENTER|wx.LEFT, 5)
        row_sizer.Add(self.textMask, 1, wx.CENTER|wx.LEFT|wx.EXPAND, 5)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.lb     ,0, flag = wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM, border = 5)
        vert_sizer.Add(row_sizer   ,1, flag = wx.EXPAND|wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM, border = 5)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT           ,border = 5)
        self.sizer.Add(vert_sizer   ,1, flag = wx.LEFT|wx.EXPAND ,border = TOOL_BORDER)
        self.SetSizer(self.sizer)

        # --- Events
        # NOTE: getBtBitmap and getToggleBtBitmap already specify the binding
        self.cbTabs.Bind   (wx.EVT_COMBOBOX, self.onTabChange)
        self.textMask.Bind(wx.EVT_TEXT_ENTER, self.onParamChangeAndPressEnter)

        # --- Init triggers
        self._Data2GUI()
        self.onToggleApply(init=True)
        self.updateTabList()

    # --- Implementation specific
    def guessMask(self):
        cols=self.tabList[0].columns_clean
        if 'Time' in cols:
            return '{Time} > 10'
        elif 'Date' in cols:
            return "{Date} > '2017-01-01"
        else:
            if len(cols)>1:
                return '{'+cols[1]+'}>0'
            else:
                return ''

    # --- Bindings for plot triggers on parameters changes
    def onParamChangeAndPressEnter(self, event=None):
        # We apply
        if self.data['active']:
            self.action.apply(self.tabList, force=True)
            self.action.updateGUI() # We call the guiCallback
        else:
            # We assume that "enter" means apply
            self.onToggleApply()

    # --- Table related
    def onTabChange(self,event=None):
        iSel=self.cbTabs.GetSelection()
        # TODO need a way to retrieve "data" from action, perTab
        if iSel==0:
            maskString = self.tabList.commonMaskString  # for "all"
        else:
            maskString = self.tabList[iSel-1].maskString # -1, because "0" is for "all"
        if len(maskString)>0:
            self.textMask.SetValue(maskString)

    def updateTabList(self,event=None):
        tabListNames = ['All opened tables']+self.tabList.getDisplayTabNames()
        #try:
        iSel=np.min([self.cbTabs.GetSelection(),len(tabListNames)])
        self.cbTabs.Clear()
        [self.cbTabs.Append(tn) for tn in tabListNames]
        self.cbTabs.SetSelection(iSel)
        #except RuntimeError:
        #    pass
          
    # --- External Calls
    def cancelAction(self):
        """ set the GUI state when the action is cancelled"""
        self.btApply.SetLabel(CHAR['cloud']+' Mask')
        self.btApply.SetValue(False)
        self.data['active'] = False

    def guiActionAppliedState(self):
        """ set the GUI state when the action is applied"""
        self.btApply.SetLabel(CHAR['sun']+' Clear')
        self.btApply.SetValue(True)
        self.data['active'] = True

    # --- Fairly generic
    def _GUI2Data(self):
        self.data['maskString'] = self.textMask.GetLineText(0)
        #iSel         = self.cbTabs.GetSelection()
        #tabList      = self.parent.selPanel.tabList

    def _Data2GUI(self):
        if len(self.data['maskString'])==0:
            self.data['maskString'] = self.guessMask() # no known mask, we guess one to help the user
        self.textMask.SetValue(self.data['maskString'])

