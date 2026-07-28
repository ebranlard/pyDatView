
import numpy as np
import math
import wx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pandas.plotting import register_matplotlib_converters
from pydatview.GUIToolBox import NavigationToolbar2WxSubTools
from pydatview.common import CHAR, pretty_num

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
        controlPanel = self.createPlotTypePanel(parent=self)
        clbrPanel = self.createColorbarPanel(parent=self)
        esthPanel = self.createEstheticsPanel(parent=self)

        # Triggers
        self.onCommonCB(plot=False)
        self.onPolarPlot(plot=False)
#         plot_options_pane = self.create_collapsible_pane(self.controlPanel, "Plot Options", self.create_plot_options)
#         layout_options_pane = self.create_collapsible_pane(self.controlPanel, "Layout Options", self.create_layout_options)

        # Add collapsible panes to a horizontal box sizer
#         sizer_control_panel = wx.BoxSizer(wx.HORIZONTAL)
#         sizer_control_panel.Add(plot_options_pane, 1, wx.EXPAND)
#         sizer_control_panel.Add(layout_options_pane, 1, wx.EXPAND)


        # Navigation Toolbar
        self.toolbar = NavigationToolbar2Wx(self.canvas)

        # Sizer
        sizer_canvas = wx.BoxSizer(wx.HORIZONTAL)
        sizer_canvas.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 1)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(sizer_canvas, 1, wx.EXPAND | wx.ALL, 1)
        sizer_main.Add(self.toolbar, 0, wx.EXPAND)
        sizer_main.Add(controlPanel, 0, wx.EXPAND)
        sizer_main.Add(esthPanel, 0, wx.EXPAND)
        sizer_main.Add(clbrPanel, 0, wx.EXPAND)
        self.SetSizer(sizer_main)

