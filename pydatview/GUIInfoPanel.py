import wx
#import wx.lib.mixins.listctrl as listmix
import numpy as np
try:
    from .common import getMonoFont, getColumn
except:
    from common import getMonoFont, getColumn

musicdata = {
0 : ("Bad English"                , "The Price Of Love"                     , "Rock")  , 
1 : ("DNA featuring Suzanne Vega" , "Tom's Diner"                           , "Rock")  , 
2 : ("George Michael"             , "Praying For Time"                      , "Rock")  , 
3 : ("Gloria Estefan"             , "Here We Are"                           , "Rock")  , 
4 : ("Linda Ronstadt"             , "Don't Know Much"                       , "Rock")  , 
5 : ("Michael Bolton"             , "How Am I Supposed To Live Without You" , "Blues") , 
6 : ("Paul Young"                 , "Oh Girl"                               , "Rock")  , 
}
 
alldata = {
0 : ("Tab 1 " , 0.5  , 1.0)  , 
1 : ("Tab 2 " , 0.6  , 2.0)  , 
2 : ("Tab 3 " , 0.7  , 3.0)  , 
}
# --------------------------------------------------------------------------------}
# --- InfoPanel 
# --------------------------------------------------------------------------------{
# class TestListCtrl(wx.ListCtrl):
#     def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
#                  size=wx.DefaultSize, style=0):
#         wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
#class TestListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
class TestListCtrl(wx.ListCtrl):
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        #listmix.ListCtrlAutoWidthMixin.__init__(self)
        #self.setResizeColumn(0)

class InfoPanel(wx.Panel):
    """ Display the list of the columns for the user to select """

    #----------------------------------------------------------------------
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.tbStats = TestListCtrl(self, size=(-1,100),
                         style=wx.LC_REPORT
                         |wx.BORDER_SUNKEN
                         )
                         #|wx.LC_SORT_ASCENDING
        self.tbStats.SetFont(getMonoFont())
        # For sorting see wx/lib/mixins/listctrl.py listmix.ColumnSorterMixin
        #self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.tbStats)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tbStats, 2, wx.ALL|wx.EXPAND, border=5)
        self.SetSizer(sizer)
        self.SetMaxSize((-1, 50))

    def showStats(self,files,tabs,ITab,ColIndexes,ColNames,iX,erase=False):
        #        if files is not None:
        #            for i,f in enumerate(files):
        #                self.tInfo.AppendText('File {}: {}\n'.format(i,f))
        Columns   = ['Column','Mean','Min','Max']
        Functions = [None,np.nanmean,np.nanmin,np.nanmax]
        Cols=[]
        Cols.append({'name':'Column','al':'L','f':None      ,'fmt':'s'    })
        Cols.append({'name':'Mean'  ,'al':'R','f':np.nanmean,'fmt':'.3e'  })
        Cols.append({'name':'Std'   ,'al':'R','f':np.nanstd ,'fmt':'.3e'  })
        Cols.append({'name':'Min'   ,'al':'R','f':np.nanmin ,'fmt':'.3e'  })
        Cols.append({'name':'Max'   ,'al':'R','f':np.nanmax ,'fmt':'.3e'  })
        Cols.append({'name':'n'     ,'al':'R','f':len       ,'fmt':'d'    })
        #Cols.append({'name':'dx'    ,'al':'R','f':lambda x:x[1]-x[0]}) # TODO

        # Adding columns
        if erase:
            self.clean()
            AL={'L':wx.LIST_FORMAT_LEFT,'R':wx.LIST_FORMAT_RIGHT,'C':wx.LIST_FORMAT_CENTER}
            for i,c in enumerate(Cols):
                self.tbStats.InsertColumn(i,c['name'], AL[c['al']])

        # Inserting items
        index = self.tbStats.GetItemCount()
        for iTab in ITab:
            tab = tabs[iTab]
            x,_,_,_=getColumn(tab.data,iX)
            for i,s in zip(ColIndexes,ColNames):
                y,yIsString,yIsDate,_=getColumn(tab.data,i)
                self.tbStats.InsertItem(index,  s)
                if yIsString:
                    pass
                #    self.tInfo.AppendText('{:15s} (string) first:{}  last:{}  min:{}  max:{}\n'.format(s,y[0],y[-1],min(y,key=len),max(y,key=len)))
                elif yIsDate:
                    pass
                #    dt0=y[1]-y[0]
                #    dt    = pretty_time(np.timedelta64((y[1]-y[0]),'s').item().total_seconds())
                #    dtAll = pretty_time(np.timedelta64((y[-1]-y[0]),'s').item().total_seconds())
                #    self.tInfo.AppendText('{:15s} (date) first:{} last:{} dt:{} range:{}\n'.format(s,y[0],y[-1],dt,dtAll))

                else:
                    for j,c in enumerate(Cols[1:]):
                        self.tbStats.SetItem(index, j+1,('{:'+c['fmt']+'}').format(c['f']((y))))
                index +=1
        for i in range(self.tbStats.GetColumnCount()):
            self.tbStats.SetColumnWidth(i, wx.LIST_AUTOSIZE_USEHEADER) 


    def clean(self):
        self.tbStats.DeleteAllItems()
        self.tbStats.DeleteAllColumns()

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

