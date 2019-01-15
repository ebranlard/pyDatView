import wx
# TODO get rid of me
try:
    from .common import getMonoFont, getColumn
    from .GUIMultiSplit import MultiSplit
    from .Tables import haveSameColumns
except:
    from common import getMonoFont, getColumn
    from GUIMultiSplit import MultiSplit
    from Tables import haveSameColumns


__all__  = ['ColumnPanel', 'TablePanel', 'SelectionPanel','SEL_MODES','SEL_MODES_ID','TablePopup','ColumnPopup']

SEL_MODES    = ['auto','Same tables'    ,'Different tables'  ]
SEL_MODES_ID = ['auto','sameColumnsMode','twoColumnsMode']


# --------------------------------------------------------------------------------}
# --- Helper functions 
# --------------------------------------------------------------------------------{
def common_start(*strings):
    """ Returns the longest common substring
        from the beginning of the `strings`
    """
    if len(strings)==1:
        strings=tuple(strings[0])
    def _iter():
        for z in zip(*strings):
            if z.count(z[0]) == len(z):  # check all elements in `z` are the same
                yield z[0]
            else:
                return
    return ''.join(_iter())

def common_end(*strings):
    if len(strings)==1:
        strings=strings[0]
    else:
        strings=list(strings)
    strings = [s[-1::-1] for s in strings]
    return common_start(strings)[-1::-1]


def ellude_common(strings):
    # Selecting only the strings that do not start with the safe '>' char
    S = [s for i,s in enumerate(strings) if ((len(s)>0) and (s[0]!= '>'))]
    if len(S)==1:
        ns=S[0].rfind('|')+1
        ne=0;
    else:
        ss = common_start(S)
        se = common_end(S)
        iu = ss[:-1].rfind('_')
        ip = ss[:-1].rfind('_')
        if iu > 0:
            if ip>0:
                if iu>ip:
                    ss=ss[:iu+1]
            else:
                ss=ss[:iu+1]

        iu = se[:-1].find('_')
        if iu > 0:
            se=se[iu:]
        iu = se[:-1].find('.')
        if iu > 0:
            se=se[iu:]
        ns=len(ss)     
        ne=len(se)     

    for i,s in enumerate(strings):
        if len(s)>0 and s[0]=='>':
            strings[i]=s[1:]
        else:
            s=s[ns:]
            if ne>0:
                s = s[:-ne]
            strings[i]=s.lstrip('_')
            if len(strings[i])==0:
                strings[i]='tab{}'.format(i)
    return strings

# --------------------------------------------------------------------------------}
# --- Popup menus
# --------------------------------------------------------------------------------{
class TablePopup(wx.Menu):
    def __init__(self, mainframe, parent):
        wx.Menu.__init__(self)
        self.parent = parent
        self.mainframe = mainframe
        self.ISel = self.parent.GetSelections()

        if len(self.ISel)>0:
            item = wx.MenuItem(self, -1, "Delete")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnDelete, item)

        if len(self.ISel)==1:
            item = wx.MenuItem(self, -1, "Rename")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnRename, item)

        if len(self.ISel)==1:
            item = wx.MenuItem(self, -1, "Export")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnExport, item)

    def OnDelete(self, event):
        self.mainframe.deleteTabs(self.ISel)

    def OnRename(self, event):
        oldName = self.parent.GetString(self.ISel[0])
        dlg = wx.TextEntryDialog(self.parent, 'New table name:', 'Rename table',oldName,wx.OK|wx.CANCEL)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            newName=dlg.GetValue()
            self.mainframe.renameTable(self.ISel[0],newName)

    def OnExport(self, event):
        self.mainframe.exportTab(self.ISel[0]);

