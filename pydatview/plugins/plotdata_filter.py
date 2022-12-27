import wx
import numpy as np
from pydatview.plugins.base_plugin import PlotDataActionEditor, TOOL_BORDER
from pydatview.common import Error, Info
from pydatview.pipeline import PlotDataAction
import platform
# --------------------------------------------------------------------------------}
# --- Data
# --------------------------------------------------------------------------------{
# See FILTERS in signal_analysis
_DEFAULT_DICT={
    'active':False, 
    'name':'Moving average', 
    'param':100, 
    'paramName':'Window Size',
    'paramRange':[1, 100000],
    'increment':1,
    'digits':0
}
# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def filterAction(label, mainframe, data=None):
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
            tableFunctionAdd = filterTabAdd,
            plotDataFunction = filterXY,
            guiEditorClass   = FilterToolPanel,
            guiCallback      = guiCallback,
            data             = data,
            mainframe        = mainframe
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
def filterXY(x, y, opts):
    """ Apply action on a x and y array """
    from pydatview.tools.signal_analysis import applyFilter
    y_new = applyFilter(x, y, opts)
    return x, y_new

def filterTabAdd(tab, opts):
    """ Apply action on a a table and return a new one with a new name 
    df_new, name_new = f(t, opts)
    """
    return tab.applyFiltering(opts['icol'], opts, bAdd=True)

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class FilterToolPanel(PlotDataActionEditor):

    def __init__(self, parent, action, **kwargs):
        PlotDataActionEditor.__init__(self, parent, action, tables=True, **kwargs)

        # --- Data
        from pydatview.tools.signal_analysis import FILTERS
        self._FILTERS_USER=FILTERS .copy()

        # --- GUI elements
        self.cbFilters = wx.ComboBox(self, choices=[filt['name'] for filt in self._FILTERS_USER], style=wx.CB_READONLY)
        self.lbParamName = wx.StaticText(self, -1, '            :')
        self.cbFilters.SetSelection(0)
        self.tParam = wx.SpinCtrlDouble(self, value='11', size=wx.Size(80,-1))
        self.lbInfo = wx.StaticText( self, -1, '')

        # --- Layout
        horzSizerT = wx.BoxSizer(wx.HORIZONTAL)
        horzSizerT.Add(wx.StaticText(self, -1, 'Table:')  , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        horzSizerT.Add(self.cbTabs                        , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 1)

        horzSizer = wx.BoxSizer(wx.HORIZONTAL)
        horzSizer.Add(wx.StaticText(self, -1, 'Filter:')  , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        horzSizer.Add(self.cbFilters                      , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 1)
        horzSizer.Add(self.lbParamName                    , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        horzSizer.Add(self.tParam                         , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 1)


        vertSizer = wx.BoxSizer(wx.VERTICAL)
        vertSizer.Add(self.lbInfo  ,0, flag = wx.LEFT          ,border = 5)
        vertSizer.Add(horzSizerT   ,1, flag = wx.LEFT|wx.EXPAND,border = 1)
        vertSizer.Add(horzSizer    ,1, flag = wx.LEFT|wx.EXPAND,border = 1)

        # self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        # self.sizer.Add(btSizer      ,0, flag = wx.LEFT          ,border = 1)
        self.sizer.Add(vertSizer    ,1, flag = wx.EXPAND|wx.LEFT          ,border = 1)
        self.sizer.Layout()


        # --- Events
        self.cbFilters.Bind(wx.EVT_COMBOBOX, self.onSelectFilt)
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.onParamChangeArrow, self.tParam)
        self.Bind(wx.EVT_TEXT_ENTER,     self.onParamChangeEnter, self.tParam)
        try:
            self.spintxt = self.tParam.Children[0]
        except:
            self.spintxt = None
        if platform.system()=='Windows':
            # See issue https://github.com/wxWidgets/Phoenix/issues/1762
            assert isinstance(self.spintxt, wx.TextCtrl)
            self.spintxt.Bind(wx.EVT_CHAR_HOOK, self.onParamChangeChar)

        # --- Init triggers
        self._Data2GUI()
        self.onToggleApply(init=True)
        self.onSelectFilt()
        
    # --- Implementation specific
    def onSelectFilt(self, event=None):
        """ Select the filter, but does not apply it to the plotData 
            self.data should be unchanged!
            Uses the action data only if the selection is the same.
        """
        iFilt = self.cbFilters.GetSelection()
        opts = self._FILTERS_USER[iFilt]
        # check if selection is the same as the one currently used
        if self.data['name']==opts['name']:
            opts['param'] = self.data['param']
        self._Data2GUI(opts)
        # Trigger plot if applied
        self.onParamChange(self)

   # --- External Calls
    def cancelAction(self):
        """ set the GUI state when the action is cancelled"""
        # Call parent class
        PlotDataActionEditor.cancelAction(self)
        # Update GUI
        self.lbInfo.SetLabel(
                    'Click on "Apply" to set filter on the fly for all plots. '+
                    'Click on "Plot" to try a filter on the current plot.'
                    )        
    def guiActionAppliedState(self):
        """ set the GUI state when the action is applied"""
        # Call parent class
        PlotDataActionEditor.guiActionAppliedState(self)
        # Update GUI
        self.lbInfo.SetLabel( 'Filter is now applied on the fly. Change parameter live. Click "Clear" to stop. ')

    # --- Fairly generic
    def _GUI2Data(self):
        iFilt = self.cbFilters.GetSelection()
        opt = self._FILTERS_USER[iFilt]
        try:
            opt['param']=np.float(self.spintxt.Value)
        except:
            print('[WARN] pyDatView: Issue on Mac: plotdata_filter.py/_GUI2Data. Help needed.')
            opt['param']=np.float(self.tParam.Value)
        if opt['param']<opt['paramRange'][0]:
            opt['param']=opt['paramRange'][0]
            self.tParam.SetValue(opt['paramRange'][0])
        self.data.update(opt)

        return opt
        
    def _Data2GUI(self, data=None):
        if data is None:
            data = self.data
        self.lbParamName.SetLabel(data['paramName']+':')
        #self.tParam.SetRange(filt['paramRange'][0], filt['paramRange'][1])
        # NOTE: if min value for range is not 0, the Ctrl prevents you to enter 0.01
        self.tParam.SetRange(0, data['paramRange'][1])
        self.tParam.SetIncrement(data['increment'])
        self.tParam.SetDigits(data['digits'])
        self.tParam.SetValue(self.data['param'])

    def onAdd(self, event=None):
        # TODO put this in GUI2Data???
        iSel          = self.cbTabs.GetSelection()
        icol, colname = self.plotPanel.selPanel.xCol
        self.data['icol'] = icol

        # Call parent class
        PlotDataActionEditor.onAdd(self)

    def onHelp(self,event=None):
        Info(self,"""Filtering.

The filtering operation changes the "y" values of a table/plot, 
applying a given filter (typically cutting off some frequencies).

To filter perform the following step:

- Chose a filtering method:
   - Moving average: apply a moving average filter, with
          a length specified by the window size (in indices)
   - High pass 1st order: apply a first oder high-pass filter,
          passing the frequencies above the cutoff frequency parameter.
   - Low pass 1st order: apply a first oder low-pass filter,
          passing the frequencies below the cutoff frequency parameter.

- Click on one of the following buttons:
   - Plot: will display the filtered data on the figure
   - Apply: will perform the filtering on the fly for all new plots
   - Add: will create new table(s) with filtered values for all 
          signals. This process might take some time.
          Currently done for all tables.
""")



if __name__ == '__main__':
    from pydatview.plugins.base_plugin import demoPlotDataActionPanel

    demoPlotDataActionPanel(FilterToolPanel, plotDataFunction=filterXY, data=_DEFAULT_DICT, tableFunctionAdd=filterTabAdd)
