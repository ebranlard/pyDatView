import wx
import platform
from pydatview.common import *
from pydatview.GUICommon import *
from pydatview.GUIMultiSplit import MultiSplit
from pydatview.GUIToolBox import GetKeyString
#     from common import *
#     from GUICommon import *
#     from GUIMultiSplit import MultiSplit


__all__  = ['ColumnPanel', 'TablePanel', 'SelectionPanel','SEL_MODES','SEL_MODES_ID','TablePopup','ColumnPopup']

SEL_MODES    = ['auto','Same tables'    ,'Sim. tables' ,'2 tables','3 tables (exp.)'  ]
SEL_MODES_ID = ['auto','sameColumnsMode','simColumnsMode','twoColumnsMode'  ,'threeColumnsMode' ]
MAX_X_COLUMNS=300 # Maximum number of columns used in combo box of the x-axis (for performance)

def ireplace(text, old, new):
    """ Replace case insensitive """
    try:
        index_l = text.lower().index(old.lower())
        return text[:index_l] + new + text[index_l + len(old):] 
    except:
        return text


# --------------------------------------------------------------------------------}
# ---  Formula diagog
# --------------------------------------------------------------------------------{
class FormulaDialog(wx.Dialog):
    def __init__(self, title='', name='', formula='',columns=[],unit='',xcol='',xunit=''):
        wx.Dialog.__init__(self, None, title=title)
        # --- Data
        self.unit=unit.strip().replace(' ','')
        self.columns=['{'+c+'}' for c in columns]
        self.xcol='{'+xcol+'}'
        self.xunit=xunit.strip().replace(' ','')
        if len(formula)==0:
            formula=' + '.join(self.columns)
        if len(name)==0:
            name=self.getDefaultName()
        self.formula_in=formula


        quick_lbl = wx.StaticText(self, label="Predefined: " )
        self.cbQuick = wx.ComboBox(self, choices=['None','x 1000','/ 1000','deg2rad','rad2deg','rpm2radps','radps2rpm','norm','squared','d/dx'], style=wx.CB_READONLY)
        self.cbQuick.SetSelection(0)
        self.cbQuick.Bind(wx.EVT_COMBOBOX  ,self.onQuickFormula)
 
        # Formula info
        formula_lbl   = wx.StaticText(self, label="Formula:      ")
        self.formula = wx.TextCtrl(self)
        #self.formula.SetFont(getMonoFont(self))

        self.formula.SetValue(formula)
        formula_sizer = wx.BoxSizer(wx.HORIZONTAL)
        formula_sizer.Add(formula_lbl ,0,wx.ALL|wx.RIGHT|wx.CENTER,5)
        formula_sizer.Add(self.formula,1,wx.ALL|wx.EXPAND|wx.CENTER,5)
        formula_sizer.Add(quick_lbl   ,0,wx.ALL|wx.CENTER,5)
        formula_sizer.Add(self.cbQuick,0,wx.ALL|wx.CENTER,5)


        # name info
        name_lbl = wx.StaticText(self, label="New name: " )
        self.name = wx.TextCtrl(self, size=wx.Size(200,-1))
        self.name.SetValue(name)
        #self.name.SetFont(getMonoFont(self))
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_sizer.Add(name_lbl ,0,wx.ALL|wx.RIGHT|wx.CENTER,5)
        name_sizer.Add(self.name,0,wx.ALL|wx.CENTER,5)
 
        info ='The formula needs to have a valid python syntax for an array manipulation. The available arrays are \n'
        info+='the columns of the current table. The column names (without units) are surrounded by curly brackets.\n'
        info+='You have access to numpy using `np`.\n\n'
        info+='For instance, if you have two columns called `ColA [m]` and `ColB [m]` you can use:\n'
        info+='  - ` {ColA} + {ColB} `\n'
        info+='  - ` np.sqrt( {ColA}**2/1000 + 1/{ColB}**2 ) `\n'
        info+='  - ` np.sin ( {ColA}*2*np.pi + {ColB} ) `\n'
        help_lbl = wx.StaticText(self, label='Help: ')
        info_lbl = wx.StaticText(self, label=info)
        help_sizer = wx.BoxSizer(wx.HORIZONTAL)
        help_sizer.Add(help_lbl ,0,wx.ALL|wx.RIGHT|wx.TOP,5)
        help_sizer.Add(info_lbl ,0,wx.ALL|wx.TOP,5)


 
        self.btOK = wx.Button(self, wx.ID_OK)#, label = "OK"    )
        btCL = wx.Button(self,label = "Cancel")
        bt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bt_sizer.Add(self.btOK, 0 ,wx.ALL,5)
        bt_sizer.Add(btCL, 0 ,wx.ALL,5)
        #btOK.Bind(wx.EVT_BUTTON,self.onOK    )
        btCL.Bind(wx.EVT_BUTTON,self.onCancel)


        main_sizer = wx.BoxSizer(wx.VERTICAL)
        #main_sizer.Add(quick_sizer  ,0,wx.ALL|wx.EXPAND,5)
        main_sizer.Add(formula_sizer,0,wx.ALL|wx.EXPAND,5)
        main_sizer.Add(name_sizer   ,0,wx.ALL|wx.EXPAND,5)
        main_sizer.Add(help_sizer   ,0 ,wx.ALL|wx.CENTER, 5)
        main_sizer.Add(bt_sizer     ,0, wx.ALL|wx.CENTER, 5)
        self.SetSizer(main_sizer)
        self.Fit()

    def stripBrackets(self,s):
        return s.replace('{','').replace('}','')

    def getOneColName(self):
        if len(self.columns)>0:
            return self.columns[-1]
        else:
            return ''

    def get_unit(self):
        if len(self.unit)>0:
            return ' ['+self.unit+']'
        else:
            return ''
    def get_squared_unit(self):
        if len(self.unit)>0:
            if self.unit[0].lower()=='-':
                return ' [-]'
            else:
                return ' [('+self.unit+')^2]'
        else:
            return ''
    def get_kilo_unit(self):
        if len(self.unit)>0:
            if len(self.unit)>=1:
                if self.unit[0].lower()=='-':
                    return ' [-]'
                elif self.unit[0].lower()=='G':
                    r='T'
                elif self.unit[0].lower()=='M':
                    r='G'
                elif self.unit[0]=='k':
                    r='M'
                elif self.unit[0]=='m':
                    if len(self.unit)==1:
                        r='km'
                    elif self.unit[1]=='/':
                        r='km'
                    else:
                        r=''
                else:
                    r='k'+self.unit[0]
                return ' ['+r+self.unit[1:]+']'
            else:
                return ' [k'+self.unit+']'
        else:
            return ''
    def get_milli_unit(self):
        if len(self.unit)>=1:
            if self.unit[0].lower()=='-':
                return ' [-]'
            elif self.unit[0].lower()=='T':
                r='G'
            elif self.unit[0]=='G':
                r='M'
            elif self.unit[0]=='M':
                r='k'
            elif self.unit[0].lower()=='k':
                r=''
            elif self.unit[0]=='m':
                if len(self.unit)==1:
                    r='mm'
                elif self.unit[1]=='/':
                    r='mm'
                else:
                    r='mu'
            else:
                r='m'+self.unit[0]

            return ' ['+r+self.unit[1:]+']'
        else:
            return ''
    def get_deriv_unit(self):
        if self.unit==self.xunit:
            return ' [-]'
        else:
            return ' ['+self.unit+'/'+self.xunit+']'

    def getDefaultName(self):
        if len(self.columns)>0:
            return self.stripBrackets(self.getOneColName())+' New'+self.get_unit()
        else:
            return ''

    def onQuickFormula(self, event):
        i = self.cbQuick.GetSelection()
        s = self.cbQuick.GetStringSelection()
        if s=='None':
            self.formula.SetValue(self.formula_in)
            return

        #self.formula_in=self.formula.GetValue()
        c1 = self.getOneColName()
        n1 = self.stripBrackets(c1)

        if s=='x 1000':
            self.formula.SetValue(c1+' * 1000')
            self.name.SetValue(n1+'_x1000'+ self.get_milli_unit())
        elif s=='/ 1000':
            self.formula.SetValue(c1+' / 1000')
            self.name.SetValue(n1+'_/1000'+self.get_kilo_unit())
        elif s=='deg2rad':
            self.formula.SetValue(c1+' *np.pi/180')
            self.name.SetValue(n1+'_rad [rad]')
        elif s=='rad2deg':
            self.formula.SetValue(c1+' *180/np.pi')
            self.name.SetValue(n1+'_deg [deg]')
        elif s=='rpm2radps':
            self.formula.SetValue(c1+' *2*np.pi/60')
            self.name.SetValue(n1+'_radps [rad/s]')
        elif s=='radps2rpm':
            self.formula.SetValue(c1+' *60/(2*np.pi)')
            self.name.SetValue(n1+'_rpm [rpm]')
        elif s=='norm':
            self.formula.SetValue('np.sqrt( '+'**2 + '.join(self.columns)+'**2 )')
            self.name.SetValue(n1+'_norm'+self.get_unit())
        elif s=='squared':
            self.formula.SetValue('**2 + '.join(self.columns)+'**2 ')
            self.name.SetValue(n1+'^2'+self.get_squared_unit())
        elif s=='d/dx':
            self.formula.SetValue('np.gradient( '+'+'.join(self.columns)+ ', '+self.xcol+' )')
            nx = self.stripBrackets(self.xcol)
            bDoNewName=True
            if self.xunit=='s':
                if n1.lower().find('speed')>=0:
                    n1=ireplace(n1,'speed','Acceleration')
                    bDoNewName=False
                elif n1.lower().find('velocity')>=0:
                    n1=ireplace(n1,'velocity','Acceleration')
                    bDoNewName=False
                elif n1.lower().find('vel')>=0:
                    n1=ireplace(n1,'vel','Acc')
                    bDoNewName=False
                elif n1.lower().find('position')>=0:
                    n1=ireplace(n1,'position','speed')
                    bDoNewName=False
                elif n1.lower().find('pos')>=0:
                    n1=ireplace(n1,'pos','Vel')
                    bDoNewName=False
                else:
                    n1='d('+n1+')/dt'
            else:
                n1='d('+n1+')/d('+nx+')'
            self.name.SetValue(n1+self.get_deriv_unit())
        else:
            raise Exception('Unknown quick formula {}'.s)

    def onCancel(self, event):
        self.Destroy()
