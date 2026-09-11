import pandas as pd
import numpy as np
import re


def pd_interp1(x_new, xLabel, df, extrap='bounded'):
    """ Interpolate a panda dataframe based on a set of new value
    This function assumes that the dataframe is a simple 2d-table
    INPUTS:
     - extrap: bounded or nan
      
    """
    from .signal_analysis import multiInterp
    x_old = df[xLabel].values
    data_new=multiInterp(x_new, x_old, df.values.T, extrap=extrap)
    df = pd.DataFrame(data=data_new.T, columns=df.columns.values)
    df[xLabel] = x_new
    return df
    #nRow,nCol = df.shape
    #nRow = len(xnew)
    #data = np.zeros((nRow,nCol))
    #xref =df[xLabel].values.astype(float)
    #for col,i in zip(df.columns.values,range(nCol)):
    #    yref = df[col].values
    #    if yref.dtype!=float:
    #        raise Exception('Wrong type for yref, consider using astype(float)')
    #    data[:,i] = np.interp(xnew, xref, yref)
    #return pd.DataFrame(data=data, columns = df.columns)

def create_dummy_dataframe(size):
    return pd.DataFrame(data={'col1': np.linspace(0,1,size), 'col2': np.random.normal(0,1,size)})


def remove_duplicated_col_df(df):
    """ Remove duplicated columns, but keep the first instance """
    return df.loc[:,~df.columns.duplicated()].copy()
    # IF we want to remove them all, Remove them all:
    # dup_cols = df.columns[df.columns.duplicated()]
    # df.drop(columns=dup_cols, inplace=False)

