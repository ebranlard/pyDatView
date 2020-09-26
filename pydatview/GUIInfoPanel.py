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
    from fatigue import eq_load

from .fatigue import eq_load
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
# --- Stats functions
# --------------------------------------------------------------------------------{
def yName(pd):
    return pd.sy, pd.sy

def fileName(pd):
    return os.path.basename(pd.filename), os.path.basename(pd.filename)

def baseDir(pd):
    return os.path.dirname(pd.filename),os.path.join(os.path.dirname(pd.filename),'')

def tabName(pd):
    return pd.tabname, pd.tabname

def ylen(pd):
    v=len(pd.y)
    s='{:d}'.format(v)
    return v,s

def y0Mean(pd):
    v=pd.y0Mean[0]
    s=pd.y0Mean[1]
    return v,s

def n0(pd):
    v=pd.n0[0]
    s=pd.n0[1]
    return v,s

def y0Std(pd):
    v=pd.y0Std[0]
    s=pd.y0Std[1]
    return v,s

def y0Var(pd):
    if pd.y0Std[0] is not None: 
        v=pd.y0Std[0]**2
        s=pretty_num(v)
    else:
        v=None
        s='NA'
    return v,s

def y0TI(pd):
    v=pd.y0Std[0]/pd.y0Mean[0]
    s=pretty_num(v)
    return v,s

def y0Min(pd):
    v=pd.y0Min[0]
    s=pd.y0Min[1]
    return v,s

def y0Max(pd):
    v=pd.y0Max[0]
    s=pd.y0Max[1]
    return v,s

def yRange(pd):
    if pd.yIsString:
        return 'NA','NA'
    elif pd.yIsDate:
        dtAll=getDt([pd.x[-1]-pd.x[0]])
        return '',pretty_time(dtAll)
    else:
        v=np.nanmax(pd.y)-np.nanmin(pd.y)
        s=pretty_num(v)
    return v,s

def xRange(pd):
    if pd.xIsString:
        return 'NA','NA'
    elif pd.xIsDate:
        dtAll=getDt([pd.x[-1]-pd.x[0]])
        return '',pretty_time(dtAll)
    else:
        v=np.nanmax(pd.x)-np.nanmin(pd.x)
        s=pretty_num(v)
    return v,s


def inty(pd):
    if pd.yIsString or pd.yIsDate or pd.xIsString or pd.xIsDate:
        return None,'NA'
    else:
        v=np.trapz(y=pd.y,x=pd.x)
        s=pretty_num(v)
    return v,s

def intyintdx(pd):
    if pd.yIsString or pd.yIsDate or pd.xIsString or pd.xIsDate:
        return None,'NA'
    else:
        v=np.trapz(y=pd.y,x=pd.x)/np.trapz(y=pd.x*0+1,x=pd.x)
        s=pretty_num(v)
    return v,s

def intyx1(pd):
    if pd.yIsString or pd.yIsDate or pd.xIsString or pd.xIsDate:
        return None,'NA'
    else:
        v=np.trapz(y=pd.y*pd.x,x=pd.x)
        s=pretty_num(v)
    return v,s

def intyx1_scaled(pd):
    if pd.yIsString or pd.yIsDate or pd.xIsString or pd.xIsDate:
        return None,'NA'
    else:
        v=np.trapz(y=pd.y*pd.x,x=pd.x)
        v=v/np.trapz(y=pd.y,x=pd.x)
        s=pretty_num(v)
    return v,s

def intyx2(pd):
    if pd.yIsString or pd.yIsDate or pd.xIsString or pd.xIsDate:
        return None,'NA'
    else:
        v=np.trapz(y=pd.y*pd.x**2,x=pd.x)
        s=pretty_num(v)
    return v,s

def dx(pd):
    if len(pd.x)<=1:
        return 'NA','NA'
    if pd.xIsString:
        return None,'NA'
    elif  pd.xIsDate:
        dt=getDt(pd.x)
        return dt,pretty_time(dt)
    else:
        v=pd.x[1]-pd.x[0]
        s=pretty_num(v)
        return v,s

def xMax(pd):
    if pd.xIsString:
        return pd.x[-1],pd.x[-1]
    elif  pd.xIsDate:
        return pd.x[-1],'{}'.format(pd.x[-1])
    else:
        v=np.nanmax(pd.x)
        s=pretty_num(v)
        return v,s
def xMin(pd):
    if pd.xIsString:
        return pd.x[0],pd.x[0]
    elif  pd.xIsDate:
        return pd.x[0],'{}'.format(pd.x[0])
    else:
        v=np.nanmin(pd.x)
        s=pretty_num(v)
        return v,s

