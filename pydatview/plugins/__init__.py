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

def _data_standardizeUnits(mainframe, event=None, label=''):
    from .data_standardizeUnits import standardizeUnitsPlugin
    standardizeUnitsPlugin(mainframe, event, label)

def _data_binning(mainframe, event=None, label=''):
    from .data_binning import BinningToolPanel
    return BinningToolPanel


dataPlugins=[
        # Name/label             , callback              , is a Panel
        ('Bin data'              , _data_binning         , True ),
        ('Standardize Units (SI)', _data_standardizeUnits, False),
        ('Standardize Units (WE)', _data_standardizeUnits, False),
        ]
