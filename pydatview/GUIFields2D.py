""" 
"""
import os
import numpy as np
import wx
from wx.lib.splitter import MultiSplitterWindow
# Local
from pydatview.common import ellude_common
from pydatview.common import CHAR
from pydatview.GUICommon import getMonoFont
from pydatview.Fields2D import extract2Dfields
from pydatview.GUIPlot2DPanel import Plot2DPanel

# --------------------------------------------------------------------------------}
# --- Fields 2D Panel 
# --------------------------------------------------------------------------------{
class Fields2DPanel(wx.Panel):
    def __init__(self, parent, mainframe):
        wx.Panel.__init__(self, parent)
        # Data
        self.parent = parent
        self.mainframe = mainframe
        self.fileobjects = None

        multi_split = MultiSplitterWindow(self)
        self.filesPanel = wx.Panel(multi_split)
        self.fieldsPanel = wx.Panel(multi_split)
        self.canvasPanel = Plot2DPanel(multi_split)

        # GUI
        self.btExtractFields = wx.Button(self.filesPanel, label=CHAR['compute']+' '+"Extract 2D fields for all", style=wx.BU_EXACTFIT)
        self.textArgs   = wx.TextCtrl(self.filesPanel, wx.ID_ANY, '', style = wx.TE_PROCESS_ENTER)
        self.lbFiles = wx.ListBox(self.filesPanel, style=wx.LB_EXTENDED)
        self.lbFields = wx.ListBox(self.fieldsPanel, style=wx.LB_EXTENDED)
        self.textArgs.SetValue('DeltaAzi=10') # TODO
        self.lbFiles.SetFont(getMonoFont(self))
        self.lbFields.SetFont(getMonoFont(self))
        self.textArgs.SetFont(getMonoFont(self))

        # Layout
        sizer_files = wx.BoxSizer(wx.VERTICAL)
        sizer_files.Add(self.textArgs, 0, wx.EXPAND | wx.ALL, 1)
        sizer_files.Add(self.btExtractFields, 0, wx.EXPAND | wx.ALL, 1)
        sizer_files.Add(self.lbFiles, 1, wx.EXPAND | wx.ALL, 1)
        self.filesPanel.SetSizer(sizer_files)

        sizer_fields = wx.BoxSizer(wx.VERTICAL)
        sizer_fields.Add(self.lbFields, 1, wx.EXPAND | wx.ALL, 1)
        self.fieldsPanel.SetSizer(sizer_fields)

        multi_split.AppendWindow(self.filesPanel, 200)
        multi_split.AppendWindow(self.fieldsPanel, 200)
        multi_split.AppendWindow(self.canvasPanel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(multi_split, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Bind
        self.lbFiles.Bind(wx.EVT_LISTBOX, self.on_file_selected)
        self.lbFields.Bind(wx.EVT_LISTBOX, self.on_2d_field_selected)
        self.btExtractFields.Bind(wx.EVT_BUTTON, self.onExtract)
        #self.textArgs.Bind(wx.EVT_TEXT_ENTER, self.onParamChangeEnter)

    def cleanGUI(self, event=None):
        self.deselect()
        self.lbFiles.Clear()
        self.lbFields.Clear()
        self.canvasPanel.clean_plot()

    def deselect(self, event=None):
        [self.lbFiles.Deselect(i) for i in self.lbFiles.GetSelections()]
        [self.lbFields.Deselect(i) for i in self.lbFields.GetSelections()]

    def updateFiles(self, filenames, fileobjects):
        self.fileobjects=fileobjects
        filenames = [os.path.abspath(f).replace('/','|').replace('\\','|') for f in filenames]
        filenames = ellude_common(filenames)
        self.lbFiles.Set(filenames)
        #self.lbFiles.SetSelection(0)
        #self.on_file_selected()

    def getArgs(self):
        args = self.textArgs.GetValue().split(',')
        kwargs={}
        for arg in args:
            k, v = arg.split('=')
            kwargs[k.strip()] = v.strip()
        return kwargs

    def onExtract(self, event=None):
        self.deselect()
        kwargs = self.getArgs()
        for fo in self.fileobjects:
            extract2Dfields(fo, force=True, **kwargs)

    def on_file_selected(self, event=None):
        self.canvasPanel.clean_plot()

        ISelF = self.lbFiles.GetSelections()
        kwargs = self.getArgs()
        # --- Compute 2d field if not done yet
        for iself in ISelF:
            file_object = self.fileobjects[iself]
            if not hasattr(file_object, 'fields2D_tmp'):
                # Computing fields here if not already done for this file
                fields = extract2Dfields(file_object, **kwargs)
            else:
                fields  = file_object.fields2D_tmp

        iself = ISelF[0]
        fieldListByFile=[]
        for iself in ISelF:
            fields  = file_object.fields2D_tmp
            if fields is not None:
                fieldListByFile.append(fields.keys())
            else:
                print('[WARN] No 2D fields for this file')

        # --- Get common columns
        if len(fieldListByFile)>0:
            commonCols = fieldListByFile[0]
            for i in np.arange(1,len(fieldListByFile)):
                commonCols = list( set(commonCols) & set( fieldListByFile[i]))
            # Respect order of first 
            commonCols = [c for c in fieldListByFile[0] if c in commonCols]
            #commonCols.sort()
            self.lbFields.Set(commonCols)

            # Trigger, we select the first field...
            if len(commonCols)>0:
                self.lbFields.SetSelection(0)
                self.on_2d_field_selected()
        else:
            print('[WARN] No 2D fields')


    def on_2d_field_selected(self, event=None):
        ISelF = self.lbFiles.GetSelections()
        self.canvasPanel.fields=[]
        for iself in ISelF :
            file_object = self.fileobjects[iself]
            ISelC = self.lbFields.GetSelections()
            for iselc in ISelC:
                sfield = self.lbFields.GetString(iselc)
                # Field is a dictionary with keys: M, x, y, sx, sy, fieldname
                field = file_object.fields2D_tmp.loc(sfield)
                self.canvasPanel.add_field(**field)
        self.canvasPanel.update_plot()




