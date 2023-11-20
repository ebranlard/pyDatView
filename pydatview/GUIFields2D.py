""" 
"""
import os
import numpy as np
import wx
from wx.lib.splitter import MultiSplitterWindow
# Local
from pydatview.common import ellude_common
from pydatview.common import CHAR
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
        self.files_panel = wx.Panel(multi_split)
        self.fields_panel = wx.Panel(multi_split)
        self.canvas_panel = Plot2DPanel(multi_split)

        self.btExtractFields = wx.Button(self.files_panel, label=CHAR['compute']+' '+"Extract 2D fields (beta)", style=wx.BU_EXACTFIT)
        self.lbFiles = wx.ListBox(self.files_panel, style=wx.LB_SINGLE)
        self.lbFiles.Bind(wx.EVT_LISTBOX, self.on_file_selected)

        sizer_files = wx.BoxSizer(wx.VERTICAL)
        sizer_files.Add(self.btExtractFields, 0, wx.EXPAND | wx.ALL, 1)
        sizer_files.Add(self.lbFiles, 1, wx.EXPAND | wx.ALL, 1)
        self.files_panel.SetSizer(sizer_files)

        self.lbFields = wx.ListBox(self.fields_panel, style=wx.LB_SINGLE)
        self.lbFields.Bind(wx.EVT_LISTBOX, self.on_2d_field_selected)

        sizer_fields = wx.BoxSizer(wx.VERTICAL)
        sizer_fields.Add(self.lbFields, 1, wx.EXPAND | wx.ALL, 1)
        self.fields_panel.SetSizer(sizer_fields)

        multi_split.AppendWindow(self.files_panel, 200)
        multi_split.AppendWindow(self.fields_panel, 200)
        multi_split.AppendWindow(self.canvas_panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(multi_split, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Bind
        #self.btExtractFields.Bind(wx.EVT_BUTTON, self.onExtract)
        self.btExtractFields.Bind(wx.EVT_BUTTON, self.cleanGUI)

    def cleanGUI(self, event=None):
        self.lbFiles.Clear()
        self.lbFields.Clear()

    def updateFiles(self, filenames, fileobjects):
        self.fileobjects=fileobjects
        filenames = [os.path.abspath(f).replace('/','|').replace('\\','|') for f in filenames]
        filenames = ellude_common(filenames)
        self.lbFiles.Set(filenames)

    def onExtract(self, event=None):
        for fo in self.fileobjects:
            extract2Dfields(fo)

    def on_file_selected(self, event=None):
        isel = self.lbFiles.GetSelection()
        file_object = self.fileobjects[isel]
        if not hasattr(file_object, 'fields2D_tmp'):
            # Computing fields here if not already done for this file
            fields = extract2Dfields(file_object)
        else:
            fields  = file_object.fields2D_tmp

        if fields is not None:
            fields_list =[]
            for ifield, field in enumerate(fields):
                for c,_ in field['Fields'].items():
                    fields_list.append(str(ifield) + '_' + field['name'] +'_' + c)
            self.lbFields.Set(fields_list)
        else:
            print('[WARN] No 2D fields for this file')


    def on_2d_field_selected(self, event=None):
        isel = self.lbFiles.GetSelection()
        file_object = self.fileobjects[isel]
        sfield = self.lbFields.GetStringSelection()
        sp = sfield.split('_')
        i = int(sp[0])
        kind = sp[1]
        col = '_'.join(sp[2:])

        field = file_object.fields2D_tmp[i]
        if field is not None:
            sx, x = field['x']
            sy, y = field['y']
            M = field['Fields'][col]
            self.canvas_panel.plot_field(x, y, M, sx, sy, fieldname=col)

