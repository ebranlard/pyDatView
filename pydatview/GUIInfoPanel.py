import wx
import wx.lib.mixins.listctrl as listmix
from wx.lib.buttons import GenButton
import numpy as np
try:
    from .common import *
    from .GUICommon import *
except:
    from common import *
    from GUICommon import *
import os
# --------------------------------------------------------------------------------}
# --- InfoPanel 
# --------------------------------------------------------------------------------{
#class TestListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
class TestListCtrl(wx.ListCtrl,listmix.ListRowHighlighter):
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        #listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.ListRowHighlighter.__init__(self)
        #self.setResizeColumn(0)



# --------------------------------------------------------------------------------}
# --- Popup menu 
# --------------------------------------------------------------------------------{
class ColCheckMenu(wx.Menu):
    def __init__(self,parent):
        wx.Menu.__init__(self)
        self.isClosed=True
        self.parent=parent
        self.Bind(wx.EVT_MENU, self.onSelChange)
        self.Bind(wx.EVT_UPDATE_UI, self.onUpdate)

    def onUpdate(self,event):
        pass
        #print('update')

    def setColumns(self,columns):
        for c in columns:
            it=self.Append(wx.ID_ANY, c['name'], kind=wx.ITEM_CHECK)
            if c['s']:
                self.Check(it.GetId(), True)

    def setItem(self, name, value):
        for it in self.GetMenuItems():
            if it.GetItemLabelText() == name:
                self.Check(it.GetId(), value)

    def getSelections(self):
        return [it.IsChecked() for it in self.GetMenuItems()]

    def onSelChange(self,event):
        self.isClosed=True
        for c,b in zip(self.parent.Cols,self.getSelections()):
            c['s']=b
        self.parent._showStats(erase=True)


