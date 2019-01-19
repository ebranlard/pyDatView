import wx
import wx.lib.mixins.listctrl as listmix
import numpy as np
try:
    from .common import *
except:
    from common import *

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

def y0Min(pd):
    v=pd.y0Min[0]
    s=pd.y0Min[1]
    return v,s

def y0Max(pd):
    v=pd.y0Max[0]
    s=pd.y0Max[1]
    return v,s

def yStd(pd):
    if pd.yIsString or  pd.yIsDate:
        return 'NA','NA'
    else:
        v=np.nanstd(pd.y)
        s=pretty_num(v)
    return (v,s)


def yRange(pd):
    if pd.yIsString:
        return 'NA','NA'
    elif pd.yIsDate:
        dtAll = pretty_time(np.timedelta64((pd.y[-1]-pd.y[0]),'s').item().total_seconds())
        return '',dtAll
    else:
        v=np.nanmax(pd.y)-np.nanmin(pd.y)
        s=pretty_num(v)
    return v,s

def xRange(pd):
    if pd.xIsString:
        return 'NA','NA'
    elif pd.xIsDate:
        dtAll = pretty_time(np.timedelta64((pd.x[-1]-pd.x[0]),'s').item().total_seconds())
        return '',dtAll
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
        dt    = pretty_time(np.timedelta64((pd.x[1]-pd.x[0]),'s').item().total_seconds())
        #    dtAll = pretty_time(np.timedelta64((y[-1]-y[0]),'s').item().total_seconds())
        return '',dt
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


def Info(pd,var):
    if var=='LSeg':
        return '','{:d}'.format(pd.Info.LSeg)
    elif var=='LWin':
        return '','{:d}'.format(pd.Info.LWin)
    elif var=='LOvlp':
        return '','{:d}'.format(pd.Info.LOvlp)
    elif var=='nFFT':
        return '','{:d}'.format(pd.Info.nFFT)




class ColCheckMenu(wx.Menu):
    def __init__(self,parent):
        wx.Menu.__init__(self)
        self.isClosed=True
        self.parent=parent
        self.Bind(wx.EVT_MENU, self.onSelChange)
        self.Bind(wx.EVT_UPDATE_UI, self.onUpdate)

    def onUpdate(self,event):
        print('update')

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

        self.ColsReg=[]
        self.ColsReg.append({'name':'Directory'    , 'al':'L' , 'f':baseDir , 's':False})
        self.ColsReg.append({'name':'Filename'     , 'al':'L' , 'f':fileName, 's':False})
        self.ColsReg.append({'name':'Table'        , 'al':'L' , 'f':tabName , 's':False})
        self.ColsReg.append({'name':'Column'       , 'al':'L' , 'f':yName  , 's':True})
        #self.ColsReg.append({'name':'Mean'        , 'al':'R' , 'f':y0Mean , 's' :True})
        self.ColsReg.append({'name':'Mean'         , 'al':'R' , 'f':yMean  , 's' :True})
        #self.ColsReg.append({'name':'Std'         , 'al':'R' , 'f':y0Std  , 's' :True})
        self.ColsReg.append({'name':'Std'          , 'al':'R' , 'f':yStd   , 's' :True})
        self.ColsReg.append({'name':'Var'          , 'al':'R' , 'f':y0Var  , 's' :False})
        #self.ColsReg.append({'name':'Min'         , 'al':'R' , 'f':y0Min  , 's' :True})
        self.ColsReg.append({'name':'Min'          , 'al':'R' , 'f':yMin   , 's' :True})
        #self.ColsReg.append({'name':'Max'         , 'al':'R' , 'f':y0Max  , 's' :True})
        self.ColsReg.append({'name':'Max'          , 'al':'R' , 'f':yMax   , 's' :True})
        self.ColsReg.append({'name':'Range'        , 'al':'R' , 'f':yRange , 's' :True})
        self.ColsReg.append({'name':'dx'           , 'al':'R' , 'f':dx     , 's' :True})
        self.ColsReg.append({'name':'xMin'         , 'al':'R' , 'f':xMin   , 's' :False})
        self.ColsReg.append({'name':'xMax'         , 'al':'R' , 'f':xMax   , 's' :False})
        self.ColsReg.append({'name':'xRange'       , 'al':'R' , 'f':xRange , 's' :False})
        self.ColsReg.append({'name':u'\u222By'     , 'al':'R' , 'f':inty   , 's' :True})
        self.ColsReg.append({'name':u'\u222By.x  ' , 'al':'R' , 'f':intyx1 , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x/\u222By  ' , 'al':'R' , 'f':intyx1_scaled , 's' :False})
        self.ColsReg.append({'name':u'\u222By.x^2' , 'al':'R' , 'f':intyx2 , 's' :False})
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
        self.ColsMinMax.append({'name':'Directory'    , 'al':'L' , 'f':baseDir , 's':False})
        self.ColsMinMax.append({'name':'Filename'     , 'al':'L' , 'f':fileName, 's':False})
        self.ColsMinMax.append({'name':'Table'        , 'al':'L' , 'f':tabName , 's':False})
        self.ColsMinMax.append({'name':'Column'       , 'al':'L' , 'f':yName  , 's':True})
        self.ColsMinMax.append({'name':'Mean'         , 'al':'R' , 'f':y0Mean , 's' :True})
        self.ColsMinMax.append({'name':'Std'          , 'al':'R' , 'f':y0Std  , 's' :True})
        self.ColsMinMax.append({'name':'Min'          , 'al':'R' , 'f':y0Min  , 's' :True})
        self.ColsMinMax.append({'name':'Max'          , 'al':'R' , 'f':y0Max  , 's' :True})
        self.ColsMinMax.append({'name':'Mean(MinMax)' , 'al':'R' , 'f':yMean  , 's' :True})
        self.ColsMinMax.append({'name':'Std(MinMax)'  , 'al':'R' , 'f':yStd   , 's' :True})
        self.ColsMinMax.append({'name':'n'            , 'al':'R' , 'f':ylen   , 's' :True})
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
    tab=Table(df=df)
    p1.showStats(None,[tab],[0],[0,1],tab.columns,0,erase=True)

    app.MainLoop()

