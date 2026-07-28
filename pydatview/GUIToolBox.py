
import wx
import matplotlib
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.widgets import Cursor, MultiCursor, Widget
# from matplotlib.widgets import AxesWidget

def GetKeyString(evt):
    """ returns a string describing the key combination being pressed """
    keyMap = {}
    keyMap[wx.WXK_TAB]    = 'TAB'
    keyMap[wx.WXK_ESCAPE] = 'ESCAPE'
    keyMap[wx.WXK_RETURN] = 'RETURN'

    keycode = evt.GetKeyCode()
    keyname = keyMap.get(keycode, None)
    modifiers = ""
    for mod, ch in ((evt.ControlDown(), 'Ctrl+'),
                    (evt.AltDown(),     'Alt+'),
                    (evt.ShiftDown(),   'Shift+'),
                    (evt.MetaDown(),    'Meta+')):
        if mod:
            modifiers += ch

    if keyname is None:
        if 27 < keycode < 256:
            keyname = chr(keycode)
        else:
            keyname = str(keycode)
    return modifiers + keyname

# --------------------------------------------------------------------------------}
# --- Toolbar utils for backwards compatibilty
# --------------------------------------------------------------------------------{


def TBAddCheckTool(tb,label,bitmap,callback=None,bitmap2=None):
    try:
        tl = tb.AddCheckTool( -1, bitmap1=bitmap, label=label )
        if callback is not None:
            tb.Bind(wx.EVT_TOOL, callback, tl)
        return tl
    except:
        pass

    tl = tb.AddLabelTool( -1, bitmap=bitmap, label=label )
    if callback is not None:
        tb.Bind(wx.EVT_TOOL, callback, tl)
    return tl

def TBAddTool(tb, label, defaultBitmap=None, callback=None, Type=None):
    """ Adding a toolbar tool, safe depending on interface and compatibility
    see also wx_compat AddTool in wx backends 
    """
    try:
        wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN)
        hasBitMap=True
    except:
        # Somehow fails on recent Mac OS
        hasBitMap     = False
        bitmap        = None
        defaultBitmap = None

    if defaultBitmap is None:
        # Last resort, we add a button only
        bt=wx.Button(tb,wx.ID_ANY, label)
        tl=tb.AddControl(bt)
        if callback is not None:
            tb.Bind(wx.EVT_BUTTON, callback, bt)
        return tl
    else:
        # --- TODO this is not pretty.. Use wx.INDEX directly?
        if defaultBitmap=='ART_REDO':
            bitmap = wx.ArtProvider.GetBitmap(wx.ART_REDO)
        elif defaultBitmap=='ART_FILE_OPEN':
                bitmap = wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN)
        elif defaultBitmap=='ART_PLUS':
            try:
                bitmap = wx.ArtProvider.GetBitmap(wx.ART_PLUS)
            except:
                bitmap = wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN)
        elif defaultBitmap=='ART_ERROR':
            bitmap = wx.ArtProvider.GetBitmap(wx.ART_ERROR)
        else:
            raise NotImplementedError(defaultBitmap)


    # Modern API
    if Type is None or Type==0:
        try:
            tl = tb.AddTool( -1, bitmap=bitmap, label=label )
            if callback is not None:
                tb.Bind(wx.EVT_TOOL, callback, tl)
            return tl
        except:
            Type=None
    # Old fashion API
    if Type is None or Type==1:
        try:
            tl = tb.AddLabelTool( -1, bitmap=bitmap, label=label )
            if callback is not None:
                tb.Bind(wx.EVT_TOOL, callback, tl)
            return tl
        except:
            Type=None
    # Using a Bitmap 
    if Type is None or Type==2:
        try:
            bt=wx.Button(tb,wx.ID_ANY, " "+label+" ", style=wx.BU_EXACTFIT)
            bt.SetBitmapLabel(bitmap)
            #b.SetBitmapMargins((2,2)) # default is 4 but that seems too big to me.
            #b.SetInitialSize()
            tl=tb.AddControl(bt)
            if callback is not None:
                tb.Bind(wx.EVT_BUTTON, callback, bt)
            return tl
        except:
            Type=None
    return tl



