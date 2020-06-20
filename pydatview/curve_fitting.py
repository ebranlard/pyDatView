import numpy as np
import scipy.optimize as so
import scipy.stats as stats
import string
import re
from collections import OrderedDict
from numpy import sqrt, pi, exp, cos, sin, log, inf, arctan # for user convenience

__all__  = ['model_fit']
__all__ += ['ModelFitter','ContinuousPolynomialFitter','DiscretePolynomialFitter']
__all__ += ['fit_polynomial_continuous','fit_polynomial_discrete', 'fit_powerlaw_u_alpha']
__all__ += ['extract_variables']
__all__ += ['MODELS','FITTERS']

# --------------------------------------------------------------------------------}
# --- Predifined functions NOTE: they need to be registered in variable `MODELS`
# --------------------------------------------------------------------------------{
def gaussian(x, p):
    """ p = (mu,sigma) """
    return 1/(p[1]*np.sqrt(2*np.pi)) * np.exp(-1/2*((x-p[0])/p[1])**2)

def gaussian_w_offset(x, p):
    """ p = (mu,sigma,y0) """
    return 1/(p[1]*np.sqrt(2*np.pi)) * np.exp(-1/2*((x-p[0])/p[1])**2) + p[2]

def logarithmic(x, p):
    """ p = (a,b) """
    return p[0]*np.log(x)+p[1]

def powerlaw_all(x, p):
    """ p = (alpha,u_ref,z_ref) """
    return p[1] * (x / p[2]) ** p[0]

def powerlaw_alpha(x, p, u_ref=10, z_ref=100):
    """ p = alpha """
    return u_ref * (x / z_ref) ** p[0]

def powerlaw_u_alpha(x, p, z_ref=100):
    """ p = (alpha, u_ref) """
    return p[1] * (x / z_ref) ** p[0]

def expdecay(x, p, z_ref=100):
    """ p = (A, k, B) formula: {A}*exp(-{k}*x)+{B} """,
    return p[0]* np.exp(-p[1]*x) + p[2]

def weibull_pdf(x, p, z_ref=100):
    """ p = (A, k) formula: {k}*x**({k}-1) / {A}**{k} * np.exp(-x/{A})**{k} """,
    return  p[1] * x ** (p[1] - 1) / p[0] ** p[1] * np.exp(-(x / p[0]) ** p[1])

def gentorque(x, p):
    """ 
     x: generator or rotor speed
     p= (RtGnSp, RtTq  , Rgn2K , SlPc , SpdGenOn)
     RtGnSp  Rated generator speed for simple variable-speed generator control (HSS side) (rpm) 
     RtTq    Rated generator torque/constant generator torque in Region 3 for simple variable-speed generator control (HSS side) (N-m) 
     Rgn2K   Generator torque constant in Region 2 for simple variable-speed generator control (HSS side) (N-m/rpm^2) 
     SlPc    Rated generator slip percentage in Region 2 1/2 for simple variable-speed generator control (%) 
     """

    # Init
    RtGnSp, RtTq  , Rgn2K , SlPc, SpdGenOn = p
    GenTrq=np.zeros(x.shape)

    xmin,xmax=np.min(x), np.max(x) 
#     if RtGnSp<(xmin+xmax)*0.4:
#         return GenTrq

    # Setting up different regions
    xR21_Start = RtGnSp*(1-SlPc/100)
    bR0      = x<SpdGenOn
    bR2      = np.logical_and(x>SpdGenOn    , x<xR21_Start)
    bR21     = np.logical_and(x>=xR21_Start , x<=RtGnSp)
    bR3      = x>RtGnSp
    # R21
    y1, y2 = Rgn2K*xR21_Start**2, RtTq
    x1, x2 = xR21_Start            , RtGnSp
    m=(y2-y1)/(x2-x1)
    GenTrq[bR21] =  m*(x[bR21]-x1) + y1  # R21
    GenTrq[bR2] =  Rgn2K * x[bR2]**2  # R2
    GenTrq[bR3] =  RtTq               # R3
    return GenTrq


MODELS =[
#     {'label':'User defined model',
#          'name':'eval:',
#          'formula':'{a}*x**2 + {b}', 
#          'coeffs':None,
#          'consts':None,
#          'bounds':None },
{'label':'Gaussian', 'handle':gaussian,'id':'predef: gaussian',
'formula':'1/({sigma}*sqrt(2*pi)) * exp(-1/2 * ((x-{mu})/{sigma})**2)',
'coeffs' :'mu=0, sigma=1', # Order Important
'consts' :None,
'bounds' :None},
{'label':'Gaussian with y-offset','handle':gaussian_w_offset,'id':'predef: gaussian-yoff',
'formula':'1/({sigma}*sqrt(2*pi)) * exp(-1/2 * ((x-{mu})/{sigma})**2) + {y0}',
'coeffs' :'mu=0, sigma=1, y0=0', #Order Important
'consts' :None,
'bounds' :'sigma=(-inf,inf), mu=(-inf,inf), y0=(-inf,inf)'},
{'label':'Exponential', 'handle': expdecay, 'id':'predef: expdecay',
'formula':'{A}*exp(-{k}*x)+{B}',
'coeffs' :'A=1, k=1, B=0',  # Order Important
'consts' :None,
'bounds' :None},
{'label':'Logarithmic', 'handle': logarithmic, 'id':'predef: logarithmic',
'formula':'{a}*log(x)+{b}',
'coeffs' :'a=1, b=0',  # Order Important
'consts' :None,
'bounds' :None},
# --- Wind Energy
{'label':'Power law (alpha)', 'handle':powerlaw_alpha, 'id':'predef: powerlaw_alpha',
'formula':'{u_ref} * (z / {z_ref}) ** {alpha}',
'coeffs' : 'alpha=0.1',          # Order important
'consts' : 'u_ref=10, z_ref=100',
'bounds' : 'alpha=(-1,1)'},
{'label':'Power law (alpha,u)', 'handle':powerlaw_u_alpha, 'id':'predef: powerlaw_u_alpha',
'formula':'{u_ref} * (z / {z_ref}) ** {alpha}',
'coeffs': 'alpha=0.1, u_ref=10', # Order important
'consts': 'z_ref=100',
'bounds': 'u_ref=(0,inf), alpha=(-1,1)'},
# 'powerlaw_all':{'label':'Power law (alpha,u,z)', 'handle':powerlaw_all, # NOTE: not that useful
#         'formula':'{u_ref} * (z / {z_ref}) ** {alpha}',
#         'coeffs': 'alpha=0.1, u_ref=10, z_ref=100',
#         'consts': None,
#         'bounds': 'u_ref=(0,inf), alpha=(-1,1), z_ref=(0,inf)'},
{'label':'Weibull PDF', 'handle': weibull_pdf, 'id':'predef: weibull_pdf',
'formula':'{k}*x**({k}-1) / {A}**{k} * np.exp(-x/{A})**{k}',
'coeffs' :'A=1, k=1',  # Order Important
'consts' :None,
'bounds' :'A=(0.1,inf), k=(0,5)'},
# {'label':'Generator Torque', 'handle': gentorque, 'id':'predef: gentorque',
# 'formula': '{RtGnSp} , {RtTq}  , {Rgn2K} , {SlPc} , {SpdGenOn}',
# 'coeffs' : 'RtGnSp=100 , RtTq=1000  , Rgn2K=0.01 ,SlPc=5 , SpdGenOn=0',  # Order Important
# 'consts' :None,
# 'bounds' :'RtGnSp=(0.1,inf) , RtTq=(1,inf), Rgn2K=(0.0,0.1) ,SlPc=(0,20) , SpdGenOn=(0,inf)'}
]

