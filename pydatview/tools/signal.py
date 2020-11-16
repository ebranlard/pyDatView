from __future__ import division
import numpy as np
from numpy.random import rand
import pandas as pd


# --- List of available filters
FILTERS=[
    {'name':'Moving average','param':100,'paramName':'Window Size','paramRange':[0,100000],'increment':1},
    {'name':'Low pass 1st order','param':1.0,'paramName':'Cutoff Freq.','paramRange':[0.0001,100000],'increment':0.1},
    {'name':'High pass 1st order','param':1.0,'paramName':'Cutoff Freq.','paramRange':[0.0001,100000],'increment':0.1},
]

SAMPLERS=[
    {'name':'Replace', 'param':[], 'paramName':'New x'},
    {'name':'Insert',  'param':[], 'paramName':'Insert list'},
    {'name':'Remove',  'param':[], 'paramName':'Remove list'},
    {'name':'Every n', 'param':2  , 'paramName':'n'},
    {'name':'Delta x', 'param':0.1, 'paramName':'dx'},
]



def reject_outliers(y, x=None, m = 2., replaceNaN=True):
    """ Reject outliers:
        If replaceNaN is true: they are replaced by NaN 
        Otherwise they are removed
    """
    if m==0: 
        # No rejection...
        pass
    else:
        dd = np.abs(y - np.nanmedian(y))
        mdev = np.nanmedian(dd)
        if mdev:
            ss = dd/mdev 
            b=ss<m
            if replaceNaN:
                y=y.copy()
                y[~b]=np.nan
            else:
                y=y[b]
                if x is not None:
                    x= x[b]
    if x is None:
        return y
    else:
        return x, y


# --------------------------------------------------------------------------------}
# --- Resampling 
# --------------------------------------------------------------------------------{
def multiInterp(x, xp, fp, extrap='bounded'):
    j   = np.searchsorted(xp, x) - 1
    dd  = np.zeros(len(x))
    bOK = np.logical_and(j>=0, j< len(xp)-1)
    bLower =j<0
    bUpper =j>=len(xp)-1
    jOK = j[bOK]
    #import pdb; pdb.set_trace()
    dd[bOK] = (x[bOK] - xp[jOK]) / (xp[jOK + 1] - xp[jOK])
    jBef=j 
    jAft=j+1
    # 
    # Use first and last values for anything beyond xp
    jAft[bUpper] = len(xp)-1
    jBef[bUpper] = len(xp)-1
    jAft[bLower] = 0
    jBef[bLower] = 0
    if extrap=='bounded':
        pass
        # OK
    elif extrap=='nan':
        dd[~bOK] = np.nan
    else:
        raise NotImplementedError()

    return (1 - dd) * fp[:,jBef] + fp[:,jAft] * dd

def resample_interp(x_old, x_new, y_old=None, df_old=None):
    #x_new=np.sort(x_new)
    if df_old is not None:
        # --- Method 1 (pandas)
        #df_new = df_old.copy()
        #df_new = df_new.set_index(x_old)
        #df_new = df_new.reindex(df_new.index | x_new)
        #df_new = df_new.interpolate().loc[x_new]
        #df_new = df_new.reset_index()
        # --- Method 2 interp storing dx
        data_new=multiInterp(x_new, x_old, df_old.values.T)
        df_new = pd.DataFrame(data=data_new.T, columns=df_old.columns.values)
        return x_new, df_new

    if y_old is not None:
        return x_new, np.interp(x_new, x_old, y_old)


def applySamplerDF(df_old, x_col, sampDict):
    x_old=df_old[x_col].values
    x_new, df_new =applySampler(x_old, y_old=None, sampDict=sampDict, df_old=df_old)
    df_new[x_col]=x_new
    return df_new


