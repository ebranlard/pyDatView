import wx
import numpy as np
from pydatview.GUITools import GUIToolPanel, TOOL_BORDER
from pydatview.common import CHAR, Error, Info, pretty_num_short
from pydatview.common import DummyMainFrame
from pydatview.plotdata import PlotData
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
def filterAction(label, mainframe=None, data=None):
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

    guiCallback=None
    if mainframe is not None:
        guiCallback = mainframe.redraw

    action = PlotDataAction(
            name=label,
            plotDataFunction = filterXY,
            guiEditorClass = FilterToolPanel,
            guiCallback = guiCallback,
            data = data,
            mainframe=mainframe
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
def filterXY(x, y, opts):
    from pydatview.tools.signal_analysis import applyFilter
    y_new = applyFilter(x, y, opts)
    return x, y_new

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class FilterToolPanel(GUIToolPanel):

    def __init__(self, parent, action=None):
        GUIToolPanel.__init__(self, parent)

        # --- Creating "Fake data" for testing only!
        if action is None:
            print('[WARN] Calling GUI without an action! Creating one.')
            mainframe = DummyMainFrame(parent)
            action = binningAction(label='dummyAction', mainframe=mainframe)
            
        # --- Data
        self.parent = parent # parent is GUIPlotPanel
        self.mainframe = action.mainframe
        self.data = action.data
        self.action = action
        from pydatview.tools.signal_analysis import FILTERS
        self._FILTERS_USER=FILTERS .copy()

        # --- GUI elements
        self.btClose = self.getBtBitmap(self,'Close','close',self.destroy)
        self.btAdd   = self.getBtBitmap(self, 'Add','add'  , self.onAdd)
        self.btHelp  = self.getBtBitmap(self, 'Help','help', self.onHelp)
        self.btClear = self.getBtBitmap(self, 'Clear Plot','sun'   , self.onClear)
        self.btPlot  = self.getBtBitmap(self, 'Plot' ,'chart'  , self.onPlot)
        self.btApply = self.getToggleBtBitmap(self,'Apply','cloud',self.onToggleApply)

        self.cbTabs     = wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
        self.cbTabs.Enable(False) # <<< Cancelling until we find a way to select tables and action better
        self.cbFilters = wx.ComboBox(self, choices=[filt['name'] for filt in self._FILTERS_USER], style=wx.CB_READONLY)
        self.lbParamName = wx.StaticText(self, -1, '            :')
        self.cbFilters.SetSelection(0)
#         self.tParam = wx.TextCtrl(self, wx.ID_ANY, '', style= wx.TE_PROCESS_ENTER, size=wx.Size(60,-1))
        self.tParam = wx.SpinCtrlDouble(self, value='11', size=wx.Size(80,-1))
        self.lbInfo = wx.StaticText( self, -1, '')


        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)
        btSizer.Add(self.btClose                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btClear                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btAdd                  , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btPlot                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btHelp                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btApply                , 0, flag = wx.ALL|wx.EXPAND, border = 1)


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

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT          ,border = 1)
        self.sizer.Add(vertSizer    ,1, flag = wx.EXPAND|wx.LEFT          ,border = 1)
        self.SetSizer(self.sizer)

        # --- Events
        self.cbTabs.Bind   (wx.EVT_COMBOBOX, self.onTabChange)
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
        self.updateTabList()
        self.onSelectFilt()
        self.onToggleApply(init=True)
        
    # --- Implementation specific
    def onSelectFilt(self, event=None):
        """ Select the filter, but does not applied it to the plotData 
            parentFilt is unchanged
            But if the parent already has 
        """
        iFilt = self.cbFilters.GetSelection()
        filt = self._FILTERS_USER[iFilt]
        self.lbParamName.SetLabel(filt['paramName']+':')
        #self.tParam.SetRange(filt['paramRange'][0], filt['paramRange'][1])
        # NOTE: if min value for range is not 0, the Ctrl prevents you to enter 0.01
        self.tParam.SetRange(0, filt['paramRange'][1])
        self.tParam.SetIncrement(filt['increment'])
        self.tParam.SetDigits(filt['digits'])

        parentFilt=self.data
        # Value
        if type(parentFilt)==dict and parentFilt['name']==filt['name']:
            self.tParam.SetValue(parentFilt['param'])
        else:
            self.tParam.SetValue(filt['param'])
        # Trigger plot if applied
        self.onParamChange(self)

    # --- Bindings for plot triggers on parameters changes
    def onParamChange(self, event=None):
        self._GUI2Data()
        if self.data['active']:
            self.parent.load_and_draw() # Data will change

    def onParamChangeArrow(self, event):
        self.onParamChange()
        event.Skip()

    def onParamChangeEnter(self, event):
        self.onParamChange()
        event.Skip()

    def onParamChangeChar(self, event):
        event.Skip()  
        code = event.GetKeyCode()
        if code in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            #print(self.spintxt.Value)
            self.tParam.SetValue(self.spintxt.Value)
            self.onParamChangeEnter(event)
            
    # --- Table related
    def onTabChange(self,event=None):
        #tabList = self.parent.selPanel.tabList
        #iSel=self.cbTabs.GetSelection()
        pass

    def updateTabList(self,event=None):
        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()
        try:
            iSel=np.max([np.min([self.cbTabs.GetSelection(),len(tabListNames)]),0])
            self.cbTabs.Clear()
            [self.cbTabs.Append(tn) for tn in tabListNames]
            self.cbTabs.SetSelection(iSel)
        except RuntimeError:
            pass

    # --- External Calls
    def cancelAction(self, redraw=True):
        """ do cancel the action"""
        self.lbInfo.SetLabel(
                    'Click on "Apply" to set filter on the fly for all plots. '+
                    'Click on "Plot" to try a filter on the current plot.'
                    )        
        self.btPlot.Enable(True)
        self.btClear.Enable(True)
        self.btApply.SetLabel(CHAR['cloud']+' Apply')
        self.btApply.SetValue(False)
        self.data['active'] = False     
        if redraw:
            self.parent.load_and_draw() # Data will change based on plotData 

    # --- Fairly generic
    def _GUI2Data(self):
        iFilt = self.cbFilters.GetSelection()
        opt = self._FILTERS_USER[iFilt]
        try:
            opt['param']=np.float(self.spintxt.Value)
        except:
            print('[WARN] pyDatView: Issue on Mac: GUITools.py/_GUI2Data. Help needed.')
            opt['param']=np.float(self.tParam.Value)
        if opt['param']<opt['paramRange'][0]:
            opt['param']=opt['paramRange'][0]
            self.tParam.SetValue(opt['paramRange'][0])
        self.data.update(opt)

        return opt
        
    def _Data2GUI(self):
        self.lbParamName.SetLabel(self.data['paramName']+':')
        #self.tParam.SetRange(filt['paramRange'][0], filt['paramRange'][1])
        # NOTE: if min value for range is not 0, the Ctrl prevents you to enter 0.01
        self.tParam.SetRange(0, self.data['paramRange'][1])
        self.tParam.SetIncrement(self.data['increment'])
        self.tParam.SetDigits(self.data['digits'])

    def onToggleApply(self, event=None, init=False):
        """
        apply Filter based on GUI Data
        """
        if not init:
            self.data['active'] = not self.data['active']

        if self.data['active']:
            self._GUI2Data()

            self.lbInfo.SetLabel(
                    'Filter is now applied on the fly. Change parameter live. Click "Clear" to stop. '
                    )
            self.btPlot.Enable(False)
            self.btClear.Enable(False)
            self.btApply.SetLabel(CHAR['sun']+' Clear')
            self.btApply.SetValue(True)
            # The action is now active we add it to the pipeline, unless it's already in it
            if self.mainframe is not None:
                self.mainframe.addAction(self.action, overwrite=True)
            if not init:
                self.parent.load_and_draw() # filter will be applied in plotData.py
        else:
            # We remove our action from the pipeline
            if not init:
                if self.mainframe is not None:
                    self.mainframe.removeAction(self.action)        
            self.cancelAction(redraw=not init)

    def onAdd(self, event=None):
        iSel         = self.cbTabs.GetSelection()
        tabList      = self.parent.selPanel.tabList
        icol, colname = self.parent.selPanel.xCol
        self._GUI2Data()
        errors=[]
        if iSel==0:
            dfs, names, errors = tabList.applyFiltering(icol, self.data, bAdd=True)
            self.parent.addTables(dfs,names,bAdd=True)
        else:
            df, name = tabList[iSel-1].applyFiltering(icol, self.data, bAdd=True)
            self.parent.addTables([df], [name], bAdd=True)
        self.updateTabList()

        if len(errors)>0:
            raise Exception('Error: The resampling failed on some tables:\n\n'+'\n'.join(errors))

        # We stop applying
        self.onToggleApply()

    def onPlot(self, event=None):
        """ 
        Overlay on current axis the filter
        """

        if len(self.parent.plotData)!=1:
            Error(self,'Plotting only works for a single plot. Plot less data.')
            return
        self._GUI2Data()
        PD = self.parent.plotData[0]
        x_new, y_new = filterXY(PD.x0, PD.y0, self.data)
        
        ax = self.parent.fig.axes[0]
        PD_new = PlotData()
        PD_new.fromXY(x_new, y_new)
        self.parent.transformPlotData(PD_new)
        ax.plot(PD_new.x, PD_new.y, '-')
        self.parent.canvas.draw()

    def onClear(self, event):
        self.parent.load_and_draw() # Data will change


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




