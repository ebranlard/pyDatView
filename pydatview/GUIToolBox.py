
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
    """ """


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



class MyNavigationToolbar2Wx(NavigationToolbar2Wx): 
    """
    Wrapped version of the Navigation toolbar from WX with the following features:
      - Tools can be removed, if not in `keep_tools`
      - Zoom is set by default, and the toggling between zoom and pan is handled internally
    """
    def __init__(self, canvas, keep_tools):
        # Taken from matplotlib/backend_wx.py but added style:
        self.VERSION = matplotlib.__version__
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

        self.pan_on=False

        # Make sure we start in zoom mode
        if 'Pan' in keep_tools:
            self.zoom() # NOTE: #22 BREAK cursors #12!

        # Remove unnecessary tools
        tools = [self.GetToolByPos(i) for i in range(self.GetToolsCount())]
        for i, t in reversed(list(enumerate(tools))):
            if t.GetLabel() not in keep_tools:
                self.DeleteToolByPos(i)

    def zoom(self, *args):
        # NEW - MPL>=3.0.0
        if self.pan_on:
            pass
        else:
            NavigationToolbar2.zoom(self,*args) # We skip wx and use the parent
        # BEFORE
        #NavigationToolbar2Wx.zoom(self,*args)

    def pan(self, *args):
        self.pan_on=not self.pan_on
        # NEW - MPL >= 3.0.0
        NavigationToolbar2.pan(self, *args) # We skip wx and use to parent
        if not self.pan_on:
            self.zoom()
        # BEFORE
        #try:
        #    isPan = self._active=='PAN'
        #except:
        #    try:
        #        from matplotlib.backend_bases import _Mode
        #        isPan = self.mode == _Mode.PAN
        #    except:
        #        raise Exception('Pan not found, report a pyDatView bug, with matplotlib version.')
        #NavigationToolbar2Wx.pan(self,*args)
        #if isPan:
        #    self.zoom()

    def home(self, *args):
        """Restore the original view."""
        self.canvas.GetParent().redraw_same_data(False)

    def set_message(self, s):
        pass
