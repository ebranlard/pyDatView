
import wx
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.widgets import Cursor, MultiCursor
# from matplotlib.widgets import AxesWidget

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
    def __init__(self, canvas):
        # Taken from matplotlib/backend_wx.py but added style:
        wx.ToolBar.__init__(self, canvas.GetParent(), -1, style=wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT | wx.TB_NODIVIDER)
        NavigationToolbar2.__init__(self, canvas)

        self.canvas = canvas
        self._idle = True
        self.statbar = None
        self.prevZoomRect = None
        self.zoom() # NOTE: #22 BREAK cursors #12!
        self.retinaFix = 'wxMac' in wx.PlatformInfo
        # --- Modif
        #NavigationToolbar2Wx.__init__(self, plotCanvas)
        self.DeleteToolByPos(1)
        self.DeleteToolByPos(1)
        self.DeleteToolByPos(3)
        #self.SetBackgroundColour('white')
    def press_zoom(self, event):
        NavigationToolbar2Wx.press_zoom(self,event)
        #self.SetToolBitmapSize((22,22))

    def press_pan(self, event):
        NavigationToolbar2Wx.press_pan(self,event)

    def zoom(self, *args):
        NavigationToolbar2Wx.zoom(self,*args)

    def pan(self, *args):
        if self._active=='PAN':
            NavigationToolbar2Wx.pan(self,*args)
            self.zoom()
        else:
            NavigationToolbar2Wx.pan(self,*args)
# 
#     def home(self, *args):
#         """Restore the original view."""
#         self.canvas.GetParent().redraw_same_data()