# --------------------------------------------------------------------------------}
# --- Plot Panel 
# --------------------------------------------------------------------------------{
class MyMultiCursor(Widget):
    """ 
    Copy pasted from matplotlib.widgets.MultiCursor, version 3.6
    A change of interface occured between 3.5 and 3.6, it's simpler to just copy paste the whole class
    The main changes are indicated with "MANU" below:
      - adding a flag horizLocal (the horizontal cross hair is based on a given local axis (when having subplots))
      - setting the hlines and vlines per axes 
      - not returning when the zoom "widgetlock" is on to keep the cross hair in zoomed mode
    """
    def __init__(self, canvas, axes, useblit=True, horizOn=False, vertOn=True,
            horizLocal=True, # MANU
                 **lineprops):
        self.axes = axes
        self.horizOn = horizOn
        self.vertOn = vertOn

        self._canvas_infos = {
            ax.figure.canvas: {"cids": [], "background": None} for ax in axes}

        self.visible = True
        self.useblit = (
            useblit
            and all(canvas.supports_blit for canvas in self._canvas_infos))
        self.needclear = False

        if self.useblit:
            lineprops['animated'] = True

        # MANU: xid and ymid are per axis basis
        self.horizLocal = horizLocal
        self.vlines = []
        self.hlines = []
        for ax in axes:
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            xmid = 0.5 * (xmin + xmax)
            ymid = 0.5 * (ymin + ymax)
            if vertOn:
                self.vlines.append(ax.axvline(xmid, visible=False, **lineprops))
            if horizOn:
                self.hlines.append(ax.axhline(ymid, visible=False, **lineprops))

        self.connect()

    def connect(self):
        """Connect events."""
        for canvas, info in self._canvas_infos.items():
            info["cids"] = [
                canvas.mpl_connect('motion_notify_event', self.onmove),
                canvas.mpl_connect('draw_event', self.clear),
            ]

    def disconnect(self):
        """Disconnect events."""
        for canvas, info in self._canvas_infos.items():
            for cid in info["cids"]:
                canvas.mpl_disconnect(cid)
            info["cids"].clear()

    def clear(self, event):
        """Clear the cursor."""
        if self.ignore(event):
            return
        if self.useblit:
            for canvas, info in self._canvas_infos.items():
                info["background"] = canvas.copy_from_bbox(canvas.figure.bbox)
        for line in self.vlines + self.hlines:
            line.set_visible(False)

    def onmove(self, event):
        if (self.ignore(event)
                or event.inaxes not in self.axes):
            # MANU: Disabling lock below so that we can have cross hairwith zoom
        #        or not event.canvas.widgetlock.available(self)):
            return
        self.needclear = True
        if not self.visible:
            return
        if self.vertOn:
            for line in self.vlines:
                line.set_xdata((event.xdata, event.xdata))
                line.set_visible(self.visible)
        if self.horizOn:
            for line in self.hlines:
                line.set_ydata((event.ydata, event.ydata))
                line.set_visible(self.visible)
        #self._update()
        # MANU: adding current axes
        self._update(currentaxes=event.inaxes)

    def _update(self, currentaxes=None):
        if self.useblit:
            for canvas, info in self._canvas_infos.items():
                if info["background"]:
                    canvas.restore_region(info["background"])
            if self.vertOn:
                for ax, line in zip(self.axes, self.vlines):
                    ax.draw_artist(line)
            if self.horizOn:
                # MANU: horizontal line only in current axes
                for ax, line in zip(self.axes, self.hlines):
                    if (self.horizLocal and currentaxes == ax) or (not self.horizLocal):
                        ax.draw_artist(line)

            for canvas in self._canvas_infos:
                canvas.blit()
        else:
            for canvas in self._canvas_infos:
                canvas.draw_idle()


