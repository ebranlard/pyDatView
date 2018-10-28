import wx
from wx.lib.splitter import MultiSplitterWindow


class MultiSplit(MultiSplitterWindow):
    def __init__(self,parent,*args,**kwargs):
        super(MultiSplit,self).__init__(parent,*args,**kwargs)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.onSashChange)
        self.Bind(wx.EVT_SIZE, self.onParentChangeSize, self)
#         self.nWindow=0

    def SetMinimumPaneSize(self,size):
        super(MultiSplit,self).SetMinimumPaneSize(size)
        self.MinSashSize=size

    def AppendWindow(self, window, **kwargs):
        super(MultiSplit,self).AppendWindow(window,**kwargs)
        window.Show()

    def DetachWindow(self, window):
        super(MultiSplit,self).DetachWindow(window)
        window.Hide()

    def InsertWindow(self, idx, window, *args, **kwargs):
        super(MultiSplit,self).InsertWindow(idx, window, *args, **kwargs)
        window.Show()

    @property
    def nWindows(self):
        return len(self._windows)

    def removeAll(self):
        for i in reversed(range(self.nWindows)): 
            w = self.GetWindow(i)
            self.DetachWindow(w)
            w.Hide()

    def onParentChangeSize(self,Event=None):
        print('here',self.GetClientSize())
        self.setEquiSash()

    def setEquiSash(self,event=None):
        if self.nWindows>0:
            S=self.GetClientSize()
            borders=5*self.nWindows-1
            equi=int((S[0]-borders)/self.nWindows)
            for i in range(self.nWindows-1):
                self.SetSashPosition(i, equi)

    def onSashChange(self,event=None):
        # Not really pretty but will ensure the size don't go out of screen
        pos=[self.GetSashPosition(i) for i in range(self.nWindows)]
        if any([p<self.MinSashSize for p in pos]):
            self.setEquiSash() # TODO




if __name__=='__main__':

    class RandomPanel(wx.Panel):
        def __init__(self, parent, color):
            wx.Panel.__init__(self, parent)
            wx.StaticText(self,label=color)
            self.SetBackgroundColour(color)

    class SelectionPanel(wx.Panel):
        """ Display options for the user to select data """
        def __init__(self, parent):
            # Superclass constructor
            super(SelectionPanel,self).__init__(parent)
            # DATA
            self.splitter = MultiSplit(self, style=wx.SP_LIVE_UPDATE)
            self.splitter.SetMinimumPaneSize(70)
            self.tabPanel  = RandomPanel(self.splitter,'blue')
            self.colPanel1 = RandomPanel(self.splitter,'red')
            self.colPanel2 = RandomPanel(self.splitter,'green')
            self.tabPanel.Hide()
            self.colPanel1.Hide()
            self.colPanel2.Hide()
            self.default()
            #self.onSashChange(event=None)

            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(self.splitter, 2, flag=wx.EXPAND, border=5)
            self.SetSizer(sizer)


        def default(self):
            self.splitter.removeAll()
            self.tabPanel.Show()
            self.colPanel1.Show()
            self.colPanel2.Show()
            self.splitter.AppendWindow(self.tabPanel)
            self.splitter.AppendWindow(self.colPanel1)
            self.splitter.AppendWindow(self.colPanel2)
            self.splitter.onSashChange()

        def mode1(self):
            if self.splitter.nWindows==2:
                self.splitter.InsertWindow(1,self.colPanel1) 
                self.colPanel1.Show()

        def mode2(self):
            if self.splitter.nWindows==3:
                self.splitter.DetachWindow(self.colPanel1) 
                self.colPanel1.Hide()

    class MainFrame(wx.Frame):
        def __init__(self, filename=None):
            # Parent constructor
            wx.Frame.__init__(self, None, -1)
            # --- ToolBar
            tb = self.CreateToolBar(wx.TB_HORIZONTAL)
            self.toolBar = tb 
            tb.AddSeparator()
            btDEBUG  = wx.Button( tb, wx.ID_ANY, "REMOVE", wx.DefaultPosition, wx.DefaultSize )
            btDEBUG2 = wx.Button( tb, wx.ID_ANY, "ADD", wx.DefaultPosition, wx.DefaultSize )
            btDEBUG3 = wx.Button( tb, wx.ID_ANY, "Default", wx.DefaultPosition, wx.DefaultSize )
            tb.AddStretchableSpace()
            tb.AddSeparator()
            tb.AddControl(btDEBUG)
            tb.AddControl(btDEBUG2)
            tb.AddControl(btDEBUG3)
            tb.AddStretchableSpace()
            tb.AddSeparator()
            tb.Bind(wx.EVT_BUTTON,self.onDEBUG,btDEBUG)
            tb.Bind(wx.EVT_BUTTON,self.onDEBUG2,btDEBUG2)
            tb.Bind(wx.EVT_BUTTON,self.onDEBUG3,btDEBUG3)
            tb.Realize() 

            # --- Main Panel and Notebook
            self.MainPanel = SelectionPanel(self)
            sizer = wx.BoxSizer()
            sizer.Add(self.MainPanel, 1, flag=wx.EXPAND)
            self.SetSizer(sizer)
            self.SetSize((800, 600))
            self.Center()
            self.Show()

        def onDEBUG3(self, event):
            self.MainPanel.default()

        def onDEBUG2(self, event):
            self.MainPanel.mode1()

        def onDEBUG(self, event):
            self.MainPanel.mode2()

    app = wx.App(False)
    frame = MainFrame()
    app.MainLoop()
