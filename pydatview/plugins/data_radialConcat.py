import unittest
import numpy as np
from pydatview.common import splitunit
from pydatview.pipeline import AdderAction

# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def radialConcatAction(label, mainframe=None):
    """ 
    Return an "action" for the current plugin, to be used in the pipeline.
    """
    guiCallback=None
    data={}
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

    action = AdderAction(
            name=label, 
            tableFunctionAdd = radialConcat,
            #tableFunctionApply = renameFldAero,
            #tableFunctionCancel= renameAeroFld,
            guiCallback=guiCallback,
            mainframe=mainframe, # shouldnt be needed
            data = data ,
            imports  = _imports,
            data_var = _data_var,
            code     = _code
            )

    return action

# --------------------------------------------------------------------------------}
# --- Main methods
# --------------------------------------------------------------------------------{
_imports = ["from pydatview.fast.postpro import spanwiseConcat"]
_data_var=None,
_code = """dfs_new = [spanwiseConcat(df)]
names_new = ['concat']
"""

def radialConcat(tab, data=None):
    from pydatview.fast.postpro import spanwiseConcat 
    df_new = spanwiseConcat(tab.data)
    name_new = tab.name+'_concat'
    return df_new, name_new


if __name__ == '__main__':
    unittest.main()
