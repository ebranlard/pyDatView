import numpy as np

def reject_outliers(y, x=None, m = 2.):
    """ Reject outliers """
    if m==0: 
        # No rejection...
        if x is None:
            return y
        else:
            return x, y

    dd = np.abs(y - np.nanmedian(y))
    mdev = np.nanmedian(dd)
    if mdev:
        ss = dd/mdev 
        b=ss<m
        if x is None:
            return y[b]
        else:
            return x[b], y[b]
    else:
        if x is None:
            return y
        else:
            return x, y
