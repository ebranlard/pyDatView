import pandas as pd
import numpy as np
from pydatview.common import splitunit
from pydatview.pipeline import IrreversibleTableAction

# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def standardizeUnitsAction(label='stdUnits', mainframe=None, flavor='SI'):
    """ 
    Return an "action" for the current plugin, to be used in the pipeline.
    """
    data = {'flavor':flavor}

    guiCallback=None
    if mainframe is not None:
        # TODO TODO TODO Clean this up
        def guiCallback():
            if hasattr(mainframe,'selPanel'):
                mainframe.selPanel.colPanel1.setColumns()
                mainframe.selPanel.colPanel2.setColumns()
                mainframe.selPanel.colPanel3.setColumns()
                mainframe.onTabSelectionChange()             # trigger replot
            if hasattr(mainframe,'pipePanel'):
                pass
    # Function that will be applied to all tables

    action = IrreversibleTableAction(
            name=label, 
            tableFunctionApply=changeUnitsTab, 
            guiCallback=guiCallback,
            mainframe=mainframe, # shouldnt be needed
            data = data ,
            imports  = _imports,
            data_var = _data_var,
            code     = _code
            )

    return action

# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
_imports=['from pydatview.tools.pandalib import changeUnits']
_data_var='changeUnitsData'
_code="""changeUnits(df, flavor=changeUnitsData['flavor'])"""

def changeUnitsTab(tab, data):
    from pydatview.tools.pandalib import changeUnits
    changeUnits(tab.data, flavor=data['flavor'])


if __name__ == '__main__':
    pass
    #unittest.main()