# --------------------------------------------------------------------------------}
# --- Main function wrapper
# --------------------------------------------------------------------------------{
def model_fit(func, x, y, p0=None, bounds=None, **fun_kwargs):
    """
    Parameters
    ----------
    func: string or function handle
        - function handle
        - string starting with "fitter: ": (see  variable _FITTER)
            - "fitter: polynomial_continuous 5'    : polyfit order 5
            - "fitter: polynomial_discrete  0 2 3 ': fit polynomial of exponents 0 2 3
        - string providing an expression to evaluate, e.g.: 
            - "eval: {a}*x + {b}*x**2     " 
        - string starting with "predef": (see  variable MODELS)
            - "predef: powerlaw_alpha"  :
            - "predef: powerlaw_all"    :
            - "predef: gaussian "       :

    Returns
    -------
    y_fit:  array with same shape as `x`
        fitted data.
    fitter: ModelFitter object
    """
    if isinstance(func,str) and func.find('fitter:')==0:
        predef_fitters=[m['id'] for m in FITTERS]
        if func not in predef_fitters:
            raise Exception('Function `{}` not defined in curve_fitting module\n Available fitters: {}'.format(func,predef_fitters))
        i = predef_fitters.index(func)
        FitterDict = FITTERS[i]
        consts=FITTERS[i]['consts']
        args, missing = set_common_keys(consts, fun_kwargs)
        if len(missing)>0:
            raise Exception('Curve fitting with `{}` requires the following arguments {}. Missing: {}'.format(func,consts.keys(),missing))

        fitter = FitterDict['handle'](x=x, y=y, p0=p0, bounds=bounds, **fun_kwargs)
    else:
        fitter = ModelFitter(func, x, y, p0=p0, bounds=bounds, **fun_kwargs)

    pfit   = [v for _,v in fitter.model['coeffs'].items()]
    return fitter.data['y_fit'], pfit , fitter


