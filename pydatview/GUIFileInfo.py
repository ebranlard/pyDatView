""" 

"""
import os
import wx
from wx.lib.splitter import MultiSplitterWindow
# Local
import pydatview.io as weio # File Formats and File Readers
from pydatview.common import ellude_common

class FileInfoPanel(wx.Panel):

    def __init__(self, parent, mainframe, filelist=None):
        wx.Panel.__init__(self, parent)
        # Data
        self.parent = parent
        self.mainframe = mainframe
        self.fileobjects = None
        # GUI
        multi_split = MultiSplitterWindow(self)
        self.list_panel = wx.Panel(multi_split)
        self.text_panel = wx.Panel(multi_split)

        self.lbFiles = wx.ListBox(self.list_panel, style=wx.LB_SINGLE)
        self.lbFiles.Bind(wx.EVT_LISTBOX, self.on_file_selected)

        sizer_list = wx.BoxSizer(wx.VERTICAL)
        sizer_list.Add(self.lbFiles, 1, wx.EXPAND | wx.ALL, 5)
        self.list_panel.SetSizer(sizer_list)

        self.tb = wx.TextCtrl(self.text_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer_text = wx.BoxSizer(wx.HORIZONTAL)
        sizer_text.Add(self.tb, 1, wx.EXPAND | wx.ALL, 5)
        self.text_panel.SetSizer(sizer_text)

        multi_split.AppendWindow(self.list_panel, 200)
        multi_split.AppendWindow(self.text_panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(multi_split, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def updateFiles(self, filenames, fileobjects):
        self.fileobjects = fileobjects
        filenames = [os.path.abspath(f).replace('/','|').replace('\\','|') for f in filenames]
        filenames = ellude_common(filenames)
        self.lbFiles.Set(filenames)

    def on_file_selected(self, event):
        isel = self.lbFiles.GetSelection()
        content = self.fileobjects[isel].__repr__()
        self.tb.SetValue(content)
