import wx

# For log dec tool
from .damping import logDecFromDecay

# --------------------------------------------------------------------------------}
# --- Default class for tools
# --------------------------------------------------------------------------------{
class GUIToolPanel(wx.Panel):
    def __init__(self, parent):
        super(GUIToolPanel,self).__init__(parent)
        self.parent   = parent

    def destroy(self,event=None):
        self.parent.removeTools()


# --------------------------------------------------------------------------------}
# ---   Log Dec
# --------------------------------------------------------------------------------{
class LogDecToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(LogDecToolPanel,self).__init__(parent)
        btClose=wx.Button(self,wx.ID_ANY,'Close', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.destroy, btClose)
        btComp=wx.Button(self,wx.ID_ANY,'Compute', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.onCompute, btComp)
        self.lb = wx.StaticText( self, -1, '                     ')
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btClose   ,0, flag = wx.LEFT|wx.CENTER,border = 1)
        self.sizer.Add(btComp    ,0, flag = wx.LEFT|wx.CENTER,border = 5)
        self.sizer.Add(self.lb   ,0, flag = wx.LEFT|wx.CENTER,border = 5)
        self.SetSizer(self.sizer)

    def onCompute(self,event=None):
        if len(self.parent.plotData)!=1:
            Error(self,'Log Dec tool only works with a single plot.')
            return
        pd =self.parent.plotData[0]
        try:
            logdec,DampingRatio,T,fn,fd,IPos,INeg,epos,eneg=logDecFromDecay(pd.y,pd.x)
            lab='LogDec.: {:.4f} - Damping ratio: {:.4f} - F_n: {:.4f} - F_d: {:.4f} - T:{:.3f}'.format(logdec,DampingRatio,fn,fd,T)
            self.lb.SetLabel(lab)
            self.sizer.Layout()
            ax=self.parent.fig.axes[0]
            ax.plot(pd.x[IPos],pd.y[IPos],'o')
            ax.plot(pd.x[INeg],pd.y[INeg],'o')
            ax.plot(pd.x ,epos,'k--')
            ax.plot(pd.x ,eneg,'k--')
            self.parent.canvas.draw()
        except:
            self.lb.SetLabel('Failed. The signal needs to look like the decay of a first order system.')
        #self.parent.redraw(); # DATA HAS CHANGED
