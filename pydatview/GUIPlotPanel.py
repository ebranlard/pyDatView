import os
import numpy as np
import wx
import wx.lib.buttons  as  buttons
import dateutil # required by matplotlib
#from matplotlib import pyplot as plt
import matplotlib
import matplotlib.dates as mdates
import matplotlib.image as mpimg
# Backends:
#  ['GTK3Agg', 'GTK3Cairo', 'GTK4Agg', 'GTK4Cairo', 'MacOSX', 'nbAgg', 'QtAgg', 'QtCairo', 'Qt5Agg', 'Qt5Cairo', 'TkAgg', 'TkCairo', 'WebAgg', 'WX', 'WXAgg', 'WXCairo', 'agg', 'cairo', 'pdf', 'pgf', 'ps', 'svg', 'template']
matplotlib.use('WX') # Important for Windows version of installer. NOTE: changed from Agg to wxAgg, then to WX
from matplotlib import rc as matplotlib_rc
try:
    from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
except Exception as e:
    print('')
    print('Error: problem importing `matplotlib.backends.backend_wx`.')
    import platform
    if platform.system()=='Darwin':
        print('')
        print('pyDatView help:')
        print('  This is a typical issue on MacOS, most likely you are')
        print('  using the native MacOS python with the native matplolib')
        print('  library, which is incompatible with `wxPython`.')
        print('')
        print('  You can solve this by either:')
        print('    - using python3, and pip3 e.g. installing it with brew')
        print('    - using a virtual environment with python 3')
        print('    - using anaconda with python 3');
        print('')
        import sys
        sys.exit(1)
    else:
        raise e
# from matplotlib.figure import Figure
from pydatview.figure import SwappyFigure as Figure
try:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - registers 3d projection
except ImportError:
    pass
from matplotlib.pyplot import rcParams as pyplot_rc
from matplotlib import font_manager
from pandas.plotting import register_matplotlib_converters

import gc

# Supported image file extensions for background images
IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')

from pydatview.common import * # unique, CHAR, pretty_date
from pydatview.plotdata import PlotData, compareMultiplePD 
from pydatview.plotdata import PDL_xlabel
from pydatview.GUICommon import * 
from pydatview.GUIToolBox import MyMultiCursor, MyNavigationToolbar2Wx, TBAddTool, TBAddCheckTool
from pydatview.GUIMeasure import GUIMeasure, find_closest_i
import pydatview.icons as icons

font = {'size'   : 8}
matplotlib_rc('font', **font)
pyplot_rc['agg.path.chunksize'] = 20000


def _patch_3d_ctrl_rotate(ax, canvas, toolbar=None):
    """Control 3D rotation/pan via the toolbar Rotate and Pan buttons.

    Rotate mode (toolbar.rotate_on):
        Left-drag rotates the 3D view (default Axes3D behaviour).

    Pan mode (toolbar.pan_on):
        Left-drag pans by shifting axis limits using the current view direction.
        Right-drag uses Axes3D native right-button behaviour.
        Hold 'x', 'y', or 'z' while dragging to constrain pan to that axis.

    Neither active:
        All mouse-drag suppressed (no accidental rotation/pan).
    """
    import math

    def _rotate_active():
        return getattr(toolbar, 'rotate_on', False)

    def _pan_active():
        return getattr(toolbar, 'pan_on', False)

    # Tracks state for the manual 3D pan gesture (left-drag in pan mode).
    _pan_state = {'active': False, 'x0': 0.0, 'y0': 0.0,
                  'xlim': None, 'ylim': None, 'zlim': None}

    def _do_pan_move(event, _ps=_pan_state):
        """Shift 3D axis limits so the scene follows the mouse drag."""
        if not _ps['active']:
            return
        try:
            dx = event.x - _ps['x0']
            dy = event.y - _ps['y0']
            W, H = canvas.get_width_height()
            if W == 0 or H == 0:
                return
            xlim = _ps['xlim']
            ylim = _ps['ylim']
            zlim = _ps['zlim']
            xr = xlim[1] - xlim[0]
            yr = ylim[1] - ylim[0]
            zr = zlim[1] - zlim[0]
            # Normalised screen delta (matplotlib y increases upward).
            nx = dx / W
            ny = dy / H
            az = math.radians(ax.azim)
            el = math.radians(ax.elev)
            # Screen-right unit vector in data space (horizontal, no z component).
            rrx = -math.sin(az)
            rry =  math.cos(az)
            # Screen-up unit vector in data space (camera up direction).
            upx = -math.cos(az) * math.sin(el)
            upy = -math.sin(az) * math.sin(el)
            upz =  math.cos(el)
            # Shift limits so data follows the mouse (negative sign).
            dpx = -(nx * rrx + ny * upx) * xr
            dpy = -(nx * rry + ny * upy) * yr
            dpz = -(ny * upz) * zr
            key = getattr(event, 'key', None)
            if key == 'x':
                dpy = 0.0; dpz = 0.0
            elif key == 'y':
                dpx = 0.0; dpz = 0.0
            elif key == 'z':
                dpx = 0.0; dpy = 0.0
            ax.set_xlim3d(xlim[0] + dpx, xlim[1] + dpx)
            ax.set_ylim3d(ylim[0] + dpy, ylim[1] + dpy)
            ax.set_zlim3d(zlim[0] + dpz, zlim[1] + dpz)
            canvas.draw_idle()
        except Exception:
            pass

    # Tracks state for the manual 3D zoom gesture (right-drag in pan or rotate mode).
    _zoom_state = {'active': False, 'x0': 0.0, 'y0': 0.0,
                   'xlim': None, 'ylim': None, 'zlim': None}

    def _do_zoom_move(event, _zs=_zoom_state):
        """Exponentially scale axis limits about their centre on right-drag."""
        if not _zs['active']:
            return
        try:
            dx = event.x - _zs['x0']
            dy = event.y - _zs['y0']
            W, H = canvas.get_width_height()
            if W == 0 or H == 0:
                return
            disp = -(dx / float(W) + dy / float(H))
            alpha = 10.0 ** disp  # alpha < 1 → zoom in, alpha > 1 → zoom out
            for lim, setter in (
                (_zs['xlim'], ax.set_xlim3d),
                (_zs['ylim'], ax.set_ylim3d),
                (_zs['zlim'], ax.set_zlim3d),
            ):
                mid = 0.5 * (lim[0] + lim[1])
                half = 0.5 * (lim[1] - lim[0]) * alpha
                setter(mid - half, mid + half)
            canvas.draw_idle()
        except Exception:
            pass

    # --- Layer 0: wrap Axes3D._button_press ---
    press_cbs = getattr(canvas.callbacks, 'callbacks', {}).get('button_press_event', {})
    for cid, val in list(press_cbs.items()):
        try:
            func = val()
        except TypeError:
            func = val
        if func is None:
            continue
        if getattr(func, '__self__', None) is ax:
            canvas.mpl_disconnect(cid)
            def _wrapped_press(event, _orig=func, _ps=_pan_state, _zs=_zoom_state):
                _orig(event)  # Axes3D sets ax.button_pressed = event.button
                if event.inaxes != ax:
                    return
                if event.button == 1 and _pan_active():
                    try:
                        ax.button_pressed = None
                        _ps['active'] = True
                        _ps['x0'] = event.x; _ps['y0'] = event.y
                        _ps['xlim'] = list(ax.get_xlim3d())
                        _ps['ylim'] = list(ax.get_ylim3d())
                        _ps['zlim'] = list(ax.get_zlim3d())
                    except Exception:
                        pass
                elif event.button == 3 and (_pan_active() or _rotate_active()):
                    try:
                        ax.button_pressed = None
                        _zs['active'] = True
                        _zs['x0'] = event.x; _zs['y0'] = event.y
                        _zs['xlim'] = list(ax.get_xlim3d())
                        _zs['ylim'] = list(ax.get_ylim3d())
                        _zs['zlim'] = list(ax.get_zlim3d())
                    except Exception:
                        pass
            canvas.mpl_connect('button_press_event', _wrapped_press)
            break

    # Clear gesture state on button release.
    def _on_release(event, _ps=_pan_state, _zs=_zoom_state):
        if event.button == 1:
            _ps['active'] = False
        elif event.button == 3:
            _zs['active'] = False
    canvas.mpl_connect('button_release_event', _on_release)

    # --- Layer 2: wrap Axes3D._on_move in the callback registry ---
    wrapped = [False]
    motion_cbs = getattr(canvas.callbacks, 'callbacks', {}).get('motion_notify_event', {})
    for cid, val in list(motion_cbs.items()):
        try:
            func = val()   # WeakMethod / weakref.ref
        except TypeError:
            func = val     # direct callable
        if func is None:
            continue
        if getattr(func, '__self__', None) is ax:
            canvas.mpl_disconnect(cid)
            def _wrapped_move(event, _orig=func):
                if event.inaxes != ax:
                    _orig(event)
                    return
                # Right-drag zoom takes precedence in both pan and rotate modes.
                if _zoom_state['active']:
                    _do_zoom_move(event)
                    return
                if _rotate_active():
                    _orig(event)
                elif _pan_active() and _pan_state['active']:
                    _do_pan_move(event)
                # else: neither rotate nor pan — suppress all drag
            canvas.mpl_connect('motion_notify_event', _wrapped_move)
            wrapped[0] = True
            break

    if not wrapped[0]:
        # Fallback for versions where _on_move isn't in canvas callbacks.
        def _on_press_fb(event, _ps=_pan_state, _zs=_zoom_state):
            if event.inaxes != ax:
                return
            if event.button == 1 and _pan_active():
                try:
                    ax.button_pressed = None
                    _ps['active'] = True
                    _ps['x0'] = event.x; _ps['y0'] = event.y
                    _ps['xlim'] = list(ax.get_xlim3d())
                    _ps['ylim'] = list(ax.get_ylim3d())
                    _ps['zlim'] = list(ax.get_zlim3d())
                except Exception:
                    pass
            elif event.button == 3 and (_pan_active() or _rotate_active()):
                try:
                    ax.button_pressed = None
                    _zs['active'] = True
                    _zs['x0'] = event.x; _zs['y0'] = event.y
                    _zs['xlim'] = list(ax.get_xlim3d())
                    _zs['ylim'] = list(ax.get_ylim3d())
                    _zs['zlim'] = list(ax.get_zlim3d())
                except Exception:
                    pass
            elif event.button == 1 and not _rotate_active():
                for attr in ('button_pressed', '_button_pressed'):
                    try:
                        setattr(ax, attr, None)
                    except Exception:
                        pass
        canvas.mpl_connect('button_press_event', _on_press_fb)

        def _on_move_fb(event):
            if event.inaxes != ax:
                return
            if _zoom_state['active']:
                _do_zoom_move(event)
            elif _pan_active() and _pan_state['active']:
                _do_pan_move(event)
        canvas.mpl_connect('motion_notify_event', _on_move_fb)

    # --- Layer 1: patch ax.drag_pan at instance level ---
    # ax.__class__.drag_pan is the unbound function (Python 3).
    # Setting ax.drag_pan = our_func makes Python call our_func(button,key,x,y)
    # when the toolbar does a.drag_pan(...), bypassing the class method.
    try:
        _orig_drag_pan = ax.__class__.drag_pan
    except AttributeError:
        _orig_drag_pan = None

    if _orig_drag_pan is not None:
        def _patched_drag_pan(button, key, x, y,
                              _orig=_orig_drag_pan, _w=wrapped):
            if button == 1:
                # Left-click: rotate only when rotate mode ON and _on_move absent.
                if _rotate_active() and not _w[0]:
                    _orig(ax, button, key, x, y)
                # Pan mode: handled in _wrapped_move / _on_move_fb.
            elif button == 3:
                # Right-drag zoom is handled manually via _do_zoom_move in
                # _wrapped_move/_on_move_fb for both pan and rotate modes.
                # Only call native behaviour in idle 3D state.
                if not _rotate_active() and not _pan_active():
                    _orig(ax, button, key, x, y)
            else:
                _orig(ax, button, key, x, y)
        ax.drag_pan = _patched_drag_pan


class PDFCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(PDFCtrlPanel,self).__init__(parent)
        self.parent   = parent
        lb = wx.StaticText( self, -1, 'Number of bins:')
        self.scBins = wx.SpinCtrl(self, value='51',size=wx.Size(70,-1), style=wx.TE_RIGHT)
        self.scBins.SetRange(3, 10000)
        self.cbSmooth = wx.CheckBox(self, -1, 'Smooth',(10,10))
        self.cbSmooth.SetValue(False)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(lb                    ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.scBins           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.cbSmooth         ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_TEXT    , self.onPDFOptionChange, self.scBins)
        self.Bind(wx.EVT_CHECKBOX, self.onPDFOptionChange)
        self.Hide() 

    def onPDFOptionChange(self,event=None):
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def _GUI2Data(self):
        data = {'nBins':  self.scBins.GetValue(),
                'smooth': self.cbSmooth.GetValue()}
        return data