class ModelFitter():
    def __init__(self,func=None, x=None, y=None, p0=None, bounds=None, **fun_kwargs):

        self.model={
            'name':None, 'model_function':None, 'consts':fun_kwargs, 'formula': 'unavailable', # model signature
            'coeffs':None, 'formula_num':'unavailable', 'fitted_function':None,  'coeffs_init':p0, 'bounds':bounds,  # model fitting
            'R2':None,
        }
        self.data={'x':x,'y':y,'y_fit':None}

        if func is None:
            return
        self.set_model(func, **fun_kwargs)

        # Initialize function if present
        # Perform fit if data and function is present
        if x is not None and y is not None:
            self.fit_data(x,y,p0,bounds)

    def set_model(self,func, **fun_kwargs):
        if callable(func):
            # We don't have much additional info
            self.model['model_function'] = func
            self.model['name']           = func.__name__
            pass

        elif isinstance(func,str):
            if func.find('predef:')==0:
                # --- Minimization from a predefined function
                predef_models=[m['id'] for m in MODELS]
                if func not in predef_models:
                    raise Exception('Predefined function `{}` not defined in curve_fitting module\n Available functions: {}'.format(func,predef_models))
                i = predef_models.index(func)
                ModelDict = MODELS[i]
                self.model['model_function'] = ModelDict['handle']
                self.model['name']           = ModelDict['label']
                self.model['formula']        = ModelDict['formula']
                self.model['coeffs']         = extract_key_num(ModelDict['coeffs'])
                self.model['coeffs_init']    = self.model['coeffs'].copy()
                self.model['consts']         = extract_key_num(ModelDict['consts'])
                self.model['bounds']         = extract_key_tuples(ModelDict['bounds'])

            elif func.find('eval:')==0:
                # --- Minimization from a eval string 
                formula=func[5:]
                # Extract coeffs {a} {b} {c}, replace by p[0]
                variables, formula_eval = extract_variables(formula)
                nParams=len(variables)
                if nParams==0:
                    raise Exception('Formula should contains parameters in curly brackets, e.g.: {a}, {b}, {u_1}. No parameters found in {}'.format(formula))

                # Check that the formula evaluates
                x=np.array([1,2,5])*np.sqrt(2) # some random evaluation vector..
                p=[np.sqrt(2)/4]*nParams         # some random initial conditions
                #print('p',p)
                #print('f',formula_eval)
                try:
                    y=eval(formula_eval)
                    y=np.asarray(y)
                    if y.shape!=x.shape:
                        raise Exception('The formula does not return an array of same size as the input variable x. The formula must include `x`: {}'.format(formula_eval))
                except SyntaxError:
                    raise Exception('The formula does not evaluate, syntax error raised: {}'.format(formula_eval))
                except ZeroDivisionError:
                    pass

                # Creating the actual function
                def func(x, p):
                    return eval(formula_eval)

                self.model['model_function'] = func
                self.model['name']           = 'user function'
                self.model['formula']        = formula
                self.model['coeffs']         = OrderedDict([(k,v) for k,v in zip(variables,p)])
                self.model['coeffs_init']    = self.model['coeffs'].copy()
                self.model['consts']         = {}
                self.model['bounds']         = None

            else:
                raise Exception('func string needs to start with `eval:` of `predef:`, func: {}'.format(func))
        else:
            raise Exception('func should be string or callable')

        if fun_kwargs is None:
            return
        if len(fun_kwargs)==0:
            return
        if self.model['consts'] is None:
            raise Exception('Fun_kwargs provided, but no function constants were defined')

        self.model['consts'], missing = set_common_keys(self.model['consts'],  fun_kwargs )
        if len(missing)>0:
            raise Exception('Curve fitting with function `{}` requires the following arguments {}. Missing: {}'.format(func.__name__,consts.keys(),missing))

    def setup_bounds(self,bounds,nParams):
        if bounds is not None:
            self.model['bounds']=bounds # store in model
        bounds=self.model['bounds'] # usemodel bounds as default
        if bounds is not None:
            if isinstance(bounds ,str): 
                bounds=extract_key_tuples(bounds)

            if isinstance(bounds ,dict): 
                if len(bounds)==0 or 'all' in bounds.keys():
                    bounds=([-np.inf]*nParams,[np.inf]*nParams)
                elif self.model['coeffs'] is not None:
                    b1=[]
                    b2=[]
                    for k in self.model['coeffs'].keys():
                        if k in bounds.keys():
                            b1.append(bounds[k][0])
                            b2.append(bounds[k][1])
                        else:
                            raise Exception('Bounds dictionary is missing the key: `{}`'.format(k))
                    bounds=(b1,b2)
                else:
                    raise NotImplementedError('Bounds dictionary with no known model coeffs.')
            else:
                # so.curve_fit needs a 2-tuple 
                b1,b2=bounds[0],bounds[1]
                if not hasattr(b1,'__len__'):
                    b1=[b1]*nParams
                if not hasattr(b2,'__len__'):
                    b2=[b2]*nParams
                bounds=(b1,b2)
        else:
            bounds=([-np.inf]*nParams,[np.inf]*nParams)

        self.model['bounds']=bounds # store in model

    def setup_guess(self,p0,bounds, nParams):
        """ Setup initial values p0:
         - if p0 is a string (e.g. " a=1, b=3"), it's converted to a dict 
         - if p0 is a dict, the ordered keys of model['coeffs'] are used to sort p0
        """
        if isinstance(p0 ,str): 
            p0=extract_key_num(p0)
            if len(p0)==0:
                p0=None

        if p0 is None:
            # There is some tricky logic here between the priority of bounds and coeffs
            if self.model['coeffs'] is not None:
                # We rely on function to give us decent init coefficients
                p0 = ([v for _,v in self.model['coeffs'].items()])
            elif bounds is None:
                p0 = ([0]*nParams)
            else:
                # use middle of bounds
                p0 = [0]*nParams
                for i,(b1,b2) in enumerate(zip(bounds[0],bounds[1])):
                    if (b1,b2)==(-np.inf,np.inf):
                        p0[i]=0
                    elif b1==-np.inf:
                        p0[i] = -abs(b2)*2
                    elif b2== np.inf:
                        p0[i] =  abs(b1)*2
                    else:
                        p0[i] = (b1+b2)/2
                p0 = (p0)
        elif isinstance(p0,dict):
            # User supplied a dictionary, we use the ordered keys of coeffs to sort p0
            p0_dict=p0.copy()
            if self.model['coeffs'] is not None:
                p0=[]
                for k in self.model['coeffs'].keys():
                    if k in p0_dict.keys():
                        p0.append(p0_dict[k])
                    else:
                        raise Exception('Guess dictionary is missing the key: `{}`'.format(k))
            else:
                raise NotImplementedError('Guess dictionary with no known model coeffs.')

        # TODO check that p0 is within bounds

        if not hasattr(p0,'__len__'):
            p0=(p0,)
        self.model['coeffs_init'] = p0

    def fit(self, func, x, y, p0=None, bounds=None, **fun_kwargs):
        """ Fit model defined by a function to data (x,y) """
        # Setup function
        self.set_model(func, **fun_kwargs)
        # Fit data to model
        self.fit_data(x, y, p0, bounds)

    def clean_data(self,x,y):
        x=np.asarray(x)
        y=np.asarray(y)
        bNaN=~np.isnan(y)
        y=y[bNaN]
        x=x[bNaN]
        bNaN=~np.isnan(x)
        y=y[bNaN]
        x=x[bNaN]
        self.data['x']=x
        self.data['y']=y
        return x,y

    def fit_data(self, x, y, p0=None, bounds=None):
        """ fit data, assuming a model is already setup"""
        if self.model['model_function'] is None:
            raise Exceptioin('Call set_function first')

        # Cleaning data, and store it in object
        x,y=self.clean_data(x,y)

        # nParams
        if isinstance(p0 ,str): 
            p0=extract_key_num(p0)
            if len(p0)==0:
                p0=None
        if p0 is not None:
            if hasattr(p0,'__len__'):
                nParams=len(p0)
            else:
                nParams=1
        elif self.model['coeffs'] is not None:
            nParams=len(self.model['coeffs'])
        else:
            raise Exception('Initial guess `p0` needs to be provided since we cant infer the size of the model coefficients.')
        if self.model['coeffs'] is not None:
            if len(self.model['coeffs'])!=nParams:
                raise Exception('Inconsistent dimension between model guess (size {}) and the model parameters (size {})'.format(nParams,len(self.model['coeffs'])))

        # Bounds
        self.setup_bounds(bounds,nParams)

        # Initial conditions
        self.setup_guess(p0,self.model['bounds'],nParams)

        # Fitting
        minimize_me = lambda x, *p : self.model['model_function'](x, p, **self.model['consts'])
        pfit, pcov = so.curve_fit(minimize_me, x, y, p0=self.model['coeffs_init'], bounds=self.model['bounds']) 

        # --- Reporting information about the fit (after the fit)
        y_fit = self.model['model_function'](x, pfit, **self.model['consts'])
        self.store_fit_info(y_fit, pfit)

        # --- Return a fitted function
        self.model['fitted_function'] = lambda xx: self.model['model_function'](xx, pfit, **self.model['consts'])

    def store_fit_info(self, y_fit, pfit):
        # --- Reporting information about the fit (after the fit)
        self.data['y_fit']=y_fit
        self.model['R2'] = rsquare(self.data['y'], y_fit)
        if self.model['coeffs'] is not None:
            if not isinstance(self.model['coeffs'], OrderedDict):
                raise Exception('Coeffs need to be of type OrderedDict')
            for k,v in zip(self.model['coeffs'].keys(), pfit):
                self.model['coeffs'][k]=v

        # Replace numerical values in formula
        if self.model['formula'] is not None:
            formula_num=self.model['formula']
            for k,v in self.model['coeffs'].items():
                formula_num = formula_num.replace('{'+k+'}',str(v))
            for k,v in self.model['consts'].items():
                formula_num = formula_num.replace('{'+k+'}',str(v))
            self.model['formula_num'] = formula_num

    def formula_num(self, fmt=None):
        """ return formula with coeffs and consts evaluted numerically"""
        if fmt is None:
            fmt_fun = lambda x: str(x)
        elif isinstance(fmt,str):
            fmt_fun = lambda x: ('{'+fmt+'}').format(x)
        elif callable(fmt):
            fmt_fun = fmt
        formula_num=self.model['formula']
        for k,v in self.model['coeffs'].items():
            formula_num = formula_num.replace('{'+k+'}',fmt_fun(v))
        for k,v in self.model['consts'].items():
            formula_num = formula_num.replace('{'+k+'}',fmt_fun(v))
        return formula_num

    def __repr__(self):
        s='<{} object> with fields:\n'.format(type(self).__name__)
        s+=' - data, dictionary with keys: \n'
        s+='   - x: [{} ... {}], n: {} \n'.format(self.data['x'][0],self.data['x'][-1],len(self.data['x']))
        s+='   - y: [{} ... {}], n: {} \n'.format(self.data['y'][0],self.data['y'][-1],len(self.data['y']))
        s+=' - model, dictionary with keys: \n'
        for k,v in self.model.items():
            s=s+'   - {:15s}: {}\n'.format(k,v)
        return s


