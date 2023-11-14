import wx
import numpy as np
import pandas as pd
import copy
from pydatview.plugins.base_plugin import GUIToolPanel
from pydatview.common import Error, Info, pretty_num_short, PyDatViewException
from pydatview.tools.curve_fitting import model_fit, extract_key_miscnum, extract_key_num, MODELS, FITTERS, set_common_keys
_HELP = """Curve fitting

To perform a curve fit, adjusts the "Inputs section on the left":
- Select a predefined equation to fit, using the scrolldown menu.
- Adjust the initial guess for the parameters (if wanted)
- (Only for few models: set constants values)
- Click on "Fit"

If you select a user-defined model:
- Equation parameters are specified using curly brackets
- Numpy functions are available using "np."

Buttons:
- Clear: remove the fit from the plot
- Add: add the fit data to the list of tables (can then be exported)
                
"""
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
        super(CurveFitToolPanel,self).__init__(parent, help_string=_HELP)

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
        outputSizer.AddGrowableCol(1,1)

        horzSizer = wx.BoxSizer(wx.HORIZONTAL)
        horzSizer.Add(inputSizer    ,1, flag = wx.LEFT|wx.EXPAND,border = 2)
        horzSizer.Add(outputSizer   ,1, flag = wx.LEFT|wx.EXPAND,border = 9)

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
        ax =self.parent.fig.axes[0]
        # Restricting data to axes visible bounds on the x axis
        xlim= ax.get_xlim_()
        b=np.logical_and(PD.x>=xlim[0], PD.x<=xlim[1])

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
            fun_kwargs     = extract_key_num(self.textConstants.GetLineText(0).replace('np.inf','inf'))
            fun_kwargs_ref = extract_key_num(d['consts'])
            if set(fun_kwargs_ref.keys()) != set(fun_kwargs.keys()):
                Error(self, 'The Field `Constants` should contain the keys: {}'.format(list(fun_kwargs_ref.keys())))
                return 


        #print('>>> Model fit sFunc :',sFunc     )
        #print('>>> Model fit p0    :',p0        )
        #print('>>> Model fit bounds:',bounds    )
        #print('>>> Model fit kwargs:',fun_kwargs)
        # Performing fit
        y_fit, pfit, fitter = model_fit(sFunc, PD.x[b], PD.y[b], p0=p0, bounds=bounds,**fun_kwargs)
            
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
        ax.plot(PD.x[b], y_fit, 'o', ms=4)
        self.parent.canvas.draw()

        self.x=PD.x[b]
        self.y_fit=y_fit
        self.sx=PD.sx
        self.sy=PD.sy

    def onClear(self,event=None):
        self.parent.load_and_draw() # DATA HAS CHANGED
        self.onModelChange()

    def onAdd(self,event=None):
        name='model_fit'
        if self.x is not None and self.y_fit is not None:
            df=pd.DataFrame({self.sx:self.x, self.sy:self.y_fit})

