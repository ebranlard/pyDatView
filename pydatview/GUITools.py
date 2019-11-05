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

# --------------------------------------------------------------------------------}
# --- Mask
# --------------------------------------------------------------------------------{
class MaskToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(MaskToolPanel,self).__init__(parent)

        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()

        allMask = tabList.commonMaskString

        btClose=wx.Button(self,wx.ID_ANY,'Close', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.destroy, btClose)

        btClear=wx.Button(self,wx.ID_ANY,'Clear (masks)', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.onClear, btClear)

        btComp=wx.Button(self,wx.ID_ANY,'Apply (new data)', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.onApply, btComp)

        btCompMask=wx.Button(self,wx.ID_ANY,'Apply (mask)', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.onApplyMask, btCompMask)


        self.lb         = wx.StaticText( self, -1, """Mask: (ex: "({Time}>100) && ({Time}<50) && ({WS}==5)"   or "{Date} > '2018-10-01'")""")
        self.cbTabs     = wx.ComboBox(self, choices=tabListNames, style=wx.CB_READONLY)
        self.cbTabs.SetSelection(0)

        self.textMask = wx.TextCtrl(self, wx.ID_ANY, allMask)
        #self.textMask.SetValue('({Time}>100) & ({Time}<400)')
        #self.textMask.SetValue("{Date} > '2018-10-01'")

        btSizer  = wx.FlexGridSizer(rows=2, cols=2, hgap=2, vgap=0)
        btSizer.Add(btClose   ,0,flag    = wx.ALL ,border = 1)
        btSizer.Add(btClear   ,0,flag    = wx.ALL ,border = 1)
        btSizer.Add(btComp    ,0,flag     = wx.ALL,border = 1)
        btSizer.Add(btCompMask,0,flag = wx.ALL    ,border = 1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(self.cbTabs  , 0, wx.ALL, 5)
        row_sizer.Add(self.textMask, 1, wx.ALL | wx.EXPAND | wx.ALIGN_RIGHT, 5)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.lb     ,0, flag = wx.EXPAND| wx.LEFT|wx.CENTER,border = 5)
        vert_sizer.Add(row_sizer   ,1, flag = wx.EXPAND| wx.LEFT|wx.CENTER,border = 5)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT|wx.CENTER,border = 1)
        self.sizer.Add(vert_sizer   ,1, flag = wx.EXPAND,border = 5)
        self.SetSizer(self.sizer)
        self.Bind(wx.EVT_COMBOBOX, self.onTabChange, self.cbTabs )

    def onTabChange(self,event=None):
        tabList = self.parent.selPanel.tabList
        iSel=self.cbTabs.GetSelection()
        if iSel==0:
            maskString = tabList.commonMaskString
        else:
            maskString= tabList.get(iSel-1).maskString
        if len(maskString)>0:
            self.textMask.SetValue(maskString)
        else:
            self.textMask.SetValue('') # no known mask


    def onClear(self,event=None):
        iSel      = self.cbTabs.GetSelection()
        tabList   = self.parent.selPanel.tabList
        mainframe = self.parent.mainframe
        if iSel==0:
            tabList.clearCommonMask()
        else:
            tabList.get(iSel-1).clearMask()

        mainframe.redraw()
        self.onTabChange()

    def onApplyMask(self,event=None):
        self.onApply(event,bAdd=False)

    def onApply(self,event=None,bAdd=True):
        maskString = self.textMask.GetLineText(0)
        iSel         = self.cbTabs.GetSelection()
        tabList      = self.parent.selPanel.tabList
        mainframe    = self.parent.mainframe
        if iSel==0:
            dfs, names, errors = tabList.applyCommonMaskString(maskString, bAdd=bAdd)
            if bAdd:
                mainframe.load_dfs(dfs,names,bAdd=bAdd)
            else:
                mainframe.redraw()
            if len(errors)>0:
                raise Exception('Error: The mask failed on some tables:\n\n'+'\n'.join(errors))
        else:
            dfs, name = tabList.get(iSel-1).applyMaskString(maskString, bAdd=bAdd)
            if bAdd:
                mainframe.load_df(df,name,bAdd=bAdd)
            else:
                mainframe.redraw()
        self.updateTabList()


    def updateTabList(self,event=None):
        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()
        self.cbTabs.Clear()
        [self.cbTabs.Append(tn) for tn in tabListNames]
        self.cbTabs.SetSelection(0)