class InfoPanel(wx.Panel):
    """ Display the list of the columns for the user to select """

    #----------------------------------------------------------------------
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        # ---
        # List of dictionaries for available "statistical" signals. Dictionary keys:
        #   name: name of statistics
        #   al  : alignement (L,R,C for left,right or center)
        #   f   : function used to evaluate value
        #   s   : selected or not
        self.ColsReg=[]
        self.ColsReg.append({'name':'Directory'    , 'al':'L' , 'm':'baseDir' , 's':False})
        self.ColsReg.append({'name':'Filename'     , 'al':'L' , 'm':'fileName', 's':False})
        self.ColsReg.append({'name':'Table'        , 'al':'L' , 'm':'tabName' , 's':False})
        self.ColsReg.append({'name':'Column'       , 'al':'L' , 'm':'yName'  , 's':True})
        self.ColsReg.append({'name':'Median'       , 'al':'R' , 'm':'yMedian' , 's' :False})
        self.ColsReg.append({'name':'Mean'         , 'al':'R' , 'm':'y0Mean'  , 's' :True})
        self.ColsReg.append({'name':'Std'          , 'al':'R' , 'm':'y0Std'   , 's' :True})
        self.ColsReg.append({'name':'Var'          , 'al':'R' , 'm':'y0Var' , 's' :False})
        self.ColsReg.append({'name':'Std/Mean (TI)', 'al':'R' , 'm':'y0TI'  , 's' :False})
        self.ColsReg.append({'name':'Min'          , 'al':'R' , 'm':'y0Min'  , 's' :True})
        self.ColsReg.append({'name':'Max'          , 'al':'R' , 'm':'y0Max'  , 's' :True})
        self.ColsReg.append({'name':'Abs. Max'     , 'al':'R' , 'm':'yAbsMax', 's' :False})
        self.ColsReg.append({'name':'Range'        , 'al':'R' , 'm':'yRange', 's' :True})
        self.ColsReg.append({'name':'dx'           , 'al':'R' , 'm':'dx'    , 's' :True})
        self.ColsReg.append({'name':'Meas 1'       , 'al':'R' , 'm':'meas'  , 's' :False})
        self.ColsReg.append({'name':'Meas 2'       , 'al':'R' , 'm':'meas'  , 's' :False})
        self.ColsReg.append({'name':'Mean (Meas)'  , 'al':'R' , 'm':'yMeanMeas'  , 's' :False})
        self.ColsReg.append({'name':'xMin'         , 'al':'R' , 'm':'xMin'  , 's' :False})
        self.ColsReg.append({'name':'xMax'         , 'al':'R' , 'm':'xMax'  , 's' :False})
        self.ColsReg.append({'name':'xRange'       , 'al':'R' , 'm':'xRange', 's' :False})
        self.ColsReg.append({'name':u'\u222By'         , 'al':'R' , 'm':'inty'          , 's' :False})
        self.ColsReg.append({'name':u'\u222By/\u222Bdx', 'al':'R' , 'm':'intyintdx'     , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x  '     , 'al':'R' , 'm':'intyx1'        , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x/\u222By','al':'R' , 'm':'intyx1_scaled' , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x^2'     , 'al':'R' , 'm':'intyx2'        , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=3)'    , 'al':'R' , 'f':lambda x:x.leq(m=3) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=4)'    , 'al':'R' , 'f':lambda x:x.leq(m=4) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=5)'    , 'al':'R' , 'f':lambda x:x.leq(m=5) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=7)'    , 'al':'R' , 'f':lambda x:x.leq(m=7) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=8)'    , 'al':'R' , 'f':lambda x:x.leq(m=8) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=9)'    , 'al':'R' , 'f':lambda x:x.leq(m=9) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=10)'   , 'al':'R' , 'f':lambda x:x.leq(m=10), 's' :False})
        self.ColsReg.append({'name':'L_eq(m=12)'   , 'al':'R' , 'f':lambda x:x.leq(m=12), 's' :False})
        self.ColsReg.append({'name':'n'            , 'al':'R' , 'm':'ylen'   , 's' :True})
        self.ColsFFT=[]
        self.ColsFFT.append({'name':'Directory'    , 'al':'L' , 'm':'baseDir' , 's':False})
        self.ColsFFT.append({'name':'Filename'     , 'al':'L' , 'm':'fileName', 's':False})
        self.ColsFFT.append({'name':'Table'        , 'al':'L' , 'm':'tabName' , 's':False})
        self.ColsFFT.append({'name':'Column'        , 'al':'L' , 'm':'yName'  , 's':True})
        self.ColsFFT.append({'name':'Mean'          , 'al':'R' , 'm':'y0Mean' , 's' :True})
        self.ColsFFT.append({'name':'Std'           , 'al':'R' , 'm':'y0Std'  , 's' :True})
        self.ColsFFT.append({'name':'Min'           , 'al':'R' , 'm':'y0Min'  , 's' :True})
        self.ColsFFT.append({'name':'Max'           , 'al':'R' , 'm':'y0Max'  , 's' :True})
        self.ColsFFT.append({'name':'Mean(FFT)'     , 'al':'R' , 'm':'yMean'  , 's' :False})
        self.ColsFFT.append({'name':'Std(FFT)'      , 'al':'R' , 'm':'yStd'   , 's' :False})
        self.ColsFFT.append({'name':'Min(FFT)'      , 'al':'R' , 'm':'yMin'   , 's' :True})
        self.ColsFFT.append({'name':'Max(FFT)'      , 'al':'R' , 'm':'yMax'   , 's' :True})
        self.ColsFFT.append({'name':'Var'           , 'al':'R' , 'm':'y0Var'  , 's' :False})
        self.ColsFFT.append({'name':u'\u222By(FFT)' , 'al':'R' , 'm':'inty'   , 's' :True})
        self.ColsFFT.append({'name':'dx(FFT)'       , 'al':'R' , 'm':'dx'     , 's' :True})
        self.ColsFFT.append({'name':'xMax(FFT)'     , 'al':'R' , 'm':'xMax'   , 's' :True})
        self.ColsFFT.append({'name':'nOvlp(FFT)'    , 'al':'R' , 'f':lambda x:x.Info('LOvlp') , 's' :False})
        self.ColsFFT.append({'name':'nSeg(FFT)'     , 'al':'R' , 'f':lambda x:x.Info('LSeg')  , 's' :False})
        self.ColsFFT.append({'name':'nWin(FFT)'     , 'al':'R' , 'f':lambda x:x.Info('LWin')  , 's' :False})
        self.ColsFFT.append({'name':'nFFT(FFT)'     , 'al':'R' , 'f':lambda x:x.Info('nFFT')  , 's' :False})
        self.ColsFFT.append({'name':'n(FFT)'        , 'al':'R' , 'm':'ylen'  , 's' :True})
        self.ColsFFT.append({'name':'Meas 1'        , 'al':'R' , 'm':'meas'  , 's' :False})
        self.ColsFFT.append({'name':'Meas 2'        , 'al':'R' , 'm':'meas'  , 's' :False})
        self.ColsFFT.append({'name':'n     '        , 'al':'R' , 'm':'n0'    , 's' :True})
        self.ColsMinMax=[]
        self.ColsMinMax.append({'name':'Directory'                  , 'al':'L' , 'm':'baseDir', 's':False})
        self.ColsMinMax.append({'name':'Filename'                   , 'al':'L' , 'm':'fileName', 's':False})
        self.ColsMinMax.append({'name':'Table'                      , 'al':'L' , 'm':'tabName' , 's':False})
        self.ColsMinMax.append({'name':'Column'                     , 'al':'L' , 'm':'yName'  , 's':True})
        self.ColsMinMax.append({'name':'Mean'                       , 'al':'R' , 'm':'y0Mean' , 's' :True})
        self.ColsMinMax.append({'name':'Std'                        , 'al':'R' , 'm':'y0Std'  , 's' :True})
        self.ColsMinMax.append({'name':'Min'                        , 'al':'R' , 'm':'y0Min'  , 's' :True})
        self.ColsMinMax.append({'name':'Max'                        , 'al':'R' , 'm':'y0Max'  , 's' :True})
        self.ColsMinMax.append({'name':'Mean(MinMax)'               , 'al':'R' , 'm':'yMean'  , 's' :True})
        self.ColsMinMax.append({'name':'Std(MinMax)'                , 'al':'R' , 'm':'yStd'   , 's' :True})
        self.ColsMinMax.append({'name':u'\u222By(MinMax)'           , 'al':'R' , 'm':'inty' , 's' :True})
        self.ColsMinMax.append({'name':u'\u222By.x(MinMax)  '       , 'al':'R' , 'm':'intyx1' , 's' :False})
        self.ColsMinMax.append({'name':u'\u222By.x/\u222By(MinMax)' , 'al':'R' , 'm':'intyx1_scaled' , 's' :False})
        self.ColsMinMax.append({'name':u'\u222By.x^2(MinMax)'       , 'al':'R' , 'm':'intyx2' , 's' :False})
        self.ColsMinMax.append({'name':'dx(MinMax)'                 , 'al':'R' , 'm':'dx'     , 's' :False})
        self.ColsMinMax.append({'name':'n'                          , 'al':'R' , 'm':'ylen'   , 's' :True})
        self.ColsPDF=[]
        self.ColsPDF.append({'name':'Directory'     , 'al':'L' , 'm':'baseDir' , 's':False})
        self.ColsPDF.append({'name':'Filename'      , 'al':'L' , 'm':'fileName', 's':False})
        self.ColsPDF.append({'name':'Table'         , 'al':'L' , 'm':'tabName' , 's':False})
        self.ColsPDF.append({'name':'Column'        , 'al':'L' , 'm':'yName'  , 's':True})
        self.ColsPDF.append({'name':'Mean'          , 'al':'R' , 'm':'y0Mean' , 's' :True})
        self.ColsPDF.append({'name':'Std'           , 'al':'R' , 'm':'y0Std'  , 's' :True})
        self.ColsPDF.append({'name':'Min'           , 'al':'R' , 'm':'y0Min'  , 's' :True})
        self.ColsPDF.append({'name':'Max'           , 'al':'R' , 'm':'y0Max'  , 's' :True})
        self.ColsPDF.append({'name':'Mean(PDF)'     , 'al':'R' , 'm':'yMean'  , 's' :False})
        self.ColsPDF.append({'name':'Std(PDF)'      , 'al':'R' , 'm':'yStd'  , 's' :False})
        self.ColsPDF.append({'name':'Min(PDF)'      , 'al':'R' , 'm':'yMin'  , 's' :True})
        self.ColsPDF.append({'name':'Max(PDF)'      , 'al':'R' , 'm':'yMax'  , 's' :True})
        self.ColsPDF.append({'name':u'\u222By(PDF)' , 'al':'R' , 'm':'inty'  , 's' :True})
        self.ColsPDF.append({'name':'Meas 1'        , 'al':'R' , 'm':'meas'  , 's' :False})
        self.ColsPDF.append({'name':'Meas 2'        , 'al':'R' , 'm':'meas'  , 's' :False})
        self.ColsPDF.append({'name':'n(PDF)'        , 'al':'R' , 'm':'ylen'  , 's' :True})
        self.ColsCmp=[]
        self.ColsCmp.append({'name':'Directory' , 'al':'L' , 'm':'baseDir' , 's':False})
        self.ColsCmp.append({'name':'Filename'  , 'al':'L' , 'm':'fileName', 's':False})
        self.ColsCmp.append({'name':'Table'     , 'al':'L' , 'm':'tabName' , 's':False})
        self.ColsCmp.append({'name':'Column'    , 'al':'L' , 'm':'yName'   ,'s':True})
        self.ColsCmp.append({'name':'Mean(Cmp)' , 'al':'R' , 'm':'yMean'  , 's' :True})
        self.ColsCmp.append({'name':'Std(Cmp)'  , 'al':'R' , 'm':'yStd'   , 's' :True})
        self.ColsCmp.append({'name':'Min(Cmp)'  , 'al':'R' , 'm':'yMin'   , 's' :True})
        self.ColsCmp.append({'name':'Max(Cmp)'  , 'al':'R' , 'm':'yMax'   , 's' :True})
        self.ColsCmp.append({'name':'n(Cmp)'    , 'al':'R' , 'm':'ylen'   , 's' :True})

        self.menuReg=ColCheckMenu(self)
        self.menuReg.setColumns(self.ColsReg)
        self.menuFFT=ColCheckMenu(self)
        self.menuFFT.setColumns(self.ColsFFT)
        self.menuPDF=ColCheckMenu(self)
        self.menuPDF.setColumns(self.ColsPDF)
        self.menuMinMax=ColCheckMenu(self)
        self.menuMinMax.setColumns(self.ColsMinMax)
        self.menuCmp=ColCheckMenu(self)
        self.menuCmp.setColumns(self.ColsCmp)

        self.Cols=self.ColsReg
        self.menu=self.menuReg
        self.PD=[]
        self.tab_mode = None
        self.last_sub = False
        self.meas_xy1 = (None, None)
        self.meas_xy2 = (None, None)

        self.tbStats = TestListCtrl(self, size=(-1,100),
                         style=wx.LC_REPORT
                         |wx.BORDER_SUNKEN
                         )
                         #|wx.LC_SORT_ASCENDING
        self.tbStats.SetFont(getMonoFont(self))
        # For sorting see wx/lib/mixins/listctrl.py listmix.ColumnSorterMixin
        #self.tbStats.Bind(wx.EVT_LIST_COL_CLICK, self.CopyToClipBoard)
        self.tbStats.Bind(wx.EVT_LIST_ITEM_SELECTED, self.CopyToClipBoard)
        # self.tbStats.Bind(wx.EVT_RIGHT_UP, self.ShowPopup)


        sizer = wx.BoxSizer(wx.HORIZONTAL)
        # sizer.Add(self.bt     , 0, wx.LEFT, border=0)

        sizer_plot_matrix = wx.BoxSizer(wx.VERTICAL)
        sizer_plot_matrix_spacer = wx.BoxSizer(wx.VERTICAL)
        plot_matrix_spacer= wx.Panel(self, size=(-1, 27))

        # self.bt = wx.Button(plot_matrix_spacer, -1, u'\u22EE', style=wx.BU_EXACTFIT)
        self.bt = wx.Button(plot_matrix_spacer, -1, u'\u2630', style=wx.BU_EXACTFIT)
        self.bt.Bind(wx.EVT_BUTTON, self.showMenu)
        sizer_plot_matrix_spacer.Add(self.bt     , 0, wx.TOP, border=0)
        plot_matrix_spacer.SetSizer(sizer_plot_matrix_spacer)

        plot_matrix_sizer  = wx.FlexGridSizer(rows=1, cols=1, hgap=0, vgap=9)
        self.plotMatrixPanel= wx.Panel(self)
        self.plotMatrixPanel.SetSizer(plot_matrix_sizer)
        self.plotMatrixPanel.Hide()

        sizer_plot_matrix.Add(plot_matrix_spacer     , 0, wx.TOP, border=0)
        sizer_plot_matrix.Add(self.plotMatrixPanel   , 0, wx.TOP, border=0)

        sizer.Add(sizer_plot_matrix, 0, wx.LEFT, border=0)
        sizer.Add(self.tbStats, 2, wx.LEFT|wx.RIGHT|wx.EXPAND, border=3)
        self.SetSizer(sizer)
        self.SetMaxSize((-1, 50))

    def CopyToClipBoard(self, event):
        nCols=self.tbStats.GetColumnCount()
        headerLine='\t'.join([self.tbStats.GetColumn(j).GetText() for j in np.arange(nCols)] )
        lines=[headerLine]
        # Loop on rows
        for i in np.arange(self.tbStats.GetItemCount()):
            if self.tbStats.IsSelected(i):
                line='\t'.join([self.tbStats.GetItemText(i,j) for j in np.arange(nCols)] )
                lines.append(line)
        # Put in ClipBoard
        clipdata = wx.TextDataObject()
        clipdata.SetText("\n".join(lines))
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()

    def showMenu(self,event=None):
        if self.menu.isClosed:
            pos = (self.bt.GetPosition()[0], self.bt.GetPosition()[1] + self.bt.GetSize()[1])
            self.menu.isClosed=False
            self.menu.ShouldNotBeTrue=True
            self.PopupMenu(self.menu, pos)
        else:
            self.menu.isClosed=True

    def showStats(self,PD,plotType='Regular',erase=True):
        #        if files is not None:
        #            for i,f in enumerate(files):
        #                self.tInfo.AppendText('File {}: {}\n'.format(i,f))

        if plotType=='Regular':
            self.menu=self.menuReg
            self.Cols=self.ColsReg
        elif plotType=='PDF':
            self.menu=self.menuPDF
            self.Cols=self.ColsPDF
        elif plotType=='MinMax':
            self.menu=self.menuMinMax
            self.Cols=self.ColsMinMax
        elif plotType=='Compare':
            self.menu=self.menuCmp
            self.Cols=self.ColsCmp
        elif plotType=='FFT':
            self.menu=self.menuFFT
            self.Cols=self.ColsFFT
        else:
            raise Exception('Unsupported plotType')
        self.PD=PD
        self._showStats(erase=erase)

    def _showStats(self,erase=True):
        self.Freeze()
        selCols=[c for c in self.Cols if c['s']]
        # Adding columns
        if erase:
            self.clean()
            AL={'L':wx.LIST_FORMAT_LEFT,'R':wx.LIST_FORMAT_RIGHT,'C':wx.LIST_FORMAT_CENTER}
            for i,c in enumerate(selCols):
                if c['s']:
                    self.tbStats.InsertColumn(i,c['name'], AL[c['al']])
        # Inserting items
        index = self.tbStats.GetItemCount()
        for PD in self.PD:
            for j,c in enumerate(selCols):
                # TODO: could be nicer:
                if 'm' in c.keys():
                    if c['name'] == 'Meas 1':
                        v,sv=getattr(PD,c['m'])(self.meas_xy1)
                    elif c['name'] == 'Meas 2':
                        v,sv=getattr(PD,c['m'])(self.meas_xy2)
                    elif c['name'] == 'Mean (Meas)':
                        v, sv = getattr(PD, c['m'])(self.meas_xy1, self.meas_xy2)
                    else:
                        v,sv=getattr(PD,c['m'])()
                else:
                    v,sv=c['f'](PD)

                try:
                    if j==0:
                        self.tbStats.InsertItem(index,  sv)
                    else:
                        self.tbStats.SetItem(index, j,sv)
                except:
                    if j==0:
                        self.tbStats.InsertStringItem(index,  sv)
                    else:
                        self.tbStats.SetStringItem(index, j,sv)
            index +=1

        for i in range(self.tbStats.GetColumnCount()):
            self.tbStats.SetColumnWidth(i, wx.LIST_AUTOSIZE_USEHEADER) 
        self.tbStats.RefreshRows()
        self.Thaw()


    def setPlotMatrixCallbacks(self, callback_left, callback_right):
        self._onPlotMatrixLeftClick = callback_left
        self._onPlotMatrixRightClick = callback_right

    def _onLeftClick(self, event):
        self._onPlotMatrixLeftClick(event)
        self.Refresh()

    def _onRightClick(self, event):
        self._onPlotMatrixRightClick(event)
        self.Refresh()

    def togglePlotMatrix(self, visibility):
        if visibility:
            self.plotMatrixPanel.Show()
        else:
            self.plotMatrixPanel.Hide()
        self.Layout()
        self.Refresh()
        self.Update()

    def setTabMode(self, mode):
        self.tab_mode = mode

    def recreatePlotMatrixPanel(self, PD, sub):
        nr_signals = len(PD)
        plot_matrix_sizer  = wx.FlexGridSizer(rows=nr_signals, cols=nr_signals, hgap=0, vgap=3)
        self.plotMatrixPanel.DestroyChildren()
        if os.name == 'nt':
            BUTTON_SIZE = 17
        else:
            BUTTON_SIZE = 21
        for i in range(nr_signals ** 2):
            buttonLabel = "-"
            showButton = False
            if sub:
                showButton = True
                # Square matrix: up to n subplots
                if (i % nr_signals) == int(i / nr_signals):
                    buttonLabel = '1'
            else:
                # Single column: single plot
                if (i % nr_signals) == 0:
                    buttonLabel = '1'
                    showButton = True
            btn = GenButton(self.plotMatrixPanel, label=buttonLabel, size=(BUTTON_SIZE, BUTTON_SIZE), style=wx.BU_EXACTFIT)
            btn.Bind(wx.EVT_BUTTON, self._onLeftClick)
            btn.Bind(wx.EVT_CONTEXT_MENU, self._onRightClick)
            
            if showButton is False:
                btn.Hide()
            plot_matrix_sizer.Add(btn)
        self.plotMatrixPanel.SetSizer(plot_matrix_sizer)
        self.Layout()
        self.Refresh()
        self.Update()

    def getNumberOfSubplots(self, PD, sub):
        """Maximum length is len(PD).
         If the selection has no entry for a column,
         the number of subplots is reduced accordingly.
         This is only allowed for the most outer subplots.
        """
        nr_signals = len(PD)
        used_subplots = [0] * nr_signals
        if nr_signals ** 2 != len(self.plotMatrixPanel.Children) or sub != self.last_sub:
            self.recreatePlotMatrixPanel(PD, sub)
        self.last_sub = sub
        for i in range(nr_signals ** 2):
            # iterate over rows where each corresponds to one signal
            subplot = i % nr_signals
            selection = self.plotMatrixPanel.Children[i].GetLabelText()
            if selection == '1' or selection == '2':
                used_subplots[subplot] = 1
        if sub is False and sum(used_subplots) == 0 and self.tab_mode == '1Tab_nCols':
            # Without subplot at least one signal must be selected
            raise IndexError
        return len([i for i, e in enumerate(used_subplots) if e != 0])
    
    def getPlotMatrix(self, PD, sub):
        """Plot_matrix is nr_signals x nr_subplots.
         Each column represents one subplot and each
         row/pair value represents signal-index that
         needs to be plotted: 1 -> left, 2 -> right, 0 -> not.
        """
        if not self.plotMatrixPanel.IsShown():
            # keep panel, display plots normally
            plot_matrix = None
        else:
            nr_signals = len(PD)
            nr_subplots = self.getNumberOfSubplots(PD, sub)
            plot_matrix  = [[0 for x in range(nr_subplots)] for y in range(nr_signals)]
            for i in range(nr_signals ** 2):
                # iterate over rows where each corresponds to one signal
                subplot = i % nr_signals
                signal = int(i / nr_signals)
                selection = self.plotMatrixPanel.Children[i].GetLabelText()
                if selection == '1':
                    plot_matrix[signal][subplot] = 1
                elif selection == '2':
                    plot_matrix[signal][subplot] = 2
        return plot_matrix
    
    def setCol(self, name, value):
        for c in self.Cols:
            if c['name'] == name:
                c['s'] = value

    def setMeasurements(self, xy1, xy2):
        if xy1 is not None:
            self.meas_xy1 = xy1
            self.menu.setItem('Meas 1', True)
            self.setCol('Meas 1', True)
        if xy2 is not None:
            self.meas_xy2 = xy2
            self.menu.setItem('Meas 2', True)
            self.setCol('Meas 2', True)
            self.menu.setItem('Mean (Meas)', True)
            self.setCol('Mean (Meas)', True)
        elif xy1 is None:
            self.menu.setItem('Meas 1', False)
            self.setCol('Meas 1', False)
            self.menu.setItem('Meas 1', False)
            self.setCol('Meas 2', False)
            self.menu.setItem('Mean (Meas)', False)
            self.setCol('Mean (Meas)', False)
        self._showStats()

    def clean(self):
        self.tbStats.DeleteAllItems()
        self.tbStats.DeleteAllColumns()

    def empty(self):
        self.clean()
        self.PD=[]

if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table

    app = wx.App(False)
    self=wx.Frame(None,-1,"Title")
    p1=InfoPanel(self)
    self.SetSize((800, 600))
    self.Center()
    self.Show()

    d ={'ColA': np.random.normal(0,1,100)+1,'ColB':np.random.normal(0,1,100)+2}
    df = pd.DataFrame(data=d)
    tab=Table(data=df)
    p1.showStats(None,[tab],[0],[0,1],tab.columns,0,erase=True)

    app.MainLoop()

