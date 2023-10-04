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
            tableFunctionApply=changeUnits, 
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
_imports=['from pydatview.plugins.data_standardizeUnits import changeUnits']
# _imports+=['from pydatview.Tables import Table']
_data_var='changeUnitsData'
_code="""changeUnits(df, changeUnitsData)"""

def changeUnits(tab, data):
    """ Change units of a table
    NOTE: it relies on the Table class, which may change interface in the future..
    """
    if not isinstance(tab, pd.DataFrame):
        df = tab.data
    else:
        df = tab

    if data['flavor']=='WE':
        cols = []
        for i, colname in enumerate(df.columns):
            colname_new, df.iloc[:,i] = change_units_to_WE(colname, df.iloc[:,i])
            cols.append(colname_new)
        df.columns = cols
    elif data['flavor']=='SI':
        cols = []
        for i, colname in enumerate(df.columns):
            colname_new, df.iloc[:,i] = change_units_to_SI(colname, df.iloc[:,i])
            cols.append(colname_new)
        df.columns = cols
    else:
        raise NotImplementedError(data['flavor'])

def change_units_to_WE(s, c):
    """ 
    Change units to wind energy units
    s: channel name (string) containing units, typically 'speed_[rad/s]'
    c: channel (array)
    """
    svar, u = splitunit(s)
    u=u.lower()
    scalings = {}
    #        OLD      =     NEW
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
    #        OLD      =     NEW
    scalings['rpm']   =  (np.pi/30,'rad/s') 
    scalings['rad' ]  =   (180/np.pi,'deg')
    scalings['deg/s' ] =   (np.pi/180,'rad/s')
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


if __name__ == '__main__':
    pass
    #unittest.main()
