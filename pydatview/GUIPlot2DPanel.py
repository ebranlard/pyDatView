
import numpy as np
import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas.plotting import register_matplotlib_converters
from pydatview.GUIToolBox import NavigationToolbar2WxSubTools
from pydatview.common import CHAR

class Plot2DPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.fields = []

        # Figure and Canvas
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.subplotsPar = None # Init

        register_matplotlib_converters()
        #self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)
        #self.canvas.mpl_connect('button_press_event', self.onMouseClick)
        #self.canvas.mpl_connect('button_release_event', self.onMouseRelease)
        #self.canvas.mpl_connect('draw_event', self.onDraw)
        self.clickLocation = (None, 0, 0)

        # Control Panel
        self.controlPanel = wx.Panel(self)
        self.add_controls()
        # Navigation Toolbar
        self.toolbar = NavigationToolbar2Wx(self.canvas)

        # Sizer
        sizer_canvas = wx.BoxSizer(wx.HORIZONTAL)
        sizer_canvas.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 1)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(sizer_canvas, 1, wx.EXPAND | wx.ALL, 1)
        sizer_main.Add(self.toolbar, 0, wx.EXPAND)
        sizer_main.Add(self.controlPanel, 0, wx.EXPAND)

        #self.navTBTop    = NavigationToolbar2WxSubTools(self.canvas, ['Home', 'Pan', 'Zoom', 'Subplots', 'Save'], plotPanel=self)
        #self.navTBBottom = NavigationToolbar2WxSubTools(self.canvas, ['Subplots', 'Save'], plotPanel=self)
        #TBAddCheckTool(self.navTBBottom,'', icons.chart.GetBitmap(), self.onEsthToggle)
        #self.navTBTop.Realize()
        #self.navTBBottom.Realize()
        #sizer_main.Add(self.navTBTop   , 0, wx.EXPAND)
        #sizer_main.Add(self.navTBBottom, 0, wx.EXPAND)


        self.SetSizer(sizer_main)

    def add_controls(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # GUI Element
        plot_type_choices = ['contourf', 'contour', 'pcolormesh']
        self.cbPlotType = wx.ComboBox(self.controlPanel, choices=plot_type_choices, style=wx.CB_READONLY)
        self.cbPlotType.SetSelection(0)
        self.btPlot = wx.Button(self.controlPanel, label=CHAR['chart']+' '+"Replot", style=wx.BU_EXACTFIT)
        levels_choices = [3, 5, 10, 20, 30, 50, 60, 100]
        self.cbLevels = wx.ComboBox(self.controlPanel, choices=[str(level) for level in levels_choices], style=wx.CB_READONLY)
        self.cbPolar  = wx.CheckBox(self.controlPanel, label = "Polar Plot")
        self.cbDeg    = wx.CheckBox(self.controlPanel, label = "X-axis in Degrees")
        self.cbCommonCB = wx.CheckBox(self.controlPanel, label = "Common colorbar")
        self.cbVertiCB  = wx.CheckBox(self.controlPanel, label = "Vertical colorbar")
        self.cbLevels.SetSelection(2)
        self.cbDeg.SetValue(True)
        self.cbCommonCB.SetValue(True)
        self.cbVertiCB.SetValue(True)

        # Layout
        sizer.Add(self.btPlot     , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbPlotType , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbLevels   , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbPolar    , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbDeg      , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbCommonCB , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbVertiCB  , 0 , wx.EXPAND | wx.ALL , 5)
        self.controlPanel.SetSizer(sizer)
        # Bind
        self.btPlot.Bind(wx.EVT_BUTTON, self.update_plot)
        self.cbPlotType.Bind(wx.EVT_COMBOBOX, self.update_plot)
        self.cbLevels.Bind(wx.EVT_COMBOBOX, self.update_plot)
        self.cbPolar.Bind(wx.EVT_CHECKBOX, self.update_plot)
        self.cbDeg.Bind(wx.EVT_CHECKBOX, self.update_plot)
        self.cbCommonCB.Bind(wx.EVT_CHECKBOX, self.update_plot)
        self.cbVertiCB.Bind(wx.EVT_CHECKBOX, self.update_plot)

    def _GUI2Data(self):
        data={}
        data['plotType'] = self.cbPlotType.GetValue()
        data['nLevels']  = int(self.cbLevels.GetValue())
        data['polar']    = self.cbPolar.GetValue()
        data['deg']      = self.cbDeg.GetValue()
        data['commonCB'] = self.cbCommonCB.GetValue()
        if self.cbVertiCB.GetValue():
            data['orientation'] = 'vertical'
        else:
            data['orientation'] = 'horizontal'
        return data

    def add_field(self, x, y, M, sx='x', sy='y', fieldname='field'):
        self.fields.append((x, y, M, sx, sy, fieldname))

    @property
    def fieldsRange(self):
        # Find minmax
        vmin, vmax = float('inf'), float('-inf')
        for i, (x, y, M, sx, sy, fieldname) in enumerate(self.fields, start=1):
            vmin = min(vmin, np.nanmin(M))
            vmax = max(vmax, np.nanmax(M))
        if vmin==vmax:
            # not so clean hack..
            vmin=vmin-1e-6
            vmax=vmax+1e-6
        return vmin, vmax


    def set_subplots(self):
        data = self._GUI2Data()
        self.subplotsPar = self.getSubplotSpacing()

        # Creating subplots
        for ax in self.fig.axes:
            self.fig.delaxes(ax)

        num_fields = len(self.fields)
        for i, f in enumerate(self.fields):
            if data['polar']:
                ax = self.fig.add_subplot(1, num_fields,  i+1, projection='polar')
                ax.set_theta_offset(np.pi / 2)
                ax.set_theta_direction(-1)
                ax.set_rlabel_position(0)
            else:
                ax = self.fig.add_subplot(1, num_fields,  i+1)
        self.fig.subplots_adjust(**self.subplotsPar)

    def getSubplotSpacing(self):
        default = {'bottom':0.18, 'top':0.95, 'left':0.13, 'right':0.85,'hspace':0.4,'wspace':0.2}
        if self.subplotsPar is None:
            return default 
        try:
            params = self.fig.subplotpars
            paramsD= {}
            for key in ['left', 'bottom', 'right', 'top', 'wspace', 'hspace']:
                paramsD[key]=getattr(params, key)
            return paramsD
        except:
            return default

    def clean_plot(self):
        self.fig.clf()
        self.canvas.draw()

    def update_plot(self, event=None):
        #
        data = self._GUI2Data()

        self.fig.clear()
        self.set_subplots()
        axes = self.fig.axes

        vmin, vmax = self.fieldsRange
        mappables=[]

        common_levels = np.linspace(vmin, vmax, data['nLevels'])
        if data['commonCB']:
            levels=common_levels
        else:
            levels=data['nLevels']
            vmin=None
            vmax=None

        # Loop on fields
        for i, (x, y, M, sx, sy, fieldname) in enumerate(self.fields):
            ax = axes[i]
            if data['polar']:
                if data['deg']:
                    x = np.deg2rad(x)

            if data['plotType'] == 'contourf':
                cf = ax.contourf(x, y, M.T, levels=levels)
            elif data['plotType'] == 'contour':
                cf = ax.contour(x, y, M.T, levels=levels)
            elif data['plotType'] == 'pcolormesh':
                cf = ax.pcolormesh(x, y, M.T, vmin=vmin, vmax=vmax)
            mappables.append(cf)

            ax.set_title("{}".format(fieldname.replace('_',' '))) # TODO ColorBar
            if not data['polar']:
                ax.set_xlabel(sx.replace('_',' '))
                ax.set_ylabel(sy.replace('_',' '))

        # --- Bounding boxes of axes
        pmin=[1,1,1,1]
        pmax=[0,0,0,0]
        for ax in axes:
            chartBox = ax.get_position()
            #x, y, w, h = chartBox.x0, chartBox.y0, chartBox.width, chartBox.height
            #print('xywh',x,y,w,h)
            p    = np.around(ax.get_position().get_points().flatten(),3) # BBox: x1, y1,  x2 y2
            pmin = np.around([min(v1, v2) for v1,v2 in zip(pmin, p)] ,3)
            pmax = np.around([max(v1, v2) for v1,v2 in zip(pmax, p)] ,3)
        #    print('pax ',p)

        # --- Colorbar
        if data['commonCB']:
            for mappable in mappables:
                mappable.set_clim([vmin, vmax])
            self.add_colorbar(axes[-1], mappables[-1], vmin, vmax, polar=data['polar'], pmin=pmin, pmax=pmax, orientation=data['orientation'])
        else:
            for ax, mappable in zip(axes, mappables):
                self.add_colorbar(ax, mappable, vmin, vmax, polar=data['polar'], orientation=data['orientation'])

        self.canvas.draw()

    def add_colorbar(self, ax, mappable, vmin, vmax, polar=False, orientation='vertical', cax=None, pmin=None, pmax=None):
        ax = mappable.axes
        fig = ax.figure

        if cax is None and pmin is not None and pmax is not None:
            # Use bounding box to figure out where to put the colorbar
            pad = 0.05
            w = 0.02
            plots_height = pmax[3]-pmin[1]
            plots_width  = pmax[2]-pmin[0]
            # BoundingBox: Left (x), Bottom (y), Width, Height
            if orientation=='vertical':
                BB = [pmax[2]+pad, pmin[1], w, plots_height]
            else:
                BB = [pmin[0], max(pmin[1]-1.5*pad-w,0), plots_width, w]
            cax = fig.add_axes(BB)
            pcax = np.around(cax.get_position().get_points().flatten(),3)
            #print('pmin',pmin)
            #print('pmax',pmax)
            #print('BB  ',BB)
            #print('pcax', pcax)



        if not polar:
            if vmin is not None:
                mappable.set_clim([vmin, vmax])
            if cax is None:
                divider = make_axes_locatable(ax)
                if orientation=='vertical':
                    cax = divider.append_axes("right", size="6%", pad="2%")
                else:
                    cax = divider.append_axes("bottom", size="2%", pad="6%")
            self.cbar = self.fig.colorbar(mappable, cax=cax, orientation=orientation)
        else:
            if cax is None:
                self.cbar = self.fig.colorbar(mappable, ax=ax, orientation=orientation)
            else:
                self.cbar = self.fig.colorbar(mappable, cax=cax, orientation=orientation)
        #self.cbar.set_clim(vmin=vmin, vmax=vmax)

if __name__ == '__main__':
    np.random.seed(2)
    # --- Dummy Data
    nx, ny = 30, 41
    field1 = np.linspace(0, 270, nx), np.linspace(0, 2, ny), np.random.randn(ny, nx)*3
    field2 = np.linspace(0, 270, nx), np.linspace(0, 2, ny), np.random.randn(ny, nx)

    # --- Dummy GUI
    app = wx.App(False)
    self = wx.Frame(None, -1, "GUI Plot Panel Demo")
    panel = Plot2DPanel(self)
    panel.add_field(*field1)
    panel.add_field(*field2)
    panel.update_plot()

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(panel, 1, flag=wx.EXPAND | wx.ALL, border=5)
    self.SetSizer(sizer)
    self.Center()
    self.SetSize((900, 600))
    self.Show()
    app.MainLoop()
