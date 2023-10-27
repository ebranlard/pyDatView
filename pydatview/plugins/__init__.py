""" 
Register your plugins in this file:
    1) add a function that calls your plugin. The signature needs to be:
            def _function_name(mainframe, event=None, label='')
       The corpus of this function should import your package
       and call the main function of your package. Your are free
       to use the signature your want for your package

    2) add a tuple to the variable DATA_PLUGINS of the form 
         (string, _function_name)

       where string will be displayed under the data menu of pyDatView.

See working examples in this file and this directory.

NOTE:
 - DATA_PLUGINS_WITH_EDITOR: plugins constructors should return an Action with a GUI Editor class

 - DATA_PLUGINS_SIMPLE: simple data plugins constructors should return an Action

 - TOOLS: tool plugins constructor should return a Panel class


"""
from collections import OrderedDict


def _data_mask(label, mainframe):
    from .data_mask import maskAction
    return maskAction(label, mainframe)

# --- plotDataActions
def _data_filter(label, mainframe):
    from .plotdata_filter import filterAction
    return filterAction(label, mainframe)

def _data_sampler(label, mainframe):
    from .plotdata_sampler import samplerAction
    return samplerAction(label, mainframe)

def _data_binning(label, mainframe):
    from .plotdata_binning import binningAction
    return binningAction(label, mainframe)

def _data_removeOutliers(label, mainframe):
    from .plotdata_removeOutliers import removeOutliersAction
    return removeOutliersAction(label, mainframe)

# --- Irreversible actions
def _data_standardizeUnitsSI(label, mainframe=None):
    from .data_standardizeUnits import standardizeUnitsAction
    return standardizeUnitsAction(label, mainframe, flavor='SI')

def _data_standardizeUnitsWE(label, mainframe=None):
    from .data_standardizeUnits import standardizeUnitsAction
    return standardizeUnitsAction(label, mainframe, flavor='WE')

# --- Reversible actions
def _data_renameFldAero(label, mainframe=None):
    from .data_renameFldAero import renameFldAeroAction
    return renameFldAeroAction(label, mainframe)

def _data_renameOF23(label, mainframe=None):
    from .data_renameOF23 import renameOFChannelsAction
    return renameOFChannelsAction(label, mainframe)

# --- Adding actions
def _data_radialConcat(label, mainframe=None):
    from .data_radialConcat import radialConcatAction
    return radialConcatAction(label, mainframe)

def _data_radialavg(label, mainframe=None):
    from .data_radialavg import radialAvgAction
    return radialAvgAction(label, mainframe)


# --- Tools
def _tool_logdec(*args, **kwargs):
    from .tool_logdec import LogDecToolPanel
    return LogDecToolPanel(*args, **kwargs)

def _tool_curvefitting(*args, **kwargs):
    from .tool_curvefitting import CurveFitToolPanel
    return CurveFitToolPanel(*args, **kwargs)


# --- Ordered dictionaries with key="Tool Name", value="Constructor"

# DATA_PLUGINS constructors should return an Action with a GUI Editor class
DATA_PLUGINS_WITH_EDITOR=OrderedDict([
    ('Mask'                  , _data_mask              ),
    ('Remove Outliers'       , _data_removeOutliers    ),
    ('Filter'                , _data_filter            ),
    ('Resample'              , _data_sampler           ),
    ('Bin data'              , _data_binning           ),
    ])

# DATA_PLUGINS_SIMPLE: simple data plugins constructors should return an Action
DATA_PLUGINS_SIMPLE=OrderedDict([
    ('Standardize Units (SI)', _data_standardizeUnitsSI),
    ('Standardize Units (WE)', _data_standardizeUnitsWE),
    ])

# TOOLS: tool plugins constructor should return a Panel class
TOOLS=OrderedDict([
    ('Estimate Freq. and Damping', _tool_logdec),
    ('Curve fitting'             , _tool_curvefitting),
    ])


# --- OpenFAST
# TOOLS: tool plugins constructor should return a Panel class
# OF_DATA_TOOLS={}
OF_DATA_PLUGINS_WITH_EDITOR=OrderedDict([ # TODO
    ('Nodal Average', _data_radialavg),
    ])
# DATA_PLUGINS_SIMPLE: simple data plugins constructors should return an Action
OF_DATA_PLUGINS_SIMPLE=OrderedDict([
    ('Nodal Time Concatenation'  , _data_radialConcat),
    ('v3.4 - Rename "Fld" > "Aero'        , _data_renameFldAero),
    ('v2.3 - Rename "B*N* " > "AB*N* '    , _data_renameOF23),
    ])
