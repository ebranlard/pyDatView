import unittest
import numpy as np
from pydatview.common import splitunit
from pydatview.pipeline import Action, IrreversibleAction

def standardizeUnitsAction(label, mainframe=None, flavor='SI'):
    """ 
    Main entry point of the plugin
    """
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
    tableFunction = lambda t: changeUnits(t, flavor=flavor)

    action = IrreversibleAction(
            name=label, 
            tableFunction=tableFunction, 
            guiCallback=guiCallback,
            mainframe=mainframe, # shouldnt be needed
            )

    return action

def changeUnits(tab, flavor='SI'):
    """ Change units of a table
    NOTE: it relies on the Table class, which may change interface in the future..
    """
    if flavor=='WE':
        for i, colname in enumerate(tab.columns):
            colname, tab.data.iloc[:,i] = change_units_to_WE(colname, tab.data.iloc[:,i])
            tab.columns[i]      = colname # TODO, use a dataframe everywhere..
        tab.data.columns = tab.columns
    elif flavor=='SI':
        for i, colname in enumerate(tab.columns):
            colname, tab.data.iloc[:,i] = change_units_to_SI(colname, tab.data.iloc[:,i])
            tab.columns[i]      = colname # TODO, use a dataframe everywhere..
        tab.data.columns = tab.columns
    else:
        raise NotImplementedError(flavor)


def change_units_to_WE(s, c):
    """ 
    Change units to wind energy units
    s: channel name (string) containing units, typically 'speed_[rad/s]'
    c: channel (array)
    """
    svar, u = splitunit(s)
    u=u.lower()
    scalings = {}
    scalings['rad/s'] =  (30/np.pi,'rpm') # TODO decide
    scalings['rad' ]  =   (180/np.pi,'deg')
    scalings['n']     =   (1e-3, 'kN')
    scalings['nm']    =   (1e-3, 'kNm')
    scalings['n-m']   =   (1e-3, 'kNm')
    scalings['n*m']   =   (1e-3, 'kNm')
    scalings['w']     =   (1e-3, 'kW')
    if u in scalings.keys():
        scale, new_unit = scalings[u]
        s = svar+'['+new_unit+']'
        c *= scale
    return s, c

def change_units_to_SI(s, c):
    """ 
    Change units to SI units
    TODO, a lot more units conversion needed...will add them as we go
    s: channel name (string) containing units, typically 'speed_[rad/s]'
    c: channel (array)
    """
    svar, u = splitunit(s)
    u=u.lower()
    scalings = {}
    scalings['rpm']   =  (np.pi/30,'rad/s') 
    scalings['rad' ]  =   (180/np.pi,'deg')
    scalings['kn']     =   (1e3, 'N')
    scalings['knm']    =   (1e3, 'Nm')
    scalings['kn-m']   =   (1e3, 'Nm')
    scalings['kn*m']   =   (1e3, 'Nm')
    scalings['kw']     =   (1e3, 'W')
    if u in scalings.keys():
        scale, new_unit = scalings[u]
        s = svar+'['+new_unit+']'
        c *= scale
    return s, c





class TestChangeUnits(unittest.TestCase):

    def test_change_units(self):
        import pandas as pd
        from pydatview.Tables import Table
        data = np.ones((1,3)) 
        data[:,0] *= 2*np.pi/60    # rad/s
        data[:,1] *= 2000          # N
        data[:,2] *= 10*np.pi/180  # rad
        df = pd.DataFrame(data=data, columns=['om [rad/s]','F [N]', 'angle_[rad]'])
        tab=Table(data=df)
        changeUnits(tab, flavor='WE')
        np.testing.assert_almost_equal(tab.data.values[:,0],[1])
        np.testing.assert_almost_equal(tab.data.values[:,1],[2])
        np.testing.assert_almost_equal(tab.data.values[:,2],[10])
        self.assertEqual(tab.columns, ['om [rpm]', 'F [kN]', 'angle [deg]'])
        raise Exception('>>>>>>>>>>>>')


if __name__ == '__main__':
    unittest.main()