class ColumnPopup(wx.Menu):
    def __init__(self, parent):
        wx.Menu.__init__(self)
        self.parent = parent
        self.ISel = self.parent.lbColumns.GetSelections()

        if len(self.ISel)>=1 and self.ISel[0]>0: 
            item = wx.MenuItem(self, -1, "Rename")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnRename, item)

    def OnRename(self, event):
        oldName = self.parent.lbColumns.GetString(self.ISel[0])
        dlg = wx.TextEntryDialog(self.parent, 'New column name:', 'Rename column',oldName,wx.OK|wx.CANCEL)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            newName=dlg.GetValue()
            self.parent.tab.renameColumn(self.ISel[0]-1,newName)
            self.parent.updateColumn(self.ISel[0],newName) #faster
            self.parent.selPanel.updateLayout()
            # a trigger for the plot is required but skipped for now

#     def OnDelete(self, event):
#         ISel=self.parent.GetSelections()
#         print("Column delete event",ISel)


# --------------------------------------------------------------------------------}
# --- Table Panel
# --------------------------------------------------------------------------------{
class TablePanel(wx.Panel):
    """ Display list of tables """
    def __init__(self, parent):
        # Superclass constructor
        super(TablePanel,self).__init__(parent)
        # DATA
        label = wx.StaticText( self, -1, 'Tables: ')
        self.lbTab=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED)
        self.lbTab.SetFont(getMonoFont())
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, border=5)
        sizer.Add(self.lbTab, 2, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)

    def setTabNames(self,tabnames):    
        self.lbTab.Set(tabnames)

    def empty(self):    
        self.lbTab.Clear()

# --------------------------------------------------------------------------------}
# --- ColumnPanel
# --------------------------------------------------------------------------------{
class ColumnPanel(wx.Panel):
    """ A list of columns for x and y axis """
    def __init__(self, parent, selPanel):
        # Superclass constructor
        super(ColumnPanel,self).__init__(parent)
        self.selPanel = selPanel;
        # Data
        self.tab=[]
        # GUI
        self.comboX = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        self.comboX.SetFont(getMonoFont())
        self.lbColumns=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED )
        self.lbColumns.SetFont(getMonoFont())
        # Events
        self.lbColumns.Bind(wx.EVT_RIGHT_DOWN, self.OnColPopup)
        # Layout
        sizerX = wx.BoxSizer(wx.HORIZONTAL)
        sizerX.Add(self.comboX   , 0, flag=wx.TOP | wx.BOTTOM | wx.EXPAND, border=5)
        sizerCol = wx.BoxSizer(wx.VERTICAL)
        sizerCol.Add(sizerX        , 0, border=5)
        sizerCol.Add(self.lbColumns, 2, flag=wx.EXPAND, border=0)
        self.SetSizer(sizerCol)
        
    def OnColPopup(self,event):
        self.PopupMenu(ColumnPopup(self), event.GetPosition())

    def getDefaultColumnX(self,tab,nColsMax):
        # Try the first column for x-axis, except if it's a string
        iSelect = min(1,nColsMax)
        _,isString,_,_=getColumn(tab.data,iSelect)
        if isString:
            iSelect = 0 # we roll back and select the index
        return iSelect

    def getDefaultColumnY(self,tab,nColsMax):
        # Try the first column for x-axis, except if it's a string
        iSelect = min(2,nColsMax)
        _,isString,_,_=getColumn(tab.data,iSelect)
        if isString:
            iSelect = 0 # we roll back and select the index
        return iSelect

    def setTab(self,tab,xSel=-1,ySel=[]):
        """ Set the table used for the columns, update the GUI """
        self.tab=tab;
        self.setColumnNames(xSel,ySel)

    def updateColumnNames(self):
        """ Update of column names from table, keeping selection """
        xSel,ySel,_,_ = self.getColumnSelection()
        self.setColumnNames(xSel,ySel)

    def updateColumn(self,i,newName):
        """ Update of one column name"""
        self.lbColumns.SetString(i,newName)
        self.comboX.SetString(i,newName)

    def setColumnNames(self,xSel=-1,ySel=[]):
        """ Set columns from table """
        # Populating..
        columns=['Index']+self.tab.columns
        self.lbColumns.Set(columns)
        self.comboX.Set(columns)
        # Restoring previous selection
        for i in ySel:
            if i<len(columns):
                self.lbColumns.SetSelection(i)
                self.lbColumns.EnsureVisible(i)
        if len(self.lbColumns.GetSelections())<=0:
            self.lbColumns.SetSelection(self.getDefaultColumnY(self.tab,len(columns)-1))
        if (xSel<0) or xSel>len(columns):
            self.comboX.SetSelection(self.getDefaultColumnX(self.tab,len(columns)-1))
        else:
            self.comboX.SetSelection(xSel)

    def forceOneSelection(self):
        ISel=self.lbColumns.GetSelections()
        self.lbColumns.SetSelection(-1)
        if len(ISel)>0:
            self.lbColumns.SetSelection(ISel[0])

    def empty(self):
        self.lbColumns.Clear()
        self.comboX.Clear()

    def getColumnSelection(self):
        iX = self.comboX.GetSelection()
        sX = self.comboX.GetStringSelection()
        IY = self.lbColumns.GetSelections()
        SY = [self.lbColumns.GetString(i) for i in IY]
        return iX,IY,sX,SY



