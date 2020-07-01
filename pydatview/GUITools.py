import wx
import numpy as np
import pandas as pd
import copy

# For log dec tool
from .damping import logDecFromDecay
from .common import CHAR, Error, pretty_num_short, Info
from collections import OrderedDict
from .curve_fitting import model_fit, extract_key_miscnum, extract_key_num, MODELS, FITTERS, set_common_keys


TOOL_BORDER=15

# --------------------------------------------------------------------------------}
# --- Default class for tools
# --------------------------------------------------------------------------------{
class GUIToolPanel(wx.Panel):
    def __init__(self, parent):
        super(GUIToolPanel,self).__init__(parent)
        self.parent   = parent

    def destroy(self,event=None):
        self.parent.removeTools()

    def getBtBitmap(self,par,label,Type=None,callback=None,bitmap=False):
        if Type is not None:
            label=CHAR[Type]+' '+label

        bt=wx.Button(par,wx.ID_ANY,label, style=wx.BU_EXACTFIT)
        #try:
        #    if bitmap is not None:    
        #            bt.SetBitmapLabel(wx.ArtProvider.GetBitmap(bitmap)) #,size=(12,12)))
        #        else:
        #except:
        #    pass
        if callback is not None:
            par.Bind(wx.EVT_BUTTON, callback, bt)
        return bt


# --------------------------------------------------------------------------------}
# ---   Log Dec
# --------------------------------------------------------------------------------{
class LogDecToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(LogDecToolPanel,self).__init__(parent)
        btClose = self.getBtBitmap(self,'Close'  ,'close'  ,self.destroy  )
        btComp  = self.getBtBitmap(self,'Compute','compute',self.onCompute)
        self.lb = wx.StaticText( self, -1, '                     ')
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btClose   ,0, flag = wx.LEFT|wx.CENTER,border = 1)
        self.sizer.Add(btComp    ,0, flag = wx.LEFT|wx.CENTER,border = 5)
        self.sizer.Add(self.lb   ,0, flag = wx.LEFT|wx.CENTER,border = 5)
        self.SetSizer(self.sizer)

    def onCompute(self,event=None):
        if len(self.parent.plotData)!=1:
            Error(self,'Log Dec tool only works with a single plot.')
            return
        pd =self.parent.plotData[0]
        try:
            logdec,DampingRatio,T,fn,fd,IPos,INeg,epos,eneg=logDecFromDecay(pd.y,pd.x)
            lab='LogDec.: {:.4f} - Damping ratio: {:.4f} - F_n: {:.4f} - F_d: {:.4f} - T:{:.3f}'.format(logdec,DampingRatio,fn,fd,T)
            self.lb.SetLabel(lab)
            self.sizer.Layout()
            ax=self.parent.fig.axes[0]
            ax.plot(pd.x[IPos],pd.y[IPos],'o')
            ax.plot(pd.x[INeg],pd.y[INeg],'o')
            ax.plot(pd.x ,epos,'k--')
            ax.plot(pd.x ,eneg,'k--')
            self.parent.canvas.draw()
        except:
            self.lb.SetLabel('Failed. The signal needs to look like the decay of a first order system.')
        #self.parent.redraw(); # DATA HAS CHANGED