# --------------------------------------------------------------------------------}
# --- Predefined fitter  
# --------------------------------------------------------------------------------{
class ContinuousPolynomialFitter(ModelFitter):
    def __init__(self,order=None, x=None, y=None, p0=None, bounds=None):
        ModelFitter.__init__(self,x=None, y=None, p0=p0, bounds=bounds)
        self.setOrder(int(order))
        if order is not None and x is not None and y is not None:
            self.fit_data(x,y,p0,bounds)

    def setOrder(self, order):
        self.order=order
        if order is not None:
            variables= string.ascii_lowercase[:order+1]
            self.model['coeffs']  = OrderedDict([(var,1) for i,var in enumerate(variables)])
            formula  = ' + '.join(['{}*x**{}'.format('{'+var+'}',order-i) for i,var in enumerate(variables)])
            self.model['formula']  = _clean_formula(formula)

    def fit_data(self, x, y, p0=None, bounds=None):
        if self.order is None:
            raise Exception('Polynomial Fitter not set, call function `setOrder` to set order')
        # Cleaning data
        x,y=self.clean_data(x,y)

        nParams=self.order+1
        # Bounds
        self.setup_bounds(bounds,nParams) # TODO
        # Initial conditions
        self.setup_guess(p0,bounds,nParams) # TODO

        # Fitting
        pfit  = np.polyfit(x,y,self.order)

        # --- Reporting information about the fit (after the fit)
        y_fit = np.polyval(pfit,x)
        self.store_fit_info(y_fit, pfit)

        # --- Return a fitted function
        self.model['fitted_function']=lambda xx : np.polyval(pfit,xx)


class DiscretePolynomialFitter(ModelFitter):
    def __init__(self,exponents=None, x=None, y=None, p0=None, bounds=None):
        ModelFitter.__init__(self,x=None, y=None, p0=p0, bounds=bounds)
        self.setExponents(exponents)
        if exponents is not None and x is not None and y is not None:
            self.fit_data(x,y,p0,bounds)

    def setExponents(self, exponents):
        self.exponents=exponents
        if exponents is not None:
            #exponents=-np.sort(-np.asarray(exponents))
            self.exponents=exponents
            variables= string.ascii_lowercase[:len(exponents)]
            self.model['coeffs']  = OrderedDict([(var,1) for i,var in enumerate(variables)])
            formula  = ' + '.join(['{}*x**{}'.format('{'+var+'}',e) for var,e in zip(variables,exponents)])
            self.model['formula']  = _clean_formula(formula)

    def fit_data(self, x, y, p0=None, bounds=None):
        if self.exponents is None:
            raise Exception('Polynomial Fitter not set, call function `setExponents` to set exponents')
        # Cleaning data, and store it in object
        x,y=self.clean_data(x,y)

        nParams=len(self.exponents)
        # Bounds
        self.setup_bounds(bounds,nParams) # TODO
        # Initial conditions
        self.setup_guess(p0,bounds,nParams) # TODO

        X_poly=np.array([])
        for i,e in enumerate(self.exponents):
            if i==0:
                X_poly = np.array([x**e])
            else:
                X_poly = np.vstack((X_poly,x**e))
        try:
            pfit = np.linalg.lstsq(X_poly.T, y, rcond=None)[0]
        except:
            pfit = np.linalg.lstsq(X_poly.T, y)

        # --- Reporting information about the fit (after the fit)
        y_fit= np.dot(pfit, X_poly)
        self.store_fit_info(y_fit, pfit)

        # --- Return a fitted function
        def fitted_function(xx):
            y=np.zeros(xx.shape)
            for i,(e,c) in enumerate(zip(self.exponents,pfit)):
                y += c*x**e
            return y
        self.model['fitted_function']=fitted_function

class GeneratorTorqueFitter(ModelFitter):
    def __init__(self,x=None, y=None, p0=None, bounds=None):
        ModelFitter.__init__(self,x=None, y=None, p0=p0, bounds=bounds)

