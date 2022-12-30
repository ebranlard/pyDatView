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
 - data plugins constructors should return an Action with a GUI Editor class

 - simple data plugins constructors should return an Action

 - tool plugins constructor should return a Panel class


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


# --- Tools
def _tool_logdec(*args, **kwargs):
    from .tool_logdec import LogDecToolPanel
    return LogDecToolPanel(*args, **kwargs)

def _tool_curvefitting(*args, **kwargs):
    from .tool_curvefitting import CurveFitToolPanel
    return CurveFitToolPanel(*args, **kwargs)

# --- TODO Action
def _tool_radialavg(*args, **kwargs):
    from .tool_radialavg import RadialToolPanel
    return RadialToolPanel(*args, **kwargs)

# --- Ordered dictionaries with key="Tool Name", value="Constructor"

DATA_PLUGINS_WITH_EDITOR=OrderedDict([
    ('Mask'                  , _data_mask              ),
    ('Remove Outliers'       , _data_removeOutliers    ),
    ('Filter'                , _data_filter            ),
    ('Resample'              , _data_sampler           ),
    ('Bin data'              , _data_binning           ),
    ])

DATA_PLUGINS_SIMPLE=OrderedDict([
    ('Standardize Units (SI)', _data_standardizeUnitsSI),
    ('Standardize Units (WE)', _data_standardizeUnitsWE),
    ])


DATA_TOOLS=OrderedDict([ # TODO
    ('FAST - Radial Average', _tool_radialavg),
    ])

TOOLS=OrderedDict([
    ('Damping from decay',_tool_logdec),
    ('Curve fitting',     _tool_curvefitting),
    ])
