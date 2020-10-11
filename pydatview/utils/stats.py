""" 
Set of tools for statistics 
  - measures
  - pdf distributions

"""
import numpy as np

def rsquare(y,f, c = True): 
    """ Compute coefficient of determination of data fit model and RMSE
    [r2 rmse] = rsquare(y,f)
    [r2 rmse] = rsquare(y,f,c)
    RSQUARE computes the coefficient of determination (R-square) value from
    actual data Y and model data F. The code uses a general version of
    R-square, based on comparing the variability of the estimation errors
    with the variability of the original values. RSQUARE also outputs the
    root mean squared error (RMSE) for the user's convenience.
    Note: RSQUARE ignores comparisons involving NaN values.
    INPUTS
      Y       : Actual data
      F       : Model fit
    
    # OPTION
      C       : Constant term in model
                R-square may be a questionable measure of fit when no
              constant term is included in the model.
      [DEFAULT] TRUE : Use traditional R-square computation
               FALSE : Uses alternate R-square computation for model
                     without constant term [R2 = 1 - NORM(Y-F)/NORM(Y)]
    # OUTPUT
      R2      : Coefficient of determination
      RMSE    : Root mean squared error """
    # Compare inputs
    if not np.all(y.shape == f.shape) :
        raise Exception('Y and F must be the same size')
    # Check for NaN
    tmp = np.logical_not(np.logical_or(np.isnan(y),np.isnan(f))) 
    y = y[tmp]
    f = f[tmp]
    if c:
        r2 = max(0,1-np.sum((y-f)**2)/np.sum((y-np.mean(y))** 2))
    else:
        r2 = 1 - np.sum((y - f) ** 2) / np.sum((y) ** 2)
        if r2 < 0:
            import warnings
            warnings.warn('Consider adding a constant term to your model')
            r2 = 0
    rmse = np.sqrt(np.mean((y - f) ** 2))
    return r2,rmse




def pdf_histogram(y,nBins=50, norm=True, count=False):
    yh, xh = np.histogram(y[~np.isnan(y)], bins=nBins)
    dx   = xh[1] - xh[0]
    xh  = xh[:-1] + dx/2
    if count:
        yh  = yh / (len(n)*dx) # TODO DEBUG /VERIFY THIS
    else:
        yh  = yh / (nBins*dx) 
    if norm:
        yh=yh/np.trapz(yh,xh)
    return xh,yh

def pdf_gaussian_kde(data, bw='scott', nOut=100, cut=3, clip=(-np.inf,np.inf)):
    """ 
    Returns a smooth probability density function (univariate kernel density estimate - kde) 
    Inspired from `_univariate_kdeplot` from `seaborn.distributions`

    INPUTS:
        bw:  float defining bandwidth or method (string) to find it (more or less sigma)   
        cut: number of bandwidth kept for x axis (e.g. 3 sigmas)
        clip: (xmin, xmax) values
    OUTPUTS:
        x, y: where y(x) = pdf(data)
    """
    from scipy import stats
    from six import string_types

    data = np.asarray(data)
    # Gaussian kde
    kde  = stats.gaussian_kde(data, bw_method = bw)
    # Finding a relevant support (i.e. x values)
    if isinstance(bw, string_types):
        bw_ = "scotts" if bw == "scott" else bw
        bw = getattr(kde, "%s_factor" % bw_)() * np.std(data)
    x_min = max(data.min() - bw * cut, clip[0])
    x_max = min(data.max() + bw * cut, clip[1])
    x = np.linspace(x_min, x_max, nOut)
    # Computing kde on support
    y = kde(x)
    return x, y


def pdf_sklearn(y):
    #from sklearn.neighbors import KernelDensity
    #kde = KernelDensity(kernel='gaussian', bandwidth=0.75).fit(y) #you can supply a bandwidth
    #x=np.linspace(0,5,100)[:, np.newaxis]
    #log_density_values=kde.score_samples(x)
    #density=np.exp(log_density)
    pass

def pdf_sns(y,nBins=50):
    import seaborn.apionly as sns
    hh=sns.distplot(y,hist=True,norm_hist=False).get_lines()[0].get_data()
    xh=hh[0]
    yh=hh[1]
    return xh,yh