#         RtGnSp, RtTq  , Rgn2K , SlPc , SpdGenOn = p
#         {'label':'Generator Torque', 'handle': gentorque, 'id':'predef: gentorque',
#         'formula': '{RtGnSp} , {RtTq}  , {Rgn2K} , {SlPc} , {SpdGenOn}',
        self.model['coeffs']= extract_key_num('RtGnSp=100 , RtTq=1000  , Rgn2K=0.01 ,SlPc=5 , SpdGenOn=0')
#         'consts' :None,
#         'bounds' :'RtGnSp=(0.1,inf) , RtTq=(1,inf), Rgn2K=(0.0,0.1) ,SlPc=(0,20) , SpdGenOn=(0,inf)'}
        if x is not None and y is not None:
            self.fit_data(x,y,p0,bounds)

    def fit_data(self, x, y, p0=None, bounds=None):
        #nParams=5
        ## Bounds
        #self.setup_bounds(bounds,nParams) # TODO
        ## Initial conditions
        #self.setup_guess(p0,bounds,nParams) # TODO

        # Cleaning data, and store it in object
        x,y=self.clean_data(x,y)

        I = np.argsort(x)
        x=x[I]
        y=y[I]

        # Estimating deltas
        xMin, xMax=np.min(x),np.max(x)
        yMin, yMax=np.min(y),np.max(y)
        DeltaX = (xMax-xMin)*0.02
        DeltaY = (yMax-yMin)*0.02

        # Binning data
        x_bin=np.linspace(xMin,xMax,min(200,len(x)))
        x_lin=x_bin[0:-1]+np.diff(x_bin)
        #y_lin=np.interp(x_lin,x,y) # TODO replace by bining
        y_lin = np.histogram(y, x_bin, weights=y)[0]/ np.histogram(y, x_bin)[0]
        y_lin, _, _ = stats.binned_statistic(x, y, statistic='mean', bins=x_bin)
        x_lin, _, _ = stats.binned_statistic(x, x, statistic='mean', bins=x_bin)
        bNaN=~np.isnan(y_lin)
        y_lin=y_lin[bNaN]
        x_lin=x_lin[bNaN]

        # --- Find good guess of parameters based on data
        # SpdGenOn
        iOn = np.where(y>0)[0][0]
        SpdGenOn_0    =  x[iOn]
        SpdGenOn_Bnds = (max(x[iOn]-DeltaX,xMin), min(x[iOn]+DeltaX,xMax))
        # Slpc
        Slpc_0    = 5
        Slpc_Bnds = (0,10)
        # RtTq
        RtTq_0    = yMax
        RtTq_Bnds = (yMax-DeltaY, yMax+DeltaY)
        # RtGnSp
        iCloseRt = np.where(y>yMax*0.50)[0][0]
        RtGnSp_0    = x[iCloseRt]
        RtGnSp_Bnds = ( RtGnSp_0 -DeltaX*2, RtGnSp_0+DeltaX*2)
        # Rgn2K
        #print('>>>',SpdGenOn_0, RtGnSp_0)
        bR2=np.logical_and(x>SpdGenOn_0, x<RtGnSp_0)
        exponents=[2]
        _, pfit, _ = fit_polynomial_discrete(x[bR2], y[bR2], exponents)
        #print(pfit)
        Rgn2K_0   =pfit[0]
        Rgn2K_Bnds=(pfit[0]/2, pfit[0]*2)
#         import matplotlib.pyplot as plt
#         fig,ax = plt.subplots(1, 1, sharey=False, figsize=(6.4,4.8)) # (6.4,4.8)
#         fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)
#         ax.plot(x,y ,'-'   , label='')
#         ax.plot(x[bR2],y[bR2],'ko', label='')
#         ax.plot(x_lin,y_lin,'bd', label='')
#         ax.set_xlabel('')
#         ax.set_ylabel('')
#         ax.tick_params(direction='in')
#         plt.show()
        def minimize_me(p):
            RtGnSp, RtTq  , Rgn2K , SlPc , SpdGenOn = p
            y_model=np.array([gentorque(x_lin, (RtGnSp, RtTq  , Rgn2K , SlPc , SpdGenOn))])
            eps = np.mean((y_lin-y_model)**2)
#             print(eps,p)
            return  eps
        bounds = (RtGnSp_Bnds, RtTq_Bnds, Rgn2K_Bnds, Slpc_Bnds, SpdGenOn_Bnds)
        p0     = [RtGnSp_0, RtTq_0, Rgn2K_0, Slpc_0, SpdGenOn_0]
        #print('Bounds',bounds)
        #print('p0',p0)
        res = so.minimize(minimize_me, x0=p0, bounds= bounds, method='SLSQP')
        pfit=res.x

        # --- Reporting information about the fit (after the fit)
        y_fit= gentorque(x, pfit)
        self.store_fit_info(y_fit, pfit)
        # --- Return a fitted function
        self.model['fitted_function']=lambda x: gentorque(x,pfit)



FITTERS= [
{'label':'Polynomial (full)'   ,'id':'fitter: polynomial_continuous', 'handle': ContinuousPolynomialFitter,
'consts':{'order':3}, 'formula': '{a_i} x^i'},
{'label':'Polynomial (partial)','id':'fitter: polynomial_discrete'  , 'handle': DiscretePolynomialFitter  ,
'consts':{'exponents':[0,2,3]},'formula': '{a_i} x^j'},
# {'label':'Generator Torque','id':'fitter: gentorque'  , 'handle': GeneratorTorqueFitter  ,
# 'consts':{},'formula': ''}
]

# --------------------------------------------------------------------------------}
# --- Helper functions  
# --------------------------------------------------------------------------------{
def extract_variables(sFormula):
    """ Extract variables in expression, e.g.  {a}*x + {b} -> ['a','b']
    The variables are replaced with p[0],..,p[n] in order of appearance
    """
    regex = r"\{(.*?)\}"
    matches = re.finditer(regex, sFormula, re.DOTALL)
    formula_eval=sFormula
    variables=[]
    ivar=0
    for i, match in enumerate(matches):
        for groupNum in range(0, len(match.groups())):
            var = match.group(1)
            if var not in variables: 
                variables.append(var)
                formula_eval = formula_eval.replace('{'+match.group(1)+'}','p[{:d}]'.format(ivar))
                ivar+=1
    return variables, formula_eval


