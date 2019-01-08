import wx
import numpy as np
try:
    from .common import getMonoFont, getColumn
except:
    from common import getMonoFont, getColumn

# --------------------------------------------------------------------------------}
# --- InfoPanel 
# --------------------------------------------------------------------------------{
class InfoPanel(wx.Panel):
    """ Display the list of the columns for the user to select """
    def __init__(self, parent):
        # Superclass constructor
        super(InfoPanel,self).__init__(parent)
        # GUI
        self.tInfo = wx.TextCtrl(self,size = (200,5),style = wx.TE_MULTILINE|wx.TE_READONLY)
        self.tInfo.SetFont(getMonoFont())

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tInfo, 2, flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)
        self.SetMaxSize((-1, 50))

    def showStats(self,files,tabs,ITab,ColIndexes,ColNames,iX,erase=False):
        if erase:
            self.clean()
#        if files is not None:
#            for i,f in enumerate(files):
#                self.tInfo.AppendText('File {}: {}\n'.format(i,f))
#
        for iTab in ITab:
            tab = tabs[iTab]
            x,_,_,_=getColumn(tab.data,iX)
            for i,s in zip(ColIndexes,ColNames):
                y,yIsString,yIsDate,_=getColumn(tab.data,i)
                if yIsString:
                    self.tInfo.AppendText('{:15s} (string) first:{}  last:{}  min:{}  max:{}\n'.format(s,y[0],y[-1],min(y,key=len),max(y,key=len)))
                elif yIsDate:
                    dt0=y[1]-y[0]
                    dt    = pretty_time(np.timedelta64((y[1]-y[0]),'s').item().total_seconds())
                    dtAll = pretty_time(np.timedelta64((y[-1]-y[0]),'s').item().total_seconds())
                    self.tInfo.AppendText('{:15s} (date) first:{} last:{} dt:{} range:{}\n'.format(s,y[0],y[-1],dt,dtAll))
                else:
                    #self.tInfo.AppendText('{:15s} mean:{:10.3e}  std:{:10.3e}  min:{:10.3e}  max:{:10.3e}  dx:{:10.3e}  n:{:d}\n'.format(s,np.nanmean(y),np.nanstd(y),np.nanmin(y),np.nanmax(y),x[1]-x[0],len(y) ))
                    self.tInfo.AppendText('{:15s} mean:{:10.3e}  std:{:10.3e}  min:{:10.3e}  max:{:10.3e}\n'.format(s,np.nanmean(y),np.nanstd(y),np.nanmin(y),np.nanmax(y),x[1]-x[0],len(y) ))
        self.tInfo.ShowPosition(0)

    def clean(self):
        self.tInfo.SetValue("")


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
    p1.showStats(None,[tab],[0],[0,1],tab.columns,0,erase=False)

    app.MainLoop()

