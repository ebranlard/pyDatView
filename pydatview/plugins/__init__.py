""" 
Register your plugins in this file:
    1) add a function that calls your plugin. The signature needs to be:
            def _function_name(mainframe, event=None, label='')
       The corpus of this function should import your package
       and call the main function of your package. Your are free
       to use the signature your want for your package

    2) add a tuple to the variable dataPlugins of the form 
         (string, _function_name)

       where string will be displayed under the data menu of pyDatView.

See working examples in this file and this directory.
"""

def _data_standardizeUnitsSI(label, mainframe=None):
    from .data_standardizeUnits import standardizeUnitsAction
    return standardizeUnitsAction(label, mainframe, flavor='SI')

def _data_standardizeUnitsWE(label, mainframe=None):
    from .data_standardizeUnits import standardizeUnitsAction
    return standardizeUnitsAction(label, mainframe, flavor='WE')

def _data_binning(label, mainframe):
    from .data_binning import binningAction
    return binningAction(label, mainframe)

def _data_sampler(label, mainframe):
    from .data_sampler import samplerAction
    return samplerAction(label, mainframe)

dataPlugins=[
        # Name/label             , callback                , is a Panel
        ('Resample'              , _data_sampler           , True ),
        ('Bin data'              , _data_binning           , True ),
        ('Standardize Units (SI)', _data_standardizeUnitsSI, False),
        ('Standardize Units (WE)', _data_standardizeUnitsWE, False),
        ]





# ---
def getDataPluginsDict():
    d={}
    for toolName, function, isPanel in dataPlugins:
        d[toolName]={'callback':function, 'isPanel':isPanel}
    return d
