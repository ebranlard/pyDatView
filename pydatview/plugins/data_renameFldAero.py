import unittest
import numpy as np
from pydatview.pipeline import ReversibleTableAction

# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def renameFldAeroAction(label, mainframe=None):
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

    action = ReversibleTableAction(
            name=label, 
            tableFunctionApply = renameFldAero,
            tableFunctionCancel= renameAeroFld,
            guiCallback=guiCallback,
            mainframe=mainframe, # shouldnt be needed
            data = data,
            imports  = _imports,
            data_var = _data_var,
            code     = _code
            )

    return action

# --------------------------------------------------------------------------------}
# --- Main methods
# --------------------------------------------------------------------------------{
_imports=[]
_data_var=''
_code="""# TODO rename channels not implemented"""

def renameFldAero(tab, data=None):
    tab.renameColumns(strReplDict={'Aero':'Fld'}) # New:Old

def renameAeroFld(tab, data=None):
    tab.renameColumns( strReplDict={'Fld':'Aero'}) # New:Old


class TestRenameFldAero(unittest.TestCase):

    def test_change_units(self):
        from pydatview.Tables import Table
        tab = Table.createDummy(n=10, columns=['RtFldCp [-]','B1FldFx [N]', 'angle [rad]'])
        renameFldAero(tab)
        self.assertEqual(tab.columns, ['Index','RtAeroCp [-]', 'B1AeroFx [N]', 'angle [rad]'])


if __name__ == '__main__':
    unittest.main()
