""" 
"""
import os
import numpy as np
import wx
from wx.lib.splitter import MultiSplitterWindow
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
# Local
from pydatview.common import ellude_common

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
        self.canvas_panel = wx.Panel(multi_split)

        self.lbFiles = wx.ListBox(self.files_panel, style=wx.LB_SINGLE)
        self.lbFiles.Bind(wx.EVT_LISTBOX, self.on_file_selected)

        sizer_files = wx.BoxSizer(wx.VERTICAL)
        sizer_files.Add(self.lbFiles, 1, wx.EXPAND | wx.ALL, 5)
        self.files_panel.SetSizer(sizer_files)

        self.lbFields = wx.ListBox(self.fields_panel, style=wx.LB_SINGLE)
        self.lbFields.Bind(wx.EVT_LISTBOX, self.on_2d_field_selected)

        sizer_fields = wx.BoxSizer(wx.VERTICAL)
        sizer_fields.Add(self.lbFields, 1, wx.EXPAND | wx.ALL, 5)
        self.fields_panel.SetSizer(sizer_fields)

        self.canvas = FigureCanvas(self.canvas_panel, -1, plt.figure())
        sizer_canvas = wx.BoxSizer(wx.HORIZONTAL)
        sizer_canvas.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        self.canvas_panel.SetSizer(sizer_canvas)

        multi_split.AppendWindow(self.files_panel, 200)
        multi_split.AppendWindow(self.fields_panel, 200)
        multi_split.AppendWindow(self.canvas_panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(multi_split, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def updateFiles(self, filenames, fileobjects):
        self.fileobjects=fileobjects
        filenames = [os.path.abspath(f).replace('/','|').replace('\\','|') for f in filenames]
        filenames = ellude_common(filenames)
        self.lbFiles.Set(filenames)


    def on_file_selected(self, event):
        selected_file = self.lbFiles.GetStringSelection()
        # Assume get_2d_fields_list() is a function that returns a list of 2D fields in the file
        fields_list = get_2d_fields_list(selected_file)
        self.lbFields.Set(fields_list)

    def on_2d_field_selected(self, event):
        selected_field = self.lbFields.GetStringSelection()
        plot_selected_2d_field(selected_field)


def generate_random_2d_field(shape=(30, 40)):
    return np.random.rand(*shape)

def get_2d_fields_list(file_path):
    # In this example, return a list of 2D fields and add "field_random"
    return ["field1", "field2", "field_random"]

def get_2d_field_data(field_name):
    # Placeholder for getting the data for the selected 2D field
    # You might want to implement this based on your actual data source
    pass

def plot_selected_2d_field(field_name):
    if field_name == "field_random":
        field_data = generate_random_2d_field()
    else:
        # Assume get_2d_field_data() is a function that returns the data for the selected 2D field
        field_data = get_2d_field_data(field_name)

    # Clear previous plot
    plt.clf()

    # Plot the 2D field on the canvas using contourf
    plt.contourf(field_data)
    plt.title(f"2D Field: {field_name}")

    # Update the canvas
    plt.draw()
