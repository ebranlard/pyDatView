import wx
import numpy as np
import os
import platform

_MONOFONTSIZE=9
_FONTSIZE=9

# --------------------------------------------------------------------------------}
# --- FONT
# --------------------------------------------------------------------------------{
def setMonoFontSize(fs):
    global _MONOFONTSIZE
    _MONOFONTSIZE=int(fs)

def getMonoFontSize():
    global _MONOFONTSIZE
    return _MONOFONTSIZE

def setFontSize(fs):
    global _FONTSIZE
    _FONTSIZE=int(fs)

def getFontSize():
    global _FONTSIZE
    return _FONTSIZE


def getFont(widget):
    global _FONTSIZE
    font = widget.GetFont()
    #font.SetFamily(wx.TELETYPE)
    font.SetPointSize(_FONTSIZE)
    #font=wx.Font(_FONTSIZE-1, wx.TELETYPE, wx.NORMAL, wx.NORMAL, False)
    return font

def getMonoFont(widget):
    global _MONOFONTSIZE
    font = widget.GetFont()
    font.SetFamily(wx.TELETYPE)
    font.SetPointSize(_MONOFONTSIZE)
    return font

# --------------------------------------------------------------------------------}
# --- Helper functions
# --------------------------------------------------------------------------------{
def About(parent, message):
    class MessageBox(wx.Dialog):
        def __init__(self, parent, title, message):
            wx.Dialog.__init__(self, parent, title=title, style=wx.CAPTION|wx.CLOSE_BOX)
            text = wx.TextCtrl(self, style=wx.TE_READONLY|wx.BORDER_NONE|wx.TE_MULTILINE|wx.TE_AUTO_URL)
            text.SetValue(message)
            text.SetBackgroundColour(wx.SystemSettings.GetColour(4))
            self.ShowModal()
            self.Destroy()
    MessageBox(parent, 'About', message)

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



