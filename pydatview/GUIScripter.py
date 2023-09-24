import wx

class GUIScripterFrame(wx.Frame):
    def __init__(self, parent, mainframe, pipeLike, title):
        super(GUIScripterFrame, self).__init__(parent, title=title, size=(800, 600))

        # --- Data
        self.mainframe = mainframe
        self.pipeline  = pipeLike
        
        # --- GUI
        self.panel = wx.Panel(self)
        self.text_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE)
        self.btGen = wx.Button(self.panel, label="Regenerate")
        self.btRun = wx.Button(self.panel, label="Run Script")
        self.btSave = wx.Button(self.panel, label="Save to File")
        self.flavors = ["welib", "pydatview", "pyFAST"]
        self.cbFlavors = wx.Choice(self.panel, choices=self.flavors)
        self.cbFlavors.SetSelection(1)
        
        # --- Layout
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        vbox.Add(self.text_ctrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        
        hbox.Add(self.cbFlavors, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        hbox.Add(self.btGen     , flag=wx.ALL, border=10)
        hbox.Add(self.btRun     , flag=wx.ALL, border=10)
        hbox.Add(self.btSave    , flag=wx.ALL, border=10)
        vbox.Add(hbox, flag=wx.EXPAND)
        
        self.panel.SetSizerAndFit(vbox)

        # -- Binding
        self.btSave.Bind(wx.EVT_BUTTON, self.onSave)
        self.btRun.Bind(wx.EVT_BUTTON, self.onRun)
        self.btGen.Bind(wx.EVT_BUTTON, self.generateScript)
        self.cbFlavors.Bind(wx.EVT_CHOICE, self.onFlavorChange)

        self.generateScript()


    def generateScript(self, *args, **kwargs):
        # GUI2Data
        flavorDict={}
        flavorDict['libFlavor'] = self.cbFlavors.GetStringSelection()

        try:
            ID,SameCol,selMode=self.mainframe.selPanel.getPlotDataSelection()
        except:
            ID is None
        s = self.pipeline.script(self.mainframe.tabList, flavorDict, ID)
        self.text_ctrl.SetValue(s)

    def onFlavorChange(self, event):
        flavor = self.cbFlavors.GetStringSelection()
        # You can add code here to handle the selected format change event
        self.generateScript()


    def onRun(self, event):
        self.pipeline.scripter.run()



    def onSave(self, event):
        file_extension = "py"
        
        dialog = wx.FileDialog(self, "Save Script to File", wildcard=f"(*.{file_extension})|*.{file_extension}", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        
        if dialog.ShowModal() == wx.ID_OK:
            file_path = dialog.GetPath()
            with open(file_path, "w") as file:
                file.write(self.text_ctrl.GetValue())
        
        dialog.Destroy()