def remap_df(df, ColMap, bColKeepNewOnly=False, inPlace=False, dataDict=None, verbose=False, raiseIfAbsent=False):
    """ 
    Add/rename columns of a dataframe, potentially perform operations between columns

    dataDict: dictionary of data to be made available as "variable" in the column mapping
         'key' (new) : value (old)

    Example:

        ColumnMap={
          'Pitch_[deg]'      : 'Bld1Pitch_[deg]'               , # new column from existing one
          'WS_[m/s]'         : '{Wind1VelX_[m/s]}'             , # new column from existing one
          'RotSpeed_[rad/s]' : '{RotSpeed_[rpm]} * 2*np.pi/60 ', # new column from existing with basic operation 
          'TotalSpeed'       : '{Speed1} * 2  + {Speed2}*3    ', # new column from multiple columns with basic operations # cannot be inverted
          'RtTSR_[-]'        : '{RtTSR_[-]} * 2               ', # change value of column based on simple arithmetic 
          'R_[m]'            : '{ones} * 15'                   , # create a constant columns # cannot be inverted
          'R_[m]'            : '{ones} * R'                    , # use dataDict['R']  # FAILS FOR NOW
          'U_[m/s]'          : 'U'                             , # use dataDict['U']  # FAILS FOR NOW
          'q_p' :  ['Q_P_[rad]', '{PtfmSurge_[deg]}*np.pi/180']  # List of possible matches
        }
        # Read
        df = weio.read('FASTOutBin.outb').toDataFrame()
        # Change columns based on formulae, potentially adding new columns
        df = fastlib.remap_df(df, ColumnMap, inplace=True)

    """
    # Insert dataDict into namespace, doesnt work
    #if dataDict is not None:
    #    for k,v in dataDict.items():
    #        print('>>>> SETTING ', k, dataDict[k])
    #        exec('{:s} = dataDict["{:s}"]'.format(k,k))


    if not inPlace:
        df=df.copy()
    ColMapMiss=[]
    ColNew=[]
    RenameMap=dict()
    # Loop for expressions
    for k0,v in ColMap.items():
        k=k0.strip()
        if type(v) is not list:
            values = [v]
        else:
            values = v
        Found = False
        ColMapMissLoc=[]
        for v in values:
            if v=='':
                v=k # <<< If Value is empty, we reproduce it
            v=v.strip()
            if Found:
                break # We avoid replacing twice
            if v.find('{')>=0:
                # --- This is an advanced substitution using formulae
                search_results = re.finditer(r'\{.*?\}', v)
                expr=v
                #if verbose:
                #    print('Attempt to insert column {:15s} with expr {}'.format(k,v))
                # For more advanced operations, we use an eval
                bFail=False
                for item in search_results:
                    col=item.group(0)[1:-1]
                    if col=='ones':
                        expr=expr.replace(item.group(0),'np.ones({:d})'.format(df.shape[0]))
                    elif col not in df.columns:
                        ColMapMissLoc.append(col)
                        bFail=True
                    else:
                        expr=expr.replace(item.group(0),'df[\''+col+'\']')
                #print(k, '=', expr)
                if not bFail:
                    if k in df:
                        if verbose:
                            print(f'Overwriting column {k:15s} with extr {v}')
                    else:
                        if verbose:
                            print(f'Inserting    column {k:15s} with expr {v}')
                    df[k]=eval(expr)
                    ColNew.append(k)
                else:
                    if verbose:
                        print('[WARN] Column not present in dataframe, cannot evaluate: ',expr)
                    if raiseIfAbsent:
                        raise Exception('Column not present in dataframe, cannot evaluate: ',expr)
            else:
                #print(k0,'=',v)
                if v not in df.columns:
                    ColMapMissLoc.append(v)
                    if verbose:
                        print('[WARN] Column not present in dataframe: ',v)
                else:
                    if k in RenameMap.keys():
                        print('[WARN] Not renaming {} with {} as the key is already present in RenameMap'.format(k,v))
                    else:
                        RenameMap[k]=v
                        Found=True
        if len(values)>0:
            if Found:
                pass
            else:
                ColMapMiss+=ColMapMissLoc
        else:
            ColMapMiss+=ColMapMissLoc


    # --- Applying renaming only now so that expressions may be applied in any order
    ColNames = list(df.columns.values)
    for k,v in RenameMap.items():
        if verbose:
            print('Renaming column {:15s} > {}'.format(v,k))
        k=k.strip()
        iCol = ColNames.index(v)
        ColNames[iCol] = k
        ColNew.append(k)
    #df.columns = df.columns.values # Hack to ensure columns are updated
    df.columns = ColNames

    if len(ColMapMiss)>0:
        if verbose:
            print('[FAIL] The following columns were not found in the dataframe:',ColMapMiss)
        if raiseIfAbsent:
            raise Exception('Column not present in dataframe, cannot evaluate: ',ColMapMiss)
        #print('Available columns are:',df.columns.values)

    if bColKeepNewOnly:
        ColNew = [c for c,_ in ColMap.items() if c in ColNew]# Making sure we respec order from user
        ColKeepSafe = [c for c in ColNew if c in df.columns.values]
        ColKeepMiss = [c for c in ColNew if c not in df.columns.values]
        if len(ColKeepMiss)>0:
            print('[WARN] Signals missing and omitted for ColKeep:\n       '+'\n       '.join(ColKeepMiss))
        df=df[ColKeepSafe]
    return df