# --------------------------------------------------------------------------------}
# --- Selection Panel 
# --------------------------------------------------------------------------------{

class SelectionPanel(wx.Panel):
    """ Display options for the user to select data """
    def __init__(self, parent, tabs, mode='auto'):
        # Superclass constructor
        super(SelectionPanel,self).__init__(parent)
        # DATA
        self.tabs          = []
        self.itabForCol    = None
        self.parent        = parent
        self.tabSelections = {}
        self.tabSelected   = []
        self.modeRequested = mode

        # GUI DATA
        self.splitter  = MultiSplit(self, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(70)
        self.tabPanel  = TablePanel (self.splitter);
        self.colPanel1 = ColumnPanel(self.splitter, self);
        self.colPanel2 = ColumnPanel(self.splitter, self);
        self.tabPanel.Hide()
        self.colPanel1.Hide()
        self.colPanel2.Hide()

        # Layout
        self.updateLayout()
        VertSizer = wx.BoxSizer(wx.VERTICAL)
        VertSizer.Add(self.splitter, 2, flag=wx.EXPAND, border=0)
        self.SetSizer(VertSizer)

        # TRIGGERS
        if len(tabs)>0:
            #print(tabs)
            self.updateTables(tabs)
            self.selectDefaultTable()
            # TODO
            #self.colPanel1.selectDefaultColumns(self.tabs[self.itabForCol])

    def updateLayout(self,mode=None):
        if mode is None:
            mode=self.modeRequested
        else:
            self.modeRequested = mode
        if mode=='auto':
            self.autoMode()
        elif mode=='sameColumnsMode':
            self.sameColumnsMode()
        elif mode=='twoColumnsMode':
            self.twoColumnsMode()
        else:
            raise Exception('Wrong mode for selection layout: {}'.format(self.mode))


    def autoMode(self):
        if hasattr(self,'tabs'):
            if len(self.tabs)<=0:
                self._mode='auto'
                self.splitter.removeAll()
            elif len(self.tabs)==1:
                self.sameColumnsMode()
            else:
                if haveSameColumns(self.tabs):
                    self.sameColumnsMode()
                else:
                    self.twoColumnsMode()

    def sameColumnsMode(self):
        self._mode='sameColumnsMode'
        self.splitter.removeAll()
        if hasattr(self,'tabs'):
            if len(self.tabs)>1:
                self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel1) 

    def twoColumnsMode(self):
        self._mode='twoColumnsMode'
        self.splitter.removeAll()
        self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel2) 
        self.splitter.AppendWindow(self.colPanel1) 
        self.splitter.setEquiSash()
        #self.parent.GetParent().GetParent().GetParent().resizeSideColumn(SIDE_COL_LARGE)

    def updateTables(self,tabs):
        """ Update the list of tables, while keeping the selection if any """
        # TODO PUT ME IN TABLE PANEL
        #print('UPDATING TABLES')
        # Emptying GUI - TODO only if needed
        self.colPanel1.empty()
        self.colPanel2.empty()
        # Adding
        self.tabs = tabs
        tabnames =[t.name for t in tabs]
        raw_names=[t.raw_name for t in tabs]
        etabnames=ellude_common(raw_names)
        self.tabPanel.setTabNames(etabnames);
        for tn in tabnames:
            if tn not in self.tabSelections.keys():
                self.tabSelections[tn]={'xSel':-1,'ySel':[]}
            else:
                pass # do nothing

        # Reselecting
        if len(self.tabSelected)>0:        
            # Removed line below since two column mode implemented
            #if not haveSameColumns(tabs,ISel):
            #    ISel=[ISel[0]]
            for i in self.tabSelected:
                if i<len(tabs):
                    self.tabPanel.lbTab.SetSelection(i)
            #
        if len(self.tabPanel.lbTab.GetSelections())==0:
            self.selectDefaultTable()
        if len(self.tabs)>0:
            # Trigger - updating columns and layout
            ISel=self.tabPanel.lbTab.GetSelections()
            self.tabSelected=ISel
            if len(ISel)>=2:
                self.setTabForCol(ISel[0],1)
                self.setTabForCol(ISel[1],2)
            else:
                self.setTabForCol(ISel[0],1)
        self.updateLayout(self.modeRequested)

    def setTabForCol(self,iTabSel,iPanel):
        t  = self.tabs[iTabSel]
        ts = self.tabSelections[t.name]
        if iPanel==1:
            self.colPanel1.setTab(t,ts['xSel'],ts['ySel'])
        elif iPanel==2:
            self.colPanel2.setTab(t,ts['xSel'],ts['ySel'])
        else:
            raise Exception('Wrong ipanel')

    def selectDefaultTable(self):
        # Selecting the first table
        if self.tabPanel.lbTab.GetCount()>0:
            self.tabPanel.lbTab.SetSelection(0)
            self.tabSelected=[0]
        else:
            self.tabSelected=[]


    def update_tabs(self, tabs):
        self.updateTables(tabs)

    def renameTable(self,iTab, oldName, newName):
        #self.printSelection()
        self.tabSelections[newName] = self.tabSelections.pop(oldName)
        raw_names=[t.raw_name for t in self.tabs]
        etabnames=ellude_common(raw_names)
        self.tabPanel.setTabNames(etabnames);
        #self.printSelection()

    def saveSelection(self):
        #self.ISel=self.tabPanel.lbTab.GetSelections()
        ISel=self.tabSelected # 
        #print('Saving selection, tabSelected were:',self.tabSelected)
        if haveSameColumns(self.tabs,ISel):
            for ii in ISel:
                t=self.tabs[ii]
                self.tabSelections[t.name]['xSel'] = self.colPanel1.comboX.GetSelection()
                self.tabSelections[t.name]['ySel'] = self.colPanel1.lbColumns.GetSelections()
        else:
            if len(ISel)>=1:
                t=self.tabs[ISel[0]]
                self.tabSelections[t.name]['xSel'] = self.colPanel1.comboX.GetSelection()
                self.tabSelections[t.name]['ySel'] = self.colPanel1.lbColumns.GetSelections()
            if len(ISel)>=2:
                t=self.tabs[ISel[1]]
                self.tabSelections[t.name]['xSel'] = self.colPanel2.comboX.GetSelection()
                self.tabSelections[t.name]['ySel'] = self.colPanel2.lbColumns.GetSelections()
        self.tabSelected = self.tabPanel.lbTab.GetSelections();

    def printSelection(self):
        print('Number of tabSelections stored:',len(self.tabSelections))
        TS=self.tabSelections
        for i,t in enumerate(self.tabs):
            tn=t.name
            if tn not in TS.keys():
                print('Tab',i,'>>> Name {} not found in selection'.format(tn))
            else:
                print('Tab',i,'xSel:',TS[tn]['xSel'],'ySel:',TS[tn]['ySel'],'Name:',tn)

    def getFullSelection(self):
        ID = []
        iX1=None; IY1=None; sX1=None; SY1=None;
        iX2=None; IY2=None; sX2=None; SY2=None;
        ITab=None;
        STab=None;
        SameCol=False
        if hasattr(self,'tabs') and len(self.tabs)>0:
            ITab,STab = self.getSelectedTables()
            iX1,IY1,sX1,SY1 = self.colPanel1.getColumnSelection()
            if self._mode =='sameColumnsMode':
                SameCol=True
                for i,(itab,stab) in enumerate(zip(ITab,STab)):
                    for j,(iy,sy) in enumerate(zip(IY1,SY1)):
                        ID.append([itab,iX1,iy,sX1,sy,stab])
            elif self._mode =='twoColumnsMode':
                SameCol=haveSameColumns(self.tabs,ITab)
                if len(ITab)>=1:
                    for j,(iy,sy) in enumerate(zip(IY1,SY1)):
                        ID.append([ITab[0],iX1,iy,sX1,sy,STab[0]])
                if len(ITab)>=2:
                    if SameCol:
                        iX2=iX1;IY2=IY1;sX2=sX1;SY2=SY1;
                    else:
                        iX2,IY2,sX2,SY2 = self.colPanel2.getColumnSelection()
                    for j,(iy,sy) in enumerate(zip(IY2,SY2)):
                        ID.append([ITab[1],iX2,iy,sX2,sy,STab[1]])
            else:
                raise Exception('Unknown mode {}'.format(self._mode))
        return ID,ITab,iX1,IY1,iX2,IY2,STab,sX1,SY1,sX2,SY2,SameCol


    def getPlotDataSelection(self):
        ID = []
        SameCol=False
        if hasattr(self,'tabs') and len(self.tabs)>0:
            ITab,STab = self.getSelectedTables()
            iX1,IY1,sX1,SY1 = self.colPanel1.getColumnSelection()
            if self._mode =='sameColumnsMode':
                SameCol=True
                for i,(itab,stab) in enumerate(zip(ITab,STab)):
                    for j,(iy,sy) in enumerate(zip(IY1,SY1)):
                        ID.append([itab,iX1,iy,sX1,sy,stab])
            elif self._mode =='twoColumnsMode':
                SameCol=haveSameColumns(self.tabs,ITab)
                if len(ITab)>=1:
                    for j,(iy,sy) in enumerate(zip(IY1,SY1)):
                        ID.append([ITab[0],iX1,iy,sX1,sy,STab[0]])
                if len(ITab)>=2:
                    if SameCol:
                        iX2=iX1;IY2=IY1;sX2=sX1;SY2=SY1;
                    else:
                        iX2,IY2,sX2,SY2 = self.colPanel2.getColumnSelection()
                    for j,(iy,sy) in enumerate(zip(IY2,SY2)):
                        ID.append([ITab[1],iX2,iy,sX2,sy,STab[1]])
            else:
                raise Exception('Unknown mode {}'.format(self._mode))
        return ID,SameCol


    def getSelectedTables(self):
        I=self.tabPanel.lbTab.GetSelections()
        S=[self.tabPanel.lbTab.GetString(i) for i in I]
        return I,S

    def clean_memory(self):
        self.colPanel1.empty()
        self.colPanel2.empty()
        self.tabPanel.empty()
        if hasattr(self,'tabs'):
            del self.tabs


if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table
    import numpy as np

    def OnTabPopup(event):
        self.PopupMenu(TablePopup(self,selPanel.tabPanel.lbTab), event.GetPosition())

    app = wx.App(False)
    self=wx.Frame(None,-1,"Title")
    tab=Table(df=pd.DataFrame(data={'ColA': np.random.normal(0,1,100)+1,'ColB':np.random.normal(0,1,100)+2}))
    selPanel=SelectionPanel(self,[tab],mode='twoColumnsMode')
    self.SetSize((800, 600))
    self.Center()
    self.Show()
    selPanel.tabPanel.lbTab.Bind(wx.EVT_RIGHT_DOWN, OnTabPopup)


    app.MainLoop()

