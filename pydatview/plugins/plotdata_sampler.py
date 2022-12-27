import wx
import numpy as np
from pydatview.plugins.base_plugin import PlotDataActionEditor, TOOL_BORDER
from pydatview.common import Error, Info
from pydatview.pipeline import PlotDataAction
# --------------------------------------------------------------------------------}
# --- Data
# --------------------------------------------------------------------------------{
# See SAMPLERS in signal_analysis
_DEFAULT_DICT={
    'active':False, 
    'name':'Every n', 
    'param':2, 
    'paramName':'n'
}
# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def samplerAction(label, mainframe, data=None):
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
            tableFunctionAdd = samplerTabAdd,
            plotDataFunction = samplerXY,
            guiEditorClass   = SamplerToolPanel,
            guiCallback      = guiCallback,
            data             = data,
            mainframe        = mainframe
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
def samplerXY(x, y, opts):
    from pydatview.tools.signal_analysis import applySampler
    x_new, y_new = applySampler(x, y, opts)
    return x_new, y_new

def samplerTabAdd(tab, opts):
    """ Apply action on a a table and return a new one with a new name 
    df_new, name_new = f(t, opts)
    """
    return tab.applyResampling(opts['icol'], opts, bAdd=True)

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class SamplerToolPanel(PlotDataActionEditor):

    def __init__(self, parent, action, **kwargs):
        PlotDataActionEditor.__init__(self, parent, action, tables=True)

        # --- Data
        from pydatview.tools.signal_analysis import SAMPLERS
        self._SAMPLERS_USER    = SAMPLERS.copy()

        # --- GUI elements
        self.cbMethods  = wx.ComboBox(self, -1, choices=[s['name'] for s in self._SAMPLERS_USER], style=wx.CB_READONLY)

        self.lbNewX   = wx.StaticText(self, -1, 'New x:  ')
        self.textNewX = wx.TextCtrl(self, wx.ID_ANY, '', style      = wx.TE_PROCESS_ENTER)
        self.textOldX = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY)
        self.textOldX.Enable(False)

        # --- Layout
        msizer  = wx.FlexGridSizer(rows=2, cols=4, hgap=2, vgap=0)
        msizer.Add(wx.StaticText(self, -1, 'Table:')    , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        msizer.Add(self.cbTabs                          , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        msizer.Add(wx.StaticText(self, -1, 'Current x:          '), 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        msizer.Add(self.textOldX                        , 1, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND, 1)
        msizer.Add(wx.StaticText(self, -1, 'Method:')   , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        msizer.Add(self.cbMethods                       , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        msizer.Add(self.lbNewX                          , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        msizer.Add(self.textNewX                        , 1, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND, 1)
        msizer.AddGrowableCol(3,1)

        #self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        #self.sizer.Add(btSizer  ,0, flag = wx.LEFT           ,border = 5)
        self.sizer.Add(msizer   ,1, flag = wx.LEFT|wx.EXPAND ,border = TOOL_BORDER)
        self.SetSizer(self.sizer)

        # --- Events
        self.cbMethods.Bind(wx.EVT_COMBOBOX, self.onMethodChange)
        self.textNewX.Bind(wx.EVT_TEXT_ENTER,self.onParamChangeEnter)

        # --- Init triggers
        self._Data2GUI()
        self.onMethodChange(init=True)
        self.onToggleApply(init=True)
        self.setCurrentX()

    # --- Implementation specific
    def getSamplerIndex(self, name):
        for i, samp in enumerate(self._SAMPLERS_USER):
            if samp['name'] == name:
                return i
        return -1

    def setCurrentX(self):
        if len(self.plotPanel.plotData)==0:
            return
        x= np.array(self.plotPanel.plotData[0].x).astype(str)
        if len(x)<50:
            s=', '.join(x)
        else:
            s=', '.join(x[[0,1,2,3]])
            s+=', ...,  '
            s+=', '.join(x[[-3,-2,-1]])
        self.textOldX.SetValue(s)

    def onMethodChange(self, event=None, init=True):
        """ Select the method, but does not applied it to the plotData 
            User data and option is unchanged
            But if the user already has some options, they are used
        """
        iOpt = self.cbMethods.GetSelection()
        opts   = self._SAMPLERS_USER[iOpt]
        # check if selection is the same as the one currently used
        if self.data['name'] == opts['name']:
            opts['param'] = self.data['param']
        self._Data2GUI(opts)
        # Trigger plot if applied
        self.onParamChange()

    # --- Bindings for plot triggers on parameters changes
    def onParamChange(self, event=None):
        if self.data['active']:
            self._GUI2Data()
            self.parent.load_and_draw() # Data will change
            self.setCurrentX()

    # --- Fairly generic
    def _GUI2Data(self):
        iOpt = self.cbMethods.GetSelection()
        # Store GUI into samplers_user list
        opt = self._SAMPLERS_USER[iOpt]
        s= self.textNewX.Value.strip().replace('[','').replace(']','')
        if len(s)>0:
            if s.find(',')>=0:
                opt['param']=np.array([v for v in s.split(',') if len(v)>0]).astype(float)
            else:
                opt['param']=np.array([v for v in s.split() if len(v)>0]).astype(float)
        # Then update our main data dictionary
        self.data.update(opt) 
        return opt

    def _Data2GUI(self, data=None):
        if data is None:
            data = self.data
        i = self.getSamplerIndex(data['name'])
        if i==-1:
            raise Exception('Unknown sampling method ', data['name'])
        self.lbNewX.SetLabel(data['paramName']+':')
        self.cbMethods.SetSelection(i)
        param = data['param']
        sParam = ', '.join(list(np.atleast_1d(param).astype(str)))
        self.textNewX.SetValue(sParam)

    def onToggleApply(self, event=None, init=False):
        # Call parent class
        PlotDataActionEditor.onToggleApply(self, event=event, init=init)
        #
        self.setCurrentX()


    def onAdd(self, event=None):
        # TODO put this in GUI2Data???
        iSel          = self.cbTabs.GetSelection()
        icol, colname = self.plotPanel.selPanel.xCol
        self.data['icol'] = icol

        # Call parent class
        PlotDataActionEditor.onAdd(self)

    def onHelp(self,event=None):
        Info(self,"""Resampling.

The resampling operation changes the "x" values of a table/plot and 
adapt the "y" values accordingly.

To resample perform the following step:

- Chose a resampling method:
   - replace: specify all the new x-values
   - insert : insert a list of x values to the existing ones
   - delete : delete a list of x values from the existing ones
   - every-n : use every n values 
   - time-based: downsample using sample averaging or upsample using
                 linear interpolation, x-axis must already be in seconds
   - delta x : specify a delta for uniform spacing of x values

- Specify the x values as a space or comma separated list

- Click on one of the following buttons:
   - Plot: will display the resampled data on the figure
   - Apply: will perform the resampling on the fly for all new plots
   - Add: will create new table(s) with resampled values for all 
          signals. This process might take some time.
          Select a table or choose all (default)
""")

if __name__ == '__main__':
    from pydatview.plugins.base_plugin import demoPlotDataActionPanel

    demoPlotDataActionPanel(SamplerToolPanel, plotDataFunction=samplerXY, data=_DEFAULT_DICT, tableFunctionAdd=samplerTabAdd)
