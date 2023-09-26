import wx
import wx.stc as stc

class GUIScripterFrame(wx.Frame):
    def __init__(self, parent, mainframe, pipeLike, title):
        super(GUIScripterFrame, self).__init__(parent, title=title, size=(800, 600))

        # --- Data
        self.mainframe = mainframe
        self.pipeline  = pipeLike
        
        # --- GUI
        self.panel = wx.Panel(self)
        #self.text_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE)
        self.text_ctrl = stc.StyledTextCtrl(self.panel, style=wx.TE_MULTILINE)
        self.setup_syntax_highlighting()


        self.btGen = wx.Button(self.panel, label="Update")
        self.btRun = wx.Button(self.panel, label="Run Script")
        self.btSave = wx.Button(self.panel, label="Save to File")

        txtLib = wx.StaticText(self.panel, -1, 'Library:')
        libflavors = ["welib", "pydatview", "pyFAST"]
        self.cbLib = wx.Choice(self.panel, choices=libflavors)
        self.cbLib.SetSelection(1)

        txtDFS= wx.StaticText(self.panel, -1, 'DF storage:')
        DFSflavors = ["dict", "list", "enumeration"]
        self.cbDFS = wx.Choice(self.panel, choices=DFSflavors)
        self.cbDFS.SetSelection(0)

        txtCom= wx.StaticText(self.panel, -1, 'Comment level:')
        ComLevels = ["1", "2"]
        self.cbCom = wx.Choice(self.panel, choices=ComLevels)
        self.cbCom.SetSelection(0)

        
        # --- Layout
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        vbox.Add(self.text_ctrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=2)
        
        hbox.Add(     txtLib, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        hbox.Add(self.cbLib, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        hbox.Add(     txtDFS, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        hbox.Add(self.cbDFS, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        hbox.Add(     txtCom, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        hbox.Add(self.cbCom,               flag=wx.EXPAND|wx.ALL, border=5)
        hbox.Add(self.btGen     , flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
        hbox.Add(self.btRun     , flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
        hbox.Add(self.btSave    , flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL, border=5)
        vbox.Add(hbox, flag=wx.EXPAND)
        
        self.panel.SetSizerAndFit(vbox)

        # -- Binding
        self.btSave.Bind(wx.EVT_BUTTON, self.onSave)
        self.btRun.Bind(wx.EVT_BUTTON, self.onRun)
        self.btGen.Bind(wx.EVT_BUTTON, self.generateScript)
        self.cbLib.Bind(wx.EVT_CHOICE, self.generateScript)
        self.cbDFS.Bind(wx.EVT_CHOICE, self.generateScript)
        self.cbCom.Bind(wx.EVT_CHOICE, self.generateScript)

        self.generateScript()

    def _GUI2Data(self, *args, **kwargs):
        # GUI2Data
        data={}
        data['libFlavor'] = self.cbLib.GetStringSelection()
        data['dfsFlavor'] = self.cbDFS.GetStringSelection()
        data['verboseCommentLevel'] = int(self.cbCom.GetStringSelection())
        return data

    def generateScript(self, *args, **kwargs):
        # --- GUI 2 data
        scripterOptions = self._GUI2Data()

        # --- Mainframe GUI 2 data
        try:
            ID,SameCol,selMode=self.mainframe.selPanel.getPlotDataSelection()
        except:
            ID = None
        try:
            fig = self.mainframe.plotPanel.canvas.figure
            gs = fig.axes[0].get_gridspec()
            x_labels = []
            y_labels = []
            IPD = []
            hasLegend = []
            for i, ax in enumerate(fig.axes):
                x_labels.append(ax.get_xlabel())
                y_labels.append(ax.get_ylabel())
                IPD.append(ax.iPD)
                hasLegend.append(ax.get_legend() is not None)
            subPlots={'i':gs.nrows, 'j':gs.ncols, 'x_labels':x_labels, 'y_labels':y_labels, 'IPD':IPD, 'hasLegend':hasLegend}
        except:
            print('[WARN] GUIScripter - Failed to retrieve Subplot Data')
            subPlots = None
        try:
            plotStyle, plot_options, font_options, font_options_legd = self.mainframe.plotPanel.getPlotOptions()
            plotStyle.update(plot_options)
        except:
            plotStyle=None
            print('[WARN] GUIScripter - Failed to retrieve Plot Options')
        try:
            plotPanel = self.mainframe.plotPanel
            pltTypePanel = self.mainframe.plotPanel.pltTypePanel
            plotType = pltTypePanel.plotType()
            if plotType=='Regular':
                plotTypeData=None
            elif plotType=='PDF':
                plotTypeData = plotPanel.pdfPanel._GUI2Data()
            elif plotType=='FFT':
                plotTypeData = plotPanel.spcPanel._GUI2Data()
                pass
            elif plotType=='MinMax':
                plotTypeData = plotPanel.mmxPanel._GUI2Data()
                pass
            elif plotType=='Compare':
                plotTypeData = plotPanel.cmpPanel._GUI2Data()
        except:
            plotType=None
            plotTypeData=None
            print('[WARN] GUIScripter - Failed to retrieve plotType and plotTypeData')

        # --- Use Pipeline on tablist to generate the script
        s = self.pipeline.script(self.mainframe.tabList, scripterOptions, ID, subPlots, plotStyle, plotType=plotType, plotTypeData=plotTypeData)
        self.text_ctrl.SetValue(s)

    def onRun(self, event):
        """ Run the script in user terminal """
        self.pipeline.scripter.run(script=self.text_ctrl.GetValue())

    def onSave(self, event):
        """ Save script to file """
        file_extension = "py"
        
        dialog = wx.FileDialog(self, "Save Script to File", wildcard=f"(*.{file_extension})|*.{file_extension}", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        
        if dialog.ShowModal() == wx.ID_OK:
            file_path = dialog.GetPath()
            with open(file_path, "w") as file:
                file.write(self.text_ctrl.GetValue())
        
        dialog.Destroy()

    def setup_syntax_highlighting(self):
        # --- Basic
        mono_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        #self.text_ctrl.SetFont(mono_font)

        # --- Advanced 
        self.text_ctrl.StyleSetForeground(stc.STC_P_COMMENTLINE, wx.Colour(0, 128, 0))  # Comments (green)
        self.text_ctrl.StyleSetForeground(stc.STC_P_NUMBER, wx.Colour(123, 0, 0))  # Numbers (red)
        self.text_ctrl.StyleSetForeground(stc.STC_P_STRING   , wx.Colour(165, 32, 247))  # Strings
        self.text_ctrl.StyleSetForeground(stc.STC_P_CHARACTER, wx.Colour(165, 32, 247))  # Characters 
        self.text_ctrl.StyleSetForeground(stc.STC_P_WORD, wx.Colour(0, 0, 128))  # Keywords (dark blue)
        self.text_ctrl.StyleSetBold(stc.STC_P_WORD, True)  # Make keywords bold
        self.text_ctrl.SetLexer(stc.STC_LEX_PYTHON)  # Set the lexer for Python
        self.text_ctrl.StyleSetForeground(stc.STC_P_DEFAULT, wx.Colour(0, 0, 0))  # Default text color (black)
        self.text_ctrl.StyleSetBackground(stc.STC_P_DEFAULT, wx.Colour(255, 255, 255))  # Default background color (white)
        self.text_ctrl.StyleSetFont(stc.STC_STYLE_DEFAULT, mono_font)
        self.text_ctrl.SetUseHorizontalScrollBar(False)
        # Remove the left margin (line number margin)
        self.text_ctrl.SetMarginWidth(1, 0)  # Set the width of margin 1 (line number margin) to 0

