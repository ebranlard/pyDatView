import wx
import numpy as np
import os


def getMonoFont():
    #return wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Monospace')
    if os.name=='nt':
        return wx.Font(9, wx.TELETYPE, wx.NORMAL, wx.NORMAL, False)
    else:
        return wx.Font(8, wx.TELETYPE, wx.NORMAL, wx.NORMAL, False)


def getColumn(df,i):
    if i == wx.NOT_FOUND or i == 0:
        x = np.array(range(len(df.iloc[:, 1])))
        c = None
        isString = False
        isDate   = False
    else:
        c = df.iloc[:, i-1]
        x = df.iloc[:, i-1].values
        isString = c.dtype == np.object and isinstance(c.values[0], str)
        isDate   = np.issubdtype(c.dtype, np.datetime64)
        if isDate:
            x=x.astype('datetime64[s]')

    return x,isString,isDate,c



def no_unit(s):
    iu=s.rfind(' [')
    if iu>1:
        return s[:iu]
    else:
        return s

def unit(s):
    iu=s.rfind('[')
    if iu>1:
        return s[iu:]
    else:
        return ''