# --------------------------------------------------------------------------------}
# --- Popup menus
# --------------------------------------------------------------------------------{
class TablePopup(wx.Menu):
    """ Popup Menu when right clicking on the table list """
    def __init__(self, parent, tabPanel, selPanel=None, mainframe=None, fullmenu=False):
        wx.Menu.__init__(self)
        self.parent    = parent    # parent is listbox
        self.tabPanel  = tabPanel
        self.tabList   = tabPanel.tabList
        self.selPanel  = selPanel
        self.mainframe = mainframe
        self.ISel = self.parent.GetSelections()

        if fullmenu:
            self.itNameFile = wx.MenuItem(self, -1, "Naming: by file names", kind=wx.ITEM_CHECK)
            self.Append(self.itNameFile)
            self.Bind(wx.EVT_MENU, self.OnNaming, self.itNameFile)
            self.Check(self.itNameFile.GetId(), self.parent.GetParent().tabList.Naming=='FileNames') # Checking the menu box

            item = wx.MenuItem(self, -1, "Sort by name")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnSort, item)

            if self.mainframe is not None:
                item = wx.MenuItem(self, -1, "Add")
                self.Append(item)
                self.Bind(wx.EVT_MENU, self.mainframe.onAdd, item)

        if len(self.ISel)>1:
            item = wx.MenuItem(self, -1, "Merge")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnMergeTabs, item)

        if len(self.ISel)>0:
            item = wx.MenuItem(self, -1, "Delete")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnDeleteTabs, item)

        if len(self.ISel)==1:
            if self.tabPanel.tabList.Naming!='FileNames':
                item = wx.MenuItem(self, -1, "Rename")
                self.Append(item)
                self.Bind(wx.EVT_MENU, self.OnRenameTab, item)

        if len(self.ISel)==1:
            item = wx.MenuItem(self, -1, "Export")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnExportTab, item)

    def OnNaming(self, event=None):
        if self.itNameFile.IsChecked():
            self.tabPanel.tabList.setNaming('FileNames')
        else:
            self.tabPanel.tabList.setNaming('Ellude')

        self.tabPanel.updateTabNames()

    def OnMergeTabs(self, event):
        # --- Figure out the common columns
        tabs = [self.tabList.get(i) for i in self.ISel]
        IKeepPerTab, IMissPerTab, IDuplPerTab, _ = getTabCommonColIndices(tabs)
        nCommonCols = len(IKeepPerTab[0])
        commonCol        = None
        ICommonColPerTab = None
        samplDict        = None
        if nCommonCols>=1:
            # We use the first one
            # TODO Menu to figure out which column to chose and how to merge (interp?)
            keepAllX = True
            #samplDict ={'name':'Replace', 'param':[], 'paramName':'New x'}
            # Index of common column for each table
            ICommonColPerTab = [I[0] for I in IKeepPerTab]
        else:
            # we'll merge based on index..
            pass

            

        # Merge tables and add it to the list
        self.tabList.mergeTabs(self.ISel, ICommonColPerTab, samplDict=samplDict)
        # Updating tables
        self.selPanel.update_tabs(self.tabList)
        # TODO select latest
        if self.mainframe:
            self.mainframe.mergeTabsTrigger()

    def OnDeleteTabs(self, event):
        self.mainframe.deleteTabs(self.ISel)

    def OnRenameTab(self, event):
        oldName = self.parent.GetString(self.ISel[0])
        dlg = wx.TextEntryDialog(self.parent, 'New table name:', 'Rename table',oldName,wx.OK|wx.CANCEL)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            newName=dlg.GetValue()
            self.mainframe.renameTable(self.ISel[0],newName)

    def OnExportTab(self, event):
        self.mainframe.exportTab(self.ISel[0]);

    def OnSort(self, event):
        self.mainframe.sortTabs()

