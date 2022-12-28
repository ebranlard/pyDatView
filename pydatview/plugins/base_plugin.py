import wx
import numpy as np
from pydatview.common import CHAR, Error, Info
from pydatview.plotdata import PlotData

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

# --------------------------------------------------------------------------------}
# --- Default class for GUI to edit plugin and control an action
# --------------------------------------------------------------------------------{
class ActionEditor(GUIToolPanel):
    """ 
    Class to edit an action. 
    Contains: 
     - the action
     - the action data
     - a set of function handles to process some triggers and callbacks
    """
    def __init__(self, parent, action, buttons=None, tables=True):
        GUIToolPanel.__init__(self, parent)
            
        # --- Data
        self.data           = action.data
        self.action         = action
        self.applyRightAway = True # This is false for plotData actions. 
        self.cancelOnRemove = True # This is false for plotData actions.
        # --- Unfortunate data to remove/manage
        self.addActionHandle    = self.pipeLike.append
        self.removeActionHandle = self.pipeLike.remove
        self.addTablesHandle    = action.mainframe.load_dfs     

        # Register ourselves to the action to be safe
        self.action.guiEditorObj = self
    
    # --- unfortunate data
    @property
    def plotPanel(self): return self.action.mainframe.plotPanel # NOTE: we need mainframe if plotPlanel is respawned..
    @property
    def redrawHandle(self): return self.action.mainframe.plotPanel.load_and_draw  # or action.guiCallback
    @property
    def pipeLike(self): return self.action.mainframe.plotPanel.pipeLike
    @property
    def tabList(self): return self.action.mainframe.plotPanel.selPanel.tabList # a bit unfortunate
        
    # --- External Calls
    def cancelAction(self):
        """ set the GUI state when the action is cancelled"""
        self.data['active'] = False     

    def guiActionAppliedState(self):
        """ set the GUI state when the action is applied"""
        self.data['active'] = True

    # --- Fairly generic
    def _GUI2Data(self):
        pass
        
    def _Data2GUI(self):
        pass

    def onToggleApply(self, event=None, init=False):
        if not init:
            self.data['active'] = not self.data['active']

        # Check if action is already in pipeline
        i = self.pipeLike.index(self.action)
            
        if self.data['active']:
            self._GUI2Data()
            # We update the GUI
            self.guiActionAppliedState()
            # Add action to pipeline, apply it right away (if needed), update the GUI (redraw)
            if i<0:
                self.addActionHandle(self.action, overwrite=True, apply=self.applyRightAway, tabList=self.tabList, updateGUI=True)
        else:
            if not init:
                # Remove action from pipeline, cancel it (if needed), update the GUI (redraw)
                self.removeActionHandle(self.action, cancel=self.cancelOnRemove, tabList=self.tabList, updateGUI=True)
            else:
                self.cancelAction()

    def onAdd(self, event=None):
        """ 
        Apply tableFunction on all selected tables, create new tables, add them to the GUI
        """
        #iSel         = self.cbTabs.GetSelection()
        #icol, colname = self.plotPanel.selPanel.xCol
        self._GUI2Data()

        dfs, names, errors = self.action.applyAndAdd(self.tabList)
        if len(errors)>0:
            raise Exception('Error: The action {} failed on some tables:\n\n'.format(action.name)+'\n'.join(errors))

        # We stop applying if we were applying it (NOTE: doing this before adding table due to redraw trigger of the whole panel)
        if self.data['active']:
            self.onToggleApply()

        self.addTablesHandle(dfs, names, bAdd=True, bPlot=False) # Triggers a redraw of the whole panel...
        #    df, name = self.tabList[iSel-1].applyFiltering(icol, self.data, bAdd=True)
        #    self.parent.addTables([df], [name], bAdd=True)
        #self.updateTabList()

    def onClear(self, event=None):
        self.redrawHandle()

    def onHelp(self,event=None):
        Info(self, """Dummy help""")


