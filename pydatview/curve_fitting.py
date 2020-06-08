import numpy as np
import scipy.optimize as so
import string
import re
from collections import OrderedDict
from numpy import sqrt, pi, exp, cos, sin, log, inf, arctan # for user convenience

__all__  = ['model_fit']
__all__ += ['ModelFitter','ContinuousPolynomialFitter','DiscretePolynomialFitter']
__all__ += ['fit_polynomial_continuous','fit_polynomial_discrete', 'fit_powerlaw_u_alpha']
__all__ += ['extract_variables']


# --------------------------------------------------------------------------------}
# --- Predifined functions  
# --------------------------------------------------------------------------------{
def gaussian(x, *p, return_description=False):
    """ 
    p[0] : mu
    p[1] : sigma
    """
    if return_description:
        if None in p:
            p=[0,1] # good starting guess 
        return OrderedDict([('mu',p[0]),('sigma',p[1])]),{}, '1/({sigma}*sqrt(2*pi)) * exp(-1/2*((x-{mu})/{sigma})**2)'
    else:
        return 1/(p[1]*np.sqrt(2*np.pi)) * np.exp(-1/2*((x-p[0])/p[1])**2)

def powerlaw_all(x, *p, return_description=False):
    """ 
    p[0] : u_ref
    p[1] : z_ref
    p[2] : alpha
    """
    if return_description:
        if None in p:
            p=[0.1,10,100] # good starting guess 
        return OrderedDict([('u_ref',p[0]),('z_ref',p[1]),('alpha',p[2])]),{}, '{u_ref} * (z / {z_ref}) ** {alpha}'
    else:
        return p[0] * (x / p[1]) ** p[2]

def powerlaw_alpha(x, *p, u_ref=10, z_ref=100, return_description=False):
    """ 
    p[0] : alpha
    """
    if return_description:
        if None in p:
            p=[0.1] # good starting guess 
        return OrderedDict([('alpha',p[0])]),{'u_ref':u_ref,'z_ref':z_ref}, '{u_ref} * (z / {z_ref}) ** {alpha}'
    else:
        return u_ref * (x / z_ref) ** p[0]

def powerlaw_u_alpha(x, *p, z_ref=100, return_description=False):
    """ 
    p[0] : u_ref
    p[1] : alpha
    """
    if return_description:
        if None in p:
            p=[10,0.1] # good starting guess 
        return OrderedDict([('u_ref',p[0]),('alpha',p[1])]),{'z_ref':z_ref}, '{u_ref} * (z / {z_ref}) ** {alpha}'
    else:
        return p[0] * (x / z_ref) ** p[1]