def leq(pd,m):
    if pd.yIsString or  pd.yIsDate:
        return 'NA','NA'
    else:
        T,_=xRange(pd)
        v=eq_load(pd.y, m=m, neq=T)[0][0]
        return v,pretty_num(v)

def Info(pd,var):
    if var=='LSeg':
        return '','{:d}'.format(pd.Info.LSeg)
    elif var=='LWin':
        return '','{:d}'.format(pd.Info.LWin)
    elif var=='LOvlp':
        return '','{:d}'.format(pd.Info.LOvlp)
    elif var=='nFFT':
        return '','{:d}'.format(pd.Info.nFFT)




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
        self.ColsReg.append({'name':'Directory'    , 'al':'L' , 'f':baseDir , 's':False})
        self.ColsReg.append({'name':'Filename'     , 'al':'L' , 'f':fileName, 's':False})
        self.ColsReg.append({'name':'Table'        , 'al':'L' , 'f':tabName , 's':False})
        self.ColsReg.append({'name':'Column'       , 'al':'L' , 'f':yName  , 's':True})
        self.ColsReg.append({'name':'Mean'         , 'al':'R' , 'f':y0Mean  , 's' :True})
        self.ColsReg.append({'name':'Std'          , 'al':'R' , 'f':y0Std   , 's' :True})
        self.ColsReg.append({'name':'Var'          , 'al':'R' , 'f':y0Var  , 's' :False})
        self.ColsReg.append({'name':'Std/Mean (TI)', 'al':'R' , 'f':y0TI   , 's' :False})
        self.ColsReg.append({'name':'Min'          , 'al':'R' , 'f':y0Min   , 's' :True})
        #self.ColsReg.append({'name':'Max'         , 'al':'R' , 'f':y0Max  , 's' :True})
        self.ColsReg.append({'name':'Max'          , 'al':'R' , 'f':y0Max   , 's' :True})
        self.ColsReg.append({'name':'Range'        , 'al':'R' , 'f':yRange , 's' :True})
        self.ColsReg.append({'name':'dx'           , 'al':'R' , 'f':dx     , 's' :True})
        self.ColsReg.append({'name':'xMin'         , 'al':'R' , 'f':xMin   , 's' :False})
        self.ColsReg.append({'name':'xMax'         , 'al':'R' , 'f':xMax   , 's' :False})
        self.ColsReg.append({'name':'xRange'       , 'al':'R' , 'f':xRange , 's' :False})
        self.ColsReg.append({'name':u'\u222By'     , 'al':'R' , 'f':inty   , 's' :False})
        self.ColsReg.append({'name':u'\u222By/\u222Bdx', 'al':'R' , 'f':intyintdx   , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x  ' , 'al':'R' , 'f':intyx1 , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x/\u222By' , 'al':'R' , 'f':intyx1_scaled , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x^2' , 'al':'R' , 'f':intyx2 , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=3)'    , 'al':'R' , 'f':lambda x:leq(x,m=3) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=4)'    , 'al':'R' , 'f':lambda x:leq(x,m=4) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=5)'    , 'al':'R' , 'f':lambda x:leq(x,m=5) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=7)'    , 'al':'R' , 'f':lambda x:leq(x,m=7) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=8)'    , 'al':'R' , 'f':lambda x:leq(x,m=8) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=9)'    , 'al':'R' , 'f':lambda x:leq(x,m=9) , 's' :False})
        self.ColsReg.append({'name':'L_eq(m=10)'   , 'al':'R' , 'f':lambda x:leq(x,m=10), 's' :False})
        self.ColsReg.append({'name':'L_eq(m=12)'   , 'al':'R' , 'f':lambda x:leq(x,m=12), 's' :False})
        self.ColsReg.append({'name':'n'            , 'al':'R' , 'f':ylen   , 's' :True})
        self.ColsFFT=[]
        self.ColsFFT.append({'name':'Directory'    , 'al':'L' , 'f':baseDir , 's':False})
        self.ColsFFT.append({'name':'Filename'     , 'al':'L' , 'f':fileName, 's':False})
        self.ColsFFT.append({'name':'Table'        , 'al':'L' , 'f':tabName , 's':False})
        self.ColsFFT.append({'name':'Column'        , 'al':'L' , 'f':yName  , 's':True})
        self.ColsFFT.append({'name':'Mean'          , 'al':'R' , 'f':y0Mean , 's' :True})
        self.ColsFFT.append({'name':'Std'           , 'al':'R' , 'f':y0Std  , 's' :True})
        self.ColsFFT.append({'name':'Min'           , 'al':'R' , 'f':y0Min  , 's' :True})
        self.ColsFFT.append({'name':'Max'           , 'al':'R' , 'f':y0Max  , 's' :True})
        self.ColsFFT.append({'name':'Mean(FFT)'     , 'al':'R' , 'f':yMean  , 's' :False})
        self.ColsFFT.append({'name':'Std(FFT)'      , 'al':'R' , 'f':yStd   , 's' :False})
        self.ColsFFT.append({'name':'Min(FFT)'      , 'al':'R' , 'f':yMin   , 's' :True})
        self.ColsFFT.append({'name':'Max(FFT)'      , 'al':'R' , 'f':yMax   , 's' :True})
        self.ColsFFT.append({'name':'Var'           , 'al':'R' , 'f':y0Var  , 's' :False})
        self.ColsFFT.append({'name':u'\u222By(FFT)' , 'al':'R' , 'f':inty   , 's' :True})
        self.ColsFFT.append({'name':'dx(FFT)'       , 'al':'R' , 'f':dx     , 's' :True})
        self.ColsFFT.append({'name':'xMax(FFT)'     , 'al':'R' , 'f':xMax   , 's' :True})
        self.ColsFFT.append({'name':'nOvlp(FFT)'    , 'al':'R' , 'f':lambda x:Info(x,'LOvlp') , 's' :False})
        self.ColsFFT.append({'name':'nSeg(FFT)'     , 'al':'R' , 'f':lambda x:Info(x,'LSeg')  , 's' :False})
        self.ColsFFT.append({'name':'nWin(FFT)'     , 'al':'R' , 'f':lambda x:Info(x,'LWin')  , 's' :False})
        self.ColsFFT.append({'name':'nFFT(FFT)'     , 'al':'R' , 'f':lambda x:Info(x,'nFFT')  , 's' :False})
        self.ColsFFT.append({'name':'n(FFT)'        , 'al':'R' , 'f':ylen   , 's' :True})
        self.ColsFFT.append({'name':'n     '        , 'al':'R' , 'f':n0     , 's' :True})
        self.ColsMinMax=[]
        self.ColsMinMax.append({'name':'Directory'                  , 'al':'L' , 'f':baseDir , 's':False})
        self.ColsMinMax.append({'name':'Filename'                   , 'al':'L' , 'f':fileName, 's':False})
        self.ColsMinMax.append({'name':'Table'                      , 'al':'L' , 'f':tabName , 's':False})
        self.ColsMinMax.append({'name':'Column'                     , 'al':'L' , 'f':yName  , 's':True})
        self.ColsMinMax.append({'name':'Mean'                       , 'al':'R' , 'f':y0Mean , 's' :True})
        self.ColsMinMax.append({'name':'Std'                        , 'al':'R' , 'f':y0Std  , 's' :True})
        self.ColsMinMax.append({'name':'Min'                        , 'al':'R' , 'f':y0Min  , 's' :True})
        self.ColsMinMax.append({'name':'Max'                        , 'al':'R' , 'f':y0Max  , 's' :True})
        self.ColsMinMax.append({'name':'Mean(MinMax)'               , 'al':'R' , 'f':yMean  , 's' :True})
        self.ColsMinMax.append({'name':'Std(MinMax)'                , 'al':'R' , 'f':yStd   , 's' :True})
        self.ColsMinMax.append({'name':u'\u222By(MinMax)'           , 'al':'R' , 'f':inty , 's' :True})
        self.ColsMinMax.append({'name':u'\u222By.x(MinMax)  '       , 'al':'R' , 'f':intyx1 , 's' :False})
        self.ColsMinMax.append({'name':u'\u222By.x/\u222By(MinMax)' , 'al':'R' , 'f':intyx1_scaled , 's' :False})
        self.ColsMinMax.append({'name':u'\u222By.x^2(MinMax)'       , 'al':'R' , 'f':intyx2 , 's' :False})
        self.ColsMinMax.append({'name':'dx(MinMax)'                 , 'al':'R' , 'f':dx     , 's' :False})
        self.ColsMinMax.append({'name':'n'                          , 'al':'R' , 'f':ylen   , 's' :True})
        self.ColsPDF=[]
        self.ColsPDF.append({'name':'Directory'    , 'al':'L' , 'f':baseDir , 's':False})
        self.ColsPDF.append({'name':'Filename'     , 'al':'L' , 'f':fileName, 's':False})
        self.ColsPDF.append({'name':'Table'        , 'al':'L' , 'f':tabName , 's':False})
        self.ColsPDF.append({'name':'Column'        , 'al':'L' , 'f':yName  , 's':True})
        self.ColsPDF.append({'name':'Mean'          , 'al':'R' , 'f':y0Mean , 's' :True})
        self.ColsPDF.append({'name':'Std'           , 'al':'R' , 'f':y0Std  , 's' :True})
        self.ColsPDF.append({'name':'Min'           , 'al':'R' , 'f':y0Min  , 's' :True})
        self.ColsPDF.append({'name':'Max'           , 'al':'R' , 'f':y0Max  , 's' :True})
        self.ColsPDF.append({'name':'Mean(PDF)'     , 'al':'R' , 'f':yMean  , 's' :False})
        self.ColsPDF.append({'name':'Std(PDF)'      , 'al':'R' , 'f':yStd   , 's' :False})
        self.ColsPDF.append({'name':'Min(PDF)'      , 'al':'R' , 'f':yMin   , 's' :True})
        self.ColsPDF.append({'name':'Max(PDF)'      , 'al':'R' , 'f':yMax   , 's' :True})
        self.ColsPDF.append({'name':u'\u222By(PDF)' , 'al':'R' , 'f':inty   , 's' :True})
        self.ColsPDF.append({'name':'n(PDF)'        , 'al':'R' , 'f':ylen   , 's' :True})
        self.ColsCmp=[]
        self.ColsCmp.append({'name':'Directory'    , 'al':'L' , 'f':baseDir , 's':False})
        self.ColsCmp.append({'name':'Filename'     , 'al':'L' , 'f':fileName, 's':False})
        self.ColsCmp.append({'name':'Table'        , 'al':'L' , 'f':tabName , 's':False})
        self.ColsCmp.append({'name':'Column','al':'L','f':yName ,'s':True})
        self.ColsCmp.append({'name':'Mean(Cmp)' , 'al':'R' , 'f':yMean  , 's' :True})
        self.ColsCmp.append({'name':'Std(Cmp)'  , 'al':'R' , 'f':yStd   , 's' :True})
        self.ColsCmp.append({'name':'Min(Cmp)'  , 'al':'R' , 'f':yMin   , 's' :True})
        self.ColsCmp.append({'name':'Max(Cmp)'  , 'al':'R' , 'f':yMax   , 's' :True})
        self.ColsCmp.append({'name':'n(Cmp)'    , 'al':'R' , 'f':ylen   , 's' :True})

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

        #self.bt = wx.Button(self, -1, u'\u22EE',style=wx.BU_EXACTFIT)
        self.bt = wx.Button(self, -1, u'\u2630',style=wx.BU_EXACTFIT)
        self.bt.Bind(wx.EVT_BUTTON, self.showMenu)

        self.tbStats = TestListCtrl(self, size=(-1,100),
                         style=wx.LC_REPORT
                         |wx.BORDER_SUNKEN
                         )
                         #|wx.LC_SORT_ASCENDING
        self.tbStats.SetFont(getMonoFont(self))
        # For sorting see wx/lib/mixins/listctrl.py listmix.ColumnSorterMixin
        #self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.tbStats)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.bt     , 0, wx.LEFT, border=0)

        sizer_plot_matrix = wx.BoxSizer(wx.VERTICAL)
        sizer_plot_matrix_spacer = wx.BoxSizer(wx.VERTICAL)
        plot_matrix_spacer= wx.Panel(self, size=(-1, 27))
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
        for pd in self.PD:
            for j,c in enumerate(selCols):
                v,sv=c['f'](pd)
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
        self._OnPlotMatrixLeftClick = callback_left
        self._OnPlotMatrixRightClick = callback_right

    def _OnLeftClick(self, event):
        self._OnPlotMatrixLeftClick(event)
        self.Refresh()

    def _OnRightClick(self, event):
        self._OnPlotMatrixRightClick(event)
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
            btn.Bind(wx.EVT_BUTTON, self._OnLeftClick)
            btn.Bind(wx.EVT_CONTEXT_MENU, self._OnRightClick)
            
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
         This is only valid in tab-mode == '1Tab_nCols'.
        """
        if self.tab_mode == '1Tab_nCols':
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
        else:
            # Destroy plot matrix panel
            self.getNumberOfSubplots([], sub)
            plot_matrix = None
        return plot_matrix

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