def extract_key_tuples(text):
    """
    all=(0.1,-2),b=(inf,0), c=(-inf,0.3e+10)
    """
    if text is None:
        return {}
    regex = re.compile(r'(?P<key>[\w\-]+)=\((?P<value1>[0-9+epinf.-]*?),(?P<value2>[0-9+epinf.-]*?)\)($|,)')
    return  {match.group("key"): (np.float(match.group("value1")),np.float(match.group("value2"))) for match in regex.finditer(text.replace(' ',''))}

def extract_key_num(text):
    """
    all=0.1, b=inf, c=-0.3e+10
    """
    if text is None:
        return {}
    regex = re.compile(r'(?P<key>[\w\-]+)=(?P<value>[0-9+epinf.-]*?)($|,)')
    return OrderedDict([(match.group("key"), np.float(match.group("value"))) for match in regex.finditer(text.replace(' ',''))])

def extract_key_miscnum(text):
    """
    all=0.1, b=(inf,0), c=[-inf,0.3e+10,10,11])
    """
    def isint(s):
        try:
            int(s)
            return True
        except:
            return False

    if text is None:
        return {}
    sp=re.compile('([\w]+)=').split(text.replace(' ',''))
    if len(sp)<3:
        return {}
    sp=sp[1:]
    keys   = sp[0::2]
    values = sp[1::2]
    d={}
    for (k,v) in zip(keys,values):
        if v.find('(')>=0:
            v=v.replace('(','').replace(')','')
            v=v.split(',')
            vect=tuple([np.float(val) for val in v if len(val.strip())>0])
        elif v.find('[')>=0:
            v=v.replace('[','').replace(']','')
            v=v.split(',')
            vect=[int(val) if isint(val) else np.float(val) for val in v if len(val.strip())>0] # NOTE returning lists
        else:
            v=v.replace(',','').strip()
            vect=int(v) if isint(v) else np.float(v)
        d[k]=vect
    return d

def set_common_keys(dict_target, dict_source):
    """ Set a dictionary using another one, missing keys in source dictionary are reported"""
    keys_missing=[]
    for k in dict_target.keys():
        if k in dict_source.keys():
            dict_target[k]=dict_source[k]
        else:
            keys_missing.append(k)
    return dict_target, keys_missing

def _clean_formula(s):
    return s.replace('+-','-').replace('**1','').replace('*x**0','')

def rsquare(y, f): 
    """ Compute coefficient of determination of data fit model and RMSE
    [r2] = rsquare(y,f)
    RSQUARE computes the coefficient of determination (R-square) value from
    actual data Y and model data F. 
    INPUTS
      y       : Actual data
      f       : Model fit
    OUTPUT
      R2      : Coefficient of determination
    """
    # Compare inputs
    if not np.all(y.shape == f.shape) :
        raise Exception('Y and F must be the same size')
    # Check for NaN
    tmp = np.logical_not(np.logical_or(np.isnan(y),np.isnan(f))) 
    y = y[tmp]
    f = f[tmp]
    R2 = max(0,1-np.sum((y-f)**2)/np.sum((y-np.mean(y))** 2))
    return R2

# --------------------------------------------------------------------------------}
# --- Low level fitter  
# --------------------------------------------------------------------------------{
def fit_polynomial_continuous(x, y, order):
    """Fit a polynomial with a continuous set of exponents up to a given order

    Parameters
    ----------
    x,y: see `model_fit`
    order: integer
        Maximum order of polynomial, e.g. 2: for a x**0 + b x**1 + c x**2

    Returns
    -------
    see `model_fit`
    """
    pfit  = np.polyfit(x,y,order)
    y_fit = np.polyval(pfit,x)

    # coeffs_dict, e.g. {'a':xxx, 'b':xxx}, formula = 'a*x + b'
    variables    = string.ascii_lowercase[:order+1]
    coeffs_dict  = OrderedDict([(var,coeff) for i,(coeff,var) in enumerate(zip(pfit,variables))])
    formula      = ' + '.join(['{}*x**{}'.format(var,order-i) for i,var in enumerate(variables)])
    formula      = _clean_formula(formula)
    

    return y_fit,pfit,{'coeffs':coeffs_dict,'formula':formula,'fitted_function':lambda xx : np.polyval(pfit,xx)}

def fit_polynomial_discrete(x, y, exponents):
    """Fit a polynomial with a discrete set of exponents

    Parameters
    ----------
    x,y: see `model_fit`
    exponents: array-like
        Exponents to be used. e.g. [0,2,5] for a x**0 + b x**2 + c x**5

    Returns
    -------
    see `model_fit`
    """
    #exponents=-np.sort(-np.asarray(exponents))
    X_poly=np.array([])
    for i,e in enumerate(exponents):
        if i==0:
            X_poly = np.array([x**e])
        else:
            X_poly = np.vstack((X_poly,x**e))
    try:
        pfit = np.linalg.lstsq(X_poly.T, y, rcond=None)[0]
    except:
        pfit = np.linalg.lstsq(X_poly.T, y)
    y_fit= np.dot(pfit, X_poly)

    variables    = string.ascii_lowercase[:len(exponents)]
    coeffs_dict  = OrderedDict([(var,coeff) for i,(coeff,var) in enumerate(zip(pfit,variables))])
    formula      = ' + '.join(['{}*x**{}'.format(var,e) for var,e in zip(variables,exponents)])
    formula      = _clean_formula(formula)

    return y_fit,pfit,{'coeffs':coeffs_dict,'formula':formula}


def fit_powerlaw_u_alpha(x, y, z_ref=100, p0=(10,0.1)):
    """ 
    p[0] : u_ref
    p[1] : alpha
    """
    pfit, _ = so.curve_fit(lambda x, *p : p[0] * (x / z_ref) ** p[1], x, y, p0=p0)
    y_fit = pfit[0] * (x / z_ref) ** pfit[1]
    coeffs_dict=OrderedDict([('u_ref',pfit[0]),('alpha',pfit[1])])
    formula = '{u_ref} * (z / {z_ref}) ** {alpha}'
    fitted_fun = lambda xx: pfit[0] * (xx / z_ref) ** pfit[1]
    return y_fit, pfit, {'coeffs':coeffs_dict,'formula':formula,'fitted_function':fitted_fun}

