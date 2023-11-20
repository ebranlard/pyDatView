import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

class Plot2DPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        # Data
        self.parent = parent
        self.canvas = FigureCanvas(self, -1, plt.figure())
        self.fields = []
        # GUI 
        sizer_canvas = wx.BoxSizer(wx.HORIZONTAL)
        sizer_canvas.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 1)
        self.SetSizer(sizer_canvas)

    def add_field(self, x, y, M, sx='x', sy='y', fieldname='field'):
        self.fields.append((x, y, M, sx, sy, fieldname))

    def plot_field(self, x, y, M, sx='x', sy='y', fieldname='field'):
        # Clear previous plot
        plt.clf()
        # Plot the 2D field on the canvas using contourf
        plt.contourf(x, y, M)
        plt.title(f"2D Field: {fieldname}")
        plt.xlabel(sx)
        plt.ylabel(sy)

        # Update the canvas
        plt.draw()
if __name__ == '__main__':
    import numpy as np
    # --- Dummy Data
    nx, ny = 10, 4
    field1 = np.linspace(0,1,nx), np.linspace(0,2,ny), np.random.randn(ny,nx)
    field2 = np.linspace(0,1,nx), np.linspace(0,2,ny), np.random.randn(ny,nx)

    # --- Dummy GUI
    app = wx.App(False)
    self = wx.Frame(None,-1,"GUI Plot Panel Demo")
    panel = Plot2DPanel(self)
    panel.add_field(*field1)
    panel.plot_field(*field1)
        
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(panel, 1, flag = wx.EXPAND|wx.ALL,border = 5)
    self.SetSizer(sizer)
    self.Center()
    self.SetSize((900, 600))
    self.Show()
    app.MainLoop()
