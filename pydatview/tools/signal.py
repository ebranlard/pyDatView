from __future__ import division
import numpy as np
from numpy.random import rand

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






