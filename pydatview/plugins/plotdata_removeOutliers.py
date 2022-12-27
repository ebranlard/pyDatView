import wx
import numpy as np
from pydatview.plugins.base_plugin import GUIToolPanel, TOOL_BORDER
from pydatview.plugins.plotdata_default_plugin import PlotDataActionEditor
from pydatview.common import Error, Info
from pydatview.pipeline import PlotDataAction
import platform
# --------------------------------------------------------------------------------}
# --- Data
# --------------------------------------------------------------------------------{
_DEFAULT_DICT={
    'active':False, 
    'medianDeviation':5
}
# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def removeOutliersAction(label, mainframe, data=None):
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

    action = PlotDataAction(
            name             = label,
            plotDataFunction = removeOutliersXY,
            guiEditorClass   = RemoveOutliersToolPanel,
            guiCallback      = guiCallback,
            data             = data,
            mainframe        = mainframe
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
def removeOutliersXY(x, y, opts):
    from pydatview.tools.signal_analysis import reject_outliers
    try:
        x, y = reject_outliers(y, x, m=opts['medianDeviation'])
    except:
        raise Exception('Warn: Outlier removal failed. Desactivate it or use a different signal. ')
    return x, y

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class RemoveOutliersToolPanel(PlotDataActionEditor):

    def __init__(self, parent, action, **kwargs):
        PlotDataActionEditor.__init__(self, parent, action, tables=False, buttons=[''], **kwargs)

        # --- GUI elements
        #self.btClose = self.getBtBitmap(self,'Close','close',self.destroy)
        #self.btApply = self.getToggleBtBitmap(self,'Apply','cloud',self.onToggleApply)

        lb1 = wx.StaticText(self, -1, 'Median deviation:')
        self.tMD = wx.SpinCtrlDouble(self, value='11', size=wx.Size(60,-1))
        self.tMD.SetValue(5)
        self.tMD.SetRange(0.0, 1000)
        self.tMD.SetIncrement(0.5)
        self.tMD.SetDigits(1)
        self.lb = wx.StaticText( self, -1, '')
        
        # --- Layout        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
#         self.sizer.Add(self.btClose,0,flag = wx.LEFT|wx.CENTER,border = 1)
#         self.sizer.Add(self.btApply,0,flag = wx.LEFT|wx.CENTER,border = 5)
        hsizer.Add(lb1         ,0,flag = wx.LEFT|wx.CENTER,border = 5)
        hsizer.Add(self.tMD    ,0,flag = wx.LEFT|wx.CENTER,border = 5)
        hsizer.Add(self.lb     ,0,flag = wx.LEFT|wx.CENTER,border = 5)

        self.sizer.Add(hsizer  ,0,flag = wx.LEFT|wx.CENTER,border = 5)
        self.SetSizer(self.sizer)

        # --- Events
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.onParamChangeArrow, self.tMD)
        self.Bind(wx.EVT_TEXT_ENTER,     self.onParamChangeEnter, self.tMD)

        if platform.system()=='Windows':
            # See issue https://github.com/wxWidgets/Phoenix/issues/1762
            self.spintxt = self.tMD.Children[0]
            assert isinstance(self.spintxt, wx.TextCtrl)
            self.spintxt.Bind(wx.EVT_CHAR_HOOK, self.onParamChangeChar)
            
        # --- Init triggers
        self._Data2GUI()        
        self.onToggleApply(init=True)

    # --- Bindings for plot triggers on parameters changes
#     def onParamChange(self, event=None):
#         self._GUI2Data()
#         if self.data['active']:
#             self.parent.load_and_draw() # Data will change
# 
#     def onParamChangeArrow(self, event):
#         self.onParamChange()
#         event.Skip()
# 
#     def onParamChangeEnter(self, event):
#         self.onParamChange()
#         event.Skip()
# 
#     def onParamChangeChar(self, event):
#         event.Skip()  
#         code = event.GetKeyCode()
#         if code in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
#             #print(self.spintxt.Value)
#             self.tMD.SetValue(self.spintxt.Value)
#             self.onParamChangeEnter(event)

    # --- Table related
    # --- External Calls
    def cancelAction(self):
        """ do cancel the action"""
        self.lb.SetLabel('Click on "Apply" to remove outliers on the fly for all new plot.')
        PlotDataActionEditor.cancelAction(self)

#         self.btApply.SetLabel(CHAR['cloud']+' Apply')
#         self.btApply.SetValue(False)
#         self.data['active'] = False     
#         if redraw:
#             self.parent.load_and_draw() # Data will change based on plotData 

    # --- Fairly generic
    def _GUI2Data(self):
        self.data['medianDeviation'] = float(self.tMD.Value)

    def _Data2GUI(self):
        self.tMD.SetValue(self.data['medianDeviation'])
# 
#     def onToggleApply(self, event=None, init=False):
# 
#         if not init:
#             self.data['active'] = not self.data['active']
# 
#         if self.data['active']:
#             self._GUI2Data()
#             self.lb.SetLabel('Outliers are now removed on the fly. Click "Clear" to stop.')
#             self.btApply.SetLabel(CHAR['sun']+' Clear')
#             self.btApply.SetValue(True)            
#             # The action is now active we add it to the pipeline, unless it's already in it
#             if self.mainframe is not None:
#                 self.mainframe.addAction(self.action, overwrite=True)
#             if not init:
#                 self.parent.load_and_draw() # filter will be applied in plotData.py
#         else:
#             # We remove our action from the pipeline
#             if not init:
#                 if self.mainframe is not None:
#                     self.mainframe.removeAction(self.action)          
#             self.cancelAction(redraw= not init)

if __name__ == '__main__':
    from pydatview.plugins.plotdata_default_plugin import demoPlotDataActionPanel

    demoPlotDataActionPanel(RemoveOutliersToolPanel, plotDataFunction=removeOutliersXY, data=_DEFAULT_DICT)
