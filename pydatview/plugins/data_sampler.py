import wx
import numpy as np
from pydatview.GUITools import GUIToolPanel, TOOL_BORDER
from pydatview.common import CHAR, Error, Info, pretty_num_short
from pydatview.common import DummyMainFrame
from pydatview.plotdata import PlotData
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
def samplerAction(label, mainframe=None, data=None):
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
            plotDataFunction = samplerXY,
            guiEditorClass = SamplerToolPanel,
            guiCallback = guiCallback,
            data = data,
            mainframe=mainframe
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
def samplerXY(x, y, opts):
    from pydatview.tools.signal_analysis import applySampler
    x_new, y_new = applySampler(x, y, opts)
    return x_new, y_new

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class SamplerToolPanel(GUIToolPanel):
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
        from pydatview.tools.signal_analysis import SAMPLERS
        self._SAMPLERS_DEFAULT = SAMPLERS.copy()
        self._SAMPLERS_USER    = SAMPLERS.copy()

        # --- GUI elements
        self.btClose    = self.getBtBitmap(self, 'Close','close', self.destroy)
        self.btAdd      = self.getBtBitmap(self, 'Add','add'  , self.onAdd)
        self.btHelp     = self.getBtBitmap(self, 'Help','help', self.onHelp)
        self.btClear    = self.getBtBitmap(self, 'Clear Plot','sun', self.onClear)
        self.btPlot     = self.getBtBitmap(self, 'Plot' ,'chart'  , self.onPlot)
        self.btApply    = self.getToggleBtBitmap(self,'Apply','cloud',self.onToggleApply)

        self.cbTabs     = wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
        self.cbTabs.Enable(False) # <<< Cancelling until we find a way to select tables and action better
        self.cbMethods  = wx.ComboBox(self, -1, choices=[s['name'] for s in self._SAMPLERS_DEFAULT], style=wx.CB_READONLY)

        self.lbNewX   = wx.StaticText(self, -1, 'New x:  ')
        self.textNewX = wx.TextCtrl(self, wx.ID_ANY, '', style      = wx.TE_PROCESS_ENTER)
        self.textOldX = wx.TextCtrl(self, wx.ID_ANY|wx.TE_READONLY)
        self.textOldX.Enable(False)

        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)
        btSizer.Add(self.btClose                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btClear                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btAdd                  , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btPlot                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btHelp                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btApply                , 0, flag = wx.ALL|wx.EXPAND, border = 1)

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

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer  ,0, flag = wx.LEFT           ,border = 5)
        self.sizer.Add(msizer   ,1, flag = wx.LEFT|wx.EXPAND ,border = TOOL_BORDER)
        self.SetSizer(self.sizer)

        # --- Events
        self.cbTabs.Bind   (wx.EVT_COMBOBOX, self.onTabChange)
        self.cbMethods.Bind(wx.EVT_COMBOBOX, self.onMethodChange)
        self.textNewX.Bind(wx.EVT_TEXT_ENTER,self.onParamChange)

        # --- Init triggers
        self._Data2GUI()
        self.onMethodChange(init=True)
        self.onToggleApply(init=True)
        self.updateTabList()

    # --- Implementation specific
    def getSamplerIndex(self, name):
        for i, samp in enumerate(self._SAMPLERS_USER):
            if samp['name'] == name:
                return i
        return -1

    def setCurrentX(self, x=None):
        if x is None:
            x= self.parent.plotData[0].x
        if len(x)<50:
            s=np.array2string(x, separator=', ')
        else:
            s =np.array2string(x[[0,1,2,3]], separator=', ') 
            s+=', ...,  '
            s+=np.array2string(x[[-3,-2,-1]], separator=', ') 
        s=s.replace('[','').replace(']','').replace(' ','').replace(',',', ')

        self.textOldX.SetValue(s)

    def onMethodChange(self, event=None, init=True):
        """ Select the method, but does not applied it to the plotData 
            User data and option is unchanged
            But if the user already has some options, they are used
        """
        iOpt = self.cbMethods.GetSelection()
        opt_default = self._SAMPLERS_DEFAULT[iOpt]
        opt_user    = self._SAMPLERS_USER[iOpt]
        self.lbNewX.SetLabel(opt_default['paramName']+':')

        # Value
        if len(self.textNewX.Value)==0:
            self.textNewX.SetValue(str(opt_user['param'])[1:-1])
            #if type(parentOpt)==dict:
            #    self.textNewX.SetValue(str(parentOpt['param'])[1:-1])
            #else:
            #    self.textNewX.SetValue(str(opt['param'])[2:-2])
        self.onParamChange()

    # --- Bindings for plot triggers on parameters changes
    def onParamChange(self, event=None):
        self._GUI2Data()
        if self.data['active']:
            self.parent.load_and_draw() # Data will change
            self.setCurrentX()

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
        self.btPlot.Enable(True)
        self.btClear.Enable(True)
        self.btApply.SetLabel(CHAR['cloud']+' Apply')
        self.btApply.SetValue(False)
        self.data['active'] = False     
        if redraw:
            self.parent.load_and_draw() # Data will change based on plotData 

    # --- Fairly generic
    def _GUI2Data(self):
        iOpt = self.cbMethods.GetSelection()
        # Store GUI into samplers_user list
        opt = self._SAMPLERS_USER[iOpt]
        s= self.textNewX.Value.strip().replace('[','').replace(']','')
        if len(s)>0:
            if s.find(','):
                opt['param']=np.array(s.split(',')).astype(float)
            else:
                opt['param']=np.array(s.split('')).astype(float)
        # Then update our main data dictionary
        self.data.update(opt) 
        return opt

    def _Data2GUI(self):
        i = self.getSamplerIndex(self.data['name'])
        if i==-1:
            raise Exception('Unknown sampling method ', self.data['name'])
        self.cbMethods.SetSelection(i)
        param = self.data['param']
        self.textNewX.SetValue(str(param).lstrip('[').rstrip(']'))

    def onToggleApply(self, event=None, init=False):
        """
        apply sampler based on GUI Data
        """
        if not init:
            self.data['active'] = not self.data['active']

        if self.data['active']:
            self._GUI2Data()
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
            
        self.setCurrentX()

    def onAdd(self,event=None):
        iSel         = self.cbTabs.GetSelection()
        tabList      = self.parent.selPanel.tabList
        icol, colname = self.parent.selPanel.xCol
        self._GUI2Data()
        errors=[]
        if iSel==0:
            dfs, names, errors = tabList.applyResampling(icol, self.data, bAdd=True)
            self.parent.addTables(dfs,names,bAdd=True)
        else:
            df, name = tabList[iSel-1].applyResampling(icol, self.data, bAdd=True)
            self.parent.addTables([df],[name], bAdd=True)
        self.updateTabList()

        if len(errors)>0:
            raise Exception('Error: The resampling failed on some tables:\n\n'+'\n'.join(errors))

        # We stop applying
        self.onToggleApply()

    def onPlot(self,event=None):
        if len(self.parent.plotData)!=1:
            Error(self,'Plotting only works for a single plot. Plot less data.')
            return
        self._GUI2Data()
        PD = self.parent.plotData[0]
        x_new, y_new = samplerXY(PD.x0, PD.y0, self.data)

        ax = self.parent.fig.axes[0]
        PD_new = PlotData()
        PD_new.fromXY(x_new, y_new)
        self.parent.transformPlotData(PD_new)
        ax.plot(PD_new.x, PD_new.y, '-')
        self.setCurrentX(x_new)

        self.parent.canvas.draw()

    def onClear(self,event=None):
        self.parent.load_and_draw() # Data will change
        # Update Current X
        self.setCurrentX()
        # Update Table list
        self.updateTabList()

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
