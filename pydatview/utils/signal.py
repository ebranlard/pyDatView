import numpy as np

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
