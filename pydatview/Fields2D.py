"""
TODO come up with some decent sepcs. Potentially use pandas or xarray

"""
import numpy as np

def extract2Dfields(fo, force=False, **kwargs):
    if not hasattr(fo, 'fields2D_tmp') or force:
        fo.fields2D_tmp = None
        #print('[INFO] Attempting to extract 2D field for file {}'.format(fo.filename))
        if not hasattr(fo, 'to2DFields'):
            print('[WARN] type {} does not have a `to2DFields` method'.format(type(fo)))
        else:
#                 try:
            fields = fo.to2DFields(**kwargs)
            fo.fields2D_tmp = Fields2D(fields)
            fo.fields2D_tmp.keys()
            print('[ OK ] 2D field computed successfully')
#                 except:
#                     print('[FAIL] Attempting to extract 2D field for file {}'.format(fo.filename))
    else:
        print('[INFO] 2D field already computed for file {}'.format(fo.filename))
        if not isinstance(fo.fields2D_tmp, Fields2D):
            raise Exception('ImplementationError')
    
    return fo.fields2D_tmp 


class Fields2D():
    """ 
    Fields2D is a list of xarray, readonly
    """
    def __init__(self, ds=None):
        if ds is None:
            ds = []
        self.ds = ds
        self._keys = None

    def __repr__(self):
        s='<{} object>:\n'.format(type(self).__name__)
        s+='|Main attributes:\n'
        s+='| - ds: {}\n'.format(self.ds)
        s+='| - _keys: {}\n'.format(self._keys)
        return s

    def keys(self):
        if self._keys is not None:
            return self._keys
        keys =[]
        variables = self.ds.variables
        # Filter variables based on dimensions (r, t)
        dims = np.unique(np.array([self.ds[var].dims for var in variables], dtype=object))
        dims2d = [d for d in dims if len(d)==2]
        for D in dims2d:
            for var in variables:
                if self.ds[var].dims==(D[0],D[1]):
                    keys.append(var)
        self._keys = keys
        return keys

    def loc(self, svar):
        try:
            i1, i2 = self.ds[svar].dims
        except:
            raise IndexError('Variable {} not found in field'.format(svar))
        sx = i1
        sy = i2
        if 'unit' in self.ds[i1].attrs.keys():
            sx += ' ['+ self.ds[i1].attrs['unit'] + ']'
        if 'unit' in self.ds[i2].attrs.keys():
            sy += ' ['+ self.ds[i2].attrs['unit'] + ']'
        fieldname = svar
        if 'unit' in self.ds[svar].attrs.keys():
            fieldname += ' ['+ self.ds[svar].attrs['unit'] + ']'
        return {'M': self.ds[svar].values, 'x':self.ds[i1].values, 'y':self.ds[i2].values, 'sx':sx, 'sy':sy, 'fieldname':fieldname}

    def iloc(self, i):
        var = self._keys[i]
        return self.loc(var)