_PREDEF={
    'gaussian'        : gaussian,
    'powerlaw_all'    : powerlaw_all,
    'powerlaw_u_alpha': powerlaw_u_alpha,
    'powerlaw_alpha'  : powerlaw_alpha
}

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
        - string starting with "predef": (see  variable _PREDEF)
            - "predef: powerlaw_alpha"  :
            - "predef: powerlaw_all"    :
            - "predef: gaussian "       :

    Returns
    -------
    y_fit:  array with same shape as `x`
        fitted data.
    fitter: ModelFitter object
    """
    if isinstance(func,str):
        if func.find('fitter:')==0:
            sp=func[8:].strip().split()
            if sp[0] not in _FITTER.keys():
                raise Exception('Predefined fitter `{}` not defined in curve_fitting module'.format(sp[0]))
            fitter = _FITTER[sp[0]](x=x, y=y, p0=p0, bounds=bounds)
            fitter.setFromString(' '.join(sp[1:]))
            fitter.fit_data(x,y,p0,bounds)
            pfit   = [v for _,v in fitter.model['coeffs'].items()]
            return fitter.data['y_fit'], pfit, fitter

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
            pass

        elif isinstance(func,str):
            if func.find('predef:')==0:
                # --- Minimization from a predefined function
                sp=func[7:].strip().split()
                if sp[0] not in _PREDEF.keys():
                    raise Exception('Predefined function `{}` not defined in curve_fitting module'.format(sp[0]))
                func = _PREDEF[sp[0]]
            elif func.find('eval:')==0:
                # --- Minimization from a string
                formula=func[5:]
                self.model['formula'] = formula
                # Extract coeffs {a} {b} {c}, replace by p[0]
                variables, formula_eval = extract_variables(formula)
                nParams=len(variables)
                if nParams==0:
                    raise Exception('Formula should contains parameters in curly brackets, e.g.: {a}, {b}, {u_1}. No parameters found in {}'.format(formula))
                self.model['variables']=variables

                # Check that the formula evaluates
                x=np.array([1,2,5])*np.sqrt(2) # some random evaluation vector..
                p=[np.sqrt(2)/4]*nParams         # some random initial conditions
                print('p',p)
                print('f',formula_eval)
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
                def func(x, *p, return_description=False):
                    if return_description:
                        if len(p)==1:
                            p=[0]*nParams
                        return OrderedDict([(k,v) for k,v in zip(variables,p)]), {}, formula
                    else:
                        return eval(formula_eval)
            else:
                raise Exception('func string needs to start with `eval:` of `predef:`, func: {}'.format(func))
        else:
            raise Exception('func should be string or callable')

        self.model['model_function'] = func
        self.model['name']           = func.__name__
        self.modelter=None
        # Trying to extract function info/signature, and arguments (consts)
        self.extract_function_info(**fun_kwargs)


    def extract_function_info(self, **kwargs):
        func = self.model['model_function']
        try:
            coeffs, consts, formula = func(None,None,return_description=True)
        except TypeError:
            print('Warning: function {} does not report the model signature, some return information will be missing.'.format(func.__name__))
            return
        args_missing=[]
        func_args={}
        for k in consts.keys():
            if k in kwargs.keys():
                func_args[k]=kwargs[k]
            else:
                args_missing.append(k)
        if len(args_missing)>0:
            raise Exception('Curve fitting with function `{}` requires the following arguments {}. Missing: {}'.format(func.__name__,consts.keys(),args_missing))
        self.model['coeffs']  = coeffs
        self.model['consts']  = func_args
        self.model['formula'] = formula

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

    def setup_guess(self,p0,bounds,nParams):
        if isinstance(p0 ,str): 
            p0=extract_key_num(p0)
            if len(p0)==0:
                p0=None

        if p0 is None:
            if bounds is None:
                if self.model['coeffs'] is not None:
                    # We rely on function to give us decent init coefficients
                    p0 = ([v for _,v in self.model['coeffs'].items()])

                else:
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

        if not hasattr(p0,'__len__'):
            p0=(p0,)
        self.model['coeffs_init'] = p0


    def fit(self, func, x, y, p0=None, bounds=None, **fun_kwargs):
        """ Fit model defined by a function to data (x,y) """
        # Setup function
        self.set_model(func, **fun_kwargs)
        # Fit data to model
        self.fit_data(x, y, p0, bounds)

    def fit_data(self, x, y, p0=None, bounds=None):
        """ fit data, assuming a model is already setup"""
        if self.model['model_function'] is None:
            raise Exceptioin('Call set_function first')
        if self.modelter is not None:
            self.modelter.fit_data(x,y,p0,bounds)
            return

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
        minimize_me = lambda x, *p : self.model['model_function'](x, *p, **self.model['consts'])
        pfit, pcov = so.curve_fit(minimize_me, x, y, p0=self.model['coeffs_init'], bounds=self.model['bounds']) 

        # --- Reporting information about the fit (after the fit)
        y_fit = self.model['model_function'](x, *pfit, **self.model['consts'])
        self.store_fit_info(y_fit, pfit)

        # --- Return a fitted function
        self.model['fitted_function'] = lambda xx: self.model['model_function'](xx, *pfit, **self.model['consts'])


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
        ModelFitter.__init__(self,x=x, y=y, p0=p0, bounds=bounds)
        self.setOrder(order)
        if order is not None and x is not None and y is not None:
            self.fit_data(x,y,p0,bounds)

    def setOrder(self, order):
        self.order=order
        if order is not None:
            variables= string.ascii_lowercase[:order+1]
            self.model['coeffs']  = OrderedDict([(var,1) for i,var in enumerate(variables)])
            formula  = ' + '.join(['{}*x**{}'.format('{'+var+'}',order-i) for i,var in enumerate(variables)])
            self.model['formula']  = _clean_formula(formula)

    def setFromString(self, s):
        exponents = np.array(s.split()).astype(int)
        self.setOrder(int(s))

    def fit_data(self, x, y, p0=None, bounds=None):
        if self.order is None:
            raise Exception('Polynomial Fitter not set, call function `setOrder` to set order')

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
        ModelFitter.__init__(self,x=x, y=y, p0=p0, bounds=bounds)
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

    def setFromString(self, s):
        self.setExponents(np.array(s.split()).astype(int))

    def fit_data(self, x, y, p0=None, bounds=None):
        if self.exponents is None:
            raise Exception('Polynomial Fitter not set, call function `setExponents` to set exponents')

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

_FITTER={
    'polynomial_continuous': ContinuousPolynomialFitter,
    'polynomial_discrete': DiscretePolynomialFitter
}

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
    regex = re.compile(r'(?P<key>[\w\-]+)=\((?P<value1>[0-9+epinf.-]*?),(?P<value2>[0-9+epinf.-]*?)\)($|,)')
    return  {match.group("key"): (np.float(match.group("value1")),np.float(match.group("value2"))) for match in regex.finditer(text.replace(' ',''))}

def extract_key_num(text):
    """
    all=0.1, b=inf, c=-0.3e+10
    """
    regex = re.compile(r'(?P<key>[\w\-]+)=(?P<value>[0-9+epinf.-]*?)($|,)')
    return {match.group("key"): np.float(match.group("value")) for match in regex.finditer(text.replace(' ',''))}


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
    x,y: see `fit_curve`
    order: integer
        Maximum order of polynomial, e.g. 2: for a x**0 + b x**1 + c x**2

    Returns
    -------
    see `fit_curve`
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
    x,y: see `fit_curve`
    exponents: array-like
        Exponents to be used. e.g. [0,2,5] for a x**0 + b x**2 + c x**5

    Returns
    -------
    see `fit_curve`
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



# --- Using so.minimize
# def minimize_me(p):
#     U_mid_VC, _ = ADFarm2VCFarm(ADFarm, base, gamma_t_Ct = lambda x : U0*gamma_CT_fun(x, *p))
#     eps = relerrinduction(X_mid, U_mid_AD, U_mid_VC,x1=-4.99,x2=-2)
#     eps = np.sum(np.array(rels).ravel())
#     print(eps, np.around(rels,3))
#     return  eps
# bnds = ((0, 0.4), (0, 0.8), (-1,1), (-1,1))
# xopt_eps = [ 0.16926954 , 0.3997195  , -0.48184335 , 0.39648173]
# xopt=xopt_mid
# res = so.minimize(minimize_me, x0=xopt_eps, bounds= bnds, method='SLSQP')

# --------------------------------------------------------------------------------}
# --- Unittests
# --------------------------------------------------------------------------------{
import unittest

class TestFitting(unittest.TestCase):

    def test_gaussian(self):
        mu,sigma=0.5,1.2
        x=np.linspace(0,1,10)
        y=gaussian(x,*(mu,sigma))
        y_fit, pfit, fitter = model_fit('predef: gaussian', x, y)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(mu   ,fitter.model['coeffs']['mu'])
        np.testing.assert_almost_equal(sigma,fitter.model['coeffs']['sigma'])

    def test_polwerlaw_alpha(self):
        u_ref,z_ref,alpha=10,12,0.12
        x = np.linspace(0,1,10)
        y=powerlaw_all(x,*(u_ref,z_ref,alpha))

        fun_kwargs = {'u_ref':u_ref,'z_ref':z_ref}
        y_fit, pfit, fitter = model_fit('predef: powerlaw_alpha', x, y, p0=(0.1), **fun_kwargs)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(alpha ,fitter.model['coeffs']['alpha'])

    def test_polwerlaw_u_alpha(self):
        u_ref,z_ref,alpha=10,12,0.12
        x = np.linspace(0,1,10)
        y=powerlaw_all(x,*(u_ref,z_ref,alpha))

        fun_kwargs = {'z_ref':z_ref}
        y_fit, pfit, fitter = model_fit('predef: powerlaw_u_alpha', x, y, **fun_kwargs)
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(alpha ,fitter.model['coeffs']['alpha'])
        np.testing.assert_almost_equal(u_ref ,fitter.model['coeffs']['u_ref'])

    def test_polycont(self):
        k = 2.0
        x = np.linspace(0,1,10)
        y = k * x**3
        y_fit, pfit, fitter = model_fit('fitter: polynomial_continuous 3', x, y)
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
        y_fit, pfit, fitter = model_fit('fitter: polynomial_discrete 0 3 5', x, y)
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
        y=powerlaw_all(x,*(u_ref,z_ref,alpha))
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
        y=powerlaw_all(x,*(u_ref,z_ref,alpha))

        y_fit, pfit, model = fit_powerlaw_u_alpha(x, y, z_ref=z_ref, p0=(9,0.1))
        np.testing.assert_array_almost_equal(y,y_fit)
        np.testing.assert_almost_equal(alpha , model['coeffs']['alpha'])
        np.testing.assert_almost_equal(u_ref , model['coeffs']['u_ref'])

    def test_debug(self):
        pass
        # --- Try Gaussian
        #     x=np.linspace(0,1,10)
        #     y=gaussian(x,*(0.5,1.2))
        #     y_fit, fitter = model_fit('predef: gaussian', x, y)
        #     fitter = ModelFitter('eval: {a}*(1.0/{b}+2/0)**{c}', x, y, p0=(8,9,0.1))
        #     fitter = ModelFitter('eval: {a}/x', x, y, p0=(8,9,0.1))

            # --- Plot 
        #     y_fit=fitter.data['y_fit']
        #     print(fitter)
        # 
        #     import matplotlib.pyplot as plt
        #     fig,ax = plt.subplots(1, 1, sharey=False, figsize=(6.4,4.8)) # (6.4,4.8)
        #     fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)
        #     ax.plot(x, y     ,'o', label='')
        #     ax.plot(x, y_fit ,'-', label='')
        #     ax.plot(x, fitter.model['fitted_function'](x) ,'.', label='')
        #     ax.set_xlabel('')
        #     ax.set_ylabel('')
        #     ax.legend()
        #     ax.tick_params(direction='in')
        #     plt.show()


if __name__ == '__main__':
    unittest.main()

#     a,b,c = 2.0, 3.0, 4.0
#     u_ref,z_ref,alpha=10,12,0.12
#     mu,sigma=0.5,1.2
#     x = np.linspace(0,1,10)
# 
#     exponents=[0,3,5]
#     y_poly = a + b*x**3 + c*x**5
#     y_power=powerlaw_all(x,*(u_ref,z_ref,alpha))
#     y_gauss=gaussian(x,*(mu,sigma))
# 
#     M=np.column_stack((x,y_poly,y_power,y_gauss))
#     np.savetxt('TestFit.csv',M,header='x,poly,power,gauss',delimiter=',')




