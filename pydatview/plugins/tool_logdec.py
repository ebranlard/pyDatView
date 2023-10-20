import wx
import numpy as np
from pydatview.common import Error, Info, Warn
from pydatview.plugins.base_plugin import GUIToolPanel
from pydatview.tools.damping import freqDampEstimator, zetaEnvelop

_HELP = """Damping and frequency estimation.

This tool attemps to estimate the natural frequency and damping ratio of the signal,
assuming it has a dominant frequency and an exponential decay or growth.
The damping ratio is referred to as "zeta".

NOTE: you can zoom on the figure first (and deselect "AutoScale"), to perform the estimation
    on the zoomed subset of the plot.

- Click on "Compute and Plot" to perform the estimate.

- Algorithm options: None for now.
     See freqDampEstimator in damping.py for ways to extend this.

- Plotting options: 
   These options do no affect the algorithm used to compute the frequency and zeta.
   - Envelop: If selected, the exponential envelop corresponding to a given zeta is shown.
   - Ref point: the reference point used to plot the envelope. The envelop will pass by this
                point, either the first, last or middle point of the plot.
   - Peaks: If selected, the upper and lower peaks that are detected by the algorithm are 
             shown on the plot
   - More Env.: Additional guess for zeta are used and plotted. This gives an idea of the min
             and max value that zeta might take.

- Results: Display values for
   - Natural frequency "F_n" (in [Hz] if x in [s])
   - Damping ratio "zeta" [-]
   - Logarithmic decrements "logdec" [-]
   - Damped  frequency "F_d" (in [Hz] if x in [s])
   - Damped period "T_d" (in [s] if x in [s])
"""
# --------------------------------------------------------------------------------}
# --- Log Dec
# --------------------------------------------------------------------------------{
class LogDecToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(LogDecToolPanel,self).__init__(parent)
        self.data = {}
        # --- GUI
        btClose = self.getBtBitmap(self,'Close'  ,'close'  ,self.destroy  )
        btComp  = self.getBtBitmap(self,'Compute and Plot','compute',self.onCompute)
        btHelp  = self.getBtBitmap(self, 'Help','help', self.onHelp)
        self.cbRefPoint = wx.ComboBox(self, -1, choices=['start','mid','end'], style=wx.CB_READONLY)
        self.cbRefPoint.SetSelection(1)
        self.cbPeaks  = wx.CheckBox(self, -1, 'Peaks',(10,10))
        self.cbEnv    = wx.CheckBox(self, -1, 'Envelop',(10,10))
        self.cbMinMax = wx.CheckBox(self, -1, 'More Envelops',(10,10))
        self.cbMinMax.SetValue(False)
        self.cbPeaks .SetValue(False)
        self.cbEnv   .SetValue(True)
        self.results   = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_READONLY)
        self.results.SetValue('Click on "Compute and Plot" to show results here                                            ')

        boldFont = self.GetFont().Bold()
        lbAlgOpts = wx.StaticText(self, -1, 'Algo. Options')
        lbPltOpts = wx.StaticText(self, -1, 'Plot Options')
        lbResults = wx.StaticText(self, -1, 'Results')
        lbAlgOpts.SetFont(boldFont)
        lbPltOpts.SetFont(boldFont)
        lbResults.SetFont(boldFont)

        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=3, cols=1, hgap=2, vgap=0)
        btSizer.Add(btClose         ,0, flag = wx.LEFT|wx.CENTER,border = 1)
        btSizer.Add(btComp          ,0, flag = wx.LEFT|wx.CENTER,border = 1)
        btSizer.Add(btHelp          ,0, flag = wx.LEFT|wx.CENTER,border = 1)

        gridSizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)

        sizerOpts = wx.BoxSizer(wx.HORIZONTAL)
        sizerOpts.Add(wx.StaticText( self, -1, 'Ref. point: ' )     , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border = 1)
        sizerOpts.Add(self.cbRefPoint                               , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border = 1)
        sizerOpts.Add(self.cbEnv                                    , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border = 10)
        sizerOpts.Add(self.cbPeaks                                  , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border = 1)
        sizerOpts.Add(self.cbMinMax                                 , 0, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border = 1)

        sizerAlg = wx.BoxSizer(wx.HORIZONTAL)
        sizerAlg.Add(wx.StaticText( self, -1, 'No options for now, using "peaks" and log dec.'), 1, flag = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border = 1)

        sizerRes = wx.BoxSizer(wx.HORIZONTAL)
        sizerRes.Add(self.results                                  , 1, flag = wx.EXPAND|wx.ALIGN_LEFT|wx.LEFT,border = 1)

        gridSizer.Add(lbAlgOpts,    0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)   
        gridSizer.Add(sizerAlg,     1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        gridSizer.Add(lbPltOpts,    0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)   
        gridSizer.Add(sizerOpts,    1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        gridSizer.Add(lbResults,    0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)   
        gridSizer.Add(sizerRes    , 1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        gridSizer.AddGrowableCol(1,1)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer   , 0, flag = wx.LEFT          ,border = 5)
        self.sizer.Add(gridSizer , 1, flag = wx.LEFT|wx.EXPAND,border = 10)
        self.SetSizer(self.sizer)

        # --- Binding
        #self.cbRefPoint.Bind(wx.EVT_COMBOBOX, self.onRefPointChange)

    def onClear(self): 
        #.mainframe.plotPanel.load_and_draw  # or action.guiCallback
        return self.parent.load_and_draw()

    def onHelp(self,event=None):
        Info(self, _HELP)

    # --- Fairly generic
    def _GUI2Data(self):
        self.data['method']   = 'fromPeaks'
        self.data['refPoint'] = self.cbRefPoint.GetValue()
        self.data['minMax']   = self.cbMinMax.IsChecked()
        self.data['env']     = self.cbEnv    .IsChecked()
        self.data['peaks']   = self.cbPeaks  .IsChecked()

    def onCompute(self,event=None):
        if len(self.parent.plotData)!=1:
            Error(self,'Log Dec tool only works with a single plot.')
            return

        # --- Clean plot..., but store limits first
        ax = self.parent.fig.axes[0]
        xlim = ax.get_xlim()
        self.onClear() # NOTE: this will create different axes..
        

        # --- GUI2Data
        self._GUI2Data()

        # --- PlotStyles
        plotStyle = self.parent.esthPanel._GUI2Data()
        lgdLoc = plotStyle['LegendPosition'].lower()
        legd_opts=dict()
        legd_opts['fontsize'] = plotStyle['LegendFont']
        legd_opts['loc'] = lgdLoc if lgdLoc != 'none' else 4
        legd_opts['fancybox'] = False

        # --- Data to work with
        PD =self.parent.plotData[0]
        ax =self.parent.fig.axes[0]
        # Restricting data to axes visible bounds on the x axis
        b=np.logical_and(PD.x>=xlim[0], PD.x<=xlim[1])
        t = PD.x[b]
        x = PD.y[b]

        try:
#         if True:
            fn, zeta, info = freqDampEstimator(x, t, opts=self.data)
        except:
            self.results.SetValue('Failed. The signal needs to look like the decay of a first order system.')
            event.Skip()
            return

        # --- Handling returned data
        logdec = 2*np.pi*zeta /np.sqrt(1-zeta**2)
        omega0 = 2*np.pi*fn
        fd = fn*np.sqrt(1-zeta**2)
        Td = 1/fd
        IPos = info['IPos']
        if self.data['refPoint']=='mid':
            iRef = IPos[int(len(IPos)/2)]
        elif self.data['refPoint']=='start':
            iRef = IPos[0]
        elif self.data['refPoint']=='end':
            iRef = IPos[-1]
        else:
            raise Exception('Wrong value for ref Point')

        lab='F_n={:.4f} , DampingRatio={:.4f} , LogDec.={:.4f}, F_d={:.4f} , T_d={:.3f}'.format(fn, zeta, logdec, fd, Td)
        self.results.SetValue(lab)
        #self.sizer.Layout()


        # --- Plot Min and Max points
        if self.data['peaks']:
            ax.plot(t[info['IPos']],x[info['IPos']],'o')
            ax.plot(t[info['INeg']],x[info['INeg']],'o')


        # --- Plot envelop
        def plotEnv(zeta, sty, c):
            epos, eneg = zetaEnvelop(x, t, omega0, zeta, iRef=iRef) 
            ax.plot(t, epos, sty, color=c, label=r'$\zeta={:.2f}$%'.format(zeta*100))
            ax.plot(t, eneg, sty, color=c)
        if self.data['env']:
            plotEnv(zeta, '--', 'k')

        # --- Plot more envelops
        if self.data['minMax']:
            # Could also do +/- 10 % of zeta
            plotEnv(info['zetaMax'] , ':', 'b')
            plotEnv(info['zetaMin'] , ':', 'r')
            plotEnv(info['zetaMean'], ':', 'g')

        ax.legend(**legd_opts)
        self.parent.canvas.draw()
        #self.parent.load_and_draw(); # DATA HAS CHANGED

