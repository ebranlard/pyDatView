try:
    import wx
    HAS_WX=True
except:
    # Creating a fake wx package just so that this package can be imported without failing 
    # and plugins can be tested without GUI
    print('[FAIL] cannot import wx')
    wx=type('wx', (object,), {'Panel':object})
    HAS_WX=False
import numpy as np
from pydatview.common import CHAR, Error, Info, Warn
from pydatview.plotdata import PlotData
from pydatview.pipeline import AdderAction

TOOL_BORDER=5

# --------------------------------------------------------------------------------}
# --- Default class for tools
# --------------------------------------------------------------------------------{
class GUIToolPanel(wx.Panel):
    def __init__(self, parent, help_string =''):
        super(GUIToolPanel,self).__init__(parent)
        self.parent   = parent
        self.help_string = help_string

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

    def onHelp(self, event=None):
        Info(self, self.help_string)


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
    def __init__(self, parent, action, buttons=None, tables=False, help_string=''):
        GUIToolPanel.__init__(self, parent, help_string=help_string)
            
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

        if issubclass(AdderAction, type(self.action)):
            self.addActionHandle(self.action, overwrite=True, apply=True, tabList=self.tabList, updateGUI=True)
            #self.addActionHandle(self.action, overwrite=True, apply=self.applyRightAway, tabList=self.tabList, updateGUI=True)
        else:
            dfs, names, errors = self.action.applyAndAdd(self.tabList)

            # We stop applying if we were applying it (NOTE: doing this before adding table due to redraw trigger of the whole panel)
            if self.data['active']:
                self.onToggleApply()

            self.addTablesHandle(dfs, names, bAdd=True, bPlot=False) # Triggers a redraw of the whole panel...
            #    df, name = self.tabList[iSel-1].applyFiltering(icol, self.data, bAdd=True)
            #    self.parent.addTables([df], [name], bAdd=True)
            #self.updateTabList()

            if len(errors)>0:
                if len(errors)>=len(self.tabList):
                    Error(self, 'Error: The action {} failed on all tables:\n\n'.format(self.action.name)+'\n'.join(errors))
                #elif len(errors)<len(self.tabList):
                #    Warn('Warning: The action {} failed on some tables:\n\n'.format(self.action.name)+'\n'.join(errors))


    def onClear(self, event=None):
        self.redrawHandle()

# --------------------------------------------------------------------------------}
# --- Default class for GUI to edit plugin and control a plot data action
# --------------------------------------------------------------------------------{
class PlotDataActionEditor(ActionEditor):

    def __init__(self, parent, action, sButtons=None, tables=False, help_string='', nBtRows=None, nBtCols=None):
        """ 
        """
        ActionEditor.__init__(self, parent, action=action, help_string=help_string)
            
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
        if sButtons is None:
            sButtons=['Close', 'Add', 'Help', 'Clear', 'Plot', 'Apply']
        self.btAdd   = None
        self.btHelp  = None
        self.btClear = None
        self.btPlot  = None
        nButtons = len(sButtons)
        buttons=[]
        for lbl in sButtons:
            if lbl=='Close':
                self.btClose = self.getBtBitmap(self,'Close','close',self.destroy)
                buttons.append(self.btClose)
            elif lbl=='Add':
                self.btAdd   = self.getBtBitmap(self, 'Add', 'add'  , self.onAdd)
                buttons.append(self.btAdd)
            elif lbl=='Help':
                self.btHelp  = self.getBtBitmap(self, 'Help', 'help', self.onHelp)
                buttons.append(self.btHelp)
            elif lbl=='Clear':
                self.btClear = self.getBtBitmap(self, 'Clear Plot', 'sun', self.onClear)
                buttons.append(self.btClear)
            elif lbl=='Plot':
                self.btPlot  = self.getBtBitmap(self, 'Plot ', 'chart'  , self.onPlot)
                buttons.append(self.btPlot)
            elif lbl=='Apply':
                self.btApply = self.getToggleBtBitmap(self, 'Apply', 'cloud', self.onToggleApply)
                buttons.append(self.btApply)
            else:
                raise NotImplementedError('Button: {}'.format(lbl))
        
        if tables:
            self.cbTabs= wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
            self.cbTabs.Enable(False) # <<< Cancelling until we find a way to select tables and action better
        else:
            self.cbTabs = None

        # --- Layout
        if nBtCols is None:
            nBtCols=2
        if nBtRows is None:
            nBtRows = int(np.ceil(nButtons/nBtCols))
        btSizer  = wx.FlexGridSizer(rows=nBtRows, cols=nBtCols, hgap=2, vgap=0)
        for bt in buttons:
            btSizer.Add(bt, 0, flag = wx.ALL|wx.EXPAND, border = 1)

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


def demoGUIPlugin(panelClass, actionCreator, data=None, mainLoop=True, title='Demo'):
    """ Function to demonstrate behavior of a plugin
    - actionCreator: interface(label, mainframe, data)

    """
    from pydatview.pipeline import PlotDataAction
    from pydatview.common import DummyMainFrame
    from pydatview.Tables import TableList
    from pydatview.pipeline import Pipeline
    from pydatview.GUIPlotPanel import PlotPanel
    from pydatview.GUISelectionPanel import SelectionPanel

#     if data is None:
#         data={'active':False}

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
    action = actionCreator(title, mainframe, data)

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

