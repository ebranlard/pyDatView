import unittest
import numpy as np
from pydatview.common import splitunit
from pydatview.pipeline import ReversibleTableAction

# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def renameOFChannelsAction(label, mainframe=None):
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
            tableFunctionApply = renameToNew,
            tableFunctionCancel= renameToOld,
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


def renameToOld(tab, data=None):
    tab.renameColumns( regReplDict={'B':'^AB(?=\dN)', 'AOA_':'Alpha_', 'AIn_':'AxInd_', 'ApI_':'TnInd_'}) # New:Old

def renameToNew(tab, data=None):
    tab.renameColumns( regReplDict={'AB':'^B(?=\dN)', 'Alpha_':'AOA_', 'AxInd_':'AIn_', 'TnInd_':'ApI_'}) # New:Old


class TestRenameOFChannels(unittest.TestCase):

    def test_change_units(self):
        from pydatview.Tables import Table
        tab = Table.createDummy(n=10, columns=['B1N001_[-]'])
        renameToNew(tab)
        self.assertEqual(tab.columns, ['Index','AB1N001_[-]'])


if __name__ == '__main__':
    unittest.main()