def applySampler(x_old, y_old, sampDict, df_old=None):

    param = np.asarray(sampDict['param']).ravel()

    if sampDict['name']=='Replace':
        if len(param)==0:
            raise Exception('Error: At least one value is required to resample the x values with')
        x_new = param
        return resample_interp(x_old, x_new, y_old, df_old)

    elif sampDict['name']=='Insert':
        if len(param)==0:
            raise Exception('Error: provide a list of values to insert')
        x_new = np.sort(np.concatenate((x_old.ravel(),param)))
        return resample_interp(x_old, x_new, y_old, df_old)

    elif sampDict['name']=='Remove':
        I=[]
        if len(param)==0:
            raise Exception('Error: provide a list of values to remove')
        for d in param:
            Ifound= np.where(np.abs(x_old-d)<1e-3)[0]
            if len(Ifound)>0:
                I+=list(Ifound.ravel())
        x_new=np.delete(x_old,I)
        return resample_interp(x_old, x_new, y_old, df_old)

    elif sampDict['name']=='Delta x':
        if len(param)==0:
            raise Exception('Error: provide value for dx')
        dx    = param[0]
        x_new = np.arange(x_old[0], x_old[-1]+dx/2, dx)
        return resample_interp(x_old, x_new, y_old, df_old)

    elif sampDict['name']=='Every n':
        if len(param)==0:
            raise Exception('Error: provide value for n')
        n = int(param[0])
        if n==0:
            raise Exception('Error: |n| should be at least 1')

        x_new=x_old[::n]
        if df_old is not None:
            return x_new, (df_old.copy()).iloc[::n,:]
        if y_old is not None:
            return x_new, y_old[::n]

    else:
        raise NotImplementedError('{}'.format(sampDict))
    pass

# --------------------------------------------------------------------------------}
# --- Filters
# --------------------------------------------------------------------------------{
#     def moving_average(x, w):
#         #t_new    = np.arange(0,Tmax,dt)
#         #nt      = len(t_new)
#         #nw=400
#         #u_new = moving_average(np.floor(np.linspace(0,3,nt+nw-1))*3+3.5, nw)
#         return np.convolve(x, np.ones(w), 'valid') / w
#     def moving_average(x,N,mode='same'):
#        y=np.convolve(x, np.ones((N,))/N, mode=mode)
#        return y
def moving_average(a, n=3) :
    """ 
    perform moving average, return a vector of same length as input

    NOTE: also in kalman.filters
    """
    a   = a.ravel()
    a   = np.concatenate(([a[0]]*(n-1),a)) # repeating first values
    ret = np.cumsum(a, dtype = float)
    ret[n:] = ret[n:] - ret[:-n]
    ret=ret[n - 1:] / n
    return ret

def lowpass1(y, dt, fc=3) :
    """ 
    1st order low pass filter
    """
    tau=1/(2*np.pi*fc)
    alpha=dt/(tau+dt)
    y_filt=np.zeros(y.shape)
    y_filt[0]=y[0]
    for i in np.arange(1,len(y)):
        y_filt[i]=alpha*y[i] + (1-alpha)*y_filt[i-1]
    return y_filt

def highpass1(y, dt, fc=3) :
    """ 
    1st order high pass filter
    """
    tau=1/(2*np.pi*fc)
    alpha=tau/(tau+dt)
    y_filt=np.zeros(y.shape)
    y_filt[0]=0
    for i in np.arange(1,len(y)):
        y_filt[i]=alpha*y_filt[i-1] + alpha*(y[i]-y[i-1])
    m0=np.mean(y)
    m1=np.mean(y_filt)
    y_filt+=m0-m1
    return y_filt


def applyFilter(x, y,filtDict):
    if filtDict['name']=='Moving average':
        return moving_average(y, n=np.round(filtDict['param']).astype(int))
    elif filtDict['name']=='Low pass 1st order':
        dt = x[1]-x[0]
        return lowpass1(y, dt=dt, fc=filtDict['param'])
    elif filtDict['name']=='High pass 1st order':
        dt = x[1]-x[0]
        return highpass1(y, dt=dt, fc=filtDict['param'])
    else:
        raise NotImplementedError('{}'.format(filtDict))

# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
def zero_crossings(y,x=None,direction=None):
    """
      Find zero-crossing points in a discrete vector, using linear interpolation.

      direction: 'up' or 'down', to select only up-crossings or down-crossings

      returns: 
          x values xzc such that y(yzc)==0
          indexes izc, such that the zero is between y[izc] (excluded) and y[izc+1] (included)

      if direction is not provided, also returns:
              sign, equal to 1 for up crossing
    """
    if x is None:
        x=np.arange(len(y))

    if np.any((x[1:] - x[0:-1]) <= 0.0):
        raise Exception('x values need to be in ascending order')

    # Indices before zero-crossing
    iBef = np.where(y[1:]*y[0:-1] < 0.0)[0]
    
    # Find the zero crossing by linear interpolation
    xzc = x[iBef] - y[iBef] * (x[iBef+1] - x[iBef]) / (y[iBef+1] - y[iBef])
    
    # Selecting points that are exactly 0 and where neighbor change sign
    iZero = np.where(y == 0.0)[0]
    iZero = iZero[np.where((iZero > 0) & (iZero < x.size-1))]
    iZero = iZero[np.where(y[iZero-1]*y[iZero+1] < 0.0)]

    # Concatenate 
    xzc  = np.concatenate((xzc, x[iZero]))
    iBef = np.concatenate((iBef, iZero))

    # Sort
    iSort = np.argsort(xzc)
    xzc, iBef = xzc[iSort], iBef[iSort]

    # Return up-crossing, down crossing or both
    sign = np.sign(y[iBef+1]-y[iBef])
    if direction == 'up':
        I= np.where(sign==1)[0]
        return xzc[I],iBef[I]
    elif direction == 'down':
        I= np.where(sign==-1)[0]
        return xzc[I],iBef[I]
    elif direction is not None:
        raise Exception('Direction should be either `up` or `down`')
    return xzc, iBef, sign


# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
def correlation(x, nMax=80, dt=1, method='manual'):
    """ 
    Compute auto correlation of a signal
    """
    nvec   = np.arange(0,nMax)
    sigma2 = np.var(x)
    R    = np.zeros(nMax)
    R[0] =1
    for i,nDelay in enumerate(nvec[1:]):
        R[i+1] = np.mean(  x[0:-nDelay] * x[nDelay:]  ) / sigma2

    tau = nvec*dt
    return R, tau


def correlated_signal(coeff, n=1000):
    """
    Create a correlated random signal of length `n` based on the correlation coefficient `coeff`
          value[t] = coeff * value[t-1]  + (1-coeff) * random
    """
    if coeff<0 or coeff>1: 
        raise Exception('Correlation coefficient should be between 0 and 1')

    x    = np.zeros(n)
    rvec = rand(n)
    x[0] = rvec[0]
    for m in np.arange(1,n):
        x[m] = coeff*x[m-1] + (1-coeff)*rvec[m] 
    x-=np.mean(x)
    return x


if __name__=='__main__':
    import numpy as np
    import matplotlib.pyplot as plt

    # Input
    dt    = 1
    n     = 10000
    coeff = 0.95 # 1:full corr, 00-corr
    nMax  = 180
    # Create a correlated time series
    tvec  = np.arange(0,n)*dt
    ts = correlated_signal(coeff, n)
    # --- Compute correlation coefficient
    R, tau = correlation(x, nMax=nMax)
    fig,axes = plt.subplots(2, 1, sharey=False, figsize=(6.4,4.8)) # (6.4,4.8)
    fig.subplots_adjust(left=0.12, right=0.95, top=0.95, bottom=0.11, hspace=0.20, wspace=0.20)
    ax=axes[0]
    # Plot time series
    ax.plot(tvec,ts)
    ax.set_xlabel('t [s]')
    ax.set_ylabel('u [m/s]')
    ax.tick_params(direction='in')
    # Plot correlation
    ax=axes[1]
    ax.plot(tau,  R              ,'b-o', label='computed')
    ax.plot(tau, coeff**(tau/dt) , 'r--' ,label='coeff^{tau/dt}') # analytical coeff^n trend
    ax.set_xlabel(r'$\tau$ [s]')
    ax.set_ylabel(r'$R(\tau)$ [-]')
    ax.legend()
    plt.show()






