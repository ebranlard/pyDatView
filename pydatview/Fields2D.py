"""
TODO come up with some decent sepcs. Potentially use pandas or xarray

"""

def extract2Dfields(fo):
    if not hasattr(fo, 'fields2D_tmp'):
        fo.fields2D_tmp = None
        print('[INFO] Attempting to extract 2D field for file {}'.format(fo.filename))
        if not hasattr(fo, 'to2DFields'):
            print('[WARN] type {} doesnt have a `to2DFields` method'.format(type(fo)))
        else:
#                 try:
            fields = fo.to2DFields()
            fo.fields2D_tmp = fields
            print('[ OK ] 2D field computed successfully')
#                 except:
#                     print('[FAIL] Attempting to extract 2D field for file {}'.format(fo.filename))
    else:
        print('[INFO] 2D field already computed for file {}'.format(fo.filename))
    return fo.fields2D_tmp 

