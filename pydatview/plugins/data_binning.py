import wx
import numpy as np
import pandas as pd
# import copy
# import platform
# from collections import OrderedDict
# For log dec tool
from pydatview.GUITools import GUIToolPanel, TOOL_BORDER
from pydatview.common import CHAR, Error, Info, pretty_num_short
from pydatview.common import DummyMainFrame
from pydatview.plotdata import PlotData
# from pydatview.tools.damping import logDecFromDecay
# from pydatview.tools.curve_fitting import model_fit, extract_key_miscnum, extract_key_num, MODELS, FITTERS, set_common_keys

from pydatview.pipeline import PlotDataAction

# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def binningAction(label, mainframe=None, data=None):
    """
    Return an "action" for the current plugin, to be used in the pipeline.
    The action is also edited and created by the GUI Editor
    """
    if data is None:
        data=_DEFAULT_DICT

    action = PlotDataAction(
            name=label,
            guiEditorClass = BinningToolPanel,
            data = data,
            mainframe=mainframe
            )
    return action

# --------------------------------------------------------------------------------}
# --- GUI to Edit Plugin and control the Action
# --------------------------------------------------------------------------------{
class BinningToolPanel(GUIToolPanel):
    def __init__(self, parent, action):
        super(BinningToolPanel, self).__init__(parent)

        # --- Creating "Fake data" for testing only!
        if action is None:
            print('[WARN] Calling GUI without an action! Creating one.')
            mainframe = DummyMainFrame(parent)
            action = binningAction(label='dummyAction', mainframe=mainframe)
        # --- Data from other modules
        self.parent = parent # parent is GUIPlotPanel
        self.mainframe = action.mainframe

        self.data = action.data
        self.action = action
        self.data['selectionChangeCallBack'] = self.selectionChange


        # --- GUI elements
        self.btClose    = self.getBtBitmap(self, 'Close','close', self.destroy)
        self.btAdd      = self.getBtBitmap(self, 'Add','add'  , self.onAdd)
        self.btHelp     = self.getBtBitmap(self, 'Help','help', self.onHelp)
        self.btClear    = self.getBtBitmap(self, 'Clear Plot','sun', self.onClear)

        #self.lb         = wx.StaticText( self, -1, """ Click help """)
        self.cbTabs     = wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
        self.scBins = wx.SpinCtrl(self, value='50', style=wx.TE_RIGHT, size=wx.Size(60,-1) )
        self.textXMin = wx.TextCtrl(self, wx.ID_ANY, '', style = wx.TE_PROCESS_ENTER|wx.TE_RIGHT, size=wx.Size(70,-1))
        self.textXMax = wx.TextCtrl(self, wx.ID_ANY, '', style = wx.TE_PROCESS_ENTER|wx.TE_RIGHT, size=wx.Size(70,-1))
        self.btPlot     = self.getBtBitmap(self, 'Plot' ,'chart'  , self.onPlot)
        self.btApply    = self.getToggleBtBitmap(self,'Apply','cloud',self.onToggleApply)
        self.btXRange = self.getBtBitmap(self, 'Default','compute', self.reset)
        self.lbDX     = wx.StaticText(self, -1, '')
        self.scBins.SetRange(3, 10000)

        boldFont = self.GetFont().Bold()
        lbInputs  = wx.StaticText(self, -1, 'Inputs: ')
        lbInputs.SetFont(boldFont)

        # --- Layout
        btSizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)
        btSizer.Add(self.btClose                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btClear                , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btAdd                  , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btPlot                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btHelp                 , 0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(self.btApply                , 0, flag = wx.ALL|wx.EXPAND, border = 1)

        msizer  = wx.FlexGridSizer(rows=1, cols=3, hgap=2, vgap=0)
        msizer.Add(wx.StaticText(self, -1, 'Table:')    , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
        msizer.Add(self.cbTabs                          , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 1)
#         msizer.Add(self.btXRange                        , 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.LEFT, 1)

        msizer2 = wx.FlexGridSizer(rows=2, cols=5, hgap=2, vgap=1)

        msizer2.Add(lbInputs                                   , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 0)
        msizer2.Add(wx.StaticText(self, -1, '#bins: ')         , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 1)
        msizer2.Add(self.scBins                                , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL, 1)
        msizer2.Add(wx.StaticText(self, -1, 'dx: ')            , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 8)
        msizer2.Add(self.lbDX                                  , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 1)
        msizer2.Add(self.btXRange                              , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 0)
        msizer2.Add(wx.StaticText(self, -1, 'xmin: ')          , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 1)
        msizer2.Add(self.textXMin                              , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 1)
        msizer2.Add(wx.StaticText(self, -1, 'xmax: ')          , 0, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL          , 8)
        msizer2.Add(self.textXMax                              , 1, wx.LEFT|wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 1)
        #msizer2.AddGrowableCol(4,1)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(msizer,0, flag = wx.TOP            ,border = 1)
        vsizer.Add(msizer2,0, flag = wx.TOP|wx.EXPAND ,border = 1)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer  ,0, flag = wx.LEFT           , border = 5)
        self.sizer.Add(vsizer   ,1, flag = wx.LEFT|wx.EXPAND , border = TOOL_BORDER)
        #self.sizer.Add(msizer   ,1, flag = wx.LEFT|wx.EXPAND ,border = TOOL_BORDER)
        self.SetSizer(self.sizer)

        # --- Events
        self.scBins.Bind(wx.EVT_TEXT, self.onParamChange)
        self.cbTabs.Bind   (wx.EVT_COMBOBOX, self.onTabChange)
        self.textXMin.Bind(wx.EVT_TEXT_ENTER, self.onParamChange)
        self.textXMax.Bind(wx.EVT_TEXT_ENTER, self.onParamChange)

        # --- Init triggers
        if self.data['active']:
            self.setXRange(x=[self.data['xMin'], self.data['xMax']])
        else:
            self.setXRange()
        self.scBins.SetValue(self.data['nBins'])
        self.onToggleApply(init=True)
        self.updateTabList()
        self.onParamChange()

    def reset(self, event=None):
        self.setXRange()
        self.updateTabList() # might as well until we add a nice callback/button..

    def setXRange(self, x=None):
        if x is None:
            x= self.parent.plotData[0].x0
        xmin, xmax = np.nanmin(x), np.nanmax(x)
        self.textXMin.SetValue(pretty_num_short(xmin))
        self.textXMax.SetValue(pretty_num_short(xmax))

    def onParamChange(self, event=None):
        self._GUI2Data()
        self.lbDX.SetLabel(pretty_num_short((self.data['xMax']- self.data['xMin'])/self.data['nBins']))

        if self.data['active']:
            self.parent.load_and_draw() # Data will change

    def selectionChange(self):
        """ function called if user change tables/columns"""
        print('>>> Binning selectionChange callback, TODO')
        self.setXRange()

    def _GUI2Data(self):
        def zero_if_empty(s):
            return 0 if len(s)==0 else s
        self.data['nBins'] = int  (self.scBins.Value)
        self.data['xMin']  = float(zero_if_empty(self.textXMin.Value))
        self.data['xMax']  = float(zero_if_empty(self.textXMax.Value))

    def onToggleApply(self, event=None, init=False):
        """
        apply sampler based on GUI Data
        """
        if not init:
            self.data['active'] = not self.data['active']

        if self.data['active']:
            self._GUI2Data()
            self.btPlot.Enable(False)
            self.btClear.Enable(False)
            self.btApply.SetLabel(CHAR['sun']+' Clear')
            # We add our action to the pipeline
            if self.mainframe is not None:
                self.mainframe.addAction(self.action)
            else:
                print('[WARN] Running data_binning without a main frame')
        else:
            print('>>>> TODO Remove Action')
            # We remove our action from the pipeline
            if not init:
                if self.mainframe is not None:
                    self.mainframe.removeAction(self.action)
                else:
                    print('[WARN] Running data_binning without a main frame')
            #self.data = None
            #self.action = None
            self.btPlot.Enable(True)
            self.btClear.Enable(True)
            self.btApply.SetLabel(CHAR['cloud']+' Apply')

        if not init:
            # This is a "plotData" action, we don't need to do anything
            self.parent.load_and_draw() # Data will change based on plotData 


    def onAdd(self,event=None):
        from pydatview.tools.stats import bin_DF
        iSel          = self.cbTabs.GetSelection()
        tabList       = self.parent.selPanel.tabList
        icol, colname = self.parent.selPanel.xCol
        if self.parent.selPanel.currentMode=='simColumnsMode':
            # The difficulty here is that we have to use 
            #      self.parent.selPanel.IKeepPerTab
            #   or maybe just do it for the first table to get the x column name, 
            #   but there is no guarantee that other tables will have the exact same column name.
            Error(self, 'Cannot add tables in "simColumnsMode" for now. Go back to 1 table mode, and add tables individually.')
            return
        if icol==0:
            Error(self, 'Cannot resample based on index')
            return

        self._GUI2Data()
        errors=[]

        if iSel==0:
            # Looping on all tables and adding new table
            dfs_new   = []
            names_new = []
            for itab, tab in enumerate(tabList):
                df_new, name_new = bin_tab(tab, icol, colname, self.data, bAdd=True)
                if df_new is not None: 
                    # we don't append when string is empty
                    dfs_new.append(df_new)
                    names_new.append(name_new)
                else:
                    errors.append(tab.active_name)
            self.parent.addTables(dfs_new, names_new, bAdd=True)
        else:
            tab = tabList.get(iSel-1)
            df_new, name_new = bin_tab(tab, icol, colname, self.data, bAdd=True)
            if df_new is not None:
                self.parent.addTables([df_new], [name_new], bAdd=True)
            else:
                errors.append(tab.active_name)
        self.updateTabList()

        if len(errors)>0:
            Error(self, 'The binning failed on some tables:\n\n'+'\n'.join(errors))
            return

    def onPlot(self,event=None):
        if len(self.parent.plotData)!=1:
            Error(self,'Plotting only works for a single plot. Plot less data.')
            return
        self._GUI2Data()
        PD = self.parent.plotData[0]
        x_new, y_new = bin_plot(PD.x0, PD.y0, self.data)

        ax = self.parent.fig.axes[0]
        PD_new = PlotData()
        PD_new.fromXY(x_new, y_new)
        self.parent.transformPlotData(PD_new)
        ax.plot(PD_new.x, PD_new.y, '-')
        self.parent.canvas.draw()

    def onClear(self,event=None):
        self.parent.load_and_draw() # Data will change
        # Update Table list
        self.updateTabList()

    def onTabChange(self,event=None):
        #tabList = self.parent.selPanel.tabList
        #iSel=self.cbTabs.GetSelection()
        pass

    def updateTabList(self,event=None):
        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()
        try:
            iSel=np.max([np.min([self.cbTabs.GetSelection(),len(tabListNames)]),0])
            self.cbTabs.Clear()
            [self.cbTabs.Append(tn) for tn in tabListNames]
            self.cbTabs.SetSelection(iSel)
        except RuntimeError:
            pass

    def onHelp(self,event=None):
        Info(self,"""Binning.

The binning operation computes average y values for a set of x ranges.

To bin perform the following step:

- Specify the number of bins (#bins)
- Specify the min and max of the x values (or click on "Default")

- Click on one of the following buttons:
   - Plot: will display the binned data on the figure
   - Apply: will perform the binning on the fly for all new plots
           (click on Clear to stop applying)
   - Add: will create new table(s) with biined values for all 
          signals. This process might take some time.
          Select a table or choose all (default)
""")


# --------------------------------------------------------------------------------}
# --- DATA
# --------------------------------------------------------------------------------{
def bin_plot(x, y, opts):
    from pydatview.tools.stats import bin_signal
    xBins = np.linspace(opts['xMin'], opts['xMax'], opts['nBins']+1)
    if xBins[0]>xBins[1]:
        raise Exception('xmin must be lower than xmax')
    x_new, y_new = bin_signal(x, y, xbins=xBins)
    return x_new, y_new

def bin_tab(tab, iCol, colName, opts, bAdd=True):
    # TODO, make it such as it's only handling a dataframe instead of a table
    from pydatview.tools.stats import bin_DF
    colName = tab.data.columns[iCol]
    error=''
    xBins = np.linspace(opts['xMin'], opts['xMax'], opts['nBins']+1)
#     try:
    df_new =bin_DF(tab.data, xbins=xBins, colBin=colName)
    # Remove index if present
    if df_new.columns[0].lower().find('index')>=0:
        df_new = df_new.iloc[:, 1:] # We don't use "drop" in case of duplicate "index"

    # Setting bin column as first columns
    colNames = list(df_new.columns.values)
    colNames.remove(colName)
    colNames.insert(0, colName)
    df_new=df_new.reindex(columns=colNames)
    if bAdd:
        name_new=tab.raw_name+'_binned'
    else:
        name_new=None
        tab.data=df_new
#     except:
#         df_new   = None
#         name_new = None

    return df_new, name_new

_DEFAULT_DICT={
    'active':False, 
    'xMin':None, 
    'xMax':None, 
    'nBins':50, 
    'dx':0, 
    'applyCallBack':bin_plot,
    'selectionChangeCallBack':None,
}


if __name__ == '__main__':
    from pydatview.Tables import TableList
    from pydatview.plotdata import PlotData
    from pydatview.GUIPlotPanel import PlotPanel
    from pydatview.GUISelectionPanel import SelectionPanel


    # --- Data
    tabList   = TableList.createDummy(nTabs=2, n=100, addLabel=False)
    app = wx.App(False)
    self = wx.Frame(None,-1,"Data Binning GUI")

    # --- Panels
    self.selPanel = SelectionPanel(self, tabList, mode='auto')
    self.plotPanel = PlotPanel(self, self.selPanel)
    self.plotPanel.load_and_draw() # <<< Important
    self.selPanel.setRedrawCallback(self.plotPanel.load_and_draw) #  Binding the two

    p = BinningToolPanel(self.plotPanel, action=None)

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(self.selPanel ,0, wx.EXPAND|wx.ALL, border=5)
    sizer.Add(self.plotPanel,1, wx.EXPAND|wx.ALL, border=5)
    #sizer.Add(p)
    self.SetSizer(sizer)
    self.SetSize((900, 600))
    self.Center()
    self.Show()

    self.plotPanel.showToolPanel(panel=p)

    app.MainLoop()

    
