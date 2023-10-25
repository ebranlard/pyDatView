import numpy as np
from pydatview.plugins.base_plugin import PlotDataActionEditor, TOOL_BORDER
from pydatview.common import Error, Info, pretty_num_short
from pydatview.pipeline import PlotDataAction
_HELP = """Binning.

The binning operation computes average y values for a set of x ranges.

To bin perform the following step:

- Specify the number of bins (#bins)
- Specify the min and max of the x values (or click on "Update x")
- Click on one of the following buttons:
   - Plot: will display the binned data on the figure
   - Apply: will perform the binning on the fly for all new plots
           (click on Clear to stop applying)
   - Add: will create new table(s) with binned values for all 
          signals. This process might take some time.
          Select a table or choose all (default)

   - Update x: retrieve the minimum and maximum x values of the current plot and update the
              corresponding fields in the GUI. The values can then used to make sure the bins
              cover the full range of the data.
               
"""
# --------------------------------------------------------------------------------}
# --- Data
# --------------------------------------------------------------------------------{
_DEFAULT_DICT={
    'active':False, 
    'xMin':None, 
    'xMax':None, 
    'nBins':50
}
# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def binningAction(label='binning', mainframe=None, data=None):
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

    guiCallback = mainframe.redraw if mainframe is not None else None

    action = PlotDataAction(
            name=label,
            tableFunctionAdd = binTabAdd,
            plotDataFunction = bin_plot,
            guiEditorClass = BinningToolPanel,
            guiCallback = guiCallback,
            data = data,
            mainframe        = mainframe,
            imports          = _imports,
            data_var         = _data_var,
            code             = _code 
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
_imports =['from pydatview.tools.stats import bin_signal']
_imports+=['import numpy as np']
_data_var='binData'
_code="""x, y = bin_signal(x, y, xbins=np.linspace(binData['xMin'], binData['xMax'], binData['nBins']+1))"""

def bin_plot(x, y, opts):
    from pydatview.tools.stats import bin_signal
    xBins = np.linspace(opts['xMin'], opts['xMax'], opts['nBins']+1)
    if xBins[0]>xBins[1]:
        raise Exception('xmin must be lower than xmax')
    x_new, y_new = bin_signal(x, y, xbins=xBins)
    return x_new, y_new

def bin_tab(tab, iCol, colName, opts, bAdd=True):
    # TODO, make it such as it's only handling a dataframe instead of a table
    from pydatview.tools.stats import bin_DF
    colName = tab.data.columns[iCol]
    error=''
    xBins = np.linspace(opts['xMin'], opts['xMax'], opts['nBins']+1)
#     try:
    df_new =bin_DF(tab.data, xbins=xBins, colBin=colName)
    # Remove index if present
    if df_new.columns[0].lower().find('index')>=0:
        df_new = df_new.iloc[:, 1:] # We don't use "drop" in case of duplicate "index"

    # Setting bin column as first columns
    colNames = list(df_new.columns.values)
    colNames.remove(colName)
    colNames.insert(0, colName)
    df_new=df_new.reindex(columns=colNames)
    if bAdd:
        name_new=tab.raw_name+'_binned'
    else:
        name_new=None
        tab.data=df_new
#     except:
#         df_new   = None
#         name_new = None

    return df_new, name_new

def binTabAdd(tab, data):
    return bin_tab(tab, data['icol'], data['colname'], data, bAdd=True)

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class BinningToolPanel(PlotDataActionEditor):

    def __init__(self, parent, action, **kwargs):
        import wx
        PlotDataActionEditor.__init__(self, parent, action, tables=False, help_string=_HELP, **kwargs)

        # --- GUI elements
        self.scBins = wx.SpinCtrl(self,      value='50', style = wx.TE_PROCESS_ENTER|wx.TE_RIGHT, size=wx.Size(60,-1) )
        self.textXMin = wx.TextCtrl(self, wx.ID_ANY, '', style = wx.TE_PROCESS_ENTER|wx.TE_RIGHT, size=wx.Size(70,-1))
        self.textXMax = wx.TextCtrl(self, wx.ID_ANY, '', style = wx.TE_PROCESS_ENTER|wx.TE_RIGHT, size=wx.Size(70,-1))

        self.btXRange = self.getBtBitmap(self, 'Update x', 'update', self.reset)
        self.lbDX     = wx.StaticText(self, -1, '')
        self.scBins.SetRange(3, 10000)

        boldFont = self.GetFont().Bold()
        lbInputs  = wx.StaticText(self, -1, 'Inputs: ')
        lbInputs.SetFont(boldFont)

        # --- Layout
        #msizer  = wx.FlexGridSizer(rows=1, cols=3, hgap=2, vgap=0)
        #msizer.Add(wx.StaticText(self, -1, '      ')    , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        #msizer.Add(wx.StaticText(self, -1, '      ')    , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        #msizer.Add(wx.StaticText(self, -1, 'Table:')    , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        #msizer.Add(self.cbTabs                          , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
#         msizer.Add(self.btXRange                        , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.LEFT, 1)

        msizer2 = wx.FlexGridSizer(rows=2, cols=5, hgap=4, vgap=1)

        msizer2.Add(lbInputs                                   , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 0)
        msizer2.Add(wx.StaticText(self, -1, '#bins: ')         , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 1)
        msizer2.Add(self.scBins                                , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 1)
        msizer2.Add(wx.StaticText(self, -1, 'dx: ')            , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 8)
        msizer2.Add(self.lbDX                                  , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 1)
        msizer2.Add(self.btXRange                              , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 0)
        msizer2.Add(wx.StaticText(self, -1, 'xmin: ')          , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 1)
        msizer2.Add(self.textXMin                              , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 1)
        msizer2.Add(wx.StaticText(self, -1, 'xmax: ')          , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 8)
        msizer2.Add(self.textXMax                              , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 1)
        #msizer2.AddGrowableCol(4,1)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        #vsizer.Add(msizer,0, flag = wx.TOP            ,border = 1)
        vsizer.Add(msizer2,0, flag = wx.TOP,border = 1)

        #self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        #self.sizer.Add(btSizer  ,0, flag = wx.LEFT           , border = 5)
        self.sizer.Add(vsizer   ,1, flag = wx.LEFT|wx.EXPAND , border = TOOL_BORDER)
        self.SetSizer(self.sizer)

        # --- Events
        self.scBins.Bind  (wx.EVT_SPINCTRL      , self.onParamChangeArrow)
        self.scBins.Bind  (wx.EVT_SPINCTRLDOUBLE, self.onParamChangeArrow)
        self.scBins.Bind  (wx.EVT_TEXT_ENTER, self.onParamChangeEnter)    
        #self.cbTabs.Bind  (wx.EVT_COMBOBOX, self.onTabChange)
        self.textXMin.Bind(wx.EVT_TEXT_ENTER, self.onParamChangeEnter)
        self.textXMax.Bind(wx.EVT_TEXT_ENTER, self.onParamChangeEnter)

        # --- Init triggers
        self.setXRange()
        self._Data2GUI()
        self.onToggleApply(init=True)

    # --- Implementation specific
    def reset(self, event=None):
        self.setXRange()
        self.updateTabList() # might as well until we add a nice callback/button..

    def setXRange(self, x=None):
        if x is None:
            if self.data['active']:
                x=[self.data['xMin'], self.data['xMax']]
            else:
                x= self.plotPanel.plotData[0].x0
        xmin, xmax = np.nanmin(x), np.nanmax(x)
        self.textXMin.SetValue(pretty_num_short(xmin))
        self.textXMax.SetValue(pretty_num_short(xmax))
        self.lbDX.SetLabel(pretty_num_short((xmax-xmin)/int  (self.scBins.Value)))

    # --- Bindings for plot triggers on parameters changes
    def onParamChange(self, event=None):
        PlotDataActionEditor.onParamChange(self)
        data = {}
        data = self._GUI2Data(data)
        #if data['nBins']<3:
        #    self.scBins.SetValue(3) # NOTE: this does not work, we might need to access the text?
        self.lbDX.SetLabel(pretty_num_short((data['xMax']- data['xMin'])/data['nBins']))

    # --- Fairly generic
    def _GUI2Data(self, data=None):
        if data is None:
            data = self.data
        def zero_if_empty(s):
            return 0 if len(s)==0 else s
        data['nBins'] = int  (self.scBins.Value)
        data['xMin']  = float(zero_if_empty(self.textXMin.Value))
        data['xMax']  = float(zero_if_empty(self.textXMax.Value))
        return data

    def _Data2GUI(self):
        if self.data['active']:
            self.lbDX.SetLabel(pretty_num_short((self.data['xMax']- self.data['xMin'])/self.data['nBins']))
            self.textXMin.SetValue(pretty_num_short(self.data['xMin']))
            self.textXMax.SetValue(pretty_num_short(self.data['xMax']))
        self.scBins.SetValue(self.data['nBins'])

    def onAdd(self,event=None):
        if self.plotPanel.selPanel.currentMode=='simColumnsMode':
            # The difficulty here is that we have to use 
            #      self.plotPanel.selPanel.IKeepPerTab
            #   or maybe just do it for the first table to get the x column name, 
            #   but there is no guarantee that other tables will have the exact same column name.
            Error(self, 'Cannot add tables in "simColumnsMode" for now. Go back to 1 table mode, and add tables individually.')
            return

        # TODO put this in GUI2Data???
        #iSel          = self.cbTabs.GetSelection()
        icol, colname = self.plotPanel.selPanel.xCol
        self.data['icol']    = icol
        self.data['colname'] = colname

        # Call parent class
        PlotDataActionEditor.onAdd(self)

if __name__ == '__main__':
    from pydatview.plugins.base_plugin import demoPlotDataActionPanel

    demoPlotDataActionPanel(BinningToolPanel, plotDataFunction=bin_plot, data=_DEFAULT_DICT, tableFunctionAdd=binTabAdd)