# --------------------------------------------------------------------------------}
# --- Unittests
# --------------------------------------------------------------------------------{
import unittest

class TestFitting(unittest.TestCase):

    def test_gaussian(self):
        mu,sigma=0.5,1.2
        x=np.linspace(0,1,10)
        y=gaussian(x,(mu,sigma))
        y_fit, pfit, fitter = model_fit('predef: gaussian', x, y)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(mu   ,fitter.model['coeffs']['mu'])
        np.testing.assert_almost_equal(sigma,fitter.model['coeffs']['sigma'])

    def test_gaussian_w_offset(self):
        mu,sigma,y0=0.5,1.2,10
        x=np.linspace(0,1,10)
        y=gaussian_w_offset(x,(mu,sigma,y0))
        y_fit, pfit, fitter = model_fit('predef: gaussian-yoff', x, y)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(mu   ,fitter.model['coeffs']['mu'])
        np.testing.assert_almost_equal(sigma,fitter.model['coeffs']['sigma'])
        np.testing.assert_almost_equal(y0   ,fitter.model['coeffs']['y0'])

    def test_powerlaw_alpha(self):
        u_ref,z_ref,alpha=20,12,0.12
        x = np.linspace(0,1,10)
        y=powerlaw_all(x,(alpha,u_ref,z_ref))

        fun_kwargs = {'u_ref':u_ref,'z_ref':z_ref}
        y_fit, pfit, fitter = model_fit('predef: powerlaw_alpha', x, y, p0=(0.1), **fun_kwargs)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(alpha ,fitter.model['coeffs']['alpha'])

    def test_powerlaw_u_alpha(self):
        u_ref,z_ref,alpha=10,12,0.12
        x = np.linspace(0,1,10)
        y=powerlaw_all(x,(alpha,u_ref,z_ref,alpha))

        fun_kwargs = {'z_ref':z_ref}
        y_fit, pfit, fitter = model_fit('predef: powerlaw_u_alpha', x, y, **fun_kwargs)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(alpha ,fitter.model['coeffs']['alpha'])
        np.testing.assert_almost_equal(u_ref ,fitter.model['coeffs']['u_ref'])

#     def test_powerlaw_all(self):
#         u_ref,z_ref,alpha=10,12,0.12
#         x = np.linspace(0,1,10)
#         y=powerlaw_all(x,(alpha,u_ref,z_ref,alpha))
# 
#         y_fit, pfit, fitter = model_fit('predef: powerlaw_all', x, y)
#         np.testing.assert_array_almost_equal(y,y_fit)
#         np.testing.assert_almost_equal(alpha ,fitter.model['coeffs']['alpha'])
# # NOTE: cannot test for u_ref or z

    def test_expdecay(self):
        A,k,B=0.5,1.2,10
        x=np.linspace(0,1,10)
        y=expdecay(x,(A,k,B))
        y_fit, pfit, fitter = model_fit('predef: expdecay', x, y)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(A,fitter.model['coeffs']['A'])
        np.testing.assert_almost_equal(k,fitter.model['coeffs']['k'])
        np.testing.assert_almost_equal(B,fitter.model['coeffs']['B'])

    def test_weibull(self):
        A, k = 10, 2.3,
        x=np.linspace(0,1,10)
        y=weibull_pdf(x,(A,k))
        y_fit, pfit, fitter = model_fit('predef: weibull_pdf', x, y)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(A,fitter.model['coeffs']['A'],5)
        np.testing.assert_almost_equal(k,fitter.model['coeffs']['k'])

    def test_gentorque(self):
        pass # TODO
#         GBRatio= 27.5647     #; % Gearbox ratio (-)
#         SpdGenOn  = 14*GBRatio#
#         RtGnSp = 1207.61    # % Rated generator speed for simple variable-speed generator control (HSS side) (rpm) 
#         RtTq   = 1790.49    # % Rated generator torque/constant generator torque in Region 3 for simple variable-speed generator control (HSS side) (N-m) 
#         Rgn2K  = 0.0004128  # % Generator torque constant in Region 2 for simple variable-speed generator control (HSS side) (N-m/rpm^2) 
#         SlPc   = 6          # % Rated generator slip percentage in Region 2 1/2 for simple variable-speed generator control (%) 
# #         x=np.linspace(300,1500,100)
#         x=np.linspace(300,1000,100)
#         y=gentorque(x, (RtGnSp, RtTq  , Rgn2K , SlPc , SpdGenOn))
# 
#         bounds='RtGnSp=(1200,1300) , RtTq=(1500,1800), Rgn2K=(0.0,0.01) ,SlPc=(0,20) , SpdGenOn=(10,500)'
#         p0 = [1250, 1700,0.001, 10, 50]
#         y_fit, pfit, fitter = model_fit('fitter: gentorque', x, y)
# 
#         y_fit, pfit, fitter = model_fit('predef: gentorque', x, y, bounds=bounds, p0=p0)
# #         np.testing.assert_array_almost_equal(y,y_fit)
#         print(fitter)
#         import matplotlib.pyplot as plt
# 
#         fig,ax = plt.subplots(1, 1, sharey=False, figsize=(6.4,4.8)) # (6.4,4.8)
#         fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)
#         ax.plot(x, y     ,'o', label='')
#         ax.plot(x, y_fit ,'-', label='')
#         ax.plot(x, fitter.model['fitted_function'](x) ,'.', label='')
#         ax.set_xlabel('')
#         ax.set_ylabel('')
#         ax.legend()
#         ax.tick_params(direction='in')
#         plt.show()

    def test_polycont(self):
        k = 2.0
        x = np.linspace(0,1,10)
        y = k * x**3
        y_fit, pfit, fitter = model_fit('fitter: polynomial_continuous', x, y, order=3)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(k ,fitter.model['coeffs']['a'])
        np.testing.assert_almost_equal(0 ,fitter.model['coeffs']['b'])
        np.testing.assert_almost_equal(0 ,fitter.model['coeffs']['c'])
        np.testing.assert_almost_equal(0 ,fitter.model['coeffs']['d'])

    def test_polydisc(self):
        exponents=[0,3,5]
        a,b,c = 2.0, 3.0, 4.0
        x = np.linspace(0,1,10)
        y = a + b*x**3 + c*x**5
        y_fit, pfit, fitter = model_fit('fitter: polynomial_discrete', x, y, exponents=exponents)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(a ,fitter.model['coeffs']['a'])
        np.testing.assert_almost_equal(b ,fitter.model['coeffs']['b'])
        np.testing.assert_almost_equal(c ,fitter.model['coeffs']['c'])

    def test_evalpoly(self):
        exponents=[0,3,5]
        a,b,c = 2.0, 3.0, 4.0
        x = np.linspace(0,1,10)
        y = a + b*x**3 + c*x**5
        y_fit, pfit, fitter = model_fit('eval: {a} + {b}*x**3 + {c}*x**5', x, y)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(a ,fitter.model['coeffs']['a'])
        np.testing.assert_almost_equal(b ,fitter.model['coeffs']['b'])
        np.testing.assert_almost_equal(c ,fitter.model['coeffs']['c'])

    def test_evalpowerlaw(self):
        u_ref,z_ref,alpha=10,12,0.12
        x = np.linspace(0,1,10)
        y=powerlaw_all(x,(alpha,u_ref,z_ref))
        y_fit, pfit, fitter = model_fit('eval: {u_ref}*(x/{z_ref})**{alpha}', x, y, p0=(8,9,0.1), bounds=(0.001,100))
        np.testing.assert_array_almost_equal(y,y_fit)

    def test_lowlevelpoly(self):
        x=np.linspace(0,1,10)
        y=x**2
        exponents=[0,1,2]
        y_fit, pfit, model = fit_polynomial_discrete(x, y, exponents)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(1 , model['coeffs']['c'])
        np.testing.assert_almost_equal(0 , model['coeffs']['a'])

        y_fit, pfit, model = fit_polynomial_continuous(x, y, 3)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(1 , model['coeffs']['b'])
        np.testing.assert_almost_equal(0 , model['coeffs']['a'])

    def test_lowlevelpowerlaw(self):
        u_ref,z_ref,alpha=10,12,0.12
        x = np.linspace(0,1,10)
        y=powerlaw_all(x,(alpha,u_ref,z_ref))

        y_fit, pfit, model = fit_powerlaw_u_alpha(x, y, z_ref=z_ref, p0=(9,0.1))
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(alpha , model['coeffs']['alpha'])
        np.testing.assert_almost_equal(u_ref , model['coeffs']['u_ref'])

