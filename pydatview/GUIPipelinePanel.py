import wx

from pydatview.pipeline import Pipeline
from pydatview.common import CHAR, Info
import wx.lib.agw.hyperlink as hl


class ActionPanel(wx.Panel):
    def __init__(self, parent, action, style=wx.TAB_TRAVERSAL):
        wx.Panel.__init__(self, parent, -1, style=style)
        #self.SetBackgroundColour((0,100,0))

        # --- Data
        self.action=action
        name = action.name

        # --- GUI
        if action.guiEditorClass is None:
            lko = wx.StaticText(self, -1, name)
        else:
            lko  = hl.HyperLinkCtrl(self, -1, name)
            lko.AutoBrowse(False)
            lko.SetUnderlines(False, False, False)
            lko.SetColours(wx.BLACK, wx.BLACK, wx.BLACK)
            lko.DoPopup(False)
            #lko.SetBold(True)
            lko.SetToolTip(wx.ToolTip('Change "'+name+'"'))
            lko.UpdateLink() # To update text properties

        lkc  = hl.HyperLinkCtrl(self, -1, 'x')
        lkc.AutoBrowse(False)
        lkc.EnableRollover(True)
        lkc.SetColours(wx.BLACK, wx.BLACK, (200,0,0))
        lkc.DoPopup(False)
        #lkc.SetBold(True)
        lkc.SetToolTip(wx.ToolTip('Remove "'+name+'"'))
        lkc.UpdateLink() # To update text properties

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(lko, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 0)
        sizer.AddSpacer(3) 
        sizer.Add(lkc, 0, wx.ALIGN_LEFT|wx.ALIGN_TOP                             , 1)
        sizer.AddSpacer(2) 

        txt = wx.StaticText(self, -1, '>')
        sizer.AddSpacer(3) 
        sizer.Add(txt, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 0)
        sizer.AddSpacer(3) 

        self.SetSizer(sizer)

        self.Bind(hl.EVT_HYPERLINK_LEFT, lambda ev: parent.onCloseAction(ev, action) , lkc)
        if action.guiEditorClass is not None:
            self.Bind(hl.EVT_HYPERLINK_LEFT, lambda ev: parent.onOpenAction(ev, action) , lko)

    def __repr__(self):
        s='<ActionPanel for action {}>\n'.format(self.action.name)
        return s