class ColumnPopup(wx.Menu):
    """ Popup Menu when right clicking on the column list """
    def __init__(self, parent, fullmenu=False):
        wx.Menu.__init__(self)
        self.parent = parent # parent is ColumnPanel
        self.ISel = self.parent.lbColumns.GetSelections()

        self.itShowID = wx.MenuItem(self, -1, "Show ID", kind=wx.ITEM_CHECK)
        self.Append(self.itShowID)
        self.Bind(wx.EVT_MENU, self.OnShowID, self.itShowID)
        self.Check(self.itShowID.GetId(), self.parent.bShowID)

        if self.parent.tab is not None:  # TODO otherwise
            item = wx.MenuItem(self, -1, "Add")
            self.Append(item)
            self.Bind(wx.EVT_MENU, self.OnAddColumn, item)

            if len(self.ISel)==1 and self.ISel[0]>=0: 
                item = wx.MenuItem(self, -1, "Rename")
                self.Append(item)
                self.Bind(wx.EVT_MENU, self.OnRenameColumn, item)
            if len(self.ISel) == 1 and any(
                    f['pos'] == self.ISel[0] for f in self.parent.tab.formulas):
                item = wx.MenuItem(self, -1, "Edit")
                self.Append(item)
                self.Bind(wx.EVT_MENU, self.OnEditColumn, item)
            if len(self.ISel)>=1 and self.ISel[0]>=0: 
                item = wx.MenuItem(self, -1, "Delete")
                self.Append(item)
                self.Bind(wx.EVT_MENU, self.OnDeleteColumn, item)

    def OnShowID(self, event=None):
        self.parent.bShowID=self.itShowID.IsChecked()
        xSel,ySel,_,_ = self.parent.getColumnSelection()
        self.parent.setGUIColumns(xSel=xSel, ySel=ySel)

    def OnRenameColumn(self, event=None):
        iFilt = self.ISel[0]
        if self.parent.bShowID:
            oldName = self.parent.lbColumns.GetString(iFilt)[4:]
        else:
            oldName = self.parent.lbColumns.GetString(iFilt)
        dlg = wx.TextEntryDialog(self.parent, 'New column name:', 'Rename column',oldName,wx.OK|wx.CANCEL)
        dlg.CentreOnParent()
        if dlg.ShowModal() == wx.ID_OK:
            newName=dlg.GetValue()
            main=self.parent.mainframe
            ITab,STab=main.selPanel.getSelectedTables()
            # TODO adapt me for Sim. tables mode
            iFull = self.parent.Filt2Full[iFilt]
            if iFull>0: # Important since -1 would rename last column of table
                if main.tabList.haveSameColumns(ITab):
                    for iTab,sTab in zip(ITab,STab):
                        main.tabList.get(iTab).renameColumn(iFull-1,newName)
                else:
                    self.parent.tab.renameColumn(iFull-1,newName)
            self.parent.updateColumn(iFilt,newName) #faster
            self.parent.selPanel.updateLayout()
            # a trigger for the plot is required but skipped for now

    def OnEditColumn(self, event):
        main=self.parent.mainframe
        if len(self.ISel) != 1:
            raise ValueError('Only one signal can be edited!')
        ITab, STab = main.selPanel.getSelectedTables()
        for iTab,sTab in zip(ITab,STab):
            if sTab == self.parent.tab.active_name:
                for f in main.tabList.get(iTab).formulas:
                    if f['pos'] == self.ISel[0]:
                        sName = f['name']
                        sFormula = f['formula']
                        break
                else:
                    raise ValueError('No formula found at {0} for table {1}!'.format(self.ISel[0], sTab))
        self.showFormulaDialog('Edit column', sName, sFormula)

    def OnDeleteColumn(self, event):
        main=self.parent.mainframe
        iX = self.parent.comboX.GetSelection()
        ITab,STab=main.selPanel.getSelectedTables()
        # TODO adapt me for Sim. tables mode
        IFull = [self.parent.Filt2Full[iFilt]-1 for iFilt in self.ISel]
        IFull = [iFull for iFull in IFull if iFull>=0]
        if main.tabList.haveSameColumns(ITab):
            for iTab,sTab in zip(ITab,STab):
                main.tabList.get(iTab).deleteColumns(IFull)
        else:
            self.parent.tab.deleteColumns(IFull)
        self.parent.setColumns()
        self.parent.setGUIColumns(xSel=iX)
        main.redraw()

    def OnAddColumn(self, event):
        main=self.parent.mainframe
        self.showFormulaDialog('Add a new column')

    def showFormulaDialog(self, title, name='', formula=''):
        bValid=False
        bCancelled=False
        main=self.parent.mainframe
        sName=name
        sFormula=formula

        if self.parent.bShowID:
            columns=[no_unit(self.parent.lbColumns.GetString(i)[4:]) for i in self.ISel]
        else:
            columns=[no_unit(self.parent.lbColumns.GetString(i)) for i in self.ISel]
        if len(self.ISel)>0:
            main_unit=unit(self.parent.lbColumns.GetString(self.ISel[-1]))
        else:
            main_unit=''
        xcol  = self.parent.comboX.GetStringSelection()
        xunit = unit(xcol)
        xcol  = no_unit(xcol)

        while (not bValid) and (not bCancelled):
            dlg = FormulaDialog(title=title,columns=columns,xcol=xcol,xunit=xunit,unit=main_unit,name=sName,formula=sFormula)
            dlg.CentreOnParent()
            if dlg.ShowModal()==wx.ID_OK:
                sName    = dlg.name.GetValue()
                sFormula = dlg.formula.GetValue()
                dlg.Destroy()
                if len(self.ISel)>0:
                    iFilt=self.ISel[-1]
                    iFull=self.parent.Filt2Full[iFilt]
                else:
                    iFull = -1

                ITab,STab=main.selPanel.getSelectedTables()
                #if main.tabList.haveSameColumns(ITab):
                sError=''
                nError=0
                haveSameColumns=main.tabList.haveSameColumns(ITab)
                for iTab,sTab in zip(ITab,STab):
                    if haveSameColumns or self.parent.tab.active_name == sTab:
                        # apply formula to all tables with same columns, otherwise only to active table
                        if title.startswith('Edit'):
                            bValid=main.tabList.get(iTab).setColumnByFormula(sName,sFormula,iFull)
                        else:
                            bValid=main.tabList.get(iTab).addColumnByFormula(sName,sFormula,iFull)
                        if not bValid:
                            sError+='The formula didn''t eval for table {}\n'.format(sTab)
                            nError+=1
                if len(sError)>0:
                    Error(self.parent,sError)
                if nError<len(ITab):
                    bValid=True
            else:
                bCancelled=True
        if bCancelled:
            return
        if bValid:
            iX = self.parent.comboX.GetSelection()
            self.parent.setColumns()
            self.parent.setGUIColumns(xSel=iX,ySel=[iFull+1])
            main.redraw()