# --------------------------------------------------------------------------------}
# --- Mask
# --------------------------------------------------------------------------------{
class MaskToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(MaskToolPanel,self).__init__(parent)

        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()

        allMask = tabList.commonMaskString
        if len(allMask)==0:
            allMask=self.guessMask(tabList) # no known mask, we guess one to help the user

        btClose    = self.getBtBitmap(self, 'Close','close', self.destroy)
        btClear    = self.getBtBitmap(self, 'Clear','sun', self.onClear) # DELETE
        btComp     = self.getBtBitmap(self, u'Mask (add)','add'  , self.onApply)
        btCompMask = self.getBtBitmap(self, 'Mask','cloud', self.onApplyMask)

        self.lb         = wx.StaticText( self, -1, """(Example of mask: "({Time}>100) && ({Time}<50) && ({WS}==5)"    or    "{Date} > '2018-10-01'")""")
        self.cbTabs     = wx.ComboBox(self, choices=tabListNames, style=wx.CB_READONLY)
        self.cbTabs.SetSelection(0)

        self.textMask = wx.TextCtrl(self, wx.ID_ANY, allMask)
        #self.textMask.SetValue('({Time}>100) & ({Time}<400)')
        #self.textMask.SetValue("{Date} > '2018-10-01'")

        btSizer  = wx.FlexGridSizer(rows=2, cols=2, hgap=2, vgap=0)
        btSizer.Add(btClose   ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btClear   ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btComp    ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btCompMask,0,flag = wx.ALL|wx.EXPAND, border = 1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(wx.StaticText(self, -1, 'Tab:')   , 0, wx.CENTER|wx.LEFT, 0)
        row_sizer.Add(self.cbTabs                       , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Mask:'), 0, wx.CENTER|wx.LEFT, 5)
        row_sizer.Add(self.textMask, 1, wx.CENTER|wx.LEFT| wx.EXPAND | wx.ALIGN_RIGHT, 5)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.lb     ,0, flag = wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM, border = 5)
        vert_sizer.Add(row_sizer   ,1, flag = wx.EXPAND|wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM, border = 5)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT           ,border = 5)
        self.sizer.Add(vert_sizer   ,1, flag = wx.LEFT|wx.EXPAND ,border = TOOL_BORDER)
        self.SetSizer(self.sizer)
        self.Bind(wx.EVT_COMBOBOX, self.onTabChange, self.cbTabs )

    def onTabChange(self,event=None):
        tabList = self.parent.selPanel.tabList
        iSel=self.cbTabs.GetSelection()
        if iSel==0:
            maskString = tabList.commonMaskString
        else:
            maskString= tabList.get(iSel-1).maskString
        if len(maskString)>0:
            self.textMask.SetValue(maskString)
        else:
            self.textMask.SetValue('') # no known mask

    def guessMask(self,tabList):
        cols=[c.lower() for c in tabList.get(0).columns_clean]
        if 'time' in cols:
            return '{Time} > 100'
        elif 'date' in cols:
            return "{Date} > '2017-01-01"
        else:
            return '' 

    def onClear(self,event=None):
        iSel      = self.cbTabs.GetSelection()
        tabList   = self.parent.selPanel.tabList
        mainframe = self.parent.mainframe
        if iSel==0:
            tabList.clearCommonMask()
        else:
            tabList.get(iSel-1).clearMask()

        mainframe.redraw()
        self.onTabChange()

    def onApplyMask(self,event=None):
        self.onApply(event,bAdd=False)

    def onApply(self,event=None,bAdd=True):
        maskString = self.textMask.GetLineText(0)
        iSel         = self.cbTabs.GetSelection()
        tabList      = self.parent.selPanel.tabList
        mainframe    = self.parent.mainframe
        if iSel==0:
            dfs, names, errors = tabList.applyCommonMaskString(maskString, bAdd=bAdd)
            if bAdd:
                mainframe.load_dfs(dfs,names,bAdd=bAdd)
            else:
                mainframe.redraw()
            if len(errors)>0:
                raise Exception('Error: The mask failed on some tables:\n\n'+'\n'.join(errors))
        else:
            dfs, name = tabList.get(iSel-1).applyMaskString(maskString, bAdd=bAdd)
            if bAdd:
                mainframe.load_df(df,name,bAdd=bAdd)
            else:
                mainframe.redraw()
        self.updateTabList()


    def updateTabList(self,event=None):
        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()
        iSel=np.min([self.cbTabs.GetSelection(),len(tabListNames)])
        self.cbTabs.Clear()
        [self.cbTabs.Append(tn) for tn in tabListNames]
        self.cbTabs.SetSelection(iSel)

# --------------------------------------------------------------------------------}
# --- Radial
# --------------------------------------------------------------------------------{
sAVG_METHODS = ['Last `n` seconds','Last `n` periods']
AVG_METHODS  = ['constantwindow','periods']

class RadialToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(RadialToolPanel,self).__init__(parent)

        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()

        btClose = self.getBtBitmap(self,'Close'  ,'close'  , self.destroy)
        btComp  = self.getBtBitmap(self,'Average','compute', self.onApply) # ART_PLUS

        self.lb         = wx.StaticText( self, -1, """Select tables, averaging method and average parameter (`Period` methods uses the `azimuth` signal) """)
        self.cbTabs     = wx.ComboBox(self, choices=tabListNames, style=wx.CB_READONLY)
        self.cbMethod   = wx.ComboBox(self, choices=sAVG_METHODS, style=wx.CB_READONLY)
        self.cbTabs.SetSelection(0)
        self.cbMethod.SetSelection(0)

        self.textAverageParam = wx.TextCtrl(self, wx.ID_ANY, '2',size = (36,-1), style=wx.TE_PROCESS_ENTER)

        btSizer  = wx.FlexGridSizer(rows=2, cols=1, hgap=0, vgap=0)
        #btSizer  = wx.BoxSizer(wx.VERTICAL)
        btSizer.Add(btClose   ,0, flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btComp    ,0, flag = wx.ALL|wx.EXPAND, border = 1)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(wx.StaticText(self, -1, 'Tab:')   , 0, wx.CENTER|wx.LEFT, 0)
        row_sizer.Add(self.cbTabs                       , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Method:'), 0, wx.CENTER|wx.LEFT, 5)
        row_sizer.Add(self.cbMethod                     , 0, wx.CENTER|wx.LEFT, 2)
        row_sizer.Add(wx.StaticText(self, -1, 'Param:') , 0, wx.CENTER|wx.LEFT, 5)
        row_sizer.Add(self.textAverageParam             , 0, wx.CENTER|wx.LEFT|wx.RIGHT| wx.EXPAND | wx.ALIGN_RIGHT, 2)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.lb     ,0, flag =wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM,border = 5)
        vert_sizer.Add(row_sizer   ,0, flag =wx.ALIGN_LEFT|wx.TOP|wx.BOTTOM,border = 5)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT          ,border = 5)
        self.sizer.Add(vert_sizer   ,0, flag = wx.LEFT|wx.EXPAND,border = TOOL_BORDER)
        self.SetSizer(self.sizer)
        self.Bind(wx.EVT_COMBOBOX, self.onTabChange, self.cbTabs )

    def onTabChange(self,event=None):
        tabList = self.parent.selPanel.tabList

    def onApply(self,event=None):
        try:
            avgParam     = float(self.textAverageParam.GetLineText(0))
        except:
            raise Exception('Error: the averaging parameter needs to be an integer or a float')
        iSel         = self.cbTabs.GetSelection()
        avgMethod   = AVG_METHODS[self.cbMethod.GetSelection()]
        tabList      = self.parent.selPanel.tabList
        mainframe    = self.parent.mainframe
        if iSel==0:
            dfs, names, errors = tabList.radialAvg(avgMethod,avgParam)
            mainframe.load_dfs(dfs,names,bAdd=True)
            if len(errors)>0:
                raise Exception('Error: The mask failed on some tables:\n\n'+'\n'.join(errors))
        else:
            dfs, names = tabList.get(iSel-1).radialAvg(avgMethod,avgParam)
            mainframe.load_dfs(dfs,names,bAdd=True)

        self.updateTabList()

    def updateTabList(self,event=None):
        tabList = self.parent.selPanel.tabList
        tabListNames = ['All opened tables']+tabList.getDisplayTabNames()
        iSel=np.min([self.cbTabs.GetSelection(),len(tabListNames)])
        self.cbTabs.Clear()
        [self.cbTabs.Append(tn) for tn in tabListNames]
        self.cbTabs.SetSelection(iSel)


# --------------------------------------------------------------------------------}
# --- Curve Fitting
# --------------------------------------------------------------------------------{
MODELS_EXAMPLE =[
    {'label':'User defined model', 'id':'eval:',
         'formula':'{a}*x**2 + {b}', 
         'coeffs':None,
         'consts':None,
         'bounds':None },
    ]
MODELS_EXTRA =[
#     {'label':'Exponential decay', 'id':'eval:',
#         'formula':'{A}*exp(-{k}*x)+{B}',
#         'coeffs' :'k=1, A=1, B=0',
#         'consts' :None,
#         'bounds' :None},
]

