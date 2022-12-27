import wx
import numpy as np
from pydatview.common import CHAR, Error, Info, pretty_num_short
from pydatview.common import DummyMainFrame
# from pydatview.plotdata import PlotData
# from pydatview.pipeline import PlotDataAction


TOOL_BORDER=15

# --------------------------------------------------------------------------------}
# --- Default class for tools
# --------------------------------------------------------------------------------{
class GUIToolPanel(wx.Panel):
    def __init__(self, parent):
        super(GUIToolPanel,self).__init__(parent)
        self.parent   = parent

    def destroyData(self):
        if hasattr(self, 'action'):
            if self.action is not None:
                # cleanup action calls
                self.action.guiEditorObj = None
                self.action = None

    def destroy(self,event=None): # TODO rename to something less close to Destroy
        self.destroyData()
        self.parent.removeTools()

    def getBtBitmap(self,par,label,Type=None,callback=None,bitmap=False):
        if Type is not None:
            label=CHAR[Type]+' '+label

        bt=wx.Button(par,wx.ID_ANY, label, style=wx.BU_EXACTFIT)
        #try:
        #    if bitmap is not None:    
        #            bt.SetBitmapLabel(wx.ArtProvider.GetBitmap(bitmap)) #,size=(12,12)))
        #        else:
        #except:
        #    pass
        if callback is not None:
            par.Bind(wx.EVT_BUTTON, callback, bt)
        return bt

    def getToggleBtBitmap(self,par,label,Type=None,callback=None,bitmap=False):
        if Type is not None:
            label=CHAR[Type]+' '+label
        bt=wx.ToggleButton(par,wx.ID_ANY, label, style=wx.BU_EXACTFIT)
        if callback is not None:
            par.Bind(wx.EVT_TOGGLEBUTTON, callback, bt)
        return bt