# --------------------------------------------------------------------------------}
# --- Table Panel
# --------------------------------------------------------------------------------{
class TablePanel(wx.Panel):
    """ Display list of tables """
    def __init__(self, parent, selPanel, mainframe, tabList):
        # Superclass constructor
        super(TablePanel,self).__init__(parent)
        # DATA
        self.parent    = parent    # splitter
        self.selPanel  = selPanel
        self.mainframe = mainframe
        self.tabList   = tabList
        # GUI
        tb = wx.ToolBar(self,wx.ID_ANY,style=wx.TB_HORIZONTAL|wx.TB_TEXT|wx.TB_HORZ_LAYOUT|wx.TB_NODIVIDER)
        self.bt=wx.Button(tb,wx.ID_ANY,CHAR['menu'], style=wx.BU_EXACTFIT)
        self.lb=wx.StaticText(tb, -1, ' Tables ' )
        tb.AddControl(self.bt)
        tb.AddControl(self.lb)
        tb.Bind(wx.EVT_BUTTON, self.showTableMenu, self.bt)
        tb.Realize() 
        #label = wx.StaticText( self, -1, 'Tables: ')
        self.lbTab=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED)
        self.lbTab.SetFont(getMonoFont(self))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(tb, 0, flag=wx.EXPAND,border=5)
        #sizer.Add(label, 0, border=5)
        sizer.Add(self.lbTab, 2, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)
        # Bind
        self.lbTab.Bind(wx.EVT_RIGHT_DOWN, self.onTabPopup)

    def onTabPopup(self, event=None):
        menu = TablePopup(self.lbTab, self, self.selPanel, self.mainframe, fullmenu=False)
        self.PopupMenu(menu, event.GetPosition())
        menu.Destroy()

    def showTableMenu(self,event=None):
        """ Table Menu is Table Popup but at button position, and with "full" menu options """
        pos = (self.bt.GetPosition()[0], self.bt.GetPosition()[1] + self.bt.GetSize()[1])
        menu = TablePopup(self.lbTab, self, self.selPanel, self.mainframe, fullmenu=True)
        self.PopupMenu(menu, pos)
        menu.Destroy()

    def updateTabNames(self):
        tabnames_display=self.tabList.getDisplayTabNames()
        # Storing selection
        ISel=self.lbTab.GetSelections()
        # Setting List Box
        self.lbTab.Set(tabnames_display)
        # Setting table active display name
        self.tabList.setActiveNames(tabnames_display)
        # Restoring selection
        for i in ISel:
            if i<self.tabList.len():
                self.lbTab.SetSelection(i)

    def empty(self):    
        self.lbTab.Clear()



