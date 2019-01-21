import wx
import numpy as np
import os
import platform

# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
def getMonoFontAbs():
    #return wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Monospace')
    if os.name=='nt':
        font=wx.Font(9, wx.TELETYPE, wx.NORMAL, wx.NORMAL, False)
    elif os.name=='posix':
        font=wx.Font(10, wx.TELETYPE, wx.NORMAL, wx.NORMAL, False)
    else:
        font=wx.Font(8, wx.TELETYPE, wx.NORMAL, wx.NORMAL, False)
    return font

def getMonoFont(widget):
    font = widget.GetFont()
    font.SetFamily(wx.TELETYPE)
    if platform.system()=='Windows':
        pass
    elif platform.system()=='Linux':
        pass
    elif platform.system()=='Darwin':
        font.SetPointSize(font.GetPointSize()-1)
    else:
        pass
    return font



def getColumn(df,i):
    if i == wx.NOT_FOUND or i == 0:
        x = np.array(range(df.shape[0]))
        c = None
        isString = False
        isDate   = False
    else:
        c = df.iloc[:, i-1]
        x = df.iloc[:, i-1].values
        isString = c.dtype == np.object and isinstance(c.values[0], str)
        if isString:
            x=x.astype(str)
        isDate   = np.issubdtype(c.dtype, np.datetime64)
        if isDate:
            x=x.astype('datetime64[s]')

    return x,isString,isDate,c

# --------------------------------------------------------------------------------}
# --- Helper functions
# --------------------------------------------------------------------------------{
def YesNo(parent, question, caption = 'Yes or no?'):
    dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_YES
    dlg.Destroy()
    return result
def Info(parent, message, caption = 'Info'):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()
def Warn(parent, message, caption = 'Warning!'):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_WARNING)
    dlg.ShowModal()
    dlg.Destroy()
def Error(parent, message, caption = 'Error!'):
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()
    dlg.Destroy()



