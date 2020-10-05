
import wx
import matplotlib
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.widgets import Cursor, MultiCursor
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
# --- Plot Panel 
# --------------------------------------------------------------------------------{
# class MyCursor(Cursor):
#     def onmove(self, event):
#         """on mouse motion draw the cursor if visible"""
#         if self.ignore(event):
#             return
#         # MANU: Disabling lock below so that we can have cross hairwith zoom
#         #if not self.canvas.widgetlock.available(self):
#         #    return
#         if event.inaxes != self.ax:
#             self.linev.set_visible(False)
#             self.lineh.set_visible(False)
# 
#             if self.needclear:
#                 self.canvas.draw()
#                 self.needclear = False
#             return
#         self.needclear = True
#         if not self.visible:
#             return
#         self.linev.set_xdata((event.xdata, event.xdata))
# 
#         self.lineh.set_ydata((event.ydata, event.ydata))
#         self.linev.set_visible(self.visible and self.vertOn)
#         self.lineh.set_visible(self.visible and self.horizOn)
# 
#         self._update()

class MyMultiCursor(MultiCursor):
    def __init__(self, canvas, axes, useblit=True, horizOn=False, vertOn=True, horizLocal=True,
                 **lineprops):
        # Taken from matplotlib/widget.py but added horizLocal
        super(MyMultiCursor,self).__init__(canvas, axes, useblit, horizOn, vertOn, **lineprops)
        self.canvas = canvas
        self.axes = axes
        self.horizOn = horizOn
        self.vertOn = vertOn
        self.visible = True
        self.useblit = useblit and self.canvas.supports_blit
        self.background = None
        self.needclear = False
        if self.useblit:
            lineprops['animated'] = True
        self.vlines = []
        self.hlines = []
        # MANU: xid and ymid are per axis basis
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
        # ---
        self.horizLocal = horizLocal

    def onmove(self, event):
        if self.ignore(event):
            return
        if event.inaxes is None:
            return
        # MANU: Disabling lock below so that we can have cross hairwith zoom
        # if not self.canvas.widgetlock.available(self):
        # return
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
        # MANU: adding current axes
        self._update(currentaxes=event.inaxes)
    def _update(self,currentaxes=None):
        if self.useblit:
            if self.background is not None:
                self.canvas.restore_region(self.background)
            if self.vertOn:
                for ax, line in zip(self.axes, self.vlines):
                    ax.draw_artist(line)
            if self.horizOn:
                # MANU: horizontal line only in current axes
                for ax, line in zip(self.axes, self.hlines):
                    if (self.horizLocal and currentaxes == ax) or (not self.horizLocal):
                        ax.draw_artist(line)
            self.canvas.blit(self.canvas.figure.bbox)
        else:
            self.canvas.draw_idle()


class MyNavigationToolbar2Wx(NavigationToolbar2Wx): 
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

        tools = [self.GetToolByPos(i) for i in range(self.GetToolsCount())]
        for i, t in reversed(list(enumerate(tools))):
            if t.GetLabel() not in keep_tools:
                self.DeleteToolByPos(i)

    def press_zoom(self, event):
        NavigationToolbar2Wx.press_zoom(self,event)
        #self.SetToolBitmapSize((22,22))

    def press_pan(self, event):
        NavigationToolbar2Wx.press_pan(self,event)

    def zoom(self, *args):
        NavigationToolbar2Wx.zoom(self,*args)

    def pan(self, *args):
        if self.VERSION[0]=='2' or self.VERSION[0]=='1': 
            if self._active=='PAN':
                NavigationToolbar2Wx.pan(self,*args)
                self.zoom()
            else:
                NavigationToolbar2Wx.pan(self,*args)
        else: # 3
            from matplotlib.backend_bases import _Mode
            if self.mode == _Mode.PAN:
                NavigationToolbar2Wx.pan(self,*args)
                self.zoom()
            else:
                NavigationToolbar2Wx.pan(self,*args)

    def home(self, *args):
        """Restore the original view."""
        self.canvas.GetParent().redraw_same_data(False)

    def set_message(self, s):
        pass