def inverse_colmap(ColMap, verbose=True):
    """
    Inverts a column mapping dictionary (ColMap) where possible.

    Supported patterns:
      - Direct rename:        'NewCol' : 'OldCol'               -> 'OldCol' : 'NewCol'
      - Formatting template:  'NewCol' : '{OldCol}'             -> 'OldCol' : 'NewCol'
      - Scaling operation:    'NewCol' : '{OldCol} * factor'    -> 'OldCol' : '{NewCol} / (factor)'
      - Division operation:   'NewCol' : '{OldCol} / factor'    -> 'OldCol' : '{NewCol} * (factor)'
      - List of matches:      'NewCol' : ['Old1', '{Old2}']     -> Inverts candidate matches individually

    Non-invertible expressions (multi-variable combinations, constants) are skipped.
    """

    def _extract_target_col(expr_str):
        """
        Extracts the underlying column name from a mapping string or template.

        Handles braced names like '{Q_P}', plain column names like 'Q_P',
        and simple arithmetic expressions. Returns None if 0 or multiple
        target columns are found.
        """
        if not isinstance(expr_str, str):
            return None

        expr_str = expr_str.strip()
        if not expr_str:
            return None

        # Check for braced variables such as '{Q_P}' or '{Q_P} * 2'
        matches = re.findall(r'\{([^{}]+)\}', expr_str)
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return None

        # Check for plain strings without braces like 'Q_P' or 'Pitch_[deg]'
        if '{' not in expr_str and '}' not in expr_str:
            if not re.search(r'[\*\/\+\-\(\)]', expr_str):
                return expr_str

            # Extract column identifier tokens if arithmetic operators exist
            tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_.-]*(?:\[[^\]]+\])?', expr_str)
            ignored = {'np', 'pi', 'sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'abs'}
            cols = [t for t in tokens if t not in ignored]
            if len(cols) == 1:
                return cols[0]

        return None


    def _invert_single_expression(new_col, expr_str):
        """
        Inverts a single expression mapping string.
        Returns (old_col_name, inverted_expression_string) or None if non-invertible.
        """
        expr_str = expr_str.strip()
        # Skip non-invertible constant definitions using {ones}
        if '{ones}' in expr_str:
            return None


        # Pattern 1: Single bracket replacement -> 'New' : '{Old}'
        match_simple = re.match(r'^\s*\{([^{}]+)\}\s*$', expr_str)
        if match_simple:
            old_col = match_simple.group(1)
            return old_col, new_col
        
        # Pattern 2: Multiplication -> 'New' : '{Old} * factor' OR 'factor * {Old}'
        # Right-hand factor: {Old} * factor
        match_mult_right = re.match(r'^\s*\{([^{}]+)\}\s*\*\s*(.+)$', expr_str)
        # Left-hand factor: factor * {Old}
        match_mult_left = re.match(r'^\s*(.+?)\s*\*\s*\{([^{}]+)\}\s*$', expr_str)
        if match_mult_right:
            old_col = match_mult_right.group(1)
            factor = match_mult_right.group(2).strip()
            if '{' in factor:
                return None
            return old_col, f"{{{new_col}}} / ({factor})"
        elif match_mult_left:
            factor = match_mult_left.group(1).strip()
            old_col = match_mult_left.group(2)
            if '{' in factor:
                return None
            return old_col, f"{{{new_col}}} / ({factor})"

        # Pattern 3: Division -> 'New' : '{Old} / factor' OR 'factor / {Old}'
        # Right-hand denominator: {Old} / factor -> Old = New * factor
        match_div_right = re.match(r'^\s*\{([^{}]+)\}\s*\/\s*(.+)$', expr_str)
        # Left-hand numerator: factor / {Old} -> Old = factor / New
        match_div_left = re.match(r'^\s*(.+?)\s*\/\s*\{([^{}]+)\}\s*$', expr_str)

        if match_div_right:
            old_col = match_div_right.group(1)
            factor = match_div_right.group(2).strip()
            if '{' in factor:
                return None
            return old_col, f"{{{new_col}}} * ({factor})"
        elif match_div_left:
            factor = match_div_left.group(1).strip()
            old_col = match_div_left.group(2)
            if '{' in factor:
                return None
            return old_col, f"({factor}) / {{{new_col}}}"

        # Pattern 4: Fallback plain rename string -> 'New' : 'Old' (e.g. 'Pitch_[deg]' : 'Bld1Pitch_[deg]')
        if '{' not in expr_str and '}' not in expr_str:
            return expr_str, new_col

        return None


    ColMapI = {}
    for new_col, expr in ColMap.items():
        new_col = new_col.strip()
        if isinstance(expr, list):
            # Process list of potential matches
            inverted_list = []
            for item in expr:
                res = _invert_single_expression(new_col, item.strip())
                if res:
                    inverted_list.append(res[1])
            if len(inverted_list) == 1:
                old_col, inverted_expr = _invert_single_expression(new_col, expr[0]) # keep structure
                ColMapI[old_col] = inverted_list[0]
            elif len(inverted_list) > 1:
                # Arbitrarily pick the first matching target key for the inverted dict
                old_col = _extract_target_col(expr[0])
                if old_col:
                    ColMapI[old_col] = inverted_list[0]

        elif isinstance(expr, str):
            expr    = expr.strip()
            res = _invert_single_expression(new_col, expr)
            if res:
                old_col, inverted_expr = res
                ColMapI[old_col] = inverted_expr
            elif verbose:
                print(f"[WARN] Unable to invert expression for key '{new_col}': '{expr}'")

    return ColMapI











def changeUnits(df, flavor='SI', inPlace=True):
    """ Change units of a dataframe

    # TODO harmonize with dfToSIunits in welib.fast.tools.lin.py !
    """
    def splitunit(s0):
        """ 
        return (variable, unit, previous character, brackets)
        e.g.   ( 'Time' ,  's',   '_'             , '[]')
        """
        s=s0.replace('(',' [').replace(')',']')
        iu=s.rfind('[')
        if iu>1:
            bracket = s0[iu:iu+1]
            if bracket=='(':
                brackets='()'
            else:
                brackets='[]'
            if iu>1:
                prev_char=s0[(iu-1):iu]
                if prev_char not in [' ', '_']:
                    prev_char=''
                    svar=s[:iu]
                else:
                    svar=s[:iu-1]
            return svar, s[iu+1:].replace(']',''), prev_char, brackets
        else:
            return s, '', '', ''
    def change_units_to_WE(s, c):
        """ 
        Change units to wind energy units
        s: channel name (string) containing units, typically 'speed_[rad/s]'
        c: channel (array)
        """
        svar, u, prev, brackets = splitunit(s)
        u=u.lower()
        scalings = {}
        #        OLD      =     NEW
        scalings['rad/s'] =  (30/np.pi,'rpm') # TODO decide
        scalings['rad' ]  =   (180/np.pi,'deg')
        scalings['n']     =   (1e-3, 'kN')
        scalings['mn']    =   (1e+3, 'kN')
        scalings['nm']    =   (1e-3, 'kNm')
        scalings['n-m']   =   (1e-3, 'kNm')
        scalings['n*m']   =   (1e-3, 'kNm')
        scalings['mnm']   =   (1e+3, 'kNm')
        scalings['mn-m']  =   (1e+3, 'kNm')
        scalings['mn*m']  =   (1e+3, 'kNm')
        scalings['w']     =   (1e-3, 'kW')
        scalings['mw']    =   (1e+3, 'kW')
        if u in scalings.keys():
            scale, new_unit = scalings[u]
            s = svar+prev+brackets[0]+new_unit+brackets[1]
            c *= scale
        return s, c

    def change_units_to_SI(s, c):
        """ 
        Change units to SI units
        TODO, a lot more units conversion needed...will add them as we go
        s: channel name (string) containing units, typically 'speed_[rad/s]'
        c: channel (array)
        """
        svar, u, prev, brackets = splitunit(s)
        u=u.lower()
        scalings = {}
        #        OLD      =     NEW
        scalings['rpm']   =  (np.pi/30,'rad/s') 
        scalings['rad' ]  =   (180/np.pi,'deg')
        scalings['deg/s' ] =   (np.pi/180,'rad/s')
        scalings['mn']     =   (1e6, 'N')
        scalings['kn']     =   (1e3, 'N')
        scalings['mnm']    =   (1e6, 'Nm')
        scalings['mnm']    =   (1e6, 'Nm')
        scalings['mn-m']   =   (1e6, 'Nm')
        scalings['mn*m']   =   (1e6, 'Nm')
        scalings['knm']    =   (1e3, 'Nm')
        scalings['kn-m']   =   (1e3, 'Nm')
        scalings['kn*m']   =   (1e3, 'Nm')
        scalings['kw']     =   (1e3, 'W')
        scalings['mw']     =   (1e6 ,'W')
        if u in scalings.keys():
            scale, new_unit = scalings[u]
            s = svar+prev+brackets[0]+new_unit+brackets[1]
            c *= scale
        return s, c

    if not inPlace:
        raise NotImplementedError()

    if flavor == 'WE':
        cols = []
        for i, colname in enumerate(df.columns):
            colname_new, col_new = change_units_to_WE(colname, df.iloc[:,i])
            df[colname] = df[colname].astype(col_new.dtype)
            df.iloc[:,i] = col_new
            cols.append(colname_new)
        df.columns = cols
    elif flavor == 'SI':
        cols = []
        for i, colname in enumerate(df.columns):
            colname_new, col_new = change_units_to_SI(colname, df.iloc[:,i])
            df[colname] = df[colname].astype(col_new.dtype) # Need to cast to new type if type changed..
            df.iloc[:,i] = col_new
            cols.append(colname_new)
        df.columns = cols
    else:
        raise NotImplementedError(flavor)
    return df