# --------------------------------------------------------------------------------}
# --- Radial
# --------------------------------------------------------------------------------{
sAVG_METHODS = ['Last `n` seconds','Last `n` periods']
AVG_METHODS  = ['constantwindow','periods']

class RadialToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(RadialToolPanel,self).__init__(parent)

        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()

        btClose=wx.Button(self,wx.ID_ANY,'Close', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.destroy, btClose)

        btComp=wx.Button(self,wx.ID_ANY,'Average (new data)', style=wx.BU_EXACTFIT)
        self.Bind(wx.EVT_BUTTON, self.onApply, btComp)

        self.lb         = wx.StaticText( self, -1, """Select tables, averaging method and average parameter: (number of periods (needs azimuth signal) or number of time steps """)
        self.cbTabs     = wx.ComboBox(self, choices=tabListNames, style=wx.CB_READONLY)
        self.cbMethod   = wx.ComboBox(self, choices=sAVG_METHODS, style=wx.CB_READONLY)
        self.cbTabs.SetSelection(0)
        self.cbMethod.SetSelection(0)

        self.textAverageParam = wx.TextCtrl(self, wx.ID_ANY, '2')

        btSizer  = wx.FlexGridSizer(rows=2, cols=2, hgap=2, vgap=0)
        btSizer.Add(btClose   ,0,flag    = wx.ALL ,border = 1)
        btSizer.Add(btComp  ,0,flag     = wx.ALL,border = 1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(self.cbTabs  , 0, wx.ALL, 5)
        row_sizer.Add(self.cbMethod, 0, wx.ALL, 5)
        row_sizer.Add(self.textAverageParam, 1, wx.ALL | wx.EXPAND | wx.ALIGN_RIGHT, 5)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.lb     ,0, flag = wx.EXPAND| wx.LEFT|wx.CENTER,border = 5)
        vert_sizer.Add(row_sizer   ,1, flag = wx.EXPAND| wx.LEFT|wx.CENTER,border = 5)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT|wx.CENTER,border = 1)
        self.sizer.Add(vert_sizer   ,1, flag = wx.EXPAND,border = 5)
        self.SetSizer(self.sizer)
        self.Bind(wx.EVT_COMBOBOX, self.onTabChange, self.cbTabs )

    def onTabChange(self,event=None):
        tabList = self.parent.selPanel.tabList
#     dfRad,dfRadTime = fastfarm.extractFFRadialData(fastfarm_out=ff_out, fastfarm_input=ff_in,D=D)
#         iSel=self.cbTabs.GetSelection()
#         if iSel==0:
#             maskString = tabList.commonMaskString
#         else:
#             maskString= tabList.get(iSel-1).maskString
#         if len(maskString)>0:
#             self.textMask.SetValue(maskString)
#         else:
#             self.textMask.SetValue('') # no known mask

    def onApply(self,event=None):
        try:
            avgParam     = float(self.textAverageParam.GetLineText(0))
        except:
            raise Exception('Error: the averaging parameter needs to be an integer or a float')
        iSel         = self.cbTabs.GetSelection()
        avgMethod   = AVG_METHODS[self.cbMethod.GetSelection()]
        tabList      = self.parent.selPanel.tabList
        mainframe    = self.parent.mainframe
        if iSel==0:
            dfs, names, errors = tabList.radialAvg(avgMethod,avgParam)
            mainframe.load_dfs(dfs,names,bAdd=True)
            if len(errors)>0:
                raise Exception('Error: The mask failed on some tables:\n\n'+'\n'.join(errors))
        else:
            dfs, names = tabList.get(iSel-1).radialAvg(avgMethod,avgParam)
            mainframe.load_dfs(dfs,names,bAdd=True)

        self.updateTabList()

    def updateTabList(self,event=None):
        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()
        self.cbTabs.Clear()
        [self.cbTabs.Append(tn) for tn in tabListNames]
        self.cbTabs.SetSelection(0)