class ErrorPanel(wx.Panel):
    def __init__(self, parent, pipeline, style=wx.TAB_TRAVERSAL):
        wx.Panel.__init__(self, parent, -1, style=style)
        #self.SetBackgroundColour((100,0,0))
        # --- Data
        self.pipeline=pipeline
        # --- GUI
        lke  = hl.HyperLinkCtrl(self, -1, 'Errors (0)')
        lke.AutoBrowse(False)
        lke.EnableRollover(True)
        lke.SetColours(wx.BLACK, wx.BLACK, (200,0,0))
        lke.DoPopup(False)
        #lkc.SetBold(True)
        lke.SetToolTip(wx.ToolTip('View errors.'))
        lke.UpdateLink() # To update text properties
        self.lke=lke

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(lke, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        self.sizer=sizer
        self.SetSizer(sizer)

        self.Bind(hl.EVT_HYPERLINK_LEFT, self.showErrors, lke)

        self.update()

    def showErrors(self, event=None):
        if len(self.pipeline.errorList)>0:
            message='\n'.join(self.pipeline.errorList)
        else:
            message='No errors'
        Info(self, message, caption = 'Errors when applying the pipeline actions:')

    def update(self):
        self.lke.SetLabel('Errors ({})'.format(len(self.pipeline.errorList)))
        self.sizer.Layout()


# --------------------------------------------------------------------------------}
# --- PipelinePanel 
# --------------------------------------------------------------------------------{
class PipelinePanel(wx.Panel, Pipeline):
    """ Display the pipeline of actions, allow user to edit it """

    def __init__(self, parent, data=None, tabList=None, style=wx.TAB_TRAVERSAL):
        # Init parent classes
        wx.Panel.__init__(self, parent, -1, style=style)
        Pipeline.__init__(self, data=data)
        #self.SetBackgroundColour(wx.BLUE)

        # --- Important GUI Data
        self.tabList = tabList
        self.actionPanels=[]
        self.ep = ErrorPanel(self, pipeline=self)

        # --- GUI
        #self.btSave  = wx.Button(self, wx.ID_ANY, 'Save', style=wx.BU_EXACTFIT)
        #self.btLoad  = wx.Button(self, wx.ID_ANY, 'Load', style=wx.BU_EXACTFIT)
        #self.btClear = wx.Button(self, wx.ID_ANY, CHAR['sun']+' Clear', style=wx.BU_EXACTFIT)
        txt = wx.StaticText(self, -1, "Pipeline:")
        leftSizer = wx.BoxSizer(wx.HORIZONTAL)
        #leftSizer.Add(self.btSave , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL                 |wx.LEFT, border=2)
        #leftSizer.Add(self.btLoad , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL                 |wx.LEFT, border=2)
        #leftSizer.Add(self.btClear, 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL                 |wx.LEFT, border=2)
        leftSizer.Add(txt         , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, border=0)

        self.wrapSizer = wx.WrapSizer(orient=wx.HORIZONTAL)


        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Sizer.Add(leftSizer     , 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT , 1)
        self.Sizer.Add(self.wrapSizer, 1, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 1)
        self.Sizer.Add(self.ep       , 0, wx.ALIGN_CENTER_VERTICAL|          wx.LEFT, 1)

        self.SetSizer(self.Sizer)

        self.populate()

    def populate(self):
        # Delete everything in wrapSizer
        self.wrapSizer.Clear(delete_windows=True)
        self.wrapSizer.Add(wx.StaticText(self, -1, ' '), wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 0)

        # Add all actions to panel
        for ia, action in enumerate(self.actions):
            self._addPanel(action)
        self.ep.update()
        self.wrapSizer.Layout()
        self.Sizer.Layout()

    def _addPanel(self, action):
        ap = ActionPanel(self, action)
        self.wrapSizer.Add(ap, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 0)

    def _deletePanel(self, action):
        for child in self.wrapSizer.Children:
            win = child.GetWindow()
            if win is not None:
                if hasattr(win,'action'):
                    if win.action==action:
                        actionPanel=win
        self.wrapSizer.Hide(actionPanel) #actionPanel.Destroy()
        self.wrapSizer.Layout()
        self.Sizer.Layout()

    def onCloseAction(self, event, action=None):
        self.remove(action, tabList=self.tabList) # TODO
        try:
            action.mainframe.plotPanel.removeTools()
        except:
            print('[FAIL] removing tool from plotPanel')

    def onOpenAction(self, event, action=None):
        """ Opens the Action GUI Editor """
        event.Skip()
        action.mainframe.plotPanel.showToolAction(action)
        

    # --- Wrap the data class
    def apply(self, tablist, force=False, applyToAll=False):
        # Call parent class (data)
        Pipeline.apply(self, tablist, force=force, applyToAll=applyToAll)
        # Update GUI
        self.ep.update()
        self.Sizer.Layout()

    def append(self, action, overwrite=True, apply=True, updateGUI=True, tabList=None):
        i = self.index(action)
        if not overwrite:
            # Delete action is already present and if it's a "unique" action
            ac = self.find(action.name)
            if ac is not None:
                if ac.unique:
                    print('>>> Deleting unique action before inserting it again', ac.name)
                    self.remove(ac, silent=True, updateGUI=False)
        # Add to pipeline
        print('>>> GUIPipeline: Adding action',action.name)
        # Call parent class (data)
        Pipeline.append(self, action, overwrite=overwrite, apply=apply, updateGUI=updateGUI, tabList=tabList)
        # Add to GUI
        if i<0:
            # NOTE: populating when "modifying" can result to some kind of segfault (likely due to the window deletion)
            self.populate() # NOTE: we populate because of the change of order between actionsData and actionsPlot..
        #self._addPanel(action)
        #self.Sizer.Layout()
        # Update list of errors
        self.ep.update()

    def remove(self, action, silent=False, cancel=True, updateGUI=True, tabList=None):
        """ NOTE: the action is only removed from the pipeline, not deleted. """
        print('>>> Deleting action', action.name)
        # Call parent class (data)
        Pipeline.remove(self, action, cancel=cancel, updateGUI=updateGUI, tabList=tabList)
        # Remove From GUI
        try:
            self._deletePanel(action)
        except:
            print('[FAIL] GUIPipeline: could not delete action')

        if action.removeNeedReload:
            if not silent:
                Info(self, 'A reload is required now that the action "{}" has been removed.'.format(action.name))

        # Update list of errors
        self.ep.update()


if __name__ == '__main__':
    """ """
    from pydatview.pipeline import Pipeline, Action, IrreversibleTableAction, PlotDataAction


    app = wx.App(False)
    self=wx.Frame(None,-1,"GUIPipelinePanel main")

    p = PipelinePanel(self)
    p.append(PlotDataAction('PlotData Do X'), apply=False)
    p.append(PlotDataAction('PlotData Do Y'), apply=False)
    p.append(Action('Change units'),          apply=False)
    p.append(IrreversibleTableAction('Rename columns'), apply=False)

    p.errorList=['This is a first error','This is a second error']

    p.populate()

    self.SetSize((800, 200))
    self.Center()
    self.Show()



    #d ={'ColA': np.random.normal(0,1,100)+1,'ColB':np.random.normal(0,1,100)+2}
    #df = pd.DataFrame(data=d)
    #tab=Table(data=df)
    #p.showStats(None,[tab],[0],[0,1],tab.columns,0,erase=True)

    app.MainLoop()