class CurveFitToolPanel(GUIToolPanel):
    def __init__(self, parent):
        super(CurveFitToolPanel,self).__init__(parent)

        # Data
        self.x     = None
        self.y_fit = None

        # GUI Objecst
        btClose    = self.getBtBitmap(self, 'Close','close', self.destroy)
        btClear    = self.getBtBitmap(self, 'Clear','sun', self.onClear) # DELETE
        btAdd      = self.getBtBitmap(self, 'Add','add'  , self.onAdd)
        btCompFit  = self.getBtBitmap(self, 'Fit','check', self.onCurveFit)
        btHelp     = self.getBtBitmap(self, 'Help','help', self.onHelp)

        boldFont = self.GetFont().Bold()
        lbOutputs = wx.StaticText(self, -1, 'Outputs')
        lbInputs  = wx.StaticText(self, -1, 'Inputs ')
        lbOutputs.SetFont(boldFont)
        lbInputs.SetFont(boldFont)

        self.textFormula   = wx.TextCtrl(self, wx.ID_ANY, '')
        self.textGuess     = wx.TextCtrl(self, wx.ID_ANY, '')
        self.textBounds    = wx.TextCtrl(self, wx.ID_ANY, '')
        self.textConstants = wx.TextCtrl(self, wx.ID_ANY, '')

        self.textFormulaNum = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_READONLY)
        self.textCoeffs     = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_READONLY)
        self.textInfo       = wx.TextCtrl(self, wx.ID_ANY, '', style=wx.TE_READONLY)


        self.Models=copy.deepcopy(MODELS_EXAMPLE) + copy.deepcopy(FITTERS) + copy.deepcopy(MODELS) + copy.deepcopy(MODELS_EXTRA)
        sModels=[d['label'] for d in self.Models]


        self.cbModels = wx.ComboBox(self, choices=sModels, style=wx.CB_READONLY)
        self.cbModels.SetSelection(0)

        btSizer  = wx.FlexGridSizer(rows=3, cols=2, hgap=2, vgap=0)
        btSizer.Add(btClose   ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btClear   ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btAdd     ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btCompFit ,0,flag = wx.ALL|wx.EXPAND, border = 1)
        btSizer.Add(btHelp    ,0,flag = wx.ALL|wx.EXPAND, border = 1)

        inputSizer  = wx.FlexGridSizer(rows=5, cols=2, hgap=0, vgap=0)
        inputSizer.Add(lbInputs                             ,0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        inputSizer.Add(self.cbModels                        ,1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        inputSizer.Add(wx.StaticText(self, -1, 'Formula:')  ,0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        inputSizer.Add(self.textFormula                     ,1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        inputSizer.Add(wx.StaticText(self, -1, 'Guess:')    ,0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        inputSizer.Add(self.textGuess                       ,1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        inputSizer.Add(wx.StaticText(self, -1, 'Bounds:')   ,0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        inputSizer.Add(self.textBounds                      ,1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        inputSizer.Add(wx.StaticText(self, -1, 'Constants:'),0, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        inputSizer.Add(self.textConstants                   ,1, flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        inputSizer.AddGrowableCol(1,1)

        outputSizer  = wx.FlexGridSizer(rows=5, cols=2, hgap=0, vgap=0)
        outputSizer.Add(lbOutputs                                 ,0 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        outputSizer.Add(wx.StaticText(self, -1, '')              ,0 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        outputSizer.Add(wx.StaticText(self, -1, 'Formula:'),0 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        outputSizer.Add(self.textFormulaNum                      ,1 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        outputSizer.Add(wx.StaticText(self, -1, 'Parameters:')   ,0 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        outputSizer.Add(self.textCoeffs                          ,1 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        outputSizer.Add(wx.StaticText(self, -1, 'Accuracy:')     ,0 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM,border = 1)
        outputSizer.Add(self.textInfo                            ,1 , flag=wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM|wx.EXPAND,border = 1)
        outputSizer.AddGrowableCol(1,0.5)

        horzSizer = wx.BoxSizer(wx.HORIZONTAL)
        horzSizer.Add(inputSizer    ,1.0, flag = wx.LEFT|wx.EXPAND,border = 2)
        horzSizer.Add(outputSizer   ,1.0, flag = wx.LEFT|wx.EXPAND,border = 9)

        vertSizer = wx.BoxSizer(wx.VERTICAL)
#         vertSizer.Add(self.lbHelp  ,0, flag = wx.LEFT          ,border = 1)
        vertSizer.Add(horzSizer    ,1, flag = wx.LEFT|wx.EXPAND,border = 1)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(btSizer      ,0, flag = wx.LEFT          ,border = 1)
#         self.sizer.Add(vertSizerCB  ,0, flag = wx.LEFT          ,border = 1)
        self.sizer.Add(vertSizer    ,1, flag = wx.EXPAND|wx.LEFT          ,border = 1)
        self.SetSizer(self.sizer)

        self.Bind(wx.EVT_COMBOBOX, self.onModelChange, self.cbModels)

        self.onModelChange()

    def onModelChange(self,event=None):
        iModel = self.cbModels.GetSelection()
        d = self.Models[iModel]
        self.textFormula.SetEditable(True)

        if d['id'].find('fitter:')==0 :
            self.textGuess.Enable(False)
            self.textGuess.SetValue('')
            self.textFormula.Enable(False)
            self.textFormula.SetValue(d['formula'])
            self.textBounds.Enable(False)
            self.textBounds.SetValue('')
            self.textConstants.Enable(True)
            # NOTE: conversion to string works with list, and tuples, not numpy array
            val = ', '.join([k+'='+str(v) for k,v in d['consts'].items()])
            self.textConstants.SetValue(val)
        else:
            # Formula
            if d['id'].find('eval:')==0 :
                self.textFormula.Enable(True)
                self.textFormula.SetEditable(True)
            else:
                #self.textFormula.Enable(False)
                self.textFormula.Enable(True)
                self.textFormula.SetEditable(False)
            self.textFormula.SetValue(d['formula'])

            # Guess
            if d['coeffs'] is None:
                self.textGuess.SetValue('')
            else:
                self.textGuess.SetValue(d['coeffs'])

            # Constants
            if d['consts'] is None or len(d['consts'].strip())==0:
                self.textConstants.Enable(False)
                self.textConstants.SetValue('')
            else:
                self.textConstants.Enable(True)
                self.textConstants.SetValue(d['consts'])

            # Bounds
            self.textBounds.Enable(True)
            if d['bounds'] is None or len(d['bounds'].strip())==0:
                self.textBounds.SetValue('all=(-np.inf, np.inf)')
            else:
                self.textBounds.SetValue(d['bounds'])

        # Outputs
        self.textFormulaNum.SetValue('(Click on Fit)')
        self.textCoeffs.SetValue('')
        self.textInfo.SetValue('')

    def onCurveFit(self,event=None):
        self.x     = None
        self.y_fit = None
        if len(self.parent.plotData)!=1:
            Error(self,'Curve fitting tool only works with a single curve. Plot less data.')
            return
        PD =self.parent.plotData[0]

        iModel = self.cbModels.GetSelection()
        d = self.Models[iModel]
        
        if d['id'].find('fitter:')==0 :
            sFunc=d['id']
            p0=None
            bounds=None
            fun_kwargs=extract_key_miscnum(self.textConstants.GetLineText(0).replace('np.inf','inf'))
        else:
            # Formula
            sFunc=d['id']
            if sFunc=='eval:':
                sFunc+=self.textFormula.GetLineText(0)
            # Bounds
            bounds=self.textBounds.GetLineText(0).replace('np.inf','inf')
            # Guess
            p0=self.textGuess.GetLineText(0).replace('np.inf','inf')
            fun_kwargs=extract_key_num(self.textConstants.GetLineText(0).replace('np.inf','inf'))
        #print('>>> Model fit sFunc :',sFunc     )
        #print('>>> Model fit p0    :',p0        )
        #print('>>> Model fit bounds:',bounds    )
        #print('>>> Model fit kwargs:',fun_kwargs)
        # Performing fit
        y_fit, pfit, fitter = model_fit(sFunc, PD.x, PD.y, p0=p0, bounds=bounds,**fun_kwargs)
            
        formatter = lambda x: pretty_num_short(x, digits=3)
        formula_num = fitter.formula_num(fmt=formatter)
        # Update info
        self.textFormulaNum.SetValue(formula_num)
        self.textCoeffs.SetValue(', '.join(['{}={:s}'.format(k,formatter(v)) for k,v in fitter.model['coeffs'].items()]))
        self.textInfo.SetValue('R2 = {:.3f} '.format(fitter.model['R2']))

        # Saving 
        d['formula'] = self.textFormula.GetLineText(0)
        d['bounds']  = self.textBounds.GetLineText(0).replace('np.inf','inf')
        d['coeffs']  = self.textGuess.GetLineText(0).replace('np.inf','inf')
        if d['id'].find('fitter:')==0 :
            d['consts'], _ = set_common_keys(d['consts'],fun_kwargs)
        else:
            d['consts']= self.textConstants.GetLineText(0).replace('np.inf','inf')


        # Plot
        ax=self.parent.fig.axes[0]
        ax.plot(PD.x,y_fit,'o', ms=4)
        self.parent.canvas.draw()

        self.x=PD.x
        self.y_fit=y_fit
        self.sx=PD.sx
        self.sy=PD.sy

    def onClear(self,event=None):
        self.parent.redraw() # DATA HAS CHANGED
        self.onModelChange()

    def onAdd(self,event=None):
        name='model_fit'
        if self.x is not None and self.y_fit is not None:
            df=pd.DataFrame({self.sx:self.x, self.sy:self.y_fit})
            self.parent.mainframe.load_df(df,name,bAdd=True)

    def onHelp(self,event=None):
        Info(self,"""Curve fitting is still in beta.

To perform a curve fit, adjusts the "Inputs section on the left":
- Select a predefined equation to fit, using the scrolldown menu.
- Adjust the initial gues for the parameters (if wanted)
- (Only for few models: set constants values)
- Click on "Fit"

If you select a user-defined model:
- Equation parameters are specified using curly brackets
- Numpy functions are available using "np"

Buttons:
- Clear: remove the fit from the plot
- Add: add the fit data to the list of tables (can then be exported)
                
""")