# --------------------------------------------------------------------------------}
# --- Default calss for GUI to edit plugin and control a plot data action
# --------------------------------------------------------------------------------{
class PlotDataActionEditor(ActionEditor):

    def __init__(self, parent, action, buttons=None, tables=True):
        """ 
        """
        ActionEditor.__init__(self, parent, action=action)
            
        # --- Data
        self.data      = action.data
        self.action    = action
        # --- Unfortunate data to remove/manage
        self.addActionHandle    = self.pipeLike.append
        self.removeActionHandle = self.pipeLike.remove
        self.addTablesHandle    = action.mainframe.load_dfs     

        # Register ourselves to the action to be safe
        self.action.guiEditorObj = self

        # --- GUI elements
        if buttons is None:
            buttons=['Close', 'Add', 'Help', 'Clear', 'Plot', 'Apply']
        self.btAdd   = None
        self.btHelp  = None
        self.btClear = None
        self.btPlot  = None
        nButtons = 0
        self.btClose = self.getBtBitmap(self,'Close','close',self.destroy); nButtons+=1
        if 'Add' in buttons:
            self.btAdd   = self.getBtBitmap(self, 'Add','add'  , self.onAdd); nButtons+=1
        if 'Help' in buttons:
            self.btHelp  = self.getBtBitmap(self, 'Help','help', self.onHelp); nButtons+=1
        if 'Clear' in buttons:
            self.btClear = self.getBtBitmap(self, 'Clear Plot','sun'   , self.onClear); nButtons+=1
        if 'Plot' in buttons:
            self.btPlot  = self.getBtBitmap(self, 'Plot' ,'chart'  , self.onPlot); nButtons+=1
        self.btApply = self.getToggleBtBitmap(self,'Apply','cloud',self.onToggleApply); nButtons+=1

        
        if tables:
            self.cbTabs= wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
            self.cbTabs.Enable(False) # <<< Cancelling until we find a way to select tables and action better
        else:
            self.cbTabs = None

        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=int(nButtons/2), cols=2, hgap=2, vgap=0)
        btSizer.Add(self.btClose                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        if self.btClear is not None:
            btSizer.Add(self.btClear                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        if self.btAdd is not None:
            btSizer.Add(self.btAdd                  , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        if self.btPlot is not None:
            btSizer.Add(self.btPlot                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        if self.btHelp is not None:
            btSizer.Add(self.btHelp                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btApply                , 0, flag = wx.ALL|wx.EXPAND, border = 1)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT          ,border = 1)
        # Child sizer will go here
        # TODO cbTabs has no sizer
        self.SetSizer(self.sizer)

        # --- Events
        if tables:
            self.cbTabs.Bind   (wx.EVT_COMBOBOX, self.onTabChange)

        ## --- Init triggers
        #self.updateTabList()
    
    # --- unfortunate data
    @property
    def plotPanel(self): return self.action.mainframe.plotPanel # NOTE: we need mainframe if plotPlanel is respawned..
    @property
    def redrawHandle(self): return self.action.mainframe.plotPanel.load_and_draw  # or action.guiCallback
    @property
    def pipeLike(self): return self.action.mainframe.plotPanel.pipeLike
    @property
    def tabList(self): return self.action.mainframe.plotPanel.selPanel.tabList # a bit unfortunate
        
    # --- Bindings for plot triggers on parameters changes
    def onParamChange(self, event=None):
        if self.data['active']:
            self._GUI2Data()
            self.redrawHandle()

    def onParamChangeArrow(self, event):
        self.onParamChange()
        event.Skip()

    def onParamChangeEnter(self, event):
        """ Action when the user presses Enter: we activate the action """
        self.onParamChange()
        if not self.data['active']:
            self.onToggleApply()
        event.Skip()

    def onParamChangeChar(self, event):
        event.Skip()  
        code = event.GetKeyCode()
        if code in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            #self.tParam.SetValue(self.spintxt.Value) # TODO
            self.onParamChangeEnter(event)
            
    # --- Table related
    def onTabChange(self,event=None):
        #tabList = self.parent.selPanel.tabList
        #iSel=self.cbTabs.GetSelection()
        pass

    def updateTabList(self,event=None):
        if self.cbTabs is not None:
            tabListNames = ['All opened tables']+self.tabList.getDisplayTabNames()
            #try:
            iSel=np.max([np.min([self.cbTabs.GetSelection(),len(tabListNames)]),0])
            self.cbTabs.Clear()
            [self.cbTabs.Append(tn) for tn in tabListNames]
            self.cbTabs.SetSelection(iSel)
            #except RuntimeError:
            #    pass

    # --- External Calls
    def cancelAction(self):
        """ set the GUI state when the action is cancelled"""
        if self.btPlot is not None:
            self.btPlot.Enable(True)
        if self.btClear is not None:
            self.btClear.Enable(True)
        self.btApply.SetLabel(CHAR['cloud']+' Apply')
        self.btApply.SetValue(False)
        self.data['active'] = False     
        ActionEditor.cancelAction(self)

    def guiActionAppliedState(self):
        """ set the GUI state when the action is applied"""
        if self.btPlot is not None:
            self.btPlot.Enable(False)
        if self.btClear is not None:
            self.btClear.Enable(False)
        self.btApply.SetLabel(CHAR['sun']+' Clear')
        self.btApply.SetValue(True)
        self.data['active'] = True
        ActionEditor.guiActionAppliedState(self)

    # --- Fairly generic
    #def _GUI2Data(self):
    #    ActionEditor._GUI2Data(self)
        
    #def _Data2GUI(self):
    #    ActionEditor._Data2GUI(self)

    #def onToggleApply(self, event=None, init=False):
    #    ActionEditor.onToggleApply(self, event=event, init=init)

    #def onAdd(self, event=None):
    #    ActionEditor.onAdd(self, event)

    def onPlot(self, event=None):
        self._GUI2Data()
        # Loop on axes and plotdata of each axes
        for ax in self.plotPanel.fig.axes:
            for iPD in ax.iPD:
                PD = self.plotPanel.plotData[iPD]
                # Apply the plotDataFunction
                x_new, y_new = self.action.plotDataFunction(PD.x0, PD.y0, self.data)
                # Go through plotPanel own pipeline
                PD_new = PlotData()
                PD_new.fromXY(x_new, y_new)
                self.plotPanel.transformPlotData(PD_new)
                # Plot
                ax.plot(PD_new.x, PD_new.y, '-')
        # Simple canvas draw (a redraw would remove what we just added)
        self.plotPanel.canvas.draw()


def demoPlotDataActionPanel(panelClass, data=None, plotDataFunction=None, tableFunctionAdd=None, mainLoop=True, title='Demo'):
    """ Function to demonstrate behavior of a plotdata plugin"""
    from pydatview.pipeline import PlotDataAction
    from pydatview.common import DummyMainFrame
    from pydatview.Tables import TableList
    from pydatview.pipeline import Pipeline
    from pydatview.GUIPlotPanel import PlotPanel
    from pydatview.GUISelectionPanel import SelectionPanel
    if data is None:
        data={'active':False}

    if plotDataFunction is None:
        plotDataFunction = lambda x,y,opts: (x+0.1, 1.01*y)

    # --- Data
    tabList   = TableList.createDummy(nTabs=2, n=100, addLabel=False)
    app = wx.App(False)
    self = wx.Frame(None,-1, title)
    pipeline = Pipeline()

    # --- Panels
    self.selPanel = SelectionPanel(self, tabList, mode='auto')
    self.plotPanel = PlotPanel(self, self.selPanel, pipeLike=pipeline)
    self.plotPanel.load_and_draw() # <<< Important
    self.selPanel.setRedrawCallback(self.plotPanel.load_and_draw) #  Binding the two

    # --- Dummy mainframe and action..
    mainframe = DummyMainFrame(self)
    mainframe.plotPanel = self.plotPanel
    guiCallback = self.plotPanel.load_and_draw
    action = PlotDataAction(
            name             = 'Dummy Action',
            tableFunctionAdd = tableFunctionAdd,
            plotDataFunction = plotDataFunction,
            guiEditorClass   = panelClass,
            guiCallback      = guiCallback,
            data             = data,
            mainframe        = mainframe
            )

    # --- Create main object to be tested
    p = panelClass(self.plotPanel, action=action)

    # --- Finalize GUI
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(self.selPanel ,0, wx.EXPAND|wx.ALL, border=5)
    sizer.Add(self.plotPanel,1, wx.EXPAND|wx.ALL, border=5)
    self.SetSizer(sizer)
    self.SetSize((900, 600))
    self.Center()
    self.plotPanel.showToolPanel(panel=p) # <<< Show

    if mainLoop:
        self.Show()
        app.MainLoop()

if __name__ == '__main__':

    demoPlotDataActionPanel(PlotDataActionEditor)