#     def test_debug(self):
#         # --- Try Gaussian
#         x=np.linspace(0,1,10)
#         y=gaussian(x,(0.5,1.2))
#         y_fit, pfit, fitter = model_fit('predef: gaussian', x, y) #, p0=(0,1))
# #         fitter = ModelFitter('eval: {a}*(1.0/{b}+2/0)**{c}', x, y, p0=(8,9,0.1))
# #         fitter = ModelFitter('eval: {a}/x', x, y, p0=(8,9,0.1))
# 
#         # --- Plot 
#         y_fit=fitter.data['y_fit']
#         print(fitter)
# 
#         import matplotlib.pyplot as plt
#         fig,ax = plt.subplots(1, 1, sharey=False, figsize=(6.4,4.8)) # (6.4,4.8)
#         fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)
#         ax.plot(x, y     ,'o', label='')
#         ax.plot(x, y_fit ,'-', label='')
#         ax.plot(x, fitter.model['fitted_function'](x) ,'.', label='')
#         ax.set_xlabel('')
#         ax.set_ylabel('')
#         ax.legend()
#         ax.tick_params(direction='in')
#         plt.show()

    def test_extract_var(self):
        var, _ = extract_variables('{a}*x + {b}')
        self.assertEqual(var,['a','b'])

        var, _ = extract_variables('{BB}*x + {a}*{BB}')
        self.assertEqual(var,['BB','a'])

        var, _ = extract_variables('{a}*x + {{b}}') #< TODO Won't work
        #self.assertEqual(var,['a','b'])

    def test_key_tuples(self):
        self.assertEqual(extract_key_tuples('a=(1,2)'),{'a':(1,2)})

        self.assertEqual(extract_key_tuples('a=(1, 2),b =(inf,0),c= ( -inf , 0.3e+10)'),{'a':(1,2),'b':(inf,0),'c':(-inf,0.3e+10)})

    def test_key_num(self):
        self.assertEqual(extract_key_num('a=2'),OrderedDict({'a':2}))
        self.assertEqual(extract_key_num('all=0.1,b =inf, c= -0.3e+10'),OrderedDict({'all':0.1,'b':inf,'c':-0.3e+10}))

    def test_key_misc(self):
        self.assertEqual(extract_key_miscnum('a=2'),{'a':2})

        #np.testing.assert_almost_equal(d['a'],(2,3))
        d=extract_key_miscnum('a=(2,3)')
        self.assertEqual(d['a'],(2,3))
        d=extract_key_miscnum('a=[2,3]')
        np.testing.assert_almost_equal(d['a'],[2,3])

        d=extract_key_miscnum('a=[2,3],b=3,c=(0,)')
        np.testing.assert_almost_equal(d['a'],[2,3])
        self.assertEqual(d['b'],3)
        self.assertEqual(d['c'],(0,))




if __name__ == '__main__':
#     TestFitting().test_debug()
#     TestFitting().test_gentorque()

#     # Writing example models to file
#     a,b,c = 2.0, 3.0, 4.0
#     u_ref,z_ref,alpha=10,12,0.12
#     mu,sigma=0.5,1.2
#     x = np.linspace(0.1,30,20)
#     A,k,B=0.5,1.2,10
#     y_exp=expdecay(x,(A,k,B))
#     A, k = 10, 2.3,
#     y_weib=weibull_pdf(x,(A,k))
#     y_log=logarithmic(x,(a,b))
#     exponents=[0,3,5]
#     y_poly = a + b*x**3 + c*x**5
#     y_power=powerlaw_all(x,(alpha,u_ref,z_ref))
#     y_gauss=gaussian(x,(mu,sigma))
#     M=np.column_stack((x,y_poly,y_power,y_gauss,y_gauss+10,y_weib,y_exp,y_log))
#     np.savetxt('../TestFit.csv',M,header='x,poly,power,gauss,gauss_off,weib,expdecay,log',delimiter=',')
# 
    unittest.main()