class NavigationToolbar2WxSubTools(NavigationToolbar2Wx): 
    """
    Wrapped version of the Navigation toolbar from WX with the following features:
      - Tools can be removed, if not in `keep_tools`
      - Zoom is set by default, and the toggling between zoom and pan is handled internally
    """
    def __init__(self, canvas, keep_tools):
        # Taken from matplotlib/backend_wx.py but added style:
        self.VERSION = matplotlib.__version__
        if self.VERSION[0]=='2' or self.VERSION[0]=='1': 
            wx.ToolBar.__init__(self, canvas.GetParent(), -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT | wx.TB_NODIVIDER)
            NavigationToolbar2.__init__(self, canvas)

            self.canvas = canvas
            self._idle = True
            try: # Old matplotlib
                self.statbar = None 
            except:
                pass
            self.prevZoomRect = None
            self.retinaFix = 'wxMac' in wx.PlatformInfo
        else:
            NavigationToolbar2Wx.__init__(self, canvas)

        self.pan_on=False

        # Remove unnecessary tools
        tools = [self.GetToolByPos(i) for i in range(self.GetToolsCount())]
        for i, t in reversed(list(enumerate(tools))):
            if t.GetLabel() not in keep_tools:
                self.DeleteToolByPos(i)

class MyNavigationToolbar2Wx(NavigationToolbar2Wx): 
    """
    Wrapped version of the Navigation toolbar from WX with the following features:
      - Tools can be removed, if not in `keep_tools`
      - Zoom is set by default, and the toggling between zoom and pan is handled internally
    """
    def __init__(self, canvas, keep_tools, plotPanel):
        # Taken from matplotlib/backend_wx.py but added style:
        self.VERSION = matplotlib.__version__
        self.plotPanel = plotPanel
        #print('MPL VERSION:',self.VERSION)
        if self.VERSION[0]=='2' or self.VERSION[0]=='1':
            wx.ToolBar.__init__(self, canvas.GetParent(), -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT | wx.TB_NODIVIDER)
            NavigationToolbar2.__init__(self, canvas)

            self.canvas = canvas
            self._idle = True
            try: # Old matplotlib
                self.statbar = None
            except:
                pass
            self.prevZoomRect = None
            self.retinaFix = 'wxMac' in wx.PlatformInfo
            #NavigationToolbar2Wx.__init__(self, plotCanvas)
        else:
            NavigationToolbar2Wx.__init__(self, canvas)

        self.pan_on = False
        self.rotate_on = False
        self._rotate_tool_id = None

        # Make sure we start in zoom mode
        if 'Pan' in keep_tools:
            self.zoom() # NOTE: #22 BREAK cursors #12!

        # Remove unnecessary tools
        tools = [self.GetToolByPos(i) for i in range(self.GetToolsCount())]
        for i, t in reversed(list(enumerate(tools))):
            if t.GetLabel() not in keep_tools:
                self.DeleteToolByPos(i)

        # Add Rotate toggle button (after filtering, so it always appears)
        if 'Pan' in keep_tools:
            try:
                _bmp = wx.ArtProvider.GetBitmap(wx.ART_REDO, wx.ART_TOOLBAR, (16, 16))
                _rt = self.AddCheckTool(-1, label='Rotate', bitmap1=_bmp)
                self._rotate_tool_id = _rt.GetId()
                self.Bind(wx.EVT_TOOL, self._toggle_rotate, id=self._rotate_tool_id)
                self.SetToolShortHelp(self._rotate_tool_id,
                    'Rotation for 3D: left rotates, right zooms')
                self.Realize()
                # Disabled until 3D mode is activated
                self.EnableTool(self._rotate_tool_id, False)
            except Exception:
                pass
            # Update Pan button tooltip to document 3D z-axis constraint
            try:
                for i in range(self.GetToolsCount()):
                    t = self.GetToolByPos(i)
                    if t.GetLabel() == 'Pan':
                        self.SetToolShortHelp(t.GetId(),
                            'When on:\n'
                            'Left pans, Right zooms\n'
                            'x/y/z fixes axis, CTRL fixes aspect\n'
                            'When off:\n'
                            'Left zooms in, right zooms out')
                        break
            except Exception:
                pass

    def _toggle_rotate(self, event=None):
        """Toggle rotate mode on/off. When on: drag rotates 3D axes; when off: left-drag pans."""
        self.rotate_on = not self.rotate_on
        if self.rotate_on:
            # Deactivate pan if active
            if self.pan_on:
                self.pan_on = False
                NavigationToolbar2.pan(self)
                # Defensive: ensure the Pan toolbar button visual is OFF.
                try:
                    for i in range(self.GetToolsCount()):
                        t = self.GetToolByPos(i)
                        if t.GetLabel() == 'Pan':
                            self.ToggleTool(t.GetId(), False)
                            break
                except Exception:
                    pass
            # Deactivate zoom if active
            try:
                from matplotlib.backend_bases import _Mode
                if self.mode == _Mode.ZOOM:
                    NavigationToolbar2.zoom(self)
            except Exception:
                try:
                    if getattr(self, '_active', None) == 'ZOOM':
                        NavigationToolbar2.zoom(self)
                except Exception:
                    pass
        else:
            # Rotate turned OFF — return to default (zoom) mode.
            NavigationToolbar2.zoom(self)
        if self._rotate_tool_id is not None:
            self.ToggleTool(self._rotate_tool_id, self.rotate_on)

    def zoom(self, *args):
        # NEW - MPL>=3.0.0
        if self.pan_on or self.rotate_on:
            pass
        else:
            NavigationToolbar2.zoom(self, *args) # We skip wx and use the parent

    def pan(self, *args):
        if self.rotate_on:
            self.rotate_on = False
        # Always force Rotate button visual OFF when Pan is clicked.
        if self._rotate_tool_id is not None:
            try:
                self.ToggleTool(self._rotate_tool_id, False)
            except Exception:
                pass
        self.pan_on = not self.pan_on
        # NEW - MPL >= 3.0.0
        NavigationToolbar2.pan(self, *args) # We skip wx and use to parent
        if not self.pan_on:
            self.zoom()

    def set3DMode(self, is3D):
        """Enable/disable the rotate button based on whether 3D mode is active."""
        if self._rotate_tool_id is not None:
            try:
                self.EnableTool(self._rotate_tool_id, is3D)
                if not is3D and self.rotate_on:
                    # Turn off rotate mode when leaving 3D
                    self.rotate_on = False
                    self.ToggleTool(self._rotate_tool_id, False)
                    NavigationToolbar2.zoom(self)
            except Exception:
                pass

    def home(self, *args):
        """Restore the original view. In 3D mode, resets camera AND axis ranges."""
        cp = getattr(self.plotPanel, 'colorPanel', None)
        if cp is not None and cp.cb3D.IsChecked():
            cp._pending_elev = 30
            cp._pending_azim = -60
            cp._pending_hide = None
            self.plotPanel.redraw_same_data(force_autoscale=True)
        else:
            # Feature: if user click on home, we trigger a tight layout
            self.plotPanel.setSubplotTight(draw=False)
            # Feature: We force autoscale
            self.canvas.GetParent().redraw_same_data(force_autoscale=True)

    def set_message(self, s):
        pass

#     def configure_subplots(self, *args):
#         NavigationToolbar2Wx.configure_subplots(self, *args)
# 
#         def close_event(e):
#             # We delete the suplot_tool (default behavior)
#             try:
#                 delattr(self, 'subplot_tool')
#             except:
#                 pass
#             # Then we introduce a hook to store the new subplot
#             params = self.canvas.figure.subplotpars
#             paramsD= {}
#             for key in ["left", "bottom", "right", "top", "wspace", "hspace"]:
#                 paramsD[key]=getattr(params, key)
#             self.canvas.figure._subplotsPar = paramsD
# 
#         # We change the default hook for the close event
#         tool_fig = self.subplot_tool.figure
#         tool_fig.canvas.mpl_connect("close_event", close_event)
# 
#         return self.subplot_tool