# --------------------------------------------------------------------------------}
# --- ColumnPanel
# --------------------------------------------------------------------------------{
class ColumnPanel(wx.Panel):
    """ A list of columns for x and y axis """
    def __init__(self, parent, selPanel, mainframe):
        # Superclass constructor
        super(ColumnPanel,self).__init__(parent)
        self.selPanel = selPanel;
        # Data
        self.tab=None
        self.mainframe=mainframe
        self.columns=[] # All the columns available (may be different from the displayed ones)
        self.Filt2Full=None # Index of GUI columns in self.columns
        self.bShowID=False
        self.bReadOnly=False
        # --- GUI Toolbar
        tb = wx.ToolBar(self,wx.ID_ANY,style=wx.TB_HORIZONTAL|wx.TB_TEXT|wx.TB_HORZ_LAYOUT|wx.TB_NODIVIDER)
        self.bt=wx.Button(tb,wx.ID_ANY,CHAR['menu'], style=wx.BU_EXACTFIT)
        self.lb=wx.StaticText(tb, -1, '                                 ' )
        tb.AddControl(self.bt)
        tb.AddControl(self.lb)
        tb.Bind(wx.EVT_BUTTON, self.showColumnMenu, self.bt)
        tb.Realize() 

        # --- GUI Filter
        self.btClear =wx.Button(self,wx.ID_ANY,CHAR['sun']  , style=wx.BU_EXACTFIT)
        self.btFilter=wx.Button(self,wx.ID_ANY,CHAR['cloud'], style=wx.BU_EXACTFIT)
        self.tFilter = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.tFilter.SetValue('')
        self.Bind(wx.EVT_BUTTON    , self.onClearFilter , self.btClear)
        self.Bind(wx.EVT_BUTTON    , self.onFilterChange, self.btFilter)
        self.tFilter.Bind(wx.EVT_KEY_DOWN, self.onFilterKey   , self.tFilter )
        self.Bind(wx.EVT_TEXT_ENTER, self.onFilterChange, self.tFilter )
        #
        self.comboX = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        self.comboX.SetFont(getMonoFont(self))
        self.lbColumns=wx.ListBox(self, -1, choices=[], style=wx.LB_EXTENDED )
        self.lbColumns.SetFont(getMonoFont(self))
        # Events
        self.lbColumns.Bind(wx.EVT_RIGHT_DOWN, self.OnColPopup)
        self.lbColumns.Bind(wx.EVT_MOTION, self.OnColMotion)

        # Layout
        sizerX = wx.BoxSizer(wx.HORIZONTAL)
        sizerX.Add(self.comboX   , 1, flag=wx.TOP | wx.BOTTOM, border=2)
        sizerF = wx.BoxSizer(wx.HORIZONTAL)

        sizerF.Add(self.tFilter, 1,  flag=          wx.CENTER|wx.TOP          , border=0)
        sizerF.Add(self.btFilter, 0, flag=          wx.CENTER|wx.LEFT|wx.RIGHT, border=1)
        sizerF.Add(self.btClear,  0, flag=          wx.CENTER|wx.LEFT         , border=1)


        sizerCol = wx.BoxSizer(wx.VERTICAL)
        sizerCol.Add(tb            , 0, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=1)
        #sizerCol.Add(self.comboX   , 0, flag=wx.TOP|wx.RIGHT|wx.BOTTOM|wx.TOP,border=2)
        sizerCol.Add(sizerX        , 0, flag=wx.EXPAND, border=0)
        sizerCol.Add(sizerF        , 0, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=0)
        sizerCol.Add(self.lbColumns, 2, flag=wx.EXPAND, border=0)
        self.SetSizer(sizerCol)

    def showColumnMenu(self,event):
        if not self.bReadOnly:
            pos = (self.bt.GetPosition()[0], self.bt.GetPosition()[1] + self.bt.GetSize()[1])
            menu = ColumnPopup(self,fullmenu=True)
            self.PopupMenu(menu, pos)
            menu.Destroy()
        
    def OnColPopup(self,event):
        if not self.bReadOnly:
            menu = ColumnPopup(self)
            self.PopupMenu(menu, event.GetPosition())
            menu.Destroy()

    def OnColMotion(self,event):
        item = self.lbColumns.HitTest(event.GetPosition())
        try:
            for f in self.tab.formulas:
                if f['pos'] == item:
                    self.lbColumns.SetToolTip(wx.ToolTip('[{0}]: {1}'.format(f['pos'], f['formula'])))
                    break
            else:
                self.lbColumns.UnsetToolTip()
        except AttributeError:
            pass
        event.Skip()

    def getDefaultColumnX(self,tab,nColsMax):
        # Try the first column for x-axis, except if it's a string
        iSelect = min(1,nColsMax)
        if tab is not None:
            _,isString,_,_ = tab.getColumn(iSelect)
            if isString:
                iSelect = 0 # we roll back and select the index
        return iSelect

    def getDefaultColumnY(self,tab,nColsMax):
        # If a filter is applied, use the first element
        # Otherwise, try the second element except if it's a string
        if nColsMax<=0:
            return -1
        if nColsMax<len(self.columns)-1:
            return 0

        iSelect = min(2,nColsMax)
        if tab is not None:
            _,isString,_,_ = tab.getColumn(iSelect)
            if isString:
                iSelect = 0 # we roll back and select the index
        return iSelect

    def getGUIcolumns(self):
        if len(self.Filt2Full)>len(self.columns):
            print('',self.Filt2Full)
            print('',self.columns)
            raise Exception('Error in Filt2Full')
        return self.columns[self.Filt2Full]


    def _setReadOnly(self):
        self.bReadOnly=True
        self.comboX.Enable(False)
        self.lbColumns.Enable(False)

    def _unsetReadOnly(self):
        self.bReadOnly=False
        self.comboX.Enable(True)
        self.lbColumns.Enable(True)

    def setReadOnly(self, tabLabel=None, cols=[]):
        """ Set this list of columns as readonly and non selectable """
        self.tab=None
        if tabLabel is not None:
            self.lb.SetLabel(tabLabel)
        self._setReadOnly()
        self.lbColumns.Enable(True)
        self.setColumns(columnNames=cols)
        self.setGUIColumns()
        self.lbColumns.SetSelection(-1)
        self.bt.Enable(False)
        self.bShowID=False
        self.btClear.Enable(False)
        self.btFilter.Enable(False)
        self.tFilter.Enable(False)
        self.tFilter.SetValue('')

    def setTab(self, tab=None, xSel=-1, ySel=[], colNames=None, tabLabel='', sFilter=None):
        """ Set the table used for the columns, update the GUI
        tab is None, when in simColumnsMode
        """
        self.tab=tab;
        self.lbColumns.Enable(True)
        self.comboX.Enable(True)
        self.bReadOnly=False
        self.btClear.Enable(True)
        self.btFilter.Enable(True)
        self.tFilter.Enable(True)
        self.bt.Enable(True)

        selInFull = True
        if sFilter is not None and len(sFilter.strip())>0:
            self.tFilter.SetValue(sFilter)
            selInFull = False

        if tab is not None:
            # For a single tab
            if tab.active_name!='default':
                self.lb.SetLabel(' '+tab.active_name)
            # Setting raw columns from raw table (self.tab)
            self.setColumns()
            self.setGUIColumns(xSel=xSel, ySel=ySel, selInFull=selInFull) # Filt2Full will be created if a filter is present
        else:
            self.lb.SetLabel(tabLabel)
            self.setColumns(columnNames=colNames)
            self.setGUIColumns(xSel=xSel, ySel=ySel, selInFull=selInFull) # Filt2Full will be created if a filter is present

    def updateColumn(self,i,newName):
        """ Update of one column name
            i: index in GUI
        """
        iFull = self.Filt2Full[i]
        if self.bShowID:
            newName='{:03d} '.format(iFull)+newName
        self.lbColumns.SetString(i,newName)
        self.comboX.SetString   (i,newName)   
        self.columns[iFull] = newName

    def Full2Filt(self,iFull):
        try:
            return self.Filt2Full.index(iFull)
        except:
            return -1

    def setColumns(self, columnNames=None):
        """ 
        For a regular table, sets "full columns" from the tab.
        In simColumnsMode, tab is None, and the columns are given by the user.
        """
        # Get columns from user inputs, or table, or stored.
        if columnNames is not None:
            # Populating based on user inputs..
            columns=columnNames
        elif self.tab is None:
            columns=self.columns
        else:
            # Populating based on table (safest if table was updated)
            columns=['Index']+self.tab.columns
        # Storing columns, considered as "Full"
        self.columns=np.array(columns)

    def setGUIColumns(self, xSel=-1, ySel=[], selInFull=True):
        """ Set columns actually shown on the GUI based on self.columns and potential filter
          if selInFull is True, the selection is assumed to be in the full/raw columns
          Otherwise, the selection is assumed to be in the filtered column
        """
        # Filtering columns if neeed
        sFilt = self.tFilter.GetLineText(0).strip()
        if len(sFilt)>0:
            Lf, If = filter_list(self.columns, sFilt)
            self.Filt2Full = If

            if len(If)==0:
                # No results
                if not selInFull:
                    # Then it's likely a reload, we cancel the filter
                    self.tFilter.SetValue('')
                    self.Filt2Full = list(np.arange(len(self.columns)))
                    selInFull=False
            elif len(If)==1:
                # Only one result, we select first value
                selInFull=False
                ySel=[0]


        else:
            self.Filt2Full = list(np.arange(len(self.columns)))
        columns=self.columns[self.Filt2Full] 

        # GUI update
        self.Freeze()
        if self.bShowID:
            columnsY= ['{:03d} '.format(i)+c for i,c in enumerate(columns)]
            columnsX= ['{:03d} '.format(i)+c for i,c in enumerate(self.columns)]
        else:
            columnsY= columns
            columnsX= self.columns
        if len(columnsY)==0:
            columnsY=['No results']
            self._setReadOnly()
        else:
            self._unsetReadOnly()
        self.lbColumns.Set(columnsY)   # potentially filterd
        #  Slow line for many columns
        # NOTE: limiting to 300 for now.. I'm not sure anywant would want to scroll more than that
        # Consider adding a "more button"
        #  see e.g. https://comp.soft-sys.wxwindows.narkive.com/gDfA1Ds5/long-load-time-in-wxpython
        if self.comboX.GetCurrentSelection()==MAX_X_COLUMNS:
            self.comboX.Set(columnsX)
        else:
            if len(columnsX)>MAX_X_COLUMNS:
                columnsX_show=np.append(columnsX[:MAX_X_COLUMNS],'[...]')
            else:
                columnsX_show=columnsX
            self.comboX.Set(columnsX_show) # non filtered

        # Set selection for y, if any, and considering filtering
        if selInFull:
            for iFull in ySel:
                if iFull<len(columnsY) and iFull>=0:
                    iFilt = self.Full2Filt(iFull)
                    if iFilt>0:
                        self.lbColumns.SetSelection(iFilt)
                        self.lbColumns.EnsureVisible(iFilt)
        else:
            for iFilt in ySel:
                if iFilt>=0 and iFilt<=len(columnsY):
                    self.lbColumns.SetSelection(iFilt)
                    self.lbColumns.EnsureVisible(iFilt)

        if len(self.lbColumns.GetSelections())<=0:
            self.lbColumns.SetSelection(self.getDefaultColumnY(self.tab,len(columnsY)-1))

        # Set selection for x, if any, NOTE x is not filtered, alwasy in full!
        if (xSel<0) or xSel>len(columnsX):
            self.comboX.SetSelection(self.getDefaultColumnX(self.tab,len(columnsX)-1))
        else:
            self.comboX.SetSelection(xSel)
        self.Thaw()

    def forceOneSelection(self):
        ISel=self.lbColumns.GetSelections()
        self.lbColumns.SetSelection(-1)
        if len(ISel)>0:
            self.lbColumns.SetSelection(ISel[0])

    def forceZeroSelection(self):
        self.lbColumns.SetSelection(-1)

    def empty(self):
        self.lbColumns.Clear()
        self.comboX.Clear()
        self.lb.SetLabel('')
        self.bReadOnly=False
        self.lbColumns.Enable(False)
        self.comboX.Enable(False)
        self.bt.Enable(False)
        self.tab=None
        self.columns=[]
        self.Filt2Full=None
        self.btClear.Enable(False)
        self.btFilter.Enable(False)
        self.tFilter.Enable(False)
        self.tFilter.SetValue('')

    def getColumnSelection(self):
        """ return the indices selected for the given table so that the plotData can be extracted
        The indices will be in "orignal/full" table, removing the account for a potential filter.

        iX - index in table corresponding to selected x column
        sX - selected x column (in table)
        IY - indices in table corresponding to selected y columns
        SY - selected Y columns (in table)
        """
        iX = self.comboX.GetSelection()
        if self.bShowID:
            sX = self.comboX.GetStringSelection()[4:]
        else:
            sX = self.comboX.GetStringSelection()
        IY = self.lbColumns.GetSelections()
        if self.bShowID:
            SY = [self.lbColumns.GetString(i)[4:] for i in IY]
        else:
            SY = [self.lbColumns.GetString(i) for i in IY]
        iXFull = iX # NOTE: x is always in full
        IYFull = [self.Filt2Full[iY] for iY in IY]
        
        if self.comboX.GetCurrentSelection()==MAX_X_COLUMNS:
            self.setGUIColumns(xSel=iXFull, ySel=IYFull)
        return iXFull,IYFull,sX,SY

    def onClearFilter(self, event=None):
        self.tFilter.SetValue('')
        self.onFilterChange()

    def onFilterChange(self, event=None):
        xSel,ySel,_,_ = self.getColumnSelection() # (indices in full)
        self.setGUIColumns(xSel=xSel, ySel=ySel) # <<< Filtering done here
        self.triggerPlot() # Trigger a col selection event

    def onFilterKey(self, event=None):
        s=GetKeyString(event)
        if s=='ESCAPE' or s=='Ctrl+C':
            self.onClearFilter()
        event.Skip()

    def triggerPlot(self):
        event=wx.PyCommandEvent(wx.EVT_LISTBOX.typeId, self.lbColumns.GetId())
        wx.PostEvent(self.GetEventHandler(), event)


