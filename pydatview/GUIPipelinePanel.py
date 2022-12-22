import wx

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
        ##lko = wx.Button(self, wx.ID_ANY, name, style=wx.BU_EXACTFIT)
        lko = wx.StaticText(self, -1, name)
        ##lko  = hl.HyperLinkCtrl(self, -1, name)
        ##lko.AutoBrowse(False)
        ##lko.SetUnderlines(False, False, False)
        ##lko.SetColours(wx.BLACK, wx.BLACK, wx.BLACK)
        ##lko.DoPopup(False)
        ###lko.SetBold(True)
        ##lko.SetToolTip(wx.ToolTip('Change "'+name+'"'))
        ##lko.UpdateLink() # To update text properties

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

        self.Bind(hl.EVT_HYPERLINK_LEFT, lambda ev: parent.onCloseAction(ev, action, self) , lkc)

    def __repr__(self):
        s='<ActionPanel for action {}>\n'.format(self.action.name)
        return s

class ErrorPanel(wx.Panel):
    def __init__(self, parent, pipeline, style=wx.TAB_TRAVERSAL):
        wx.Panel.__init__(self, parent, -1, style=style)
        #self.SetBackgroundColour((100,0,0))
        # --- Data
        self.parent=parent
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
        Info(self.parent, message, caption = 'Errors when applying the pipeline actions:')

    def update(self):
        self.lke.SetLabel('Errors ({})'.format(len(self.pipeline.errorList)))
        self.sizer.Layout()


class PipelinePanel(wx.Panel):
    """ Display the pipeline of actions, allow user to edit it """

    def __init__(self, parent, pipeline, style=wx.TAB_TRAVERSAL):
        #style=wx.RAISED_BORDER
        wx.Panel.__init__(self, parent, -1, style=style)
        #self.SetBackgroundColour(wx.BLUE)

        # --- Data
        self.parent = parent
        self.pipeline = pipeline
        self.actionPanels=[]

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

        self.ep = ErrorPanel(self, self.pipeline)

        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Sizer.Add(leftSizer     , 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT , 1)
        self.Sizer.Add(self.wrapSizer, 1, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 1)
        self.Sizer.Add(self.ep       , 0, wx.ALIGN_CENTER_VERTICAL|          wx.LEFT, 1)

        self.SetSizer(self.Sizer)

        self.populate()

    def populate(self):
        # Delete everything in wrapSizer
        self.wrapSizer.Clear(True)
        self.wrapSizer.Add(wx.StaticText(self, -1, ' '), wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 0)

        # Add all actions to panel
        for ia, action in enumerate(self.pipeline.actions):
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

    def onCloseAction(self, event, action=None, actionPanel=None):
        self.remove(action)

    # --- Wrap the data class
    def apply(self, tablist, force=False, applyToAll=False):
        self.pipeline.apply(tablist, force=force, applyToAll=applyToAll)

        self.ep.update()
        self.Sizer.Layout()

    def append(self, action, cancelIfPresent=False):
        if not cancelIfPresent:
            # Delete action is already present and if it's a "unique" action
            ac = self.pipeline.find(action.name)
            if ac is not None:
                if ac.unique:
                    print('>>> Deleting unique action before inserting it again', ac.name)
                    self.remove(ac, silent=True)
        # Add to pipeline
        print('>>> Adding action',action.name)
        self.pipeline.append(action, cancelIfPresent=cancelIfPresent)
        # Add to GUI
        self.populate() # NOTE: we populate because of the change of order between actionsData and actionsPlot..
        #self._addPanel(action)
        #self.Sizer.Layout()

    def remove(self, action, silent=False):
        """ NOTE: the action is only removed from the pipeline, not deleted. """
        print('>>> Deleting action',action.name)
        # Remove From Data
        self.pipeline.remove(action)
        # Remove From GUI
        self._deletePanel(action)

        if action.removeNeedReload:
            if not silent:
                Info(self.parent, 'A reload is required now that the action "{}" has been removed.'.format(action.name))
            # TODO trigger reload/reapply
            # TODO trigger GUI update
        self.ep.update()


if __name__ == '__main__':
    """ """
    from pydatview.pipeline import Pipeline, Action, IrreversibleAction, PlotDataAction

    pl = Pipeline()

    app = wx.App(False)
    self=wx.Frame(None,-1,"GUIPipelinePanel main")

    p = PipelinePanel(self, pl)
    p.append(PlotDataAction('PlotData Do X'))
    p.append(PlotDataAction('PlotData Do Y'))
    p.append(Action('Change units'))
    p.append(IrreversibleAction('Rename columns'))

    pl.errorList=['This is a first error','This is a second error']

    p.populate()

    self.SetSize((800, 200))
    self.Center()
    self.Show()



    #d ={'ColA': np.random.normal(0,1,100)+1,'ColB':np.random.normal(0,1,100)+2}
    #df = pd.DataFrame(data=d)
    #tab=Table(data=df)
    #p.showStats(None,[tab],[0],[0,1],tab.columns,0,erase=True)

    app.MainLoop()