#     def create_collapsible_pane(self, parent, label, content_func):
#         # Create a collapsible pane with a static box
#         pane = wx.CollapsiblePane(parent, label=label, style=wx.CP_DEFAULT_STYLE | wx.CP_NO_TLW_RESIZE)
#         pane.Collapse()
# 
#         # Create a static box for the content of the collapsible pane
#         box = wx.StaticBox(pane.GetPane(), -1, label)
#         box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
# 
#         # Call the content_func to populate the content of the static box
#         content_func(box.GetStaticBox())
# 
#         # Set sizer for the static box
#         pane.GetPane().SetSizer(box_sizer)
# 
#         return pane
# 
#     def create_plot_options(self, parent):
#         # Create controls for Plot Options
#         sizer = wx.BoxSizer(wx.VERTICAL)
#         # ... (existing code)
#         parent.SetSizer(sizer)
# 
#     def create_layout_options(self, parent):
#         # Create controls for Layout Options
#         sizer = wx.BoxSizer(wx.VERTICAL)
#         # ... (existing code)
#         parent.SetSizer(sizer)
# 
    def createEstheticsPanel(self, parent):
        boldFont = self.GetFont().Bold()
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        lb = wx.StaticText(panel, -1, 'Esthetics: ')
        lb.SetFont(boldFont)

        levels_choices = [3, 5, 10, 20, 30, 50, 60, 100]
        cmaps = ['viridis','coolwarm','hot','jet','Accent','bone']
        cmaps = cmaps+[v for v in plt.colormaps() if v not in cmaps and v.find('_r')<0 ]
        self.cbLevels = wx.ComboBox(panel, choices=[str(level) for level in levels_choices], style=wx.CB_READONLY)
        self.cbLevels.SetSelection(2)
        self.cbColorMap = wx.ComboBox(panel, choices=cmaps, style=wx.CB_READONLY)
        self.cbColorMap.SetSelection(0)
        self.cbFlipXY = wx.CheckBox(panel, label="flipXY")
        self.cbMatrixView = wx.CheckBox(panel, label="Matrix View")
        self.cbGrid = wx.CheckBox(panel, label="Grid lines")

        sizer.Add(lb              , 0 , wx.ALL | wx.ALIGN_CENTER , 5)
        sizer.Add(wx.StaticText(panel, -1, 'Levels:'), 0, flag = wx.ALIGN_CENTER)
        sizer.Add(self.cbLevels   , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(wx.StaticText(panel, -1, 'Colormap:'), 0, flag = wx.ALIGN_CENTER)
        sizer.Add(self.cbColorMap, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.cbFlipXY   , 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.cbMatrixView, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.cbGrid     , 0, wx.EXPAND | wx.ALL, 5)


        # Bind
        self.cbColorMap.Bind(wx.EVT_COMBOBOX, self.update_plot)
        self.cbLevels.Bind(wx.EVT_COMBOBOX, self.update_plot)
        self.cbFlipXY.Bind(wx.EVT_CHECKBOX, self.update_plot)
        self.cbMatrixView.Bind(wx.EVT_CHECKBOX, self.onMatrixView)
        self.cbGrid.Bind(wx.EVT_CHECKBOX, self.update_plot)

        panel.SetSizer(sizer)
        return panel

    def createColorbarPanel(self, parent):
        boldFont = self.GetFont().Bold()
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbCB = wx.StaticText(panel, -1, 'Colorbar: ')
        lbCB.SetFont(boldFont)
        self.cbCommonCB = wx.CheckBox(panel, label = "Common colorbar")
        self.cbVertiCB  = wx.CheckBox(panel, label = "Vertical colorbar")
        self.cbManuCB   = wx.CheckBox(panel, label = "Manual range")
        self.btGetRange = wx.Button(panel, label=CHAR['compute']+' '+"Get range", style=wx.BU_EXACTFIT)
        self.textVMin = wx.TextCtrl(panel, wx.ID_ANY, '0.0', style = wx.TE_PROCESS_ENTER)
        self.textVMax = wx.TextCtrl(panel, wx.ID_ANY, '0.0', style = wx.TE_PROCESS_ENTER)
        self.btSetRange = wx.Button(panel, label=CHAR['compute']+' '+"Set range", style=wx.BU_EXACTFIT)
        self.cbCommonCB.SetValue(True)
        self.cbVertiCB.SetValue(True)
        self.cbManuCB.SetValue(False)
        # Layout
        sizer.Add(lbCB            , 0 , wx.ALL | wx.ALIGN_CENTER , 5)
        sizer.Add(self.cbCommonCB , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbVertiCB  , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.btGetRange, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.cbManuCB, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.textVMin, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.textVMax, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.btSetRange, 0, wx.EXPAND | wx.ALL, 5)
        # Bind
        self.cbCommonCB.Bind(wx.EVT_CHECKBOX, self.onCommonCB)
        self.cbVertiCB.Bind(wx.EVT_CHECKBOX, self.update_plot)
        self.cbManuCB.Bind(wx.EVT_CHECKBOX, self.onManuCB)
        self.btGetRange.Bind(wx.EVT_BUTTON, self.getRange)
        self.btSetRange.Bind(wx.EVT_BUTTON, self.onRangeChange)
        self.textVMin.Bind(wx.EVT_TEXT_ENTER, self.onRangeChange)
        self.textVMax.Bind(wx.EVT_TEXT_ENTER, self.onRangeChange)
        panel.SetSizer(sizer)

        return panel


    def createPlotTypePanel(self, parent):
        boldFont = self.GetFont().Bold()
        panel= wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        # GUI Element
        lb = wx.StaticText(panel, -1, 'Plot type: ')
        lb.SetFont(boldFont)
        plot_type_choices = ['contourf', 'contour', 'pcolormesh', 'matrix', 'surface']
        self.cbPlotType = wx.ComboBox(panel, choices=plot_type_choices, style=wx.CB_READONLY)
        self.cbPlotType.SetSelection(0)
        self.btPlot = wx.Button(panel, label=CHAR['chart']+' '+"Replot", style=wx.BU_EXACTFIT)
        self.cbVSubplots = wx.ComboBox(panel, choices=[str(i) for i in [1,2,3,4]], style=wx.CB_READONLY)
        self.cbPolar  = wx.CheckBox(panel, label = "Polar Plot")
        self.cbDeg    = wx.CheckBox(panel, label = "X-axis in Degrees")
        self.cbVSubplots.SetSelection(0)
        self.cbDeg.SetValue(True)
        # Layout
        sizer.Add(lb              , 0 , wx.ALL | wx.ALIGN_CENTER , 5)
        sizer.Add(wx.StaticText(panel, -1, 'Plot Type:'), 0, flag = wx.ALIGN_CENTER)
        sizer.Add(self.cbPlotType , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbPolar    , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.cbDeg      , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(wx.StaticText(panel, -1, 'Vertical subplots:'), 0, flag = wx.ALIGN_CENTER)
        sizer.Add(self.cbVSubplots , 0 , wx.EXPAND | wx.ALL , 5)
        sizer.Add(self.btPlot     , 0 , wx.EXPAND | wx.ALL , 5)
        panel.SetSizer(sizer)
        # Bind
        self.btPlot.Bind(wx.EVT_BUTTON, self.update_plot)
        self.cbPlotType.Bind(wx.EVT_COMBOBOX, self.onPlotTypeChange)
        self.cbVSubplots.Bind(wx.EVT_COMBOBOX, self.update_plot)
        self.cbPolar.Bind(wx.EVT_CHECKBOX, self.onPolarPlot)
        self.cbDeg.Bind(wx.EVT_CHECKBOX, self.update_plot)
        self.cbVSubplots.Bind(wx.EVT_CHECKBOX, self.update_plot)
        return panel


    def onPolarPlot(self, event=None, plot=True):
        if self.cbPolar.GetValue():
            self.cbDeg.Enable(True)
            self.cbMatrixView.SetValue(False)
            self.cbMatrixView.Enable(False)
            self.cbFlipXY.SetValue(False)
            self.cbFlipXY.Enable(False)
            if self.cbPlotType.GetValue() == 'matrix':
                iPlotType = self.cbPlotType.FindString('pcolormesh')
                if iPlotType >= 0:
                    self.cbPlotType.SetSelection(iPlotType)
        else:
            self.cbDeg.Enable(False)
            self.cbMatrixView.Enable(True)
            self.cbFlipXY.Enable(True)
        if plot:
            self.update_plot()

    def onPlotTypeChange(self, event=None):
        is_matrix = self.cbPlotType.GetValue() == 'matrix'
        self.cbMatrixView.SetValue(is_matrix)
        self.cbGrid.SetValue(is_matrix)
        if is_matrix and self.cbPolar.GetValue():
            self.cbPolar.SetValue(False)
            self.cbDeg.Enable(False)
        self.update_plot()

    def onCommonCB(self, event=None, plot=True):
        if self.cbCommonCB.GetValue():
            self.cbManuCB.Enable(True)
        else:
            self.cbManuCB.Enable(False)
        self.onManuCB(plot=False)
        if plot:
            self.update_plot()

    def onManuCB(self, event=None, plot=True):
        if self.cbManuCB.GetValue():
            self.textVMin.Enable(True)
            self.textVMax.Enable(True)
            self.btSetRange.Enable(True)
        else:
            self.textVMin.Enable(False)
            self.textVMax.Enable(False)
            self.btSetRange.Enable(False)
        if plot:
            self.update_plot()

    def getRange(self, event=None):
        # Populate vmin and vmax based on the current data
        vmin, vmax = self.fieldsRange
        if self.cbCommonCB.GetValue():
            self.cbManuCB.SetValue(True)
        self.onManuCB(plot=False)
        self.textVMin.SetValue(pretty_num(vmin))
        self.textVMax.SetValue(pretty_num(vmax))

    def onRangeChange(self, event=None):
        self.update_plot()

    def onMatrixView(self, event=None):
        # Keep the checkbox synchronized with the dedicated matrix plot type.
        if self.cbMatrixView.GetValue():
            if self.cbPolar.GetValue():
                self.cbPolar.SetValue(False)
                self.cbDeg.Enable(False)
            #if self.cbPlotType.GetValue() != 'matrix':
            #    iPlotType = self.cbPlotType.FindString('matrix')
            #    if iPlotType >= 0:
            #        self.cbPlotType.SetSelection(iPlotType)
        #elif self.cbPlotType.GetValue() == 'matrix':
        #    iPlotType = self.cbPlotType.FindString('pcolormesh')
        #    if iPlotType >= 0:
        #        self.cbPlotType.SetSelection(iPlotType)
        self.update_plot()

    #def save_figure(self, event):
    #    # Save the figure to a file
    #    with wx.FileDialog(self, "Save Figure As", wildcard="PNG files (*.png)|*.png", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
    #        if fileDialog.ShowModal() == wx.ID_CANCEL:
    #            return
    #        path = fileDialog.GetPath()
    #        self.fig.savefig(path)


    def _GUI2Data(self):
        data={}
        data['plotType'] = self.cbPlotType.GetValue()
        data['nLevels']  = int(self.cbLevels.GetValue())
        data['polar']    = self.cbPolar.GetValue()
        data['deg']      = self.cbDeg.GetValue()
        data['flipXY']   = self.cbFlipXY.GetValue()
        data['matrixView'] = self.cbMatrixView.GetValue()
        data['grid']     = self.cbGrid.GetValue()
        data['commonCB'] = self.cbCommonCB.GetValue()
        if self.cbVertiCB.GetValue():
            data['orientation'] = 'vertical'
        else:
            data['orientation'] = 'horizontal'
        data['colormap']   = self.cbColorMap.GetValue()
        data['nVSubplots'] = int(self.cbVSubplots.GetValue())
        data['manualRange']  = self.cbManuCB.GetValue()
        data['VMin']       = float(self.textVMin.GetLineText(0))
        data['VMax']       = float(self.textVMax.GetLineText(0))
        return data

    def _is_integer_axis(self, v, tol=1e-10):
        v = np.asarray(v, dtype=float)
        if len(v) == 0:
            return False
        return np.all(np.isfinite(v)) and np.allclose(v, np.round(v), atol=tol, rtol=0)

    def _grid_edges(self, v):
        v = np.asarray(v, dtype=float)
        if len(v) == 0:
            return v
        if len(v) == 1:
            return np.array([v[0] - 0.5, v[0] + 0.5])

        dv = np.diff(v)
        edges = np.empty(len(v) + 1)
        edges[1:-1] = 0.5 * (v[:-1] + v[1:])
        edges[0] = v[0] - 0.5 * dv[0]
        edges[-1] = v[-1] + 0.5 * dv[-1]
        return edges

    def _apply_tick_style(self, ax, matrix_view=False):
        ax.tick_params(direction='in', top=True, right=True, labelright=False, labeltop=False, which='both')
        if matrix_view:
            ax.xaxis.set_label_position('top')
            ax.xaxis.tick_top()
            ax.tick_params(axis='x', which='both', top=True, bottom=True, labeltop=True, labelbottom=False)
            ax.tick_params(axis='y', which='both', left=True, right=True, labelleft=True, labelright=False)
        else:
            ax.xaxis.set_label_position('bottom')
            ax.xaxis.tick_bottom()
            ax.tick_params(axis='x', which='both', top=True, bottom=True, labeltop=False, labelbottom=True)
            ax.tick_params(axis='y', which='both', left=True, right=True, labelleft=True, labelright=False)

    def _apply_matrix_ticks(self, ax, x, y, use_index_grid=False):
        if use_index_grid and len(x) <= 80 and len(y) <= 80:
            ax.set_xticks(x)
            ax.set_yticks(y)
            ax.set_xticks(self._grid_edges(x), minor=True)
            ax.set_yticks(self._grid_edges(y), minor=True)
            ax.tick_params(axis='both', which='major', length=0)
            ax.tick_params(axis='both', which='minor', length=6)

    def _apply_grid(self, ax, x, y, use_index_grid=False, cell_grid=False):
        x = np.asarray(x)
        y = np.asarray(y)
        nxy = max(len(x), len(y))
        if nxy > 200:
            # Keep only a light major grid when the matrix is dense.
            ax.grid(True, which='major', linestyle='--', linewidth=0.4, alpha=0.15)
            return

        if use_index_grid and len(x) <= 80 and len(y) <= 80:
            ax.set_xticks(x)
            ax.set_yticks(y)
            if cell_grid:
                ax.grid(True, which='minor', linestyle='-', linewidth=0.6, alpha=0.35)
                return
        ax.grid(True, which='major', linestyle='-', linewidth=0.4, alpha=0.25)

    def add_field(self, x, y, M, sx='x', sy='y', fieldname='field'):
        self.fields.append({'x':x, 'y':y, 'M':M, 'sx':sx, 'sy':sy, 'fieldname':fieldname})

    @property
    def fieldsRange(self):
        # Find minmax
        vmin, vmax = float('inf'), float('-inf')
        for i, field in enumerate(self.fields, start=1):
            vmin = min(vmin, np.nanmin(field['M']))
            vmax = max(vmax, np.nanmax(field['M']))
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
        nRows = min(data['nVSubplots'], num_fields)
        nCols = math.ceil(num_fields/nRows)
        
        for i, field in enumerate(self.fields):

            j = i +1
        
            if data['plotType']=='surface':
                ax = self.fig.add_subplot(nRows, nCols, j, projection='3d')
            elif data['polar']:
                ax = self.fig.add_subplot(nRows, nCols, j, projection='polar')
                ax.set_theta_offset(np.pi / 2)
                ax.set_theta_direction(-1)
                ax.set_rlabel_position(0)
            else:
                ax = self.fig.add_subplot(nRows, nCols, j)
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
        # NOTE: clear and set_subplots will create a flashing
        self.fig.clear()
        self.set_subplots()
        axes = self.fig.axes

        if data['manualRange']:
            vmin, vmax = data['VMin'], data['VMax']
        else:
            vmin, vmax = self.fieldsRange
        mappables=[]

        common_levels = np.linspace(vmin, vmax, data['nLevels'])
        if data['commonCB']:
            levels=common_levels
        else:
            levels=data['nLevels']
            vmin=None
            vmax=None

        # Titles
        all_fieldnames = np.array([f['fieldname'].replace('_',' ') for f in self.fields])
        oneTitle = len(np.unique(all_fieldnames))==1

        # Loop on fields
        for i, field in enumerate(self.fields):
            sx = field['sx']
            sy = field['sy']
            x  = field['x']
            y  = field['y']
            M  = field['M']
            fieldname = field['fieldname']
            ax = axes[i]
            
            if data['polar'] and data['deg']:
                x = np.deg2rad(x)

            x_plot = x
            y_plot = y
            z_plot = M.T
            sx_plot = sx
            sy_plot = sy
            do_flip = data['flipXY'] and (not data['polar'])
            if do_flip:
                x_plot = y
                y_plot = x
                z_plot = M
                sx_plot = sy
                sy_plot = sx

            if data['plotType'] == 'contourf':
                cf = ax.contourf(x_plot, y_plot, z_plot, levels=levels, cmap=data['colormap'])
            elif data['plotType'] == 'contour':
                cf = ax.contour(x_plot, y_plot, z_plot, levels=levels, cmap=data['colormap'])
            elif data['plotType'] == 'pcolormesh' or data['plotType'] == 'matrix':
                cf = ax.pcolormesh(x_plot, y_plot, z_plot, vmin=vmin, vmax=vmax, cmap=data['colormap'])
            elif data['plotType'] == 'surface':
                if data['polar']:
                    T, R = np.meshgrid(x, y)
                    X = R * np.cos(T)
                    Y = R * np.sin(T)
                    Z = M.T
                else:
                    X, Y = np.meshgrid(x_plot, y_plot)
                    Z = z_plot
                cf = ax.plot_surface(X, Y, Z, linewidth=0, antialiased=False, cmap=data['colormap'])
            mappables.append(cf)

            if not oneTitle:
                ax.set_title("{}".format(fieldname.replace('_',' '))) 
            if data['polar']:
                ax.grid(data['grid'])
            else:
                ax.set_xlabel(sx_plot.replace('_',' '))
                ax.set_ylabel(sy_plot.replace('_',' '))
                self._apply_tick_style(ax, matrix_view=data['matrixView'])
                if data['matrixView']:
                    # Show row 0 on top so pcolormesh matches matrix orientation.
                    ax.invert_yaxis()
                    use_index_grid = self._is_integer_axis(x_plot) and self._is_integer_axis(y_plot)
                    self._apply_matrix_ticks(ax, x_plot, y_plot, use_index_grid=use_index_grid)
                if data['grid'] and data['plotType'] != 'surface':
                    use_index_grid = self._is_integer_axis(x_plot) and self._is_integer_axis(y_plot)
                    use_cell_grid = data['plotType'] == 'matrix'
                    self._apply_grid(ax, x_plot, y_plot, use_index_grid=use_index_grid, cell_grid=use_cell_grid)

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
            self.add_colorbar(axes[-1], mappables[-1], vmin, vmax, polar=data['polar'], pmin=pmin, pmax=pmax, orientation=data['orientation'], title=all_fieldnames[0], plotType=data['plotType'])
        else:
            for ax, mappable in zip(axes, mappables):
                self.add_colorbar(ax, mappable, vmin, vmax, polar=data['polar'], orientation=data['orientation'], plotType=data['plotType'])

        self.canvas.draw()

    def add_colorbar(self, ax, mappable, vmin, vmax, polar=False, orientation='vertical', cax=None, pmin=None, pmax=None, title=None, plotType='contourf'):
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
                if plotType=='surface':
                    cax=None # TODO
                elif orientation=='vertical':
                    cax = divider.append_axes("right", size="6%", pad="2%")
                else:
                    cax = divider.append_axes("bottom", size="2%", pad="6%")
            self.cbar = self.fig.colorbar(mappable, cax=cax, orientation=orientation)


        else:
            if cax is None:
                self.cbar = self.fig.colorbar(mappable, ax=ax, orientation=orientation)
            else:
                self.cbar = self.fig.colorbar(mappable, cax=cax, orientation=orientation)

        self.cbar.ax.set_title(title)
        #self.cbar.ax.tick_params(labelsize=8) 
        #self.cbar.set_clim(vmin=vmin, vmax=vmax)

if __name__ == '__main__':
    np.random.seed(2)
    # --- Dummy Data
    nx, ny = 30, 41
    field1 = np.linspace(0, 270, nx), np.linspace(0, 2, ny), np.random.randn(nx, ny)*3
    field2 = np.linspace(0, 270, nx), np.linspace(0, 2, ny), np.random.randn(nx, ny)

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