class MinMaxPanel(wx.Panel):
    def __init__(self, parent):
        super(MinMaxPanel,self).__init__(parent)
        # Data
        self.parent = parent
        self.yRef = None
        self.cbxMinMax = wx.CheckBox(self, -1, 'xMinMax',(10,10))
        self.cbyMinMax = wx.CheckBox(self, -1, 'yMinMax',(10,10))
        self.cbxMinMax.SetValue(False)
        self.cbyMinMax.SetValue(True)
        lbCentering  = wx.StaticText( self, -1, 'Y-centering:')
        self.lbyRef  = wx.StaticText( self, -1, '            ')
        self.cbyMean  = wx.ComboBox(self, choices=['None', 'Mid=0', 'Mid=ref', 'Mean=0', 'Mean=ref'], style=wx.CB_READONLY)
        #self.cbyMean  = wx.ComboBox(self, choices=['None', '0', 'Mean of means'] , style=wx.CB_READONLY)
        self.cbyMean.SetSelection(0)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.cbxMinMax ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(self.cbyMinMax ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(lbCentering    ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbyMean   ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(self.lbyRef    ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_CHECKBOX, self.onMinMaxChange)
        self.cbyMean.Bind(wx.EVT_COMBOBOX, self.onMeanChange)
        self.Hide() 

    def setYRef(self, yRef=None):
        self.yRef = yRef
        if yRef is None:
            self.lbyRef.SetLabel('')
        else:
            self.lbyRef.SetLabel('Y-ref: '+pretty_num(yRef))


    def onMinMaxChange(self, event=None):
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def onMeanChange(self, event=None):
        self.setYRef(None)
        if self.cbyMean.GetValue()=='None':
            self.cbyMinMax.Enable(True)
        else:
            self.cbyMinMax.Enable(False)
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def _GUI2Data(self):
        data={'yScale':self.cbyMinMax.IsChecked(),
              'xScale':self.cbxMinMax.IsChecked(),
              'yCenter':self.cbyMean.GetValue(),
              'yRef':self.yRef,
              }
        return data

class PolarPanel(wx.Panel):
    def __init__(self, parent):
        super(PolarPanel,self).__init__(parent)
        # Data
        self.parent = parent
        self.rRef = None
        self.cbPolarDeg      = wx.CheckBox(self, -1, 'Theta [deg]',(10,10))
        self.cbPolarBins = wx.ComboBox(self, choices=['None', '12', '36', '60', '180', '360'], style=wx.CB_READONLY)
        self.cbPolarAbout = wx.ComboBox(self, choices=['x (from z, y hori flip, z vert)', 'z (from x, x hori, y vert)'], style=wx.CB_READONLY)
        self.cbPolarSameMean = wx.CheckBox(self, -1, 'Same Mean',(10,10))
#         self.cbPolarCenter   = wx.CheckBox(self, -1, 'Center',(10,10))
        self.lbrRef  = wx.StaticText( self, -1, '            ')
        self.cbPolarDeg.SetValue(True)
        lbBins  = wx.StaticText( self, -1, 'Bins:')
        lbAbout = wx.StaticText( self, -1, 'About:')
        self.cbPolarBins.SetSelection(0)
        self.cbPolarAbout.SetSelection(0)
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.cbPolarDeg      ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(lbBins               ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbPolarBins     ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(lbAbout               ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbPolarAbout     ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        dummy_sizer.Add(self.cbPolarSameMean ,0, flag=wx.CENTER|wx.LEFT, border = 2)
#         dummy_sizer.Add(self.cbPolarCenter   ,0, flag=wx.CENTER|wx.LEFT, border = 1)
        dummy_sizer.Add(self.lbrRef          ,0, flag=wx.CENTER|wx.LEFT, border = 2)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_CHECKBOX, self.onParamChange)
        self.Bind(wx.EVT_COMBOBOX, self.onParamChange)
        self.Hide() 

    def onParamChange(self, event=None):
        self.setRRef(None)
        if self.cbPolarAbout.GetValue().startswith('x'): # TODO
            self.parent.cbFlipX.SetValue(True)
        else:
            self.parent.cbFlipX.SetValue(False)
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def setRRef(self, rRef=None):
        self.rRef = rRef
        if rRef is None:
            self.lbrRef.SetLabel('')
        else:
            self.lbrRef.SetLabel('R-ref: '+pretty_num(rRef))

    def _GUI2Data(self):
        data={'Bins':self.cbPolarBins.GetValue(),
              'Deg':self.cbPolarDeg.IsChecked(),
              'About':self.cbPolarAbout.GetValue(),
              'SameMean':self.cbPolarSameMean.IsChecked(),
#               'Center':self.cbPolarCenter.IsChecked(),
              'rRef':self.rRef,
              }
        return data


class CompCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(CompCtrlPanel,self).__init__(parent)
        self.parent   = parent
        lblList = ['Relative', '|Relative|','Ratio','Absolute','Y-Y'] 
        self.rbType = wx.RadioBox(self, label = 'Type', choices = lblList,
                majorDimension = 1, style = wx.RA_SPECIFY_ROWS) 
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.rbType           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        self.SetSizer(dummy_sizer)
        self.rbType.Bind(wx.EVT_RADIOBOX,self.onTypeChange)
        self.Hide() 

    def onTypeChange(self,e): 
        self.parent.load_and_draw(); # DATA HAS CHANGED

    def _GUI2Data(self):
        data = {'type':  self.rbType.GetString(self.rbType.GetSelection())}
        return data

class ColorCtrlPanel(wx.Panel):
    """Control panel shown when a Z/color variable is selected."""
    COLORMAP = 'viridis'

    def __init__(self, parent):
        super(ColorCtrlPanel, self).__init__(parent)
        self.parent = parent
        self.cb3D = wx.CheckBox(self, -1, '3D view')
        self.cb3D.SetValue(False)
        # View buttons (shown only in 3D mode)
        self.btXY     = wx.Button(self, -1, 'x-y plane', style=wx.BU_EXACTFIT)
        self.btYZ     = wx.Button(self, -1, 'y-z plane', style=wx.BU_EXACTFIT)
        self.btXZ     = wx.Button(self, -1, 'x-z plane', style=wx.BU_EXACTFIT)
        self.btFree   = wx.Button(self, -1, 'Free',      style=wx.BU_EXACTFIT)
        self.cbPlot3D = wx.ComboBox(self, choices=['Scatter', 'Surf'], style=wx.CB_READONLY, size=(75, -1))
        self.cbPlot3D.SetSelection(0)
        self.cb3D.SetToolTip("Enable 3D scatter/surface plot (requires a Z variable)")
        self.btXY.SetToolTip("View from above: x-y plane (z hidden)")
        self.btYZ.SetToolTip("View from the side: y-z plane (x hidden)")
        self.btXZ.SetToolTip("View from the front: x-z plane (y hidden)")
        self.btFree.SetToolTip("Reset to free perspective 3D view")
        self.cbPlot3D.SetToolTip("3D plot type: Scatter = point cloud; Surf = surface")
        self.btXY.Hide()
        self.btYZ.Hide()
        self.btXZ.Hide()
        self.btFree.Hide()
        self.cbPlot3D.Hide()
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(self.cb3D    , 0, flag=wx.CENTER|wx.LEFT, border=8)
        dummy_sizer.Add(self.btXY   , 0, flag=wx.CENTER|wx.LEFT, border=8)
        dummy_sizer.Add(self.btYZ   , 0, flag=wx.CENTER|wx.LEFT, border=4)
        dummy_sizer.Add(self.btXZ   , 0, flag=wx.CENTER|wx.LEFT, border=4)
        dummy_sizer.Add(self.btFree , 0, flag=wx.CENTER|wx.LEFT, border=4)
        dummy_sizer.Add(self.cbPlot3D, 0, flag=wx.CENTER|wx.LEFT, border=8)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_CHECKBOX, self.on3DChange,      self.cb3D)
        self.Bind(wx.EVT_BUTTON,   self.onViewXY,        self.btXY)
        self.Bind(wx.EVT_BUTTON,   self.onViewYZ,        self.btYZ)
        self.Bind(wx.EVT_BUTTON,   self.onViewXZ,        self.btXZ)
        self.Bind(wx.EVT_BUTTON,   self.onViewFree,      self.btFree)
        self.Bind(wx.EVT_COMBOBOX, self.on3DTypeChange,  self.cbPlot3D)
        # Pending camera state applied after set_subplots recreates 3D axes
        self._pending_elev = None
        self._pending_azim = None
        self._pending_hide = None   # 'x', 'y', 'z', or None
        self.Hide()

    def _update3DButtons(self):
        """Show/hide plane buttons – does NOT redraw. cbPlot3D replaced by cbCurveType."""
        is3D = self.cb3D.IsChecked()
        self.btXY.Show(is3D)
        self.btYZ.Show(is3D)
        self.btXZ.Show(is3D)
        self.btFree.Show(is3D)
        self.cbPlot3D.Hide()  # cbCurveType (in ctrlPanel) now serves this role
        self.GetSizer().Layout()

    def on3DChange(self, event=None):
        self.parent.set3DMode(self.cb3D.IsChecked())

    @staticmethod
    def _apply_3d_plane(ax, elev, azim, hide_axis):
        """Set camera, projection type and axis visibility on one 3D axes."""
        ax.view_init(elev=elev, azim=azim)
        if hide_axis:
            try:
                ax.set_proj_type('ortho')
            except Exception:
                pass
            for name in ('x', 'y', 'z'):
                axis_obj = getattr(ax, '{}axis'.format(name), None)
                if axis_obj is None:
                    continue
                visible = (name != hide_axis)
                axis_obj.set_visible(visible)
                try:
                    axis_obj.pane.set_visible(visible)
                    axis_obj.pane.fill = visible
                except Exception:
                    pass
        else:
            try:
                ax.set_proj_type('persp')
            except Exception:
                pass
            for name in ('x', 'y', 'z'):
                axis_obj = getattr(ax, '{}axis'.format(name), None)
                if axis_obj is None:
                    continue
                axis_obj.set_visible(True)
                try:
                    axis_obj.pane.set_visible(True)
                    axis_obj.pane.fill = True
                except Exception:
                    pass

    def _setView(self, elev, azim, hide_axis=None):
        self._pending_elev = elev
        self._pending_azim = azim
        self._pending_hide = hide_axis
        for ax in self.parent.fig.axes:
            if hasattr(ax, 'view_init'):
                self._apply_3d_plane(ax, elev, azim, hide_axis)
        self.parent.canvas.draw()

    def onViewXY(self, event=None):
        self._setView(elev=90, azim=-90, hide_axis='z')

    def onViewYZ(self, event=None):
        self._setView(elev=0, azim=0, hide_axis='x')

    def onViewXZ(self, event=None):
        self._setView(elev=0, azim=-90, hide_axis='y')

    def on3DTypeChange(self, event=None):
        """Redraw when 3D plot type (Scatter/Surf) changes."""
        self.parent.load_and_draw()

    def onViewFree(self, event=None):
        """Reset camera angles to free perspective without rescaling axis ranges."""
        self._setView(elev=30, azim=-60, hide_axis=None)

    def _GUI2Data(self):
        # plot3DType is now driven by the unified cbCurveType in the parent PlotPanel
        try:
            plot3D_type = self.parent.cbCurveType.GetValue()
            if plot3D_type not in ('Scatter', 'Surf'):
                plot3D_type = 'Scatter'
        except Exception:
            plot3D_type = self.cbPlot3D.GetValue()
        return {
            'colormap':    self.COLORMAP,
            'colorbar':    True,
            'view3D':      self.cb3D.IsChecked(),
            'plot3DType':  plot3D_type,
        }


class SpectralCtrlPanel(wx.Panel):
    def __init__(self, parent):
        super(SpectralCtrlPanel,self).__init__(parent)
        self.parent   = parent
        # --- GUI widgets
        lb = wx.StaticText( self, -1, 'Type:')
        self.cbType            = wx.ComboBox(self, choices=['PSD','f x PSD','Amplitude'] , style=wx.CB_READONLY)
        self.cbType.SetSelection(0)
        lbAveraging            = wx.StaticText( self, -1, 'Avg.:')
        self.cbAveraging       = wx.ComboBox(self, choices=['None','Welch','Binning'] , style=wx.CB_READONLY)
        self.cbAveraging.SetSelection(1)
        self.lbAveragingMethod = wx.StaticText( self, -1, 'Window:')
        self.cbAveragingMethod = wx.ComboBox(self, choices=['Hamming','Hann','Rectangular'] , style=wx.CB_READONLY)
        self.cbAveragingMethod.SetSelection(0)
        self.lbP2 = wx.StaticText( self, -1, '2^n:')
        self.scP2 = wx.SpinCtrl(self, value='11',size=wx.Size(40,-1))
        self.lbWinLength = wx.StaticText( self, -1, '(2048) ')
        self.scP2.SetRange(3, 50)
        self.previousNExp = 8
        self.previousNDec = 20
        lbMaxFreq     = wx.StaticText( self, -1, 'Xlim:')
        self.tMaxFreq = wx.TextCtrl(self,size = (30,-1),style=wx.TE_PROCESS_ENTER)
        self.tMaxFreq.SetValue("-1")
        self.cbDetrend = wx.CheckBox(self, -1, 'Detrend',(10,10))
        lbX = wx.StaticText( self, -1, 'x:')
        self.cbTypeX = wx.ComboBox(self, choices=['1/x','2pi/x','x'] , style=wx.CB_READONLY)
        self.cbTypeX.SetSelection(0)
        # Layout
        dummy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dummy_sizer.Add(lb                    ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.cbType           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbAveraging           ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.cbAveraging      ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.lbAveragingMethod,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.cbAveragingMethod,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.lbP2             ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.scP2             ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.lbWinLength      ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbMaxFreq             ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.tMaxFreq         ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(lbX                   ,0, flag = wx.CENTER|wx.LEFT,border = 6)
        dummy_sizer.Add(self.cbTypeX          ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        dummy_sizer.Add(self.cbDetrend        ,0, flag = wx.CENTER|wx.LEFT,border = 7)
        self.SetSizer(dummy_sizer)
        self.Bind(wx.EVT_COMBOBOX  ,self.onSpecCtrlChange)
        self.Bind(wx.EVT_TEXT      ,self.onP2ChangeText  ,self.scP2     )
        self.Bind(wx.EVT_TEXT_ENTER,self.onXlimChange    ,self.tMaxFreq )
        self.Bind(wx.EVT_CHECKBOX  ,self.onDetrendChange ,self.cbDetrend)
        self.Hide() 

    def onXlimChange(self,event=None):
        self.parent.redraw_same_data();

    def onSpecCtrlChange(self,event=None):
        if self.cbAveraging.GetStringSelection()=='None':
            self.scP2.Enable(False)
            self.cbAveragingMethod.Enable(False)
            self.lbP2.SetLabel('')
            self.lbWinLength.SetLabel('')
        elif self.cbAveraging.GetStringSelection()=='Binning':
            self.previousNExp= self.scP2.GetValue()
            self.scP2.SetValue(self.previousNDec)
            self.scP2.Enable(True)
            self.cbAveragingMethod.Enable(False)
            self.lbP2.SetLabel('n:')
            self.lbWinLength.SetLabel('')
        else:
            self.previousDec= self.scP2.GetValue()
            self.scP2.SetValue(self.previousNExp)
            self.lbP2.SetLabel('2^n:')
            self.scP2.Enable(True)
            self.cbAveragingMethod.Enable(True)
            self.onP2ChangeText(event=None)
        self.parent.load_and_draw() # Data changes

    def onDetrendChange(self,event=None):
        self.parent.load_and_draw() # Data changes

    def onP2ChangeText(self,event=None):
        if self.cbAveraging.GetStringSelection()=='Binning':
            pass
        else:
            nExp=self.scP2.GetValue()
            self.updateP2(nExp)
        self.parent.load_and_draw() # Data changes

    def updateP2(self,P2):
        self.lbWinLength.SetLabel("({})".format(2**P2))


    def _GUI2Data(self):
        data = {}
        data['xType']      = self.cbTypeX.GetStringSelection()
        data['yType']      = self.cbType.GetStringSelection()
        data['avgMethod']  = self.cbAveraging.GetStringSelection()
        data['avgWindow']  = self.cbAveragingMethod.GetStringSelection()
        data['bDetrend']   = self.cbDetrend.IsChecked()
        data['nExp']       = self.scP2.GetValue()
        data['nPerDecade'] = self.scP2.GetValue()
        return data



class PlotTypePanel(wx.Panel):
    def __init__(self, parent):
        # Superclass constructor
        super(PlotTypePanel,self).__init__(parent)
        #self.SetBackgroundColour('yellow')
        # data
        self.parent   = parent # PlotPanel is parent
        # --- Ctrl Panel
        self.cbRegular = wx.RadioButton(self, -1, 'Regular',style=wx.RB_GROUP)
        self.cbPDF     = wx.RadioButton(self, -1, 'PDF'    ,                 )
        self.cbFFT     = wx.RadioButton(self, -1, 'FFT'    ,                 )
        self.cbMinMax  = wx.RadioButton(self, -1, 'MinMax' ,                 )
        self.cbCompare = wx.RadioButton(self, -1, 'Compare',                 )
        self.cbPolar   = wx.RadioButton(self, -1, 'Polar (beta)',            )
        self.cbRegular.SetValue(True)
        # BIND
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbPDF    )
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbFFT    )
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbMinMax )
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbCompare)
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbRegular)
        self.Bind(wx.EVT_RADIOBUTTON, self.plotTypeChange, self.cbPolar)
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=6, cols=1, hgap=0, vgap=0)
        cb_sizer.Add(self.cbRegular , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPDF     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFFT     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMinMax  , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbCompare , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPolar   , 0, flag=wx.ALL, border=1)
        self.SetSizer(cb_sizer)
        # Link Panels and Comboboxes 
        PTDict = {}
        PTDict['Regular']= {'opt_panel': None           ,  'cb':self.cbRegular}
        PTDict['FFT']    = {'opt_panel': parent.spcPanel,  'cb':self.cbFFT}
        PTDict['PDF']    = {'opt_panel': parent.pdfPanel,  'cb':self.cbPDF}
        PTDict['Compare']= {'opt_panel': parent.cmpPanel,  'cb':self.cbCompare}
        PTDict['MinMax'] = {'opt_panel': parent.mmxPanel,  'cb':self.cbMinMax}
        PTDict['Polar']  = {'opt_panel': parent.polPanel,  'cb':self.cbPolar}
        self.PTDict = PTDict

    def plotType(self):
        plotType='Regular'
        if self.cbMinMax.GetValue():
            plotType='MinMax'
        elif self.cbPDF.GetValue():
            plotType='PDF'
        elif self.cbFFT.GetValue():
            plotType='FFT'
        elif self.cbCompare.GetValue():
            plotType='Compare'
        elif self.cbPolar.GetValue():
            plotType='Polar'
        return plotType

    def plotTypeChange(self, event=None):
        self.clear_measures()
        self.parent.cleanMarkers()
        self.parent.Freeze()
        # --- Show and hide panels based on check box values
        currentPlotType=''
        for plotType, d in self.PTDict.items():
            if d['cb'].GetValue():
                currentPlotType=plotType
                if d['opt_panel'] is not None:
                    d['opt_panel'].Show()
                    d['opt_panel'].Refresh()
                    self.parent.slEsth.Show()
                else:
                    self.parent.slEsth.Hide()
            else:
                if d['opt_panel'] is not None:
                    d['opt_panel'].Hide()
        #plotType = self.plotType()
        plotType = currentPlotType
        # --- Special cases
        # Default
        self.parent.cbFlipX.SetValue(False)
        self.parent.cbLogY.SetValue(False)
        if plotType == 'Regular':
            pass
        elif plotType == 'MinMax':
            pass
        elif plotType == 'PDF':
            self.parent.cbLogX.SetValue(False)
            pass
        elif plotType == 'FFT':
            self.parent.cbLogY.SetValue(True)
        elif plotType == 'Compare':
            pass
        elif plotType == 'Polar':
            self.parent.cbLogX.SetValue(False)
            if self.parent.polPanel.cbPolarAbout.GetValue().startswith('x'): # TODO
                self.parent.cbFlipX.SetValue(True)

        self.parent.plotsizer.Layout()
        self.parent.Thaw()
        self.parent.load_and_draw() # Data changes


    def clear_measures(self):
        self.parent.rightMeasure.clear()
        self.parent.leftMeasure.clear()
        self.parent.lbDeltaX.SetLabel('')
        self.parent.lbDeltaY.SetLabel('')