# --------------------------------------------------------------------------------}
# --- Selection Panel 
# --------------------------------------------------------------------------------{
class SelectionPanel(wx.Panel):
    """ Display options for the user to select data """
    def __init__(self, parent, tabList, mode='auto', mainframe=None):
        # Superclass constructor
        super(SelectionPanel,self).__init__(parent)
        # DATA
        self.mainframe     = mainframe
        self.tabList       = None
        self.itabForCol    = None
        self.parent        = parent
        self.tabSelections = {}      # x-Y-Columns selected for each table
        self.simTabSelection = {}   # selection for simTable case
        self.filterSelection = ['','','']   # filters 
        self.tabSelected   = [] # NOTE only used to remember a selection after a reload
        self.modeRequested = mode
        self.currentMode   = None
        self.nSplits = -1
        self.IKeepPerTab=None

        # GUI DATA
        self.splitter  = MultiSplit(self, style=wx.SP_LIVE_UPDATE)
        self.splitter.SetMinimumPaneSize(70)
        self.tabPanel  = TablePanel (self.splitter, self, mainframe, tabList)
        self.colPanel1 = ColumnPanel(self.splitter, self, mainframe);
        self.colPanel2 = ColumnPanel(self.splitter, self, mainframe);
        self.colPanel3 = ColumnPanel(self.splitter, self, mainframe);
        self.tabPanel.Hide()
        self.colPanel1.Hide()
        self.colPanel2.Hide()
        self.colPanel3.Hide()

        # Layout
        self.updateLayout()
        VertSizer = wx.BoxSizer(wx.VERTICAL)
        VertSizer.Add(self.splitter, 2, flag=wx.EXPAND, border=0)
        self.SetSizer(VertSizer)

        # TRIGGERS
        self.setTables(tabList)

    def updateLayout(self, mode=None):
        self.Freeze()
        if mode is None:
            mode=self.modeRequested
        else:
            self.modeRequested = mode
        if mode=='auto':
            self.autoMode()
        elif mode=='sameColumnsMode':
            self.sameColumnsMode()
        elif mode=='simColumnsMode':
            self.simColumnsMode()
        elif mode=='twoColumnsMode':
            self.twoColumnsMode()
        elif mode=='threeColumnsMode':
            self.threeColumnsMode()
        else:
            self.Thaw()
            raise Exception('Wrong mode for selection layout: {}'.format(mode))
        self.Thaw()

    def autoMode(self):
        ISel=self.tabPanel.lbTab.GetSelections()
        if self.tabList is not None:
            if self.tabList.len()<=0:
                self.nSplits=-1
                self.splitter.removeAll()
            elif self.tabList.haveSameColumns():
                self.sameColumnsMode()
            elif self.tabList.haveSameColumns(ISel):
                # We don't do same column because we know at least one table is different
                # to avoid "jumping" too much
                self.twoColumnsMode()
            else:
                # See if tables are quite similar
                IKeepPerTab, IMissPerTab, IDuplPerTab, nCols = getTabCommonColIndices([self.tabList.get(i) for i in ISel])
                if np.all(np.array([len(I) for I in IMissPerTab]))<np.mean(nCols)*0.8  and np.all(np.array([len(I) for I in IKeepPerTab])>=2):
                    self.simColumnsMode()
                elif len(ISel)==2:
                    self.twoColumnsMode()
                elif len(ISel)==3:
                    self.threeColumnsMode()
                else:
                    #self.simColumnsMode(self)
                    raise Exception('Too many panels selected with significant columns differences.')

    def sameColumnsMode(self):
        self.currentMode = 'sameColumnsMode'
        if self.nSplits==1:
            return
        if self.nSplits==0 and self.tabList.len()<=1:
            return
        self.splitter.removeAll()
        if self.tabList is not None:
            if self.tabList.len()>1:
                self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel1) 
        if  self.mainframe is not None:
            self.mainframe.mainFrameUpdateLayout()
        if self.tabList is not None:
            if self.tabList.len()<=1:
                self.nSplits=0
            else:
                self.nSplits=1
        else:
            self.nSplits=0

    def simColumnsMode(self):
        self.currentMode = 'simColumnsMode'
        self.splitter.removeAll()
        self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel2) 
        self.splitter.AppendWindow(self.colPanel1) 
        self.splitter.setEquiSash()
        if self.nSplits<2 and self.mainframe is not None:
            self.mainframe.mainFrameUpdateLayout()
        self.nSplits=2

    def twoColumnsMode(self):
        self.currentMode = 'twoColumnsMode'
        if self.nSplits==2:
            return
        self.splitter.removeAll()
        self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel2) 
        self.splitter.AppendWindow(self.colPanel1) 
        self.splitter.setEquiSash()
        if self.nSplits<2 and self.mainframe is not None:
            self.mainframe.mainFrameUpdateLayout()
        self.nSplits=2

    def threeColumnsMode(self):
        self.currentMode = 'threeColumnsMode'
        if self.nSplits==3:
            return
        self.splitter.removeAll()
        self.splitter.AppendWindow(self.tabPanel) 
        self.splitter.AppendWindow(self.colPanel3) 
        self.splitter.AppendWindow(self.colPanel2) 
        self.splitter.AppendWindow(self.colPanel1) 
        self.splitter.setEquiSash()
        if self.mainframe is not None:
            self.mainframe.mainFrameUpdateLayout()
        self.nSplits=3

    def setTables(self,tabList,update=False):
        """ Set the list of tables. Keeping the selection if it's an update """
        # TODO PUT ME IN TABLE PANEL
        # Find a better way to remember selection
        #print('UPDATING TABLES')
        # Emptying GUI - TODO only if needed
        self.colPanel1.empty()
        self.colPanel2.empty()
        self.colPanel3.empty()
        # Adding
        self.tabList = tabList
        self.tabPanel.tabList = self.tabList
        tabnames = self.tabList.tabNames
        self.tabPanel.updateTabNames()
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
                if i<self.tabList.len():
                    self.tabPanel.lbTab.SetSelection(i)
            #
        if len(self.tabPanel.lbTab.GetSelections())==0:
            self.selectDefaultTable()
        if self.tabList.len()>0:
            # Trigger - updating columns and layout
            ISel=self.tabPanel.lbTab.GetSelections()
            self.tabSelected=ISel
            # Mode might have changed if tables changed
            if self.modeRequested=='auto':
                self.autoMode()
            if self.currentMode=='simColumnsMode':
                self.setColForSimTab(ISel)
            else:
                if len(ISel)==1:
                    self.setTabForCol(ISel[0],1)
                elif len(ISel)==2:
                    self.setTabForCol(ISel[0],1)
                    self.setTabForCol(ISel[1],2)
                elif len(ISel)==3:
                    self.setTabForCol(ISel[0],1)
                    self.setTabForCol(ISel[1],2)
                    self.setTabForCol(ISel[2],3)
                else: # Likely all tables have the same columns
                    self.setTabForCol(ISel[0],1)
        self.updateLayout(self.modeRequested)

    def setTabForCol(self,iTabSel,iPanel):
        t  = self.tabList.get(iTabSel)
        ts = self.tabSelections[t.name]
        if iPanel==1:
            self.colPanel1.setTab(t,ts['xSel'],ts['ySel'], sFilter=self.filterSelection[0])
        elif iPanel==2:
            self.colPanel2.setTab(t,ts['xSel'],ts['ySel'], sFilter=self.filterSelection[1])
        elif iPanel==3:
            self.colPanel3.setTab(t,ts['xSel'],ts['ySel'], sFilter=self.filterSelection[2])
        else:
            raise Exception('Wrong ipanel')

    def setColForSimTab(self,ISel):
        """ Set column panels for similar tables """
        tabs = [self.tabList.get(i) for i in ISel]
        IKeepPerTab, IMissPerTab, IDuplPerTab, _ = getTabCommonColIndices(tabs)
        LenMiss = np.array([len(I) for I in IMissPerTab])
        LenKeep = np.array([len(I) for I in IKeepPerTab])
        LenDupl = np.array([len(I) for I in IDuplPerTab])

        ColInfo  = ['Sim. table mode ']
        ColInfo += ['']
        if self.tabList.haveSameColumns(ISel):
            if len(ISel)>1:
                ColInfo += ['Columns identical','']
        else:
            if (np.all(np.array(LenMiss)==0)):
                ColInfo += ['Columns identical']
                ColInfo += ['Order different!']

                ColInfo += ['','First difference:']
                ColInfo.append('----------------------------------')
                bFirst=True
                for it,t in enumerate(tabs):
                    print('IKeep',IKeepPerTab[it])
                    if it==0:
                        continue
                    INotOrdered=[ii for i,ii in enumerate(IKeepPerTab[it]) if ii!=IKeepPerTab[0][i]]
                    print('INot',INotOrdered)
                    if len(INotOrdered)>0:
                        im=INotOrdered[0]
                        if bFirst:
                            ColInfo.append('{}:'.format(tabs[0].active_name))
                            ColInfo.append('{:03d} {:s}'.format(im, tabs[0].columns[im]))
                            bFirst=False
                        ColInfo.append('{}:'.format(t.active_name))
                        ColInfo.append('{:03d} {:s}'.format(im, t.columns[im]))
                        ColInfo.append('----------------------------------')

            else:
                ColInfo += ['Columns different!']
                ColInfo += ['(similar: {})'.format(LenKeep[0])]
                ColInfo += ['','Missing columns:']
                ColInfo.append('----------------------------------')
                for it,t in enumerate(tabs):
                    ColInfo.append('{}:'.format(t.active_name))
                    if len(IMissPerTab[it])==0:
                        ColInfo.append('    (None) ')
                    for im in IMissPerTab[it]:
                        ColInfo.append('{:03d} {:s}'.format(im, t.columns[im]))
                    ColInfo.append('----------------------------------')

        if (np.any(np.array(LenDupl)>0)):
            if len(ISel)>1:
                ColInfo += ['','Common duplicates:']
            else:
                ColInfo += ['','Duplicates:']
            ColInfo.append('----------------------------------')
            for it,t in enumerate(tabs):
                ColInfo.append('{}:'.format(t.active_name))
                if len(IDuplPerTab[it])==0:
                    ColInfo.append('    (None) ')
                for im in IDuplPerTab[it]:
                    ColInfo.append('{:03d} {:s}'.format(im, t.columns[im]))
                ColInfo.append('----------------------------------')



        colNames = ['Index'] + [tabs[0].columns[i] for i in IKeepPerTab[0]]

        # restore selection 
        xSel = -1
        ySel = []
        sFilter = self.filterSelection[0]
        if 'xSel' in self.simTabSelection:
            xSel = self.simTabSelection['xSel']
            ySel = self.simTabSelection['ySel']
        # Set the colPanels
        self.colPanel1.setTab(tab=None, colNames=colNames, tabLabel=' Tab. Intersection', xSel=xSel, ySel=ySel, sFilter=sFilter)
        self.colPanel2.setReadOnly(' Tab. Difference', ColInfo)
        self.IKeepPerTab=IKeepPerTab



    def selectDefaultTable(self):
        # Selecting the first table
        if self.tabPanel.lbTab.GetCount()>0:
            self.tabPanel.lbTab.SetSelection(0)
            self.tabSelected=[0]
        else:
            self.tabSelected=[]

    def tabSelectionChanged(self):
        # TODO This can be cleaned-up and merged with updateLayout
        # Storing the previous selection 
        self.saveSelection() # 
        ISel=self.tabPanel.lbTab.GetSelections()
        if len(ISel)>0:
            if self.modeRequested=='auto':
                self.autoMode()
            if self.currentMode=='simColumnsMode':# and len(ISel)>1:
                self.setColForSimTab(ISel)
                self.tabSelected=self.tabPanel.lbTab.GetSelections()
                return

            if self.tabList.haveSameColumns(ISel):
                # Setting tab
                self.setTabForCol(ISel[0],1) 
                self.colPanel2.empty()
                self.colPanel3.empty()
            else:
                if self.nSplits==2:
                    if len(ISel)>2:
                        Error(self,'In this mode, only two tables can be selected. To compare three tables, uses the "3 different tables" mode. Otherwise the tables need to have the same columns.')
                        ISel=ISel[0:2]
                        self.tabPanel.lbTab.SetSelection(wx.NOT_FOUND)
                        for isel in ISel:
                            self.tabPanel.lbTab.SetSelection(isel)
                    self.colPanel3.empty()
                elif self.nSplits==3:
                    if len(ISel)>3:
                        Error(self,'In this mode, only three tables can be selected. To compare more than three tables, the tables need to have the same columns.')
                        ISel=ISel[0:3]
                        self.tabPanel.lbTab.SetSelection(wx.NOT_FOUND)
                        for isel in ISel:
                            self.tabPanel.lbTab.SetSelection(isel)
                else:
                    Error(self,'The tables selected have different columns.\n\nThis is not compatible with the "Same tables" mode. To compare them, chose one of the following mode: "2 tables", "3 tables" or "Sim. tables".')
                    self.colPanel2.empty()
                    self.colPanel3.empty()
                    # unselect all and select only the first one
                    ISel=[ISel[0]]
                    self.tabPanel.lbTab.SetSelection(wx.NOT_FOUND)
                    self.tabPanel.lbTab.SetSelection(ISel[0])
                for iPanel,iTab in enumerate(ISel):
                    self.setTabForCol(iTab,iPanel+1) 
            #print('>>Updating tabSelected, from',self.tabSelected,'to',self.tabPanel.lbTab.GetSelections())
            self.tabSelected=self.tabPanel.lbTab.GetSelections()

    def colSelectionChanged(self):
        """ Simple triggers when column selection is changed, NOTE: does not redraw """
        if self.currentMode=='simColumnsMode':
            self.colPanel2.forceZeroSelection()
        else:
            if self.nSplits in [2,3]:
                ISel=self.tabPanel.lbTab.GetSelections()
                if self.tabList.haveSameColumns(ISel):
                    pass # TODO: this test is identical to onTabSelectionChange. Unification.
                # elif len(ISel)==2:
                #     self.colPanel1.forceOneSelection()
                #     self.colPanel2.forceOneSelection()
                # elif len(ISel)==3:
                #     self.colPanel1.forceOneSelection()
                #     self.colPanel2.forceOneSelection()
                #     self.colPanel3.forceOneSelection()

    def update_tabs(self, tabList):
        self.setTables(tabList, update=True)

    def renameTable(self,iTab, oldName, newName):
        #self.printSelection()
        self.tabSelections[newName] = self.tabSelections.pop(oldName)
        self.tabPanel.updateTabNames()
        #self.printSelection()

    def saveSelection(self):
        #self.ISel=self.tabPanel.lbTab.GetSelections()
        ISel=self.tabSelected # 

        # --- Save filters
        self.filterSelection  = [self.colPanel1.tFilter.GetLineText(0).strip()]
        self.filterSelection += [self.colPanel2.tFilter.GetLineText(0).strip()]
        self.filterSelection += [self.colPanel3.tFilter.GetLineText(0).strip()]

        # --- Save simTab is needed
        if self.currentMode=='simColumnsMode':
            self.simTabSelection['xSel'] = self.colPanel1.comboX.GetSelection()
            self.simTabSelection['ySel'] = self.colPanel1.lbColumns.GetSelections()
        else:
            #self.simTabSelection = {} # We do not erase it
            # --- Save selected columns for each tab
            if self.tabList.haveSameColumns(ISel):
                for ii in ISel:
                    t=self.tabList.get(ii)
                    self.tabSelections[t.name]['xSel'] = self.colPanel1.comboX.GetSelection()
                    self.tabSelections[t.name]['ySel'] = self.colPanel1.lbColumns.GetSelections()
            else:
                if len(ISel)>=1:
                    t=self.tabList.get(ISel[0])
                    self.tabSelections[t.name]['xSel'] = self.colPanel1.comboX.GetSelection()
                    self.tabSelections[t.name]['ySel'] = self.colPanel1.lbColumns.GetSelections()
                if len(ISel)>=2:
                    t=self.tabList.get(ISel[1])
                    self.tabSelections[t.name]['xSel'] = self.colPanel2.comboX.GetSelection()
                    self.tabSelections[t.name]['ySel'] = self.colPanel2.lbColumns.GetSelections()
                if len(ISel)>=3:
                    t=self.tabList.get(ISel[2])
                    self.tabSelections[t.name]['xSel'] = self.colPanel3.comboX.GetSelection()
                    self.tabSelections[t.name]['ySel'] = self.colPanel3.lbColumns.GetSelections()
            self.tabSelected = self.tabPanel.lbTab.GetSelections();
        #self.printSelection()

    def printSelection(self):
        TS=self.tabSelections
        for i,tn in enumerate(self.tabList.tabNames):
            if tn not in TS.keys():
                print('Tab',i,' Name {} not found in selection'.format(tn))
            else:
                print('Tab',i,'xSel:',TS[tn]['xSel'],'ySel:',TS[tn]['ySel'],'Name:',tn)
        print('simTab ', self.simTabSelection)
        print('filters', self.filterSelection)

    def getPlotDataSelection(self):
        """ Returns the table/columns indices to be plotted"""
        ID = []
        SameCol=False
        if self.tabList is not None  and self.tabList.len()>0:
            ITab,STab = self.getSelectedTables()
            if self.currentMode=='simColumnsMode' and len(ITab)>1:
                iiX1,IY1,ssX1,SY1 = self.colPanel1.getColumnSelection()
                SameCol=False
                for i,(itab,stab) in enumerate(zip(ITab,STab)):
                    IKeep=self.IKeepPerTab[i]
                    for j,(iiy,ssy) in enumerate(zip(IY1,SY1)):
                        if iiy==0:
                            iy =  0
                            sy =  ssy
                        else:
                            iy =  IKeep[iiy-1]+1
                            sy =  self.tabList.get(itab).columns[IKeep[iiy-1]]
                        if iiX1==0:
                            iX1 =  0
                            sX1 = ssX1
                        else:
                            iX1 =  IKeep[iiX1-1]+1
                            sX1 =  self.tabList.get(itab).columns[IKeep[iiX1-1]]
                        ID.append([itab,iX1,iy,sX1,sy,stab])
            else:
                iX1,IY1,sX1,SY1 = self.colPanel1.getColumnSelection()
                SameCol=self.tabList.haveSameColumns(ITab)
                if self.nSplits in [0,1] or SameCol:
                    for i,(itab,stab) in enumerate(zip(ITab,STab)):
                        for j,(iy,sy) in enumerate(zip(IY1,SY1)):
                            ID.append([itab,iX1,iy,sX1,sy,stab])
                elif self.nSplits in [2,3]:
                    if len(ITab)>=1:
                        for j,(iy,sy) in enumerate(zip(IY1,SY1)):
                            ID.append([ITab[0],iX1,iy,sX1,sy,STab[0]])
                    if len(ITab)>=2:
                        iX2,IY2,sX2,SY2 = self.colPanel2.getColumnSelection()
                        for j,(iy,sy) in enumerate(zip(IY2,SY2)):
                            ID.append([ITab[1],iX2,iy,sX2,sy,STab[1]])
                    if len(ITab)>=3:
                        iX2,IY2,sX2,SY2 = self.colPanel3.getColumnSelection()
                        for j,(iy,sy) in enumerate(zip(IY2,SY2)):
                            ID.append([ITab[2],iX2,iy,sX2,sy,STab[2]])
                else:
                    raise Exception('Wrong number of splits {}'.format(self.nSplits))
        return ID,SameCol,self.currentMode

    def getSelectedTables(self):
        I=self.tabPanel.lbTab.GetSelections()
        S=[self.tabPanel.lbTab.GetString(i) for i in I]
        return I,S

    def getAllTables(self):
        I=range(self.tabPanel.lbTab.GetCount())
        S=[self.tabPanel.lbTab.GetString(i) for i in I]
        return I,S

    def clean_memory(self):
        self.colPanel1.empty()
        self.colPanel2.empty()
        self.colPanel3.empty()
        self.tabPanel.empty()
        del self.tabList
        self.tabList=None

    @property
    def xCol(self):
        iX, _, sX, _ = self.colPanel1.getColumnSelection()
        return iX,sX


if __name__ == '__main__':
    import pandas as pd;
    from Tables import Table, TableList
    import numpy as np


    app = wx.App(False)
    self=wx.Frame(None,-1,"Title")
    tab1=Table(data=pd.DataFrame(data={'ID': np.arange(0,100),'ColA': np.random.normal(0,1,100)+1,'ColB':np.random.normal(0,1,100)+2}))
    tab2=Table(data=pd.DataFrame(data={'ID': np.arange(50,150),'ColA': np.random.normal(0,1,100)+1,'ColB':np.random.normal(0,1,100)+2}))
    tabs = TableList([tab1,tab2])

    selPanel=SelectionPanel(self, tabs, mode='twoColumnsMode')
    self.SetSize((800, 600))
    self.Center()
    self.Show()


    selPanel.tabPanel.lbTab.SetSelection(0)
    selPanel.tabPanel.lbTab.SetSelection(1)
    menu = TablePopup(selPanel.tabPanel.lbTab, selPanel.tabPanel, selPanel)
    menu.OnMergeTabs(None)

    app.MainLoop()