class EstheticsPanel(wx.Panel):
    def __init__(self, parent, data):
        wx.Panel.__init__(self, parent)
        self.parent=parent
        #self.SetBackgroundColour('red')

        # Font
        lbFont = wx.StaticText( self, -1, 'Font:')
        fontChoices = ['6','7','8','9','10','11','12','13','14','15','16','17','18']
        self.cbFont = wx.ComboBox(self, choices=fontChoices , style=wx.CB_READONLY)
        try:
            i = fontChoices.index(str(data['Font']))
        except ValueError:
            i = 2
        self.cbFont.SetSelection(i)
        self.cbFont.SetToolTip("Axis tick and label font size")
        # Legend
        # NOTE: we don't offer "best" since best is slow
        lbLegend = wx.StaticText( self, -1, 'Legend:')
        lbChoices = ['None','Upper right','Upper left','Lower left','Lower right','Right','Center left','Center right','Lower center','Upper center','Center']
        self.cbLegend = wx.ComboBox(self, choices=lbChoices, style=wx.CB_READONLY)
        try:
            i = lbChoices.index(str(data['LegendPosition']))
        except ValueError:
            i=1
        self.cbLegend.SetSelection(i)
        self.cbLegend.SetToolTip("Position of the plot legend")
        # Legend Font
        lbLgdFont = wx.StaticText( self, -1, 'Legend font:')
        self.cbLgdFont = wx.ComboBox(self, choices=fontChoices, style=wx.CB_READONLY)
        try:
            i = fontChoices.index(str(data['LegendFont']))
        except ValueError:
            i = 2
        self.cbLgdFont.SetSelection(i)
        self.cbLgdFont.SetToolTip("Font size for legend text")
        # Line Width Font
        lbLW = wx.StaticText( self, -1, 'Line width:')
        LWChoices = ['0.5','1.0','1.25','1.5','1.75','2.0','2.5','3.0']
        self.cbLW = wx.ComboBox(self, choices=LWChoices , style=wx.CB_READONLY)
        try:
            i = LWChoices.index(str(data['LineWidth']))
        except ValueError:
            i = 3
        self.cbLW.SetSelection(i)
        self.cbLW.SetToolTip("Width of plot lines in points")
        #  Marker Size
        lbMS = wx.StaticText( self, -1, 'Marker size:')
        MSChoices = ['0.5','1','2','3','4','5','6','7','8']
        self.cbMS= wx.ComboBox(self, choices=MSChoices, style=wx.CB_READONLY)
        try:
            i = MSChoices.index(str(data['MarkerSize']))
        except ValueError:
            i = 2
        self.cbMS.SetSelection(i)
        self.cbMS.SetToolTip("Size of data point markers")
        # Axis Limits
        lbXMin = wx.StaticText(self, -1, 'xmin:')
        self.tXMin = wx.TextCtrl(self, size=(60, -1), style=wx.TE_PROCESS_ENTER)
        self.tXMin.SetValue(str(data.get('xmin', '')))
        self.tXMin.SetToolTip("Minimum x-axis limit (empty = auto)")
        lbXMax = wx.StaticText(self, -1, 'xmax:')
        self.tXMax = wx.TextCtrl(self, size=(60, -1), style=wx.TE_PROCESS_ENTER)
        self.tXMax.SetValue(str(data.get('xmax', '')))
        self.tXMax.SetToolTip("Maximum x-axis limit (empty = auto)")
        lbYMin = wx.StaticText(self, -1, 'ymin:')
        self.tYMin = wx.TextCtrl(self, size=(60, -1), style=wx.TE_PROCESS_ENTER)
        self.tYMin.SetValue(str(data.get('ymin', '')))
        self.tYMin.SetToolTip("Minimum y-axis limit (empty = auto)")
        lbYMax = wx.StaticText(self, -1, 'ymax:')
        self.tYMax = wx.TextCtrl(self, size=(60, -1), style=wx.TE_PROCESS_ENTER)
        self.tYMax.SetValue(str(data.get('ymax', '')))
        self.tYMax.SetToolTip("Maximum y-axis limit (empty = auto)")
        lbZMin = wx.StaticText(self, -1, 'zmin:')
        self.tZMin = wx.TextCtrl(self, size=(60, -1), style=wx.TE_PROCESS_ENTER)
        self.tZMin.SetValue(str(data.get('zmin', '')))
        self.tZMin.SetToolTip("Minimum z value (empty = auto). 3D: z axis. 2D+Z: color scale lower bound.")
        lbZMax = wx.StaticText(self, -1, 'zmax:')
        self.tZMax = wx.TextCtrl(self, size=(60, -1), style=wx.TE_PROCESS_ENTER)
        self.tZMax.SetValue(str(data.get('zmax', '')))
        self.tZMax.SetToolTip("Maximum z value (empty = auto). 3D: z axis. 2D+Z: color scale upper bound.")

        # Layout — single WrapSizer holding both the esthetic controls and
        # the axis-limit controls. Previously this was a BoxSizer(VERTICAL)
        # containing two nested WrapSizers, but nested WrapSizers inside a
        # BoxSizer break the panel's Hide() propagation on first show — the
        # esthetics panel would leak through as visible on startup — so we
        # keep a single WrapSizer and let it wrap naturally.
        self.lbZMin = lbZMin
        self.lbZMax = lbZMax
        main_sizer = wx.WrapSizer(orient=wx.HORIZONTAL)
        main_sizer.Add(lbFont                ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(self.cbFont           ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbLW                  ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.cbLW             ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbMS                  ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.cbMS             ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbLegend              ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.cbLegend         ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbLgdFont             ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.cbLgdFont        ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbXMin                ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.tXMin            ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbXMax                ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.tXMax            ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbYMin                ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.tYMin            ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbYMax                ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.tYMax            ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbZMin                ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.tZMin            ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        main_sizer.Add(lbZMax                ,0, flag = wx.CENTER|wx.LEFT,border = 5)
        main_sizer.Add(self.tZMax            ,0, flag = wx.CENTER|wx.LEFT,border = 1)
        self.SetSizer(main_sizer)
        self.Hide()
        # Callbacks
        self.Bind(wx.EVT_COMBOBOX  ,self.onAnyEsthOptionChange)
        self.cbFont.Bind(wx.EVT_COMBOBOX  ,self.onFontOptionChange)
        self.tXMin.Bind(wx.EVT_TEXT_ENTER, self.onAxisLimitChange)
        self.tXMax.Bind(wx.EVT_TEXT_ENTER, self.onAxisLimitChange)
        self.tYMin.Bind(wx.EVT_TEXT_ENTER, self.onAxisLimitChange)
        self.tYMax.Bind(wx.EVT_TEXT_ENTER, self.onAxisLimitChange)
        self.tZMin.Bind(wx.EVT_TEXT_ENTER, self.onAxisLimitChange)
        self.tZMax.Bind(wx.EVT_TEXT_ENTER, self.onAxisLimitChange)

        # Store data
        self.data={}
        self._GUI2Data()

    def onAnyEsthOptionChange(self,event=None):
        self.parent.redraw_same_data()

    def onFontOptionChange(self,event=None):
        matplotlib_rc('font', **{'size':int(self.cbFont.Value) }) # affect all (including ticks)
        self.onAnyEsthOptionChange()

    def onAxisLimitChange(self, event=None):
        if self.parent.cbAutoScale.IsChecked():
            self.parent.cbAutoScale.SetValue(False)
        self.parent.redraw_same_data()

    def getAxisLimits(self):
        """Return axis limit values. Empty/invalid fields become None."""
        def _parse(tc):
            v = tc.GetValue().strip()
            if v == '':
                return None
            try:
                return float(v)
            except ValueError:
                return None
        return {
            'xmin': _parse(self.tXMin),
            'xmax': _parse(self.tXMax),
            'ymin': _parse(self.tYMin),
            'ymax': _parse(self.tYMax),
            'zmin': _parse(self.tZMin),
            'zmax': _parse(self.tZMax),
        }

    def showZLimits(self, show):
        """Show or hide the z-axis limit fields."""
        self.lbZMin.Show(show)
        self.tZMin.Show(show)
        self.lbZMax.Show(show)
        self.tZMax.Show(show)
        self.Layout()

    def _GUI2Data(self):
        """ data['plotStyle'] """
        self.data['Font']           = int(self.cbFont.GetValue())
        self.data['LegendFont']     = int(self.cbLgdFont.GetValue())
        self.data['LegendPosition'] = self.cbLegend.GetValue()
        self.data['LineWidth']      = float(self.cbLW.GetValue())
        self.data['MarkerSize']     = float(self.cbMS.GetValue())
        self.data['xmin']           = self.tXMin.GetValue()
        self.data['xmax']           = self.tXMax.GetValue()
        self.data['ymin']           = self.tYMin.GetValue()
        self.data['ymax']           = self.tYMax.GetValue()
        self.data['zmin']           = self.tZMin.GetValue()
        self.data['zmax']           = self.tZMax.GetValue()
        return self.data


class PlotPanel(wx.Panel):
    def __init__(self, parent, selPanel, pipeLike=None, infoPanel=None, data=None):

        # Superclass constructor
        super(PlotPanel,self).__init__(parent)

        # Font handling
        font = parent.GetFont()
        font.SetPointSize(font.GetPointSize()-1)
        self.SetFont(font) 
        # Preparing a special font manager for chinese characters
        self.specialFont=None
        try:
            pyplot_path = matplotlib.get_data_path()
        except:
            pyplot_path = pyplot_rc['datapath']
        CH_F_PATHS = [
                os.path.join(pyplot_path, 'fonts/ttf/SimHei.ttf'),
                os.path.join(os.path.dirname(__file__),'../SimHei.ttf')]
        for fpath in CH_F_PATHS:
            if os.path.exists(fpath):
                fontP = font_manager.FontProperties(fname=fpath)
                fontP.set_size(font.GetPointSize())
                self.specialFont=fontP
                break
        # data
        self.selPanel = selPanel # <<< dependency with selPanel should be minimum
        self.pipeLike = pipeLike #
        self.selMode  = '' 
        self.infoPanel=infoPanel
        if self.infoPanel is not None:
            self.infoPanel.setPlotMatrixCallbacks(self._onPlotMatrixLeftClick, self._onPlotMatrixRightClick)
        self.parent   = parent
        self.plotData = []
        self.toolPanel=None
        self.subplotsPar=None
        self.plotDone=False
        if data is not None:
            self.data  = data
        else:
            self.data = self.defaultData()
        if self.selPanel is not None:
            bg=self.selPanel.BackgroundColour
            self.SetBackgroundColour(bg) # sowhow, our parent has a wrong color
        #self.SetBackgroundColour('red')
        self.leftMeasure = GUIMeasure(1, 'firebrick')
        self.rightMeasure = GUIMeasure(2, 'darkgreen')
        self.markers = [] # List of GUIMeasures
        self.xlim_prev = [[0, 1]]
        self.ylim_prev = [[0, 1]]
        self.zlim_prev = []      # per-axis z-limits for 3D axes; None otherwise
        self.view3d_prev = []    # per-axis (elev, azim) for 3D axes; None otherwise
        self.addTablesCallback = None
        self._bg_image = None    # numpy array for background image
        self._bg_glued = False   # True = 'Moving with axes' (glued to data coords);
                                 # False = 'Fixed' (pinned to plot rectangle, default)
        self._bg_extent = None   # [xmin, xmax, ymin, ymax] in data coords, captured
                                 # when entering 'Moving with axes' mode
        self._bg_display_image = None  # cropped image rendered in Fixed mode
                                       # (None = use the full _bg_image)
        self._bg_axes_extent = None    # [afx0, afx1, afy0, afy1] in axes-fraction
                                       # coords for Fixed-mode artist (None = [0,1,0,1])
        self._bg_crop_box = None       # [col0, col1, row0, row1] as fractions [0,1]
                                       # of the original _bg_image that
                                       # _bg_display_image represents (None = full image)

        # --- GUI
        self.fig = Figure(facecolor="white", figsize=(1, 1))
        register_matplotlib_converters()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)
        self.canvas.mpl_connect('button_press_event', self.onMouseClick)
        self.canvas.mpl_connect('button_release_event', self.onMouseRelease)
        self.canvas.mpl_connect('draw_event', self.onDraw)
        self.clickLocation = (None, 0, 0)

        self.navTBTop    = MyNavigationToolbar2Wx(self.canvas, ['Home', 'Pan'], plotPanel=self)
        self.navTBBottom = MyNavigationToolbar2Wx(self.canvas, ['Subplots', 'Save'], plotPanel=self)
        TBAddCheckTool(self.navTBBottom,'', icons.chart.GetBitmap(), self.onEsthToggle)
        self.esthToggle=False
        TBAddTool(self.navTBBottom, 'BG', callback=self.onBgMenu)

        self.navTBBottom.Realize()

        #self.navTB = wx.ToolBar(self, style=wx.TB_HORIZONTAL|wx.TB_HORZ_LAYOUT|wx.TB_NODIVIDER|wx.TB_FLAT)
        #self.navTB.SetMargins(0,0)
        #self.navTB.SetToolPacking(0)
        #self.navTB.AddCheckTool(-1, label='', bitmap1=icons.chart.GetBitmap())
        #self.navTB.Realize()

        self.toolbar_sizer  = wx.BoxSizer(wx.VERTICAL)
        self.toolbar_sizer.Add(self.navTBTop)
        self.toolbar_sizer.Add(self.navTBBottom)


        # --- Tool Panel
        self.toolSizer= wx.BoxSizer(wx.VERTICAL)
        # --- Plot type specific options
        self.spcPanel   = SpectralCtrlPanel(self)
        self.pdfPanel   = PDFCtrlPanel(self)
        self.cmpPanel   = CompCtrlPanel(self)
        self.mmxPanel   = MinMaxPanel(self)
        self.polPanel   = PolarPanel(self)
        self.colorPanel = ColorCtrlPanel(self)
        # --- PlotType Panel (Needs the different pansel above)
        self.pltTypePanel= PlotTypePanel(self);

        # --- Esthetics panel
        self.esthPanel = EstheticsPanel(self, data=self.data['plotStyle'])
        self.esthPanel.showZLimits(False)  # hidden until a Z variable is selected


        # --- Ctrl Panel
        self.ctrlPanel= wx.Panel(self)
        #self.ctrlPanel.SetBackgroundColour('blue')
        # Check Boxes
        self.cbCurveType = wx.ComboBox(self.ctrlPanel, choices=['Plain','LS','Markers','Mix'] , style=wx.CB_READONLY)
        self.cbCurveType.SetSelection(1)
        self.cbSub        = wx.CheckBox(self.ctrlPanel, -1, 'Subplot',(10,10))
        self.cbLogX       = wx.CheckBox(self.ctrlPanel, -1, 'Log-x',(10,10))
        self.cbLogY       = wx.CheckBox(self.ctrlPanel, -1, 'Log-y',(10,10))
        self.cbSync       = wx.CheckBox(self.ctrlPanel, -1, 'Sync-x',(10,10))
        self.cbXHair      = wx.CheckBox(self.ctrlPanel, -1, 'CrossHair',(10,10))
        self.cbPlotMatrix = wx.CheckBox(self.ctrlPanel, -1, 'Matrix',(10,10))
        self.cbAutoScale  = wx.CheckBox(self.ctrlPanel, -1, 'AutoScale',(10,10))
        self.cbGrid       = wx.CheckBox(self.ctrlPanel, -1, 'Grid',(10,10))
        self.cbStepPlot   = wx.CheckBox(self.ctrlPanel, -1, 'StepPlot',(10,10))
        self.cbMeasure    = wx.CheckBox(self.ctrlPanel, -1, 'Measure',(10,10))
        self.cbMarkPt     = wx.CheckBox(self.ctrlPanel, -1, 'Mark Points',(10,10))
        self.cbSwapXY     = wx.CheckBox(self.ctrlPanel, -1, 'Swap XY',(10,10))
        self.cbFlipX      = wx.CheckBox(self.ctrlPanel, -1, 'Flip X',(10,10))
        self.cbFlipY      = wx.CheckBox(self.ctrlPanel, -1, 'Flip Y',(10,10))
        # Save default combo selections for 2D/3D/2DZ switching
        self._2d_curve_type_sel  = 1  # 'LS'
        self._2dZ_curve_type_sel = 0  # 'Scatter'
        self._3d_curve_type_sel  = 0  # 'Scatter'
        self._combo_mode = '2D'  # '2D' | '2DZ' | '3D'
        # Tooltips
        self.cbCurveType.SetToolTip("Line style: Plain = solid lines; LS = varied dashes; Markers = symbols; Mix = both")
        self.cbSub.SetToolTip("Split each y-variable into its own subplot")
        self.cbLogX.SetToolTip("Use logarithmic scale on x-axis")
        self.cbLogY.SetToolTip("Use logarithmic scale on y-axis")
        self.cbSync.SetToolTip("Synchronise x-axis limits across all subplots")
        self.cbXHair.SetToolTip("Show a crosshair cursor on the plot")
        self.cbPlotMatrix.SetToolTip("Show a scatter-plot matrix of all selected columns")
        self.cbAutoScale.SetToolTip("Rescale axes on every redraw")
        self.cbGrid.SetToolTip("Show grid lines on the plot")
        self.cbStepPlot.SetToolTip("Draw data as a step/staircase plot")
        self.cbMeasure.SetToolTip("Enable measurement mode: click two points to measure distance")
        self.cbMarkPt.SetToolTip("Mark individual data points with markers")
        self.cbSwapXY.SetToolTip("Swap the x and y axes")
        self.cbFlipX.SetToolTip("Flip (reverse) the x-axis direction")
        self.cbFlipY.SetToolTip("Flip (reverse) the y-axis direction")
        #self.cbSub.SetValue(True) # DEFAULT TO SUB?
        self.cbSync.SetValue(True)
        self.cbXHair.SetValue(self.data['CrossHair']) # Have cross hair by default
        self.cbAutoScale.SetValue(True)
        self.cbGrid.SetValue(self.data['Grid'])
        # BIND - Callbacks
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSub    )
        self.Bind(wx.EVT_COMBOBOX, self.redraw_event     , self.cbCurveType)
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogX   )
        self.Bind(wx.EVT_CHECKBOX, self.log_select       , self.cbLogY   )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbSync )
        self.Bind(wx.EVT_CHECKBOX, self.crosshair_event  , self.cbXHair )
        self.Bind(wx.EVT_CHECKBOX, self.plot_matrix_event, self.cbPlotMatrix )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbAutoScale )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbGrid )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbStepPlot )
        self.Bind(wx.EVT_CHECKBOX, self.measure_event    , self.cbMeasure )
        self.Bind(wx.EVT_CHECKBOX, self.markpt_event     , self.cbMarkPt )
        self.Bind(wx.EVT_CHECKBOX, self.swap_event       , self.cbSwapXY )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbFlipX )
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event     , self.cbFlipY )
        # LAYOUT
        cb_sizer  = wx.FlexGridSizer(rows=5, cols=3, hgap=0, vgap=0)
        cb_sizer.Add(self.cbCurveType , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSub       , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbAutoScale , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogX      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbLogY      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbStepPlot  , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbXHair     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbGrid      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSync      , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbPlotMatrix, 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMeasure   , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbMarkPt    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbSwapXY    , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFlipX     , 0, flag=wx.ALL, border=1)
        cb_sizer.Add(self.cbFlipY     , 0, flag=wx.ALL, border=1)

        # --- 3D-specific ctrl panel (shown only in 3D mode, RIGHT NEXT to the other checkboxes)
        self.ctrl3DPanel = wx.Panel(self.ctrlPanel)
        self.cbLogZ  = wx.CheckBox(self.ctrl3DPanel, -1, 'Log-z',  (10, 10))
        self.cbFlipZ = wx.CheckBox(self.ctrl3DPanel, -1, 'Flip Z', (10, 10))
        self.cbLogZ.SetToolTip("Use logarithmic scale on z-axis")
        self.cbFlipZ.SetToolTip("Flip (reverse) the z-axis direction")
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event, self.cbLogZ)
        self.Bind(wx.EVT_CHECKBOX, self.redraw_event, self.cbFlipZ)
        sizer3D = wx.FlexGridSizer(rows=5, cols=1, hgap=0, vgap=0)
        sizer3D.Add(self.cbLogZ,  0, flag=wx.ALL, border=1)
        sizer3D.Add(self.cbFlipZ, 0, flag=wx.ALL, border=1)
        self.ctrl3DPanel.SetSizer(sizer3D)
        self.ctrl3DPanel.Hide()
        # Wrap cb_sizer and ctrl3DPanel in a horizontal sizer inside ctrlPanel
        ctrlHSizer = wx.BoxSizer(wx.HORIZONTAL)
        ctrlHSizer.Add(cb_sizer, 0, flag=wx.ALL, border=0)
        ctrlHSizer.Add(self.ctrl3DPanel, 0, flag=wx.LEFT|wx.EXPAND, border=4)
        self.ctrlPanel.SetSizer(ctrlHSizer)

        # --- Crosshair Panel
        crossHairPanel= wx.Panel(self)
        self.lbCrossHairX = wx.StaticText(crossHairPanel, -1, 'x = ...       ')
        self.lbCrossHairY = wx.StaticText(crossHairPanel, -1, 'y = ...       ')
        self.lbCrossHairZ = wx.StaticText(crossHairPanel, -1, 'z = ...       ')
        self.lbDeltaX = wx.StaticText(crossHairPanel,     -1, '              ')
        self.lbDeltaY = wx.StaticText(crossHairPanel,     -1, '              ')
        self.lbCrossHairX.SetFont(getMonoFont(self))
        self.lbCrossHairY.SetFont(getMonoFont(self))
        self.lbCrossHairZ.SetFont(getMonoFont(self))
        self.lbDeltaX.SetFont(getMonoFont(self))
        self.lbDeltaY.SetFont(getMonoFont(self))
        self.lbCrossHairZ.Hide()  # shown only in 3D mode
        cbCH  = wx.FlexGridSizer(rows=5, cols=1, hgap=0, vgap=0)
        cbCH.Add(self.lbCrossHairX   , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbCrossHairY   , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbCrossHairZ   , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbDeltaX       , 0, flag=wx.ALL, border=1)
        cbCH.Add(self.lbDeltaY       , 0, flag=wx.ALL, border=1)
        crossHairPanel.SetSizer(cbCH)

        # --- layout of panels
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sl2 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        sl3 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        sl4 = wx.StaticLine(self, -1, size=wx.Size(1,-1), style=wx.LI_VERTICAL)
        row_sizer.Add(self.pltTypePanel , 0 , flag=wx.LEFT|wx.RIGHT|wx.CENTER          , border=1)
        row_sizer.Add(sl2               , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(self.toolbar_sizer, 0 , flag=wx.LEFT|wx.RIGHT|wx.CENTER          , border=1)
        row_sizer.Add(sl3               , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(self.ctrlPanel    , 1 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(sl4               , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=0)
        row_sizer.Add(crossHairPanel    , 0 , flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.CENTER, border=1)

        plotsizer = wx.BoxSizer(wx.VERTICAL)
        self.slCtrl = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.slCtrl.Hide()
        self.slEsth = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.slEsth.Hide()
        sl1 = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        plotsizer.Add(self.toolSizer  ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.canvas     ,1,flag = wx.EXPAND,border = 5 )
        plotsizer.Add(sl1             ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.spcPanel   ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.pdfPanel   ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.cmpPanel   ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.mmxPanel   ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.polPanel   ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.colorPanel ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slEsth     ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(self.esthPanel  ,0,flag = wx.EXPAND|wx.TOP|wx.BOTTOM,border = 10)
        plotsizer.Add(self.slCtrl     ,0,flag = wx.EXPAND,border = 0)
        plotsizer.Add(row_sizer       ,0,flag = wx.EXPAND|wx.NORTH ,border = 2)

        self.SetSizer(plotsizer)
        self.plotsizer=plotsizer;
        # Explicitly hide optional panels via the sizer. Each panel calls
        # self.Hide() at the end of its own __init__, but on some platforms
        # that pre-Add state is not reliably honored by the sizer once the
        # parent first lays itself out, so the panels would briefly appear
        # on first open. Hiding via the sizer after SetSizer makes it stick.
        for _p in (self.spcPanel, self.pdfPanel, self.cmpPanel, self.mmxPanel,
                   self.polPanel, self.colorPanel, self.esthPanel,
                   self.slEsth, self.slCtrl):
            plotsizer.Hide(_p)
        plotsizer.Layout()
#         self.setSubplotSpacing(init=True)

    # --- Bindings/callback
    def setAddTablesCallback(self, callback):
        self.addTablesCallback = callback

    def addTables(self, *args, **kwargs):
        if self.addTablesCallback is not None:
            self.addTablesCallback(*args, **kwargs)
        else:
            print('[WARN] callback to add tables to parent was not set. (call setAddTablesCallback)')


    def set3DMode(self, is3D, redraw=True):
        """Switch cbCurveType between 2D/3D choices, show/hide 3D-only controls."""
        # Temporarily unbind EVT_COMBOBOX to prevent spurious redraw on Windows
        # (ComboBox.Set() can fire selection-change events on some platforms)
        self.Unbind(wx.EVT_COMBOBOX, source=self.cbCurveType)
        try:
            if is3D:
                # Save current selection before switching to 3D
                if self._combo_mode == '2D':
                    self._2d_curve_type_sel = self.cbCurveType.GetSelection()
                elif self._combo_mode == '2DZ':
                    self._2dZ_curve_type_sel = self.cbCurveType.GetSelection()
                self.cbCurveType.Set(['Scatter', 'Surf'])
                self.cbCurveType.SetSelection(max(0, min(self._3d_curve_type_sel, 1)))
                self.cbCurveType.SetToolTip("3D plot type: Scatter = point cloud; Surf = triangulated surface")
                self._combo_mode = '3D'
            else:
                self._3d_curve_type_sel = self.cbCurveType.GetSelection()
                # Return to plain 2D – setZMode will upgrade to '2DZ' if Z is present
                self.cbCurveType.Set(['Plain', 'LS', 'Markers', 'Mix'])
                self.cbCurveType.SetSelection(self._2d_curve_type_sel)
                self.cbCurveType.SetToolTip("Line style: Plain = solid lines; LS = varied dashes; Markers = symbols; Mix = both")
                self._combo_mode = '2D'
        finally:
            self.Bind(wx.EVT_COMBOBOX, self.redraw_event, self.cbCurveType)
        self.ctrl3DPanel.Show(is3D)
        self.lbCrossHairZ.Show(is3D)
        self.colorPanel._update3DButtons()
        if hasattr(self, 'navTBTop'):
            try:
                self.navTBTop.set3DMode(is3D)
            except Exception:
                pass
        self.ctrlPanel.Layout()
        self.plotsizer.Layout()
        if redraw:
            self.load_and_draw()

    def setZMode(self, hasZ):
        """Switch cbCurveType between plain-2D and 2D+Z choices.

        Called after getPlotData determines whether any series has a Z variable
        and 3D mode is NOT active. Does nothing if already in the correct mode.
        """
        if self.colorPanel.cb3D.IsChecked():
            return  # 3D is handled exclusively by set3DMode
        target = '2DZ' if hasZ else '2D'
        if target == self._combo_mode:
            return
        self.Unbind(wx.EVT_COMBOBOX, source=self.cbCurveType)
        try:
            if hasZ:
                # Switching from plain 2D → 2DZ
                self._2d_curve_type_sel = self.cbCurveType.GetSelection()
                self.cbCurveType.Set(['Scatter', 'Scatter+Line'])
                self.cbCurveType.SetSelection(max(0, min(self._2dZ_curve_type_sel, 1)))
                self.cbCurveType.SetToolTip(
                    "2D scatter coloured by Z: Scatter = dots only; Scatter+Line = dots with connecting lines")
            else:
                # Switching from 2DZ → plain 2D
                self._2dZ_curve_type_sel = self.cbCurveType.GetSelection()
                self.cbCurveType.Set(['Plain', 'LS', 'Markers', 'Mix'])
                self.cbCurveType.SetSelection(self._2d_curve_type_sel)
                self.cbCurveType.SetToolTip(
                    "Line style: Plain = solid lines; LS = varied dashes; Markers = symbols; Mix = both")
        finally:
            self.Bind(wx.EVT_COMBOBOX, self.redraw_event, self.cbCurveType)
        self._combo_mode = target

    # --- GUI DATA
    def saveData(self, data):
        data['Grid']      = self.cbGrid.IsChecked()
        data['CrossHair'] = self.cbXHair.IsChecked()
        self.esthPanel._GUI2Data()
        data['plotStyle']= self.esthPanel.data

    def captureViewData(self):
        """Capture current plot panel state for view saving"""
        data = {}
        data['plotType']  = self.pltTypePanel.plotType()
        data['logX']      = self.cbLogX.IsChecked()
        data['logY']      = self.cbLogY.IsChecked()
        data['grid']      = self.cbGrid.IsChecked()
        data['crossHair'] = self.cbXHair.IsChecked()
        data['subplot']   = self.cbSub.IsChecked()
        data['sync']      = self.cbSync.IsChecked()
        data['autoScale'] = self.cbAutoScale.IsChecked()
        data['stepPlot']  = self.cbStepPlot.IsChecked()
        data['curveType'] = self.cbCurveType.GetValue()   # string e.g. 'LS' or 'Scatter'
        data['logZ']      = self.cbLogZ.IsChecked()  if hasattr(self, 'cbLogZ')  else False
        data['flipZ']     = self.cbFlipZ.IsChecked() if hasattr(self, 'cbFlipZ') else False
        data['plotStyle'] = {
            'Font':           self.esthPanel.cbFont.GetValue(),
            'LegendFont':     self.esthPanel.cbLgdFont.GetValue(),
            'LegendPosition': self.esthPanel.cbLegend.GetValue(),
            'LineWidth':      self.esthPanel.cbLW.GetValue(),
            'MarkerSize':     self.esthPanel.cbMS.GetValue(),
        }
        data['view3D']      = self.colorPanel.cb3D.IsChecked()
        # Use cbCurveType (the live widget) not the always-hidden cbPlot3D
        data['plot3D_type'] = self.cbCurveType.GetValue() if data['view3D'] else 'Scatter'
        # Camera angle for 3D view
        elev, azim = None, None
        for ax in self.fig.axes:
            if hasattr(ax, 'elev'):
                elev = ax.elev
                azim = ax.azim
                break
        data['view3D_elev'] = elev
        data['view3D_azim'] = azim
        data['view3D_hide'] = self.colorPanel._pending_hide
        # R1 – Spectral / FFT panel
        spc = self.spcPanel._GUI2Data()
        spc['xlim'] = self.spcPanel.tMaxFreq.GetValue()
        data['spectral'] = spc
        # R2 – Compare panel
        data['compare']   = self.cmpPanel._GUI2Data()
        # R3 – MinMax panel
        data['minmax']    = self.mmxPanel._GUI2Data()
        # R4 – PDF panel
        data['pdf']       = self.pdfPanel._GUI2Data()
        # R5 – Polar panel
        data['polar']     = self.polPanel._GUI2Data()
        # R6 – Swap XY
        data['swapXY']    = self.cbSwapXY.IsChecked()
        # R7 – Flip axes
        data['flipX']     = self.cbFlipX.IsChecked()
        data['flipY']     = self.cbFlipY.IsChecked()
        # R8 – Plot matrix
        data['plotMatrix'] = self.cbPlotMatrix.IsChecked()
        # R9 – Axis limits
        data['axisLimits'] = {
            'xmin': self.esthPanel.tXMin.GetValue(),
            'xmax': self.esthPanel.tXMax.GetValue(),
            'ymin': self.esthPanel.tYMin.GetValue(),
            'ymax': self.esthPanel.tYMax.GetValue(),
            'zmin': self.esthPanel.tZMin.GetValue(),
            'zmax': self.esthPanel.tZMax.GetValue(),
        }
        return data

    def restoreViewData(self, data):
        """Restore plot panel state from a saved view (does not redraw)"""
        plotType = data.get('plotType', 'Regular')
        # Set radio buttons without triggering events, then show/hide opt panels
        for pt, d in self.pltTypePanel.PTDict.items():
            d['cb'].SetValue(pt == plotType)
            if d['opt_panel'] is not None:
                d['opt_panel'].Show() if pt == plotType else d['opt_panel'].Hide()
        has_opt_panel = self.pltTypePanel.PTDict.get(plotType, {}).get('opt_panel') is not None
        self.slEsth.Show() if has_opt_panel else self.slEsth.Hide()
        self.plotsizer.Layout()
        # Checkboxes
        self.cbLogX.SetValue(data.get('logX', False))
        self.cbLogY.SetValue(data.get('logY', plotType == 'FFT'))
        self.cbGrid.SetValue(data.get('grid', False))
        self.cbXHair.SetValue(data.get('crossHair', True))
        self.cbSub.SetValue(data.get('subplot', False))
        self.cbSync.SetValue(data.get('sync', True))
        self.cbAutoScale.SetValue(data.get('autoScale', True))
        self.cbStepPlot.SetValue(data.get('stepPlot', False))
        # R6-R8 – axis toggles and matrix
        self.cbSwapXY.SetValue(data.get('swapXY', False))
        self.cbFlipX.SetValue(data.get('flipX', False))
        self.cbFlipY.SetValue(data.get('flipY', False))
        self.cbPlotMatrix.SetValue(data.get('plotMatrix', False))
        # Aesthetics
        plotStyle = data.get('plotStyle', {})
        if plotStyle:
            fontChoices = ['6','7','8','9','10','11','12','13','14','15','16','17','18']
            LWChoices   = ['0.5','1.0','1.25','1.5','1.75','2.0','2.5','3.0']
            MSChoices   = ['0.5','1','2','3','4','5','6','7','8']
            lbChoices   = ['None','Upper right','Upper left','Lower left','Lower right','Right','Center left','Center right','Lower center','Upper center','Center']
            try:
                self.esthPanel.cbFont.SetSelection(fontChoices.index(str(plotStyle.get('Font','11'))))
            except ValueError:
                pass
            try:
                self.esthPanel.cbLgdFont.SetSelection(fontChoices.index(str(plotStyle.get('LegendFont','11'))))
            except ValueError:
                pass
            try:
                self.esthPanel.cbLegend.SetSelection(lbChoices.index(str(plotStyle.get('LegendPosition','Upper right'))))
            except ValueError:
                pass
            try:
                self.esthPanel.cbLW.SetSelection(LWChoices.index(str(plotStyle.get('LineWidth','1.5'))))
            except ValueError:
                pass
            try:
                self.esthPanel.cbMS.SetSelection(MSChoices.index(str(plotStyle.get('MarkerSize','2'))))
            except ValueError:
                pass
            try:
                matplotlib_rc('font', **{'size': int(plotStyle.get('Font', '11'))})
            except Exception:
                pass
        # Restore 3D mode first (switches cbCurveType items, shows/hides ctrl3DPanel)
        view3D = data.get('view3D', False)
        self.colorPanel.cb3D.SetValue(view3D)
        self.set3DMode(view3D, redraw=False)
        # Restore cbCurveType value (handles both old integer index and new string format)
        curveType = data.get('curveType', None)
        if view3D:
            _choices = ['Scatter', 'Surf']
            if isinstance(curveType, str) and curveType in _choices:
                self.cbCurveType.SetSelection(_choices.index(curveType))
            elif data.get('plot3D_type') in _choices:
                self.cbCurveType.SetSelection(_choices.index(data['plot3D_type']))
            else:
                self.cbCurveType.SetSelection(0)
        else:
            _2d_choices  = ['Plain', 'LS', 'Markers', 'Mix']
            _2dZ_choices = ['Scatter', 'Scatter+Line']
            if isinstance(curveType, str) and curveType in _2dZ_choices:
                # Saved while in 2DZ mode – store for when setZMode activates it
                self._2dZ_curve_type_sel = _2dZ_choices.index(curveType)
                # Leave combo in plain-2D for now; setZMode will switch if Z data present
                self.cbCurveType.SetSelection(self._2d_curve_type_sel)
            elif isinstance(curveType, str) and curveType in _2d_choices:
                self.cbCurveType.SetSelection(_2d_choices.index(curveType))
            elif isinstance(curveType, int):
                self.cbCurveType.SetSelection(min(curveType, len(_2d_choices) - 1))
            else:
                self.cbCurveType.SetSelection(1)  # default LS
        # Restore 3D extra options
        if hasattr(self, 'cbLogZ'):
            self.cbLogZ.SetValue(data.get('logZ', False))
        if hasattr(self, 'cbFlipZ'):
            self.cbFlipZ.SetValue(data.get('flipZ', False))
        # Store pending camera state so set_subplots applies it after redraw
        self.colorPanel._pending_elev = data.get('view3D_elev')
        self.colorPanel._pending_azim = data.get('view3D_azim')
        self.colorPanel._pending_hide = data.get('view3D_hide')
        # R1 – Spectral / FFT panel
        spc = data.get('spectral', {})
        if spc:
            _spc_types    = ['PSD', 'f x PSD', 'Amplitude']
            _spc_typeX    = ['1/x', '2pi/x', 'x']
            _spc_avg      = ['None', 'Welch', 'Binning']
            _spc_avgwin   = ['Hamming', 'Hann', 'Rectangular']
            try:
                self.spcPanel.cbType.SetSelection(_spc_types.index(spc.get('yType', 'PSD')))
            except ValueError:
                pass
            try:
                self.spcPanel.cbTypeX.SetSelection(_spc_typeX.index(spc.get('xType', '1/x')))
            except ValueError:
                pass
            try:
                self.spcPanel.cbAveraging.SetSelection(_spc_avg.index(spc.get('avgMethod', 'Welch')))
            except ValueError:
                pass
            try:
                self.spcPanel.cbAveragingMethod.SetSelection(_spc_avgwin.index(spc.get('avgWindow', 'Hamming')))
            except ValueError:
                pass
            self.spcPanel.cbDetrend.SetValue(spc.get('bDetrend', False))
            self.spcPanel.scP2.SetValue(int(spc.get('nExp', 11)))
            self.spcPanel.tMaxFreq.SetValue(str(spc.get('xlim', '-1')))
        # R2 – Compare panel
        cmp = data.get('compare', {})
        if cmp:
            _cmp_types = ['Relative', '|Relative|', 'Ratio', 'Absolute', 'Y-Y']
            try:
                self.cmpPanel.rbType.SetSelection(_cmp_types.index(cmp.get('type', 'Relative')))
            except ValueError:
                pass
        # R3 – MinMax panel
        mmx = data.get('minmax', {})
        if mmx:
            self.mmxPanel.cbyMinMax.SetValue(mmx.get('yScale', True))
            self.mmxPanel.cbxMinMax.SetValue(mmx.get('xScale', False))
            _mmx_centers = ['None', 'Mid=0', 'Mid=ref', 'Mean=0', 'Mean=ref']
            try:
                self.mmxPanel.cbyMean.SetSelection(_mmx_centers.index(mmx.get('yCenter', 'None')))
            except ValueError:
                pass
        # R4 – PDF panel
        pdf = data.get('pdf', {})
        if pdf:
            self.pdfPanel.scBins.SetValue(int(pdf.get('nBins', 51)))
            self.pdfPanel.cbSmooth.SetValue(pdf.get('smooth', False))
        # R5 – Polar panel
        pol = data.get('polar', {})
        if pol:
            _pol_bins  = ['None', '12', '36', '60', '180', '360']
            _pol_about = ['x (from z, y hori flip, z vert)', 'z (from x, x hori, y vert)']
            self.polPanel.cbPolarDeg.SetValue(pol.get('Deg', True))
            self.polPanel.cbPolarSameMean.SetValue(pol.get('SameMean', False))
            try:
                self.polPanel.cbPolarBins.SetSelection(_pol_bins.index(str(pol.get('Bins', 'None'))))
            except ValueError:
                pass
            try:
                self.polPanel.cbPolarAbout.SetSelection(_pol_about.index(pol.get('About', _pol_about[0])))
            except ValueError:
                pass
        # R9 – Axis limits
        axisLimits = data.get('axisLimits', {})
        self.esthPanel.tXMin.SetValue(str(axisLimits.get('xmin', '')))
        self.esthPanel.tXMax.SetValue(str(axisLimits.get('xmax', '')))
        self.esthPanel.tYMin.SetValue(str(axisLimits.get('ymin', '')))
        self.esthPanel.tYMax.SetValue(str(axisLimits.get('ymax', '')))
        self.esthPanel.tZMin.SetValue(str(axisLimits.get('zmin', '')))
        self.esthPanel.tZMax.SetValue(str(axisLimits.get('zmax', '')))

    @staticmethod
    def defaultData():
        data={}
        data['CrossHair']=True
        data['Grid']=False
        plotStyle = dict()
        plotStyle['Font']           = '11'
        plotStyle['LegendFont']     = '11'
        plotStyle['LegendPosition'] = 'Upper right'
        plotStyle['LineWidth']      = '1.5'
        plotStyle['MarkerSize']     = '2'
        plotStyle['xmin']           = ''
        plotStyle['xmax']           = ''
        plotStyle['ymin']           = ''
        plotStyle['ymax']           = ''
        plotStyle['zmin']           = ''
        plotStyle['zmax']           = ''
        data['plotStyle']= plotStyle
        return data

    def onEsthToggle(self,event):
        self.esthToggle=not self.esthToggle
        self.Freeze()
        if self.esthToggle:
            self.slCtrl.Show()
            self.esthPanel.Show()
        else:
            self.slCtrl.Hide()
            self.esthPanel.Hide()
        self.plotsizer.Layout()
        self.Thaw()
        event.Skip()

    # --- Background image
    def onBgMenu(self, event):
        """Show popup menu with background image options."""
        menu = wx.Menu()
        m1 = menu.Append(wx.ID_ANY, 'Load from file...')
        m2 = menu.Append(wx.ID_ANY, 'Paste from clipboard')
        menu.AppendSeparator()
        m3 = menu.Append(wx.ID_ANY, 'Clear background')
        m3.Enable(self._bg_image is not None)
        menu.AppendSeparator()
        # Mode toggle: radio items — only one can be active at a time.
        mFixed  = menu.AppendRadioItem(wx.ID_ANY, 'Fixed (default)')
        mMoving = menu.AppendRadioItem(wx.ID_ANY, 'Moving with axes')
        mFixed.Enable(self._bg_image is not None)
        mMoving.Enable(self._bg_image is not None)
        if self._bg_image is not None:
            if self._bg_glued:
                mMoving.Check(True)
            else:
                mFixed.Check(True)
        self.Bind(wx.EVT_MENU, self.onLoadBgImage,  m1)
        self.Bind(wx.EVT_MENU, self.onPasteBgImage, m2)
        self.Bind(wx.EVT_MENU, self.onClearBgImage, m3)
        self.Bind(wx.EVT_MENU, self.onBgModeFixed,  mFixed)
        self.Bind(wx.EVT_MENU, self.onBgModeMoving, mMoving)
        self.PopupMenu(menu)
        menu.Destroy()

    def _setBgImage(self, img_array):
        """Install a new background image without touching any GUI setting.

        The image is shown filling the current plot area ('Fixed' mode), so
        AutoScale, axis limits and other plot options are left exactly as the
        user had them.
        """
        self._bg_image = img_array
        self._bg_glued = False
        self._bg_extent = None
        self._bg_display_image = None
        self._bg_axes_extent = None
        self._bg_crop_box = None
        self.redraw_same_data()

    def onLoadBgImage(self, event):
        """Load a background image from file."""
        exts_pattern = ';'.join('*' + e for e in IMAGE_EXTS)
        wildcard = 'Image files ({0})|{0}|All files (*.*)|*.*'.format(exts_pattern)
        with wx.FileDialog(self, 'Load background image', wildcard=wildcard,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
        try:
            img = mpimg.imread(path)
            self._setBgImage(img)
            # Track in the Recent Files menu
            top = self.GetTopLevelParent()
            if hasattr(top, '_track_recent'):
                top._track_recent(path)
        except Exception as e:
            Error(self, 'Failed to load image:\n{}'.format(str(e)))

    def onPasteBgImage(self, event):
        """Paste a background image from the clipboard."""
        bmp_data = wx.BitmapDataObject()
        success = False
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(bmp_data)
            wx.TheClipboard.Close()
        if not success:
            Warn(self, 'No image found in clipboard.')
            return
        bmp = bmp_data.GetBitmap()
        img = bmp.ConvertToImage()
        width, height = img.GetWidth(), img.GetHeight()
        buf = bytes(img.GetDataBuffer())
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3).copy()
        # Normalize to 0-1 float for matplotlib
        self._setBgImage(arr.astype(np.float64) / 255.0)

    def onClearBgImage(self, event):
        """Remove the background image."""
        self._bg_image = None
        self._bg_glued = False
        self._bg_extent = None
        self._bg_display_image = None
        self._bg_axes_extent = None
        self._bg_crop_box = None
        self.redraw_same_data()

    def _compute_bg_screen_lock(self, ax):
        """Given an axis currently showing the bg image (in data coords),
        compute the cropped image and the axes-fraction extent that, when
        rendered with transAxes, reproduces the currently-visible portion
        of the bg pinned to the plot rectangle.

        Returns (cropped_image, [afx0, afx1, afy0, afy1]) or (None, None)
        if the bg is not visible at all in the current viewport.
        """
        if self._bg_image is None:
            return None, None, None
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        vx0, vx1 = sorted(xlim)
        vy0, vy1 = sorted(ylim)
        # Locate the current bg artist on this axis to read its image and extent.
        bg_artist = None
        for img in ax.images:
            if getattr(img, '_is_pydatview_bg', False):
                bg_artist = img
                break
        if bg_artist is not None:
            try:
                src = np.asarray(bg_artist.get_array())
            except Exception:
                src = self._bg_image
            ext = bg_artist.get_extent()
            if bg_artist.get_transform() == ax.transData:
                bx0, bx1, by0, by1 = ext
                if bx0 > bx1: bx0, bx1 = bx1, bx0
                if by0 > by1: by0, by1 = by1, by0
            else:
                # transAxes: extent is axes-fraction; map back to data coords.
                afx0, afx1, afy0, afy1 = ext
                bx0 = vx0 + afx0 * (vx1 - vx0)
                bx1 = vx0 + afx1 * (vx1 - vx0)
                by0 = vy0 + afy0 * (vy1 - vy0)
                by1 = vy0 + afy1 * (vy1 - vy0)
        else:
            # No artist drawn yet: treat as Fixed-default (full image == viewport).
            src = self._bg_image
            bx0, bx1, by0, by1 = vx0, vx1, vy0, vy1
        ix0, ix1 = max(bx0, vx0), min(bx1, vx1)
        iy0, iy1 = max(by0, vy0), min(by1, vy1)
        if ix1 <= ix0 or iy1 <= iy0:
            return None, None, None
        # Crop fractions WITHIN the source array (cropped or full).
        col_lf = (ix0 - bx0) / (bx1 - bx0)
        col_rf = (ix1 - bx0) / (bx1 - bx0)
        # origin='upper': image row 0 is at by1 (top), row h is at by0 (bottom).
        row_tf = (by1 - iy1) / (by1 - by0)
        row_bf = (by1 - iy0) / (by1 - by0)
        h, w = src.shape[:2]
        col0 = max(0, min(w, int(round(col_lf * w))))
        col1 = max(0, min(w, int(round(col_rf * w))))
        row0 = max(0, min(h, int(round(row_tf * h))))
        row1 = max(0, min(h, int(round(row_bf * h))))
        if col1 <= col0 or row1 <= row0:
            return None, None, None
        cropped = src[row0:row1, col0:col1]
        afx0 = (ix0 - vx0) / (vx1 - vx0)
        afx1 = (ix1 - vx0) / (vx1 - vx0)
        afy0 = (iy0 - vy0) / (vy1 - vy0)
        afy1 = (iy1 - vy0) / (vy1 - vy0)
        # Compose with the existing crop box so the new crop box is expressed
        # as a fraction of the original _bg_image (regardless of whether the
        # source we just cropped was the full image or an already-cropped one).
        parent = self._bg_crop_box if self._bg_crop_box is not None \
                 else [0.0, 1.0, 0.0, 1.0]
        pa, pb, pc, pd = parent
        crop_box = [pa + col_lf * (pb - pa),
                    pa + col_rf * (pb - pa),
                    pc + row_tf * (pd - pc),
                    pc + row_bf * (pd - pc)]
        return cropped, [afx0, afx1, afy0, afy1], crop_box

    def _full_extent_from_state(self, ax):
        """Compute the data-coord extent of the FULL _bg_image needed to
        place its currently-cropped portion (described by _bg_axes_extent
        and _bg_crop_box) at exactly the screen rectangle it now occupies
        within the current viewport. Used at Fixed -> Moving transition.
        """
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        vx0, vx1 = sorted(xlim)
        vy0, vy1 = sorted(ylim)
        ae = self._bg_axes_extent if self._bg_axes_extent is not None \
             else [0.0, 1.0, 0.0, 1.0]
        afx0, afx1, afy0, afy1 = ae
        # Current cropped image's data-coord rectangle.
        dx0 = vx0 + afx0 * (vx1 - vx0)
        dx1 = vx0 + afx1 * (vx1 - vx0)
        dy0 = vy0 + afy0 * (vy1 - vy0)
        dy1 = vy0 + afy1 * (vy1 - vy0)
        cb = self._bg_crop_box if self._bg_crop_box is not None \
             else [0.0, 1.0, 0.0, 1.0]
        a, b, c, d = cb
        if (b - a) <= 0 or (d - c) <= 0:
            return [vx0, vx1, vy0, vy1]
        full_w = (dx1 - dx0) / (b - a)
        full_h = (dy1 - dy0) / (d - c)
        Dx0 = dx0 - a * full_w
        Dx1 = Dx0 + full_w
        # origin='upper': row 0 (fraction c) corresponds to data y = dy1 (top).
        Dy1 = dy1 + c * full_h
        Dy0 = Dy1 - full_h
        return [Dx0, Dx1, Dy0, Dy1]

    def _replace_bg_artists(self):
        """Remove existing bg artists on every 2D axis and re-create them
        per the current bg state (_bg_glued, _bg_extent, _bg_display_image,
        _bg_axes_extent). Used by the mode-toggle handlers so the change is
        immediate and does not require a full plot rebuild.
        """
        for ax in self.fig.axes:
            if hasattr(ax, 'set_zlim'):
                continue
            for img in list(ax.images):
                if getattr(img, '_is_pydatview_bg', False):
                    img.remove()
            if self._bg_image is None:
                continue
            if self._bg_glued and self._bg_extent is not None:
                bg_artist = ax.imshow(
                    self._bg_image, extent=self._bg_extent,
                    transform=ax.transData,
                    aspect='auto', zorder=0, origin='upper',
                    interpolation='bilinear')
            elif (self._bg_display_image is not None
                  and self._bg_axes_extent is not None):
                bg_artist = ax.imshow(
                    self._bg_display_image, extent=self._bg_axes_extent,
                    transform=ax.transAxes,
                    aspect='auto', zorder=0, origin='upper',
                    interpolation='bilinear')
            else:
                bg_artist = ax.imshow(
                    self._bg_image, extent=[0, 1, 0, 1],
                    transform=ax.transAxes,
                    aspect='auto', zorder=0, origin='upper',
                    interpolation='bilinear')
            bg_artist._is_pydatview_bg = True

    def onBgModeFixed(self, event):
        """'Fixed' (default) mode: the image is pinned to the plot rectangle.

        We snapshot the currently-visible portion of the bg and re-render
        it in axes (screen) coordinates via transAxes. From this point on,
        any axis-limit change (toolbar zoom, limits panel, autoscale) is
        independent of the bg — what the user saw at the moment of the
        switch stays pixel-identical until they switch modes again or
        change the bg image.
        """
        if self._bg_image is None or len(self.fig.axes) == 0:
            self._bg_glued = False
            self._bg_extent = None
            self._bg_display_image = None
            self._bg_axes_extent = None
            self._bg_crop_box = None
            self.canvas.draw_idle()
            return
        cropped, ax_extent, crop_box = self._compute_bg_screen_lock(
            self.fig.axes[0])
        self._bg_glued = False
        self._bg_extent = None
        self._bg_display_image = cropped
        self._bg_axes_extent = ax_extent
        self._bg_crop_box = crop_box
        self._replace_bg_artists()
        self.canvas.draw_idle()

    def onBgModeMoving(self, event):
        """'Moving with axes' mode: the image is glued to data coordinates.

        Render the FULL _bg_image at a data-coord extent chosen so the
        currently-displayed crop lands exactly where it was on screen. The
        previously-hidden portions of the bg (axis labels etc.) become
        accessible by panning/zooming the axes. As the user pans/zooms,
        the bg stays put in data space (its screen position changes
        naturally with the viewport).
        """
        if len(self.fig.axes) == 0 or self._bg_image is None:
            return
        ax = self.fig.axes[0]
        if (self._bg_axes_extent is not None
                or self._bg_crop_box is not None):
            self._bg_extent = self._full_extent_from_state(ax)
        else:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            vx0, vx1 = sorted(xlim)
            vy0, vy1 = sorted(ylim)
            self._bg_extent = [vx0, vx1, vy0, vy1]
        self._bg_glued = True
        self._bg_display_image = None
        self._bg_axes_extent = None
        self._bg_crop_box = None
        self._replace_bg_artists()
        self.canvas.draw_idle()

    def setSubplotSpacing(self, init=False, tight=False):
        """ 
        Handle default subplot spacing

        NOTE:
           - Tight fails when the ylabel is too long, especially for fft with multiplt signals
           - might need to change depending on window size/resizing
           - need to change if right axis needed 
           - this will override the user settings
        """
        if tight: 
            self.setSubplotTight(draw=False)
            return

        if init: 
            subplotsParLoc={'bottom':0.12, 'top':0.97, 'left':0.12, 'right':0.98}
            self.fig.subplots_adjust(**subplotsParLoc)
            return

        if self.subplotsPar is not None:
            if self.cbPlotMatrix.GetValue(): # TODO detect it
                self.subplotsPar['right'] = 0.98 - self.subplotsPar['left']
            # See GUIToolBox.py configure_toolbar
            self.fig.subplots_adjust(**self.subplotsPar)
            return
        else:
            self.setSubplotTight(draw=False)

    def setSubplotTight(self, draw=True):
        self.fig.tight_layout()
        self.subplotsPar = self.getSubplotSpacing()

        # --- Ensure some minimum spacing based on panel size
        if self.Size[1]<300:
            bottom=0.20
        elif self.Size[1]<350:
            bottom=0.18
        elif self.Size[1]<430:
            bottom=0.16
        elif self.Size[1]<600:
            bottom=0.13
        elif self.Size[1]<800:
            bottom=0.09
        else:
            bottom=0.07
        if self.Size[0]<300:
            left=0.22
        elif self.Size[0]<450:
            left=0.20
        elif self.Size[0]<950:
            left=0.12
        else:
            left=0.06

        self.subplotsPar['left']   = max(self.subplotsPar['left']  , left)
        self.subplotsPar['bottom'] = max(self.subplotsPar['bottom'], bottom)
        self.subplotsPar['top']    = min(self.subplotsPar['top']   , 0.97)
        self.subplotsPar['right']  = min(self.subplotsPar['right'] , 0.995)
        self.fig.subplots_adjust(**self.subplotsPar)
        if draw:
            self.canvas.draw()

    def getSubplotSpacing(self):
        try:
            params = self.fig.subplotpars
            paramsD= {}
            for key in ['left', 'bottom', 'right', 'top', 'wspace', 'hspace']:
                paramsD[key]=getattr(params, key)
            return paramsD
        except:
            return None # At Init we don't have a figure

    def plot_matrix_event(self, event):
        if self.cbSwapXY.IsChecked():
            print('[WARN] Cant have plot Matrix and Swap XY for now')
            self.cbSwapXY.SetValue(False)

        if self.infoPanel is not None:
            self.infoPanel.togglePlotMatrix(self.cbPlotMatrix.GetValue())
        self.redraw_same_data()

    def swap_event(self, event):
        if self.cbPlotMatrix.IsChecked():
            print('[WARN] Cant have plot Matrix and Swap XY for now')
            self.cbPlotMatrix.SetValue(False)
            self.infoPanel.togglePlotMatrix(False)

        self.redraw_same_data()

    def measure_event(self, event):
        if self.cbMeasure.IsChecked():
            # Can't measure and Mark points at the same time
            self.cbMarkPt.SetValue(False) 
            self.cleanMarkers()
            # We do nothing, onMouseRelease will trigger the plot and setting
        else:
            self.cleanMeasures()
        # We redraw after cleaning (measures or markers)
        self.redraw_same_data()

    def setAndPlotMeasures(self, ax, x, y, which=None):
        if which is None:
            which=[1,2]
        if not hasattr(ax, 'PD'):
            print('[WARN] Cannot measure on an empty plot')
            return
        if 1 in which:
            # Left click, measure 1 - set values, compute all intersections and plot
            self.leftMeasure.set(ax, x, y) 
            if self.infoPanel is not None:
                self.infoPanel.showMeasure1()
        if 2 in which:
            # Right click, measure 2 - set values, compute all intersections and plot
            self.rightMeasure.set(ax, x, y)
            if self.infoPanel is not None:
                self.infoPanel.showMeasure2()
        self.plotMeasures(which=which)

    def plotMeasures(self, which=None):
        if which is None:
            which=[1,2]
        ## plot them
        if 1 in which:
            self.leftMeasure.plot (self.fig.axes, self.plotData)
        if 2 in which:
            self.rightMeasure.plot(self.fig.axes, self.plotData)
        ## Update dx,dy label
        self.lbDeltaX.SetLabel(self.rightMeasure.sDeltaX(self.leftMeasure))
        self.lbDeltaY.SetLabel(self.rightMeasure.sDeltaY(self.leftMeasure))

        #if not self.cbAutoScale.IsChecked():
        #    print('>>> On Mouse Release Restore LIMITS')
        #    self._restore_limits()
        #else:
        #    print('>>> On Mouse Release Not Restore LIMITS')
        # Update label

    def cleanMeasures(self):
        # We clear
        for measure in [self.leftMeasure, self.rightMeasure]:
            measure.clear()
        if self.infoPanel is not None:
            self.infoPanel.clearMeasurements()
        # Update dx,dy label
        self.lbDeltaX.SetLabel('')
        self.lbDeltaY.SetLabel('')

    def markpt_event(self, event):

        if self.cbMarkPt.IsChecked():
            # Can't measure and Mark points at the same time
            self.cbMeasure.SetValue(False) 
            self.cleanMeasures()
            # We do nothing, onMouseRelease will trigger the plot and setting
            self.markers = [] 
        else:
            self.cleanMarkers()
        # We redraw after cleaning markesr or measures
        self.redraw_same_data()

    def plotMarkers(self):
        for marker in self.markers:
            marker.plot (self.fig.axes, self.plotData)

    def cleanMarkers(self):
        # We clear
        for marker in self.markers:
            marker.clear()
        self.markers=[]

    def redraw_event(self, event):
        self.redraw_same_data()

    def log_select(self, event):
        if self.pltTypePanel.cbPDF.GetValue():
            self.cbLogX.SetValue(False)
            self.cbLogY.SetValue(False)
        else:
            self.redraw_same_data()

    def crosshair_event(self, event):
        try:
            self.multiCursors.vertOn =self.cbXHair.GetValue()
            self.multiCursors.horizOn=self.cbXHair.GetValue()
            self.multiCursors._update()
        except:
            pass

    @property
    def sharex(self):
        return self.cbSync.IsChecked() and (not self.pltTypePanel.cbPDF.GetValue())

    def set_subplots(self,nPlots):
        # Determine if 3D view is requested
        hasZ = any(pd.z is not None for pd in self.plotData)
        use3D = hasZ and self.colorPanel.cb3D.IsChecked()
        # Creating subplots
        for ax in self.fig.axes:
            self.fig.delaxes(ax)
        sharex=None
        for i in range(nPlots):
            # Vertical stack
            if use3D:
                ax = self.fig.add_subplot(nPlots, 1, i+1, projection='3d')
                _patch_3d_ctrl_rotate(ax, self.canvas, toolbar=self.navTBTop)
                # Restore pending camera angle (set by plane buttons or view restore)
                cp = self.colorPanel
                elev = cp._pending_elev
                azim = cp._pending_azim
                hide = cp._pending_hide
                if elev is not None or azim is not None or hide is not None:
                    ColorCtrlPanel._apply_3d_plane(
                        ax,
                        elev if elev is not None else ax.elev,
                        azim if azim is not None else ax.azim,
                        hide,
                    )
            elif i==0:
                ax=self.fig.add_subplot(nPlots,1,i+1)
                # Store first axis to share with other
                if self.sharex:
                    sharex=ax
            else:
                if self.cbSwapXY.IsChecked():
                    ax=self.fig.add_subplot(nPlots,1,i+1, sharey=sharex)
                else:
                    ax=self.fig.add_subplot(nPlots,1,i+1, sharex=sharex)
            # Horizontal stack
            #self.fig.add_subplot(1,nPlots,i+1)

    def onMouseMove(self, event):
        if event.inaxes and len(self.plotData)>0:
            x, y = event.xdata, event.ydata
            ax = event.inaxes
            if hasattr(ax, 'view_init'):  # 3D axes
                try:
                    coord_str = ax.format_coord(x, y)
                    # format_coord returns e.g. "x=1.23, y=4.56, z=7.89"
                    parts = {}
                    for part in coord_str.replace(', ', ',').split(','):
                        if '=' in part:
                            k, v = part.split('=', 1)
                            parts[k.strip()] = v.strip()
                    self.lbCrossHairX.SetLabel('x = ' + parts.get('x', '...'))
                    self.lbCrossHairY.SetLabel('y = ' + parts.get('y', '...'))
                    self.lbCrossHairZ.SetLabel('z = ' + parts.get('z', '...'))
                except Exception:
                    pass
                return
            self.lbCrossHairX.SetLabel('x =' + self.formatLabelValue(x,self.plotData[0].xIsDate))
            self.lbCrossHairY.SetLabel('y =' + self.formatLabelValue(y,self.plotData[0].yIsDate))

    def onMouseClick(self, event):
        self.clickLocation = (event.inaxes, event.xdata, event.ydata)

    def onMouseRelease(self, event):
        if self.cbMeasure.GetValue():
            # --- Measures
            # Loop on axes
            for iax, ax in enumerate(self.fig.axes):
                if event.inaxes == ax:
                    x, y = event.xdata, event.ydata
                    if self.clickLocation != (ax, x, y):
                        # Ignore measurements for zoom-actions. Possibly add small tolerance.
                        # Zoom-actions disable autoscale
                        #self.cbAutoScale.SetValue(False)
                        return
                    if self.cbSwapXY.IsChecked():
                        x, y = y, x
                    if event.button == 1:
                        which =[1] # Left click, measure 1
                    elif event.button == 3:
                        which =[2] # Right click, measure 2
                    else:
                        return
                    self.setAndPlotMeasures(ax, x, y, which)
                    return # We return as soon as one ax match the click location
        elif self.cbMarkPt.GetValue():
            # --- Markers
            for iax, ax in enumerate(self.fig.axes):
                if event.inaxes == ax:
                    x, y = event.xdata, event.ydata
                    if self.clickLocation != (ax, x, y):
                        return
                    if self.cbSwapXY.IsChecked():
                        x, y = y, x
                    if event.button == 1:
                        # We add a marker
                        from pydatview.tools.colors import fColrs, python_colors
                        n = len(self.markers)
                        IDs = set([m.ID for m in self.markers])
                        All = set(np.arange(1,n+2))
                        ID = list(All.difference(IDs))[0] # Should be only of size 1
                        #marker = GUIMeasure(1, python_colors(n+1), ID=ID)
                        marker = GUIMeasure(1, fColrs(ID, cmap='darker'), ID=ID)
                        #marker = GUIMeasure(1, 'firebrick', ID=ID)
                        #GUIMeasure(2, 'darkgreen')
                        self.markers.append(marker)
                        marker.setAndPlot(self.fig.axes, ax, x, y, self.plotData)
                    elif event.button == 3:
                        # find the closest marker
                        XY = np.array([m.P_target_raw for m in self.markers])
                        i = find_closest_i(XY, (x,y))
                        # We clear it fomr the plot
                        self.markers[i].clear()
                        # We delete it
                        del self.markers[i]
                    else:
                        return

    def onDraw(self, event):
        self._store_limits()

    def formatLabelValue(self, value, isdate):
        try:
            if isdate:
                s = pretty_date(mdates.num2date(value))
            elif abs(value)<1000 and abs(value)>1e-4:
                s = '{:10.5f}'.format(value)
            else:
                s = '{:10.3e}'.format(value)
        except TypeError:
            s = '            '
        return s

    def removeTools(self, event=None, Layout=True):
        if self.toolPanel is not None:
            self.toolPanel.destroyData() # clean destroy of data (action callbacks)
        self.toolSizer.Clear(delete_windows=True) # Delete Windows
        if Layout:
            self.plotsizer.Layout()

    def showTool(self, toolName=''):
        from pydatview.plugins import TOOLS
        if toolName in TOOLS.keys():
            self.showToolPanel(panelClass=TOOLS[toolName])
        else:
            raise Exception('Unknown tool {}'.format(toolName))

    def showToolAction(self, action):
        """ Show a tool panel based on an action"""
        self.showToolPanel(panelClass=action.guiEditorClass, action=action)

    def showToolPanel(self, panelClass=None, panel=None, action=None):
        """ Show a tool panel based on a panel class (should inherit from GUIToolPanel)"""
        self.Freeze()
        self.removeTools(Layout=False)
        if panel is not None:
            self.toolPanel=panel # use the panel directly
        else:
            if action is None:
                print('NOTE: calling a panel without action')
                self.toolPanel=panelClass(parent=self) # calling the panel constructor
            else:
                self.toolPanel=panelClass(parent=self, action=action) # calling the panel constructor
                action.guiEditorObj = self.toolPanel
        self.toolSizer.Add(self.toolPanel, 0, wx.EXPAND|wx.ALL, 5)
        self.plotsizer.Layout()
        self.Thaw()


    def setPD_PDF(self,PD,c):
        """ Convert plot data to PDF data based on GUI options"""
        # ---PDF
        data = self.pdfPanel._GUI2Data()
        nBins_out= PD.toPDF(**data)
        if nBins_out != data['nBins']:
            self.pdfPanel.scBins.SetValue(data['nBins'])

    def setPD_MinMax(self, PD, firstCall=False):
        """ Convert plot data to MinMax data based on GUI options"""
        data = self.mmxPanel._GUI2Data()
        if data['yCenter'] in ['Mean=ref', 'Mid=ref']:
            if firstCall:
                try:
                    data['yRef'] = PD._y0Mean[0] # Will fail for strings
                    if np.isnan(data['yRef']): # Will fail for datetimes
                        data['yRef'] = 0
                except:
                    data['yRef'] = 0
                    print('[WARN] Fail to get yRef, setting it to 0')
                self.mmxPanel.setYRef(data['yRef']) # Update GUI
        try:
            PD.toMinMax(**data)
        except Exception as e:
            self.mmxPanel.cbxMinMax.SetValue(False)
            raise e # Used to be Warn

    def setPD_FFT(self, PD):
        """ Convert plot data to FFT data based on GUI options"""
        data = self.spcPanel._GUI2Data()
        # Convert plotdata to FFT data
        try:
            Info = PD.toFFT(**data) 
            # Trigger
            if hasattr(Info,'nExp') and Info.nExp!=data['nExp']:
                self.spcPanel.scP2.SetValue(Info.nExp)
                self.spcPanel.updateP2(Info.nExp)
        except Exception as e:
            self.spcPanel.Hide();
            self.plotsizer.Layout()
            raise e

    def setPD_Polar(self, PD, firstCall=False):
        """ Convert plot data to Polar data based on GUI options"""
        data = self.polPanel._GUI2Data()
        if data['SameMean'] and firstCall:
            try:
                data['rRef'] = PD._y0Mean[0] # Will fail for strings
                if np.isnan(data['rRef']): # Will fail for datetimes
                    data['rRef'] = 0
            except:
                data['rRef'] = 0
                print('[WARN] Fail to get yRef, setting it to 0')
            self.polPanel.setRRef(data['rRef']) # Update GUI

        PD.toPolar(**data)


    def transformPlotData(self, PD, firstCall=False):
        """" 
        Apply MinMax, PDF or FFT transform to plot based on GUI data
        """
        plotType=self.pltTypePanel.plotType()
        if plotType=='MinMax':
            self.setPD_MinMax(PD, firstCall=firstCall) 
        elif plotType=='PDF':
            self.setPD_PDF(PD, PD.c)  
        elif plotType=='FFT':
            self.setPD_FFT(PD) 
        elif plotType=='Polar':
            self.setPD_Polar(PD, firstCall=firstCall) 

    def getPlotData(self, plotType=None):
        if plotType is None:
            plotType = self.pltTypePanel.plotType()

        ID,SameCol,selMode=self.selPanel.getPlotDataSelection()

        self.selMode=selMode # we store the selection mode
        del self.plotData
        self.plotData=[]
        tabs=self.selPanel.tabList

        try:
            for i,idx in enumerate(ID):
                # Initialize each plotdata based on selected table and selected id channels
                PD = PlotData();
                PD.fromIDs(tabs, i, idx, SameCol, pipeline=self.pipeLike)
                self.transformPlotData(PD, firstCall=i==0)
                self.plotData.append(PD)
        except Exception as e:
            self.plotData=[]
            raise e

        # Show/hide colorPanel based on whether any plot has a Z/color variable
        hasZ = any(pd.z is not None for pd in self.plotData)
        if hasZ:
            self.colorPanel.Show()
        else:
            self.colorPanel.Hide()
        # Show z-limit fields when a Z variable is present (3D or color-mapped 2D)
        self.esthPanel.showZLimits(hasZ)
        # Adapt the curve-type combo for 2D+Z (only when not already in 3D mode)
        self.setZMode(hasZ and not self.colorPanel.cb3D.IsChecked())
        self.plotsizer.Layout()

    def PD_Compare(self,mode):
        """ Perform comparison of the selected PlotData, returns new plotData with the comparison. """
        sComp = self.cmpPanel.rbType.GetStringSelection()
        try:
            result = compareMultiplePD(self.plotData, mode, sComp)
            if result:  # only replace plotData when compare produced results
                self.plotData = result
            # if result is empty (e.g. only 1 series), keep plotData so it still draws
        except Exception as e:
            self.pltTypePanel.cbRegular.SetValue(True)
            raise e

    def _onPlotMatrixLeftClick(self, event):
        """Toggle plot-states from None, to left-axis, to right-axis.
            Left-click goes forwards, right-click goes backwards.
            IndexError to avoid "holes" in matrix with outer adjacent populated entries
        """
        btn = event.GetEventObject()
        label = btn.GetLabelText()
        if label == '-':
            btn.SetLabel('1')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('-')
        elif label == '1':
            btn.SetLabel('2')
        else:
            btn.SetLabel('-')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('1')
        self.redraw_same_data()

    def _onPlotMatrixRightClick(self, event):
        btn = event.GetEventObject()
        label = btn.GetLabelText()
        if label == '-':
            btn.SetLabel('2')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('-')
        elif label == '1':
            btn.SetLabel('-')
            try:
                self.infoPanel.getPlotMatrix(self.plotData, self.cbSub.IsChecked())
            except IndexError:
                btn.SetLabel('2')
        else:
            btn.SetLabel('1')
        self.redraw_same_data()

    def set_axes_lim(self, PDs, axis, plotType='Regular'):
        """ 
        It's usually faster to set the axis limits first (before plotting) 
        and disable autoscaling. This way the limits are not recomputed when plot data are added.
        Also, we already have computed the min and max, so we leverage that. 
        NOTE: 
          doesnt not work with strings
          doesnt not work for FFT and compare 

        INPUTS:
            PDs: list of plot data
        """
        # TODO option for tight axes
        def getDelta(xMin, xMax):
            delta = xMax-xMin
            if delta==0:
                delta=1
            else:
            #    if tight:
            #        delta=0
            #    else:
                delta = delta*pyplot_rc['axes.xmargin']
            return delta

        tight=False
        if plotType in ['FFT','Compare']:
            axis.autoscale(True, axis='both', tight=tight)
            return
        elif plotType =='Polar':
            axis.set_aspect('equal', adjustable='box')
            xMin=np.min([PDs[i]._xMin[0] for i in axis.iPD])
            xMax=np.max([PDs[i]._xMax[0] for i in axis.iPD])
            yMin=np.min([PDs[i]._yMin[0] for i in axis.iPD])
            yMax=np.max([PDs[i]._yMax[0] for i in axis.iPD])
            xMax =  max (abs(xMin), abs(xMax))
            yMax =  max (abs(yMin), abs(yMax))
            Max  =  max (abs(xMax), abs(yMax))
            Min = -Max
            delta = getDelta(Min, Max)
            axis.set_xlim_(Min-delta, Max+delta)
            axis.set_ylim_(Min-delta, Max+delta)
            axis.autoscale(False, axis='x', tight=False)
            axis.autoscale(False, axis='y', tight=False)
            return 

        vXString=[PDs[i].xIsString for i in axis.iPD]
        vYString=[PDs[i].yIsString for i in axis.iPD]
        if not any(vXString) and not self.cbLogX.IsChecked():
            try:
                xMin=np.min([PDs[i]._xMin[0] for i in axis.iPD])
                xMax=np.max([PDs[i]._xMax[0] for i in axis.iPD])
                delta = getDelta(xMin, xMax)
                axis.set_xlim_(xMin-delta,xMax+delta)
                axis.autoscale(False, axis='x', tight=False)
            except:
                pass
        if not any(vYString) and not self.cbLogY.IsChecked(): 
            try:
                yMin=np.min([PDs[i]._yMin[0] for i in axis.iPD])
                yMax=np.max([PDs[i]._yMax[0] for i in axis.iPD])
                delta = (yMax-yMin)
                # Old behavior
                if np.isclose(yMin,yMax): 
                    # NOTE: by using 10% of yMax we usually avoid having the "mean" written at
                    #   the top of the script
                    delta=1 if np.isclose(yMax,0) else 0.1*yMax
                else:
                    delta = delta*pyplot_rc['axes.xmargin']
#                 if delta==0:
#                     # If delta is zero, we extend the bounds to "readable" values
#                     yMean = (yMax+yMin)/2
#                     if abs(yMean)>1e-6:
#                         delta = 0.05*yMean
#                     else:
#                         delta = 1
#                 elif abs(yMin)>1e-6:
#                     delta_rel = delta/abs(yMin)
#                     if delta<1e-5:
#                         delta = 0.1
#                     elif delta_rel<1e-5:
#                         # we set a delta such that the numerical fluctuations are visible but
#                         # it's obvious that it's still a "constant" signal
#                         delta = 100*delta 
#                     else:
#                         delta = delta*pyplot_rc['axes.xmargin']
#                 else:
#                     if delta<1e-5:
#                         delta = 1
#                     else:
#                         delta = delta*pyplot_rc['axes.xmargin']
                axis.set_ylim_(yMin-delta,yMax+delta)
                axis.autoscale(False, axis='y', tight=False)
            except:
                pass

    def getPlotOptions(self, PD=None):
        # --- PlotStyles
        plotStyle = self.esthPanel._GUI2Data()

        # --- Plot options
        plot_options = dict()
        plot_options['step'] = self.cbStepPlot.IsChecked()
        plot_options['swapXY'] = self.cbSwapXY.IsChecked()
        plot_options['flipX'] = self.cbFlipX.IsChecked()
        plot_options['flipY'] = self.cbFlipY.IsChecked()
        plot_options['logX'] = self.cbLogX.IsChecked()
        plot_options['logY'] = self.cbLogY.IsChecked()
        plot_options['logZ']  = self.cbLogZ.IsChecked()  if hasattr(self, 'cbLogZ')  else False
        plot_options['flipZ'] = self.cbFlipZ.IsChecked() if hasattr(self, 'cbFlipZ') else False
        if self.cbGrid.IsChecked():
            plot_options['grid'] = {'visible': self.cbGrid.IsChecked(), 'linestyle':'-', 'linewidth':0.5, 'color':'#b0b0b0'}
        else:
            plot_options['grid'] = {'visible': False}
        plot_options['tick_params'] = {'direction':'in', 'top':True, 'right':True, 'labelright':False, 'labeltop':False, 'which':'both'}

        plot_options['lw']=plotStyle['LineWidth']
        plot_options['ms']=plotStyle['MarkerSize']
        if self.cbCurveType.Value=='Plain':
            plot_options['LineStyles'] = ['-']
            plot_options['Markers']    = ['']
        elif self.cbCurveType.Value=='LS':
            plot_options['LineStyles'] = ['-','--','-.',':']
            plot_options['Markers']    = ['']
        elif self.cbCurveType.Value=='Markers':
            plot_options['LineStyles'] = ['']
            plot_options['Markers']    = ['o','d','v','^','s']
        elif self.cbCurveType.Value=='Mix': # NOTE, can be improved
            plot_options['LineStyles'] = ['-','--', '-','-','-']
            plot_options['Markers']    = ['' ,''   ,'o','^','s']
        elif self.cbCurveType.Value in ('Scatter', 'Scatter+Line'):
            # 2DZ mode – line style choices are not used for scatter; keep defaults
            plot_options['LineStyles'] = ['-']
            plot_options['Markers']    = ['']
        else:
            # 3D mode ('Scatter'/'Surf') or unknown – use plain defaults
            plot_options['LineStyles'] = ['-']
            plot_options['Markers']    = ['']
        # 2D+Z scatter style (only meaningful when Z present and not 3D)
        plot_options['plot2DZType'] = self.cbCurveType.Value if self.cbCurveType.Value in ('Scatter', 'Scatter+Line') else 'Scatter'

        # --- Font options
        font_options      = dict()
        font_options_legd = dict()
        font_options['size']          = plotStyle['Font']
        font_options_legd['fontsize'] = plotStyle['LegendFont']
        if PD is not None:
            needChineseFont = any([pd.needChineseFont for pd in PD])
            if needChineseFont and self.specialFont is not None:
                font_options['fontproperties']=  self.specialFont
                font_options_legd['prop']     =  self.specialFont 

        return plotStyle, plot_options, font_options, font_options_legd



    def plot_all(self, autoscale=True):
        """ 
        autoscale: if True, find the limits based on the data.
                  Otherwise, the limits are restored using:
                     self._restore_limits and the variables: self.xlim_prev, self.ylim_prev
        """
        self.multiCursors=[]

        axes=self.fig.axes
        PD=self.plotData

        # --- PlotStyles
        plotType = self.pltTypePanel.plotType()
        plotStyle, plot_options, font_options, font_options_legd = self.getPlotOptions()

        # --- Loop on axes. Either use ax.iPD to chose the plot data, or rely on plotmatrix
        for axis_idx, ax_left in enumerate(axes):
            ax_right = None
            # Swap XY
            ax_left.setSwap(plot_options['swapXY'])
            # Checks
            vDate=[PD[i].yIsDate for i in ax_left.iPD]
            if any(vDate) and len(vDate)>1:
                Error(self,'Cannot plot date and other value on the same axis')
                return

            # Set limit before plot when possible, for optimization
            self.set_axes_lim(PD, ax_left, plotType)

            # Draw background image if present (not supported on 3D axes).
            # Three rendering modes:
            #   Moving       : transData with extent=_bg_extent
            #   Fixed-locked : transAxes with cropped image at _bg_axes_extent
            #   Fixed-default: transAxes with full image at [0,1,0,1]
            if self._bg_image is not None and not hasattr(ax_left, 'set_zlim'):
                if self._bg_glued and self._bg_extent is not None:
                    bg_artist = ax_left.imshow(
                        self._bg_image, extent=list(self._bg_extent),
                        transform=ax_left.transData,
                        aspect='auto', zorder=0, origin='upper',
                        interpolation='bilinear')
                elif (self._bg_display_image is not None
                      and self._bg_axes_extent is not None):
                    bg_artist = ax_left.imshow(
                        self._bg_display_image, extent=self._bg_axes_extent,
                        transform=ax_left.transAxes,
                        aspect='auto', zorder=0, origin='upper',
                        interpolation='bilinear')
                else:
                    bg_artist = ax_left.imshow(
                        self._bg_image, extent=[0, 1, 0, 1],
                        transform=ax_left.transAxes,
                        aspect='auto', zorder=0, origin='upper',
                        interpolation='bilinear')
                bg_artist._is_pydatview_bg = True

            # Actually plot
            if self.infoPanel is not None:
                pm = self.infoPanel.getPlotMatrix(PD, self.cbSub.IsChecked())
            else:
                pm = None
            __, bAllNegLeft        = self.plotSignals(ax_left, axis_idx, PD, pm, 1, plot_options, autoscale=autoscale)
            ax_right, bAllNegRight = self.plotSignals(ax_left, axis_idx, PD, pm, 2, plot_options, autoscale=autoscale)

            # Log Axes
            if plot_options['logX'] and not hasattr(ax_left, 'set_zlim'):
                try:
                    ax_left.set_xscale("log", nonpositive='clip') # latest
                except Exception:
                    try:
                        ax_left.set_xscale("log", nonposx='clip') # legacy
                    except Exception:
                        pass

            if plot_options['logY'] and not hasattr(ax_left, 'set_zlim'):
                if bAllNegLeft is False:
                    try:
                        ax_left.set_yscale("log", nonpositive='clip') # latest
                    except Exception:
                        try:
                            ax_left.set_yscale("log", nonposy='clip')
                        except Exception:
                            pass
                if bAllNegRight is False and ax_right is not None:
                    try:
                        ax_right.set_yscale("log", nonpositive='clip') # latest
                    except Exception:
                        try:
                            ax_left.set_yscale("log", nonposy='clip') # legacy
                        except Exception:
                            pass

            if not autoscale:
                user_lim = self.esthPanel.getAxisLimits()
                has_user_lim = any(v is not None for v in user_lim.values())
                if has_user_lim:
                    # User specified at least one limit: start from data-computed
                    # limits (already set by set_axes_lim), override with user values
                    for ax_i in axes:
                        cur_xlim = list(ax_i.get_xlim_())
                        cur_ylim = list(ax_i.get_ylim_())
                        if user_lim['xmin'] is not None:
                            cur_xlim[0] = user_lim['xmin']
                        if user_lim['xmax'] is not None:
                            cur_xlim[1] = user_lim['xmax']
                        if user_lim['ymin'] is not None:
                            cur_ylim[0] = user_lim['ymin']
                        if user_lim['ymax'] is not None:
                            cur_ylim[1] = user_lim['ymax']
                        ax_i.set_xlim_(cur_xlim)
                        ax_i.set_ylim_(cur_ylim)
                        # Z-axis limits (3D only). In log-z 3D mode the z
                        # values are plotted in log10 space, so the user's
                        # limits (entered in data space) must also be
                        # log-transformed to match.
                        if hasattr(ax_i, 'set_zlim'):
                            if user_lim['zmin'] is not None or user_lim['zmax'] is not None:
                                cur_zlim = list(ax_i.get_zlim())
                                u_zmin = user_lim['zmin']
                                u_zmax = user_lim['zmax']
                                if plot_options.get('logZ', False):
                                    with np.errstate(divide='ignore', invalid='ignore'):
                                        if u_zmin is not None and u_zmin > 0:
                                            u_zmin = float(np.log10(u_zmin))
                                        elif u_zmin is not None:
                                            u_zmin = None
                                        if u_zmax is not None and u_zmax > 0:
                                            u_zmax = float(np.log10(u_zmax))
                                        elif u_zmax is not None:
                                            u_zmax = None
                                if u_zmin is not None:
                                    cur_zlim[0] = u_zmin
                                if u_zmax is not None:
                                    cur_zlim[1] = u_zmax
                                ax_i.set_zlim(cur_zlim)
                else:
                    # No user limits: restore previous zoom/pan state
                    self._restore_limits()
            elif self.pltTypePanel.cbFFT.GetValue():
                # XLIM - TODO FFT ONLY NASTY
                try:
                    xlim=float(self.spcPanel.tMaxFreq.GetLineText(0))
                    if xlim>0:
                            ax_left.set_xlim_([0,xlim])
                            pd=PD[ax_left.iPD[0]]
                            I=pd.x<xlim
                            ymin = np.min([np.min(PD[ipd].y[I]) for ipd in ax_left.iPD])
                            ax_left.set_ylim_(bottom=ymin/2)
                    if self.spcPanel.cbTypeX.GetStringSelection()=='x':
                        ax_left.invert_xaxis()
                except:
                    pass

            # --- Grid
            if plotType=='Polar':
                if plot_options['grid']['visible']:
                    vr = np.unique(np.abs(ax_left.get_xticks()))
                    grid_opts = plot_options['grid'].copy()
                    del grid_opts['visible']
                    # Temporary grid, might use a Polar plot in the future...
                    th = np.linspace(0,2*np.pi, 60)
                    for r in vr:
                        ax_left.plot(r*np.cos(th), r*np.sin(th), **grid_opts)
                    ax_left.plot([-r,r],[0,0], **grid_opts)
                    ax_left.plot([0,0],[-r,r], **grid_opts)
            else:
                ax_left.grid(**plot_options['grid'])
                if ax_right is not None:
                    l = ax_left.get_ylim_()
                    l2 = ax_right.get_ylim_()
                    f = lambda x : l2[0]+(x-l[0])/(l[1]-l[0])*(l2[1]-l2[0])
                    ticks = f(ax_left.get_yticks())
                    ax_right.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
                    if len(ax_left.lines) == 0:
                        ax_left.set_yticks(ax_right.get_yticks())
                        ax_left.yaxis.set_visible(False)
                        ax_right.grid(**plot_options['grid'])
            # Flip
            if plot_options['flipX']:
                ax_left.invert_xaxis()
            if plot_options['flipY']:
                ax_left.invert_yaxis()
            if plot_options.get('flipZ', False) and hasattr(ax_left, 'invert_zaxis'):
                try:
                    ax_left.invert_zaxis()
                except Exception:
                    pass

            # TODO put this in set_axes_lim
            if plotType=='Compare':
                if self.cmpPanel.rbType.GetStringSelection()=='Y-Y':
                    xmin,xmax=ax_left.get_xlim_()

            # Ticks
            ax_left.tick_params(**plot_options['tick_params'])
            if ax_right is not None:
                ax_right.tick_params(**plot_options['tick_params'])

            # Labels
            yleft_labels = []
            yright_labels = []
            yleft_legends = []
            yright_legends = []
            if pm is None:
                yleft_labels = unique([PD[i].sy for i in ax_left.iPD])
                if axis_idx == 0:
                    yleft_legends = unique([PD[i].syl for i in ax_left.iPD])
            else:
                for signal_idx in range(len(PD)):
                    if pm[signal_idx][axis_idx] == 1:
                        yleft_labels.append(PD[signal_idx].sy)
                        yleft_legends.append(PD[signal_idx].syl)
                    elif pm[signal_idx][axis_idx] == 2:
                        yright_labels.append(PD[signal_idx].sy)
                        yright_legends.append(PD[signal_idx].syl)
                yleft_labels = unique(yleft_labels)
                yright_labels = unique(yright_labels)
                yleft_legends = unique(yleft_legends)
                yright_legends = unique(yright_legends)

            if len(yleft_labels) > 0 and len(yleft_labels) <= 3:
                ax_left.set_ylabel(' and '.join(yleft_labels), **font_options)
            elif ax_left is not None:
                ax_left.set_ylabel('')
            if len(yright_labels) > 0 and len(yright_labels) <= 3:
                ax_right.set_ylabel(' and '.join(yright_labels), **font_options)
            elif ax_right is not None:
                ax_right.set_ylabel('')
            # Z label for 3D plots
            if hasattr(ax_left, 'set_zlabel'):
                z_labels = unique([PD[i].sz for i in ax_left.iPD if PD[i].z is not None])
                if len(z_labels) > 0 and len(z_labels) <= 3:
                    ax_left.set_zlabel(' and '.join(z_labels), **font_options)

            # Legends
            lgdLoc = plotStyle['LegendPosition'].lower()
            if (self.pltTypePanel.cbCompare.GetValue() or 
                ((len(yleft_legends) + len(yright_legends)) > 1)):
                if lgdLoc !='none':
                    if len(yleft_legends) > 0:
                        ax_left.legend(fancybox=False, loc=lgdLoc, **font_options_legd)
                if ax_right is not None and len(yright_legends) > 0:
                    ax_right.legend(fancybox=False, loc=4, **font_options_legd)
            elif len(axes)>1 and len(axes)==len(PD):
                # TODO: can this be removed? If there is only one unique signal
                # per subplot, normally only ylabel is displayed and no legend.
                # Special case when we have subplots and all plots have the same label
                if lgdLoc !='none':
                    usy = unique([pd.sy for pd in PD])
                    if len(usy)==1:
                        for ax in axes:
                            ax.legend(fancybox=False, loc=lgdLoc, **font_options_legd)

        # --- End loop on axes
        # --- Measure: Done as an overlay in plotMeasures

        # --- xlabel
        #axes[-1].set_xlabel(PD[axes[-1].iPD[0]].sx, **font_options)
        axes[-1].set_xlabel(PDL_xlabel(PD), **font_options)

        #print('sy :',[pd.sy for pd in PD])
        #print('syl:',[pd.syl for pd in PD])

        # --- Cursors for each individual plot
        # NOTE: cursors needs to be stored in the object!
        #for ax_left in self.fig.axes:
        #    self.cursors.append(MyCursor(ax_left,horizOn=True, vertOn=False, useblit=True, color='gray', linewidth=0.5, linestyle=':'))
        # Vertical cusor for all, commonly (not supported for 3D axes)
        bXHair = self.cbXHair.GetValue()
        hasZ = any(pd.z is not None for pd in PD)
        use3D = hasZ and self.colorPanel.cb3D.IsChecked()
        if not use3D:
            try:
                self.multiCursors = MyMultiCursor(self.canvas, tuple(self.fig.axes), useblit=True, horizOn=bXHair, vertOn=bXHair, color='gray', linewidth=0.5, linestyle=':')
            except Exception:
                pass

    def plotSignals(self, ax, axis_idx, PD, pm, left_right, opts, autoscale=True):
        axis = None
        bAllNeg = True
        if pm is None:
            loop_range = ax.iPD
        else:
            loop_range = range(len(PD))

        # Gather color-panel options once
        colorOpts = self.colorPanel._GUI2Data()
        colormap     = colorOpts['colormap']
        showColorBar = colorOpts['colorbar']
        use3D        = colorOpts['view3D']
        plot3DType   = colorOpts.get('plot3DType', 'Scatter')
        logZ         = opts.get('logZ', False)
        flipZ        = opts.get('flipZ', False)

        # --- Pre-compute shared Z normalisation across all Z-coloured signals on this axis
        # This ensures consistent colours and a single correct colorbar for all signals.
        # NOTE: z_norm must be built regardless of `showColorBar`, because it
        # also controls the color mapping of the scatter/surf calls. If we
        # only built it when the colorbar is on, disabling the colorbar would
        # silently drop the user's zmin/zmax limits.
        z_norm = None
        z_label_combined = ''
        _z_signals_pd = []   # PlotData objects that will be plotted with Z coloring
        for signal_idx in loop_range:
            will_plot = (
                (left_right == 1 and (pm is None or pm[signal_idx][axis_idx] == left_right)) or
                (left_right == 2 and pm is not None and pm[signal_idx][axis_idx] == left_right)
            )
            if will_plot:
                pd_i = PD[signal_idx]
                # Only include Z-coloured signals where the Z array still
                # aligns with the plotted X/Y. After FFT/PDF/MinMax/Polar
                # transforms, pd.x and pd.y are reshaped (often shorter) but
                # pd.z is left at its original length. Plotting colour in
                # that case would error silently and leave a stray colorbar.
                if (pd_i.z is not None
                        and not pd_i.zIsString
                        and not getattr(pd_i, 'zIsDate', False)
                        and hasattr(pd_i, 'x') and pd_i.x is not None
                        and len(pd_i.z) == len(pd_i.x)):
                    _z_signals_pd.append(pd_i)

        if _z_signals_pd:
            import matplotlib.colors as mcolors
            all_z_parts = []
            z_label_parts = []
            for pd_i in _z_signals_pd:
                z_vals = np.asarray(pd_i.z, dtype=float)
                if logZ:
                    with np.errstate(divide='ignore', invalid='ignore'):
                        z_vals = np.log10(z_vals)
                all_z_parts.append(z_vals)
                z_label_parts.append(pd_i.sz)
            all_z = np.concatenate(all_z_parts)
            finite_z = all_z[np.isfinite(all_z)]
            # Start from data-driven vmin/vmax (if any finite data)
            z_vmin = None
            z_vmax = None
            if len(finite_z) > 0:
                z_vmin = float(np.min(finite_z))
                z_vmax = float(np.max(finite_z))
            # Override with user-specified z-limits if provided.
            # Only honored when AutoScale is off, matching the x/y/z handling
            # in plot_all(); otherwise stale values in the zmin/zmax fields
            # would desynchronise the colorbar from the data-driven axes.
            # In log-z mode the data was transformed with log10 above, so
            # the user's limits (entered in data space) must also be log10'd.
            if not autoscale:
                user_lim = self.esthPanel.getAxisLimits()
                u_zmin = user_lim['zmin']
                u_zmax = user_lim['zmax']
                if logZ:
                    with np.errstate(divide='ignore', invalid='ignore'):
                        if u_zmin is not None and u_zmin > 0:
                            u_zmin = float(np.log10(u_zmin))
                        elif u_zmin is not None:
                            u_zmin = None  # invalid: drop
                        if u_zmax is not None and u_zmax > 0:
                            u_zmax = float(np.log10(u_zmax))
                        elif u_zmax is not None:
                            u_zmax = None  # invalid: drop
                if u_zmin is not None:
                    z_vmin = u_zmin
                if u_zmax is not None:
                    z_vmax = u_zmax
            # Ensure a valid pair. Handle edge cases:
            # - inverted user limits (zmin > zmax): swap silently
            # - constant Z data (zmin == zmax): pad by a small epsilon so
            #   Normalize doesn't collapse to a single colour
            if z_vmin is not None and z_vmax is not None:
                if z_vmin > z_vmax:
                    z_vmin, z_vmax = z_vmax, z_vmin
                if z_vmin == z_vmax:
                    eps = max(abs(z_vmin), 1.0) * 1e-6
                    z_vmin -= eps
                    z_vmax += eps
                z_norm = mcolors.Normalize(vmin=z_vmin, vmax=z_vmax)
            elif z_vmin is not None or z_vmax is not None:
                # Partial limits — build norm with what we have
                z_norm = mcolors.Normalize(vmin=z_vmin, vmax=z_vmax)
            z_label_combined = ' / '.join(unique(z_label_parts))
            if logZ:
                z_label_combined = 'log\u2081\u2080(' + z_label_combined + ')'

        iPlot = -1
        _colorbar_added = False  # show colorbar at most once per axis
        for signal_idx in loop_range:
            do_plot = False
            if left_right == 1 and (pm is None or pm[signal_idx][axis_idx] == left_right):
                do_plot = True
                axis = ax
            elif left_right == 2 and pm is not None and pm[signal_idx][axis_idx] == left_right:
                do_plot = True
                if axis is None:
                    axis = ax.twinx()
                    ax.set_zorder(axis.get_zorder()+1)
                    ax.patch.set_visible(False)
                    axis._get_lines.prop_cycler = ax._get_lines.prop_cycler
            pd=PD[signal_idx]
            if do_plot:
                iPlot+=1
                # Only treat as Z-coloured if z is present AND aligned with x
                # (transforms like FFT/PDF reshape x but not z).
                hasZ = (pd.z is not None
                        and not pd.zIsString
                        and not getattr(pd, 'zIsDate', False)
                        and pd.x is not None
                        and len(pd.z) == len(pd.x))
                if hasZ and use3D:
                    # 3D plot: x, y, z as spatial axes
                    # Apply log-z via data transformation (Axes3D does not support set_zscale)
                    z_plot = np.asarray(pd.z, dtype=float)
                    if logZ:
                        with np.errstate(divide='ignore', invalid='ignore'):
                            z_plot = np.log10(z_plot)
                    # NOTE: flipZ is applied once per axis after the signal
                    # loop, NOT here. invert_zaxis() toggles state, so calling
                    # it per-signal would cancel out for an even number of
                    # Z-coloured signals.
                    try:
                        if plot3DType == 'Surf':
                            sc = axis.plot_trisurf(pd.x, pd.y, z_plot, cmap=colormap, alpha=0.85,
                                                   norm=z_norm)
                        else:
                            sc = axis.scatter(pd.x, pd.y, z_plot, label=pd.syl,
                                              s=opts['ms']**2, cmap=colormap, c=z_plot, norm=z_norm)
                    except Exception:
                        try:
                            axis.scatter(pd.x, pd.y, z_plot, label=pd.syl, s=opts['ms']**2)
                        except Exception:
                            pass
                    try:
                        bAllNeg = bAllNeg and all(pd.y<=0)
                    except Exception:
                        pass
                elif hasZ:
                    # 2D scatter coloured by Z variable – use shared norm for consistent colours
                    z_color = np.asarray(pd.z, dtype=float)
                    if logZ:
                        with np.errstate(divide='ignore', invalid='ignore'):
                            z_color = np.log10(z_color)
                    try:
                        if opts.get('plot2DZType') == 'Scatter+Line':
                            axis.plot(pd.x, pd.y, color='#808080', alpha=0.4,
                                      lw=opts['lw'], zorder=1)
                        sc = axis.scatter(pd.x, pd.y, c=z_color, cmap=colormap,
                                          label=pd.syl, s=opts['ms']**2, norm=z_norm, zorder=2)
                    except Exception:
                        try:
                            axis.scatter(pd.x, pd.y, label=pd.syl, s=opts['ms']**2)
                        except Exception:
                            pass
                    try:
                        bAllNeg = bAllNeg and all(pd.y<=0)
                    except Exception:
                        pass
                else:
                    # --- styling per plot
                    if len(pd.x)==1:
                        marker='o'; ls=''
                    else:
                        # TODO allow PlotData to override for "per plot" options in the future
                        marker = opts['Markers'][np.mod(iPlot,len(opts['Markers']))]
                        ls     = opts['LineStyles'][np.mod(iPlot,len(opts['LineStyles']))]
                    if opts['step']:
                        plot = axis.step
                    else:
                        plot = axis.plot
                    plot(pd.x,pd.y,label=pd.syl,ms=opts['ms'], lw=opts['lw'], marker=marker, ls=ls)
                    try:
                        bAllNeg = bAllNeg and all(pd.y<=0)
                    except:
                        pass # Dates or strings

        # --- Single colorbar for all Z-coloured signals on this axis.
        # Skip when z_norm is None (no finite z data and no user limits),
        # otherwise ScalarMappable would build a misleading default 0..1 bar.
        # Also skip when plotSignals already added one on this physical
        # subplot (e.g. twinx right axis coming in after the left axis).
        # Both bars would crowd the same subplot with effectively the same
        # information for the user.
        already = getattr(ax, '_colorbar_added', False)
        if (showColorBar and _z_signals_pd and not _colorbar_added
                and z_norm is not None and axis is not None and not already):
            try:
                import matplotlib.cm as mcm, matplotlib.colors as mcolors
                sm = mcm.ScalarMappable(norm=z_norm, cmap=colormap)
                sm.set_array([])
                if use3D:
                    self.fig.colorbar(sm, ax=axis, label=z_label_combined, shrink=0.7, pad=0.1)
                else:
                    self.fig.colorbar(sm, ax=axis, label=z_label_combined)
                _colorbar_added = True
                try:
                    ax._colorbar_added = True
                except Exception:
                    pass
            except Exception:
                pass

        return axis, bAllNeg
            
    def findPlotMode(self,PD):
        uTabs = unique([pd.it for pd in PD])
        usy   = unique([pd.sy for pd in PD])
        uiy   = unique([pd.iy for pd in PD])
        if len(uTabs)<=0:
            raise Exception('No Table. Contact developer')
        if len(uTabs)==1:
            mode='1Tab_nCols'
        else:
            if PD[0].SameCol:
                mode='nTabs_SameCols'
            else:
                # Now that we allow multiple selections detecting "simColumns" is more difficult 
                if len(uTabs) == len(PD):
                    mode='nTabs_1Col'
                elif self.selMode=='simColumnsMode':
                    mode='nTabs_SimCols'
                else:
                    mode='nTabs_mCols'
        return mode

    def findSubPlots(self,PD,mode):
        uTabs = unique([pd.it for pd in PD])
        usy   = unique([pd.sy for pd in PD])
        bSubPlots = self.cbSub.IsChecked()
        bCompare  = self.pltTypePanel.cbCompare.GetValue() # NOTE bCompare somehow always 1Tab_nCols
        nSubPlots=1
        spreadBy='none'
        if self.infoPanel is not None:
            self.infoPanel.setTabMode(mode) # TODO get rid of me
        if mode=='1Tab_nCols':
            if bSubPlots:
                if bCompare or len(uTabs)==1:
                    if self.infoPanel is not None:
                        nSubPlots = self.infoPanel.getNumberOfSubplots(PD, bSubPlots)
                    else:
                        nSubPlots=len(usy)
                else:
                    nSubPlots=len(usy)
                spreadBy='iy'
        elif mode=='nTabs_SameCols':
            if bSubPlots:
                if bCompare:
                    print('>>>TODO ',mode,len(usy),len(uTabs))
                else:
                    if len(usy)==1:
                        # Temporary hack until we have an option for spread by tabs or col
                        nSubPlots=len(uTabs)
                        spreadBy='it'
                    else:
                        nSubPlots=len(usy)
                        spreadBy='iy'
        elif mode=='nTabs_SimCols':
            if bSubPlots:
                if bCompare:
                    print('>>>TODO ',mode,len(usy),len(uTabs))
                else:
                    nSubPlots=int(len(PD)/len(uTabs))
                    spreadBy='mod-ip'
        elif mode=='nTabs_mCols':
            if bSubPlots:
                if bCompare:
                    print('>>>TODO ',mode,len(usy),len(uTabs))
                else:
                    if bCompare or len(uTabs)==1:
                        nSubPlots = self.infoPanel.getNumberOfSubplots(PD, bSubPlots)
                    else:
                        nSubPlots=len(PD)
                    spreadBy='mod-ip'
        elif mode=='nTabs_1Col':
            if bSubPlots:
                if bCompare:
                    print('>>> TODO',mode,len(uTabs))
                else:
                    nSubPlots=len(uTabs)
                    spreadBy='it'
        else:
            raise Exception('Unknown mode, contact developer.')
        return nSubPlots,spreadBy

    def distributePlots(self,mode,nSubPlots,spreadBy):
        """ Assigns plot data to axes and axes to plot data """
        axes=self.fig.axes

        # Link plot data to axes
        if nSubPlots==1 or spreadBy=='none':
            axes[0].iPD=[i for i in range(len(self.plotData))]
        else:
            for ax in axes:
                ax.iPD=[]
            PD=self.plotData
            uTabs=unique([pd.it for pd in PD])
            uiy=unique([pd.iy for pd in PD])
            if spreadBy=='iy':
                for ipd,pd in enumerate(PD):
                    i=uiy.index(pd.iy)
                    if i < len(axes):
                        axes[i].iPD.append(ipd)
            elif spreadBy=='it':
                for ipd,pd in enumerate(PD):
                    i=uTabs.index(pd.it)
                    axes[i].iPD.append(ipd)
            elif spreadBy=='mod-ip':
                for ipd,pd in enumerate(PD):
                    i=np.mod(ipd, nSubPlots)
                    axes[i].iPD.append(ipd)
            else:
                raise Exception('Wrong spreadby value')
        # Use PD
        for ax in axes:
            ax.PD=[self.plotData[i] for i in ax.iPD]

    def setLegendLabels(self,mode):
        """ Set labels for legend """
        if mode=='1Tab_nCols':
            for pd in self.plotData:
                if self.pltTypePanel.cbMinMax.GetValue():
                    pd.syl = no_unit(pd.sy)
                else:
                    pd.syl = pd.sy

        elif mode=='nTabs_SameCols':
            for pd in self.plotData:
                pd.syl=pd.st

        elif mode=='nTabs_1Col':
            usy=unique([pd.sy for pd in self.plotData])
            if len(usy)==1:
                for pd in self.plotData:
                    pd.syl=pd.st
            else:
                for pd in self.plotData:
                    if self.pltTypePanel.cbMinMax.GetValue():
                        pd.syl=no_unit(pd.sy)
                    else:
                        pd.syl=pd.sy #pd.syl=pd.st + ' - '+pd.sy
        elif mode=='nTabs_SimCols':
            bSubPlots = self.cbSub.IsChecked()
            if bSubPlots: # spread by table name
                for pd in self.plotData:
                    pd.syl=pd.st
            else:
                for pd in self.plotData:
                    pd.syl=pd.st + ' - '+pd.sy
        elif mode=='nTabs_mCols':
            usy=unique([pd.sy for pd in self.plotData])
            bSubPlots = self.cbSub.IsChecked()
            if bSubPlots and len(usy)==1: # spread by table name
                for pd in self.plotData:
                    pd.syl=pd.st
            else:
                for pd in self.plotData:
                    pd.syl=pd.st + ' - '+pd.sy
        else:
            raise Exception('Unknown mode {}'.format(mode))


    def empty(self):
        self.cleanPlot()

    def clean_memory(self):
        if hasattr(self,'plotData'):
            del self.plotData
            self.plotData=[]
            for ax in self.fig.axes:
                ax.iPD=[]
                self.fig.delaxes(ax)
            gc.collect()

    def clean_memory_plot(self):
        pass

    def cleanPlot(self):
        for ax in self.fig.axes:
            if hasattr(ax,'iPD'):
                del ax.iPD
            self.fig.delaxes(ax)
        gc.collect()
        self.fig.add_subplot(111)
        ax = self.fig.axes[0]
        ax.set_axis_off()
        #ax.plot(1,1)
        self.canvas.draw()
        gc.collect()

    def load_and_draw(self):
        """ Full draw event:
          - Get plot data based on selection
          - Plot them
          - Trigger changes to infoPanel

        """
        if self.plotDone:
            self.subplotsPar = self.getSubplotSpacing()
        else:
            self.subplotsPar = None
        self.clean_memory()
        self.getPlotData()
        if len(self.plotData)==0: 
            self.cleanPlot();
            return
        mode=self.findPlotMode(self.plotData)
        if self.pltTypePanel.cbCompare.GetValue():
            self.PD_Compare(mode)
            if len(self.plotData)==0: 
                self.cleanPlot();
                return
        self.redraw_same_data()
        if self.infoPanel is not None:
            self.infoPanel.showStats(self.plotData,self.pltTypePanel.plotType())
        self.plotDone=True

    def redraw_same_data(self, force_autoscale=False):
        """ 
         - force_autoscale: if True, for the plot area to autoscale
                This is used when the user click on "Home"

        """
        if len(self.plotData)==0: 
            self.cleanPlot();
            return
        elif len(self.plotData) == 1:
            if self.plotData[0].xIsString or self.plotData[0].yIsString: 
                # or self.plotData[0].xIsDate or self.plotData[0].yIsDate:
                self.cbAutoScale.SetValue(True)
            else:
                if len(self.xlim_prev)==0: # Might occur if some date didn't plot before (e.g. strings)
                    self.cbAutoScale.SetValue(True)
                # KEEP ME below, check if plot data is within a given rectangle
                # If no plot data is present in the window 
                #elif not rectangleOverlap(self.plotData[0]._xMin[0], self.plotData[0]._yMin[0], 
                #            self.plotData[0]._xMax[0], self.plotData[0]._yMax[0],
                #            self.xlim_prev[0][0], self.ylim_prev[0][0], 
                #            self.xlim_prev[0][1], self.ylim_prev[0][1]):
                #    self.cbAutoScale.SetValue(True)

        mode=self.findPlotMode(self.plotData)
        nPlots,spreadBy=self.findSubPlots(self.plotData,mode)

        self.clean_memory_plot()
        self.set_subplots(nPlots)
        self.distributePlots(mode,nPlots,spreadBy)
        self.setSubplotSpacing()

        if not self.pltTypePanel.cbCompare.GetValue():
            self.setLegendLabels(mode)

        autoscale = (self.cbAutoScale.IsChecked()) or (force_autoscale)
        self.plot_all(autoscale=autoscale)
        self.plotMarkers()
        self.canvas.draw()


    def _store_limits(self):
        self.xlim_prev = []
        self.ylim_prev = []
        self.zlim_prev = []
        self.view3d_prev = []
        for ax in self.fig.axes:
            try:
                self.xlim_prev.append(ax.get_xlim_())
                self.ylim_prev.append(ax.get_ylim_())
            except AttributeError:
                self.xlim_prev.append((0, 1))
                self.ylim_prev.append((0, 1))
            # Capture 3D-only state so redraws don't silently discard it.
            if hasattr(ax, 'set_zlim'):
                try:
                    self.zlim_prev.append(tuple(ax.get_zlim()))
                except Exception:
                    self.zlim_prev.append(None)
            else:
                self.zlim_prev.append(None)
            if hasattr(ax, 'view_init'):
                try:
                    self.view3d_prev.append((float(ax.elev), float(ax.azim)))
                except Exception:
                    self.view3d_prev.append(None)
            else:
                self.view3d_prev.append(None)
        # Mirror the latest interactive rotation back into the pending slots
        # so that the next set_subplots (which rebuilds the 3D axes from
        # scratch) keeps the user's view angle instead of snapping back to
        # matplotlib's default. Only copy the first 3D axis — that's what the
        # existing view-save path does.
        for vs in self.view3d_prev:
            if vs is not None:
                try:
                    self.colorPanel._pending_elev = vs[0]
                    self.colorPanel._pending_azim = vs[1]
                except Exception:
                    pass
                break

    def _restore_limits(self):
        axes = list(self.fig.axes)
        for i, ax in enumerate(axes):
            if i >= len(self.xlim_prev):
                break
            try:
                ax.set_xlim_(self.xlim_prev[i])
                ax.set_ylim_(self.ylim_prev[i])
            except AttributeError:
                pass
            if (hasattr(ax, 'set_zlim')
                    and i < len(self.zlim_prev)
                    and self.zlim_prev[i] is not None):
                try:
                    ax.set_zlim(self.zlim_prev[i])
                except Exception:
                    pass
            if (hasattr(ax, 'view_init')
                    and i < len(self.view3d_prev)
                    and self.view3d_prev[i] is not None):
                try:
                    elev, azim = self.view3d_prev[i]
                    ax.view_init(elev=elev, azim=azim)
                except Exception:
                    pass

if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table,TableList
    from pydatview.Tables import TableList
    from pydatview.GUISelectionPanel import SelectionPanel

    # --- Data
    tabList   = TableList.createDummy(1)
    app = wx.App(False)
    self=wx.Frame(None,-1,"GUI Plot Panel Demo")

    # --- Panels
    self.selPanel  = SelectionPanel(self, tabList, mode='auto')
    self.plotPanel = PlotPanel(self, self.selPanel)
    self.plotPanel.load_and_draw() # <<< Important
    self.selPanel.setRedrawCallback(self.plotPanel.load_and_draw) #  Binding the two

    # --- Finalize GUI
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(self.selPanel ,0, flag = wx.EXPAND|wx.ALL,border = 5)
    sizer.Add(self.plotPanel,1, flag = wx.EXPAND|wx.ALL,border = 5)
    self.SetSizer(sizer)
    self.Center()
    self.SetSize((900, 600))
    self.Show()
    app.MainLoop()


