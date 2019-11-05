import os
import glob
import numpy as np
import pandas as pd
try:
    import weio
except:
    raise Exception('Python package `weio` not found, please install it from https://github.com/ebranlard/weio ')
try:
    import welib.fastlib.fastlib as fastlib
except:
    try:
        import fastlib
    except:
        raise Exception('You need the python module fastlib, you can get it by installing `welib` from https://github.com/ebranlard/welib or just download it from there')



def SensorsFARMRadial(nWT=3,nD=10,nR=30,signals=None):
    """ Returns a list of FASTFarm sensors that are used for the radial distribution
    of quantities (e.g. Ct, Wake Deficits).
    If `signals` is provided, the output is the list of sensors within the list `signals`.
    """
    WT  = np.arange(nWT)
    r   = np.arange(nR)
    D   = np.arange(nD)
    sens=[]
    sens+=['CtT{:d}N{:02d}_[-]'.format(i+1,j+1) for i in WT for j in r]
    sens+=['WkDfVxT{:d}N{:02d}D{:d}_[m/s]'.format(i+1,j+1,k+1) for i in WT for j in r for k in D]
    sens+=['WkDfVrT{:d}N{:02d}D{:d}_[m/s]'.format(i+1,j+1,k+1) for i in WT for j in r for k in D]
    if signals is not None:
        sens = [c for c in sens if c in signals]
    return sens

def SensorsFARMDiam(nWT,nD):
    """ Returns a list of FASTFarm sensors that contain quantities at different downstream diameters
     (e.g. WkAxs, WkPos, WkVel, WkDiam)
    If `signals` is provided, the output is the list of sensors within the list `signals`.
    """
    WT  = np.arange(nWT)
    D   = np.arange(nD)
    XYZ = ['X','Y','Z']
    sens=[]
    sens+=['WkAxs{}T{:d}D{:d}_[-]'.format(x,i+1,j+1) for x in XYZ for i in WT for j in D]
    sens+=['WkPos{}T{:d}D{:d}_[m]'.format(x,i+1,j+1) for x in XYZ for i in WT for j in D]
    sens+=['WkVel{}T{:d}D{:d}_[m/s]'.format(x,i+1,j+1) for x in XYZ for i in WT for j in D]
    sens+=['WkDiam{}T{:d}D{:d}_[m]'.format(x,i+1,j+1) for x in XYZ for i in WT for j in D]
    if signals is not None:
        sens = [c for c in sens if c in signals]
    return sens


def extractFFRadialData(fastfarm_out,fastfarm_input,avgMethod='constantwindow',avgParam=30,D=1,df=None):
    # LEGACY
    return spanwisePostProFF(fastfarm_input,avgMethod=avgMethod,avgParam=avgParam,D=D,df=df,fastfarm_out=fastfarm_out)


def spanwisePostProFF(fastfarm_input,avgMethod='constantwindow',avgParam=30,D=1,df=None,fastfarm_out=None):
    """ 
    Opens a FASTFarm output file, extract the radial data, average them and returns spanwise data

    D: diameter TODO, extract it from the main file

    See faslibt.averageDF for `avgMethod` and `avgParam`.
    """
    # --- Opening input file and extracting inportant variables
    main=weio.FASTInFile(fastfarm_input)
    iOut    = main['OutRadii']
    dr      = main['dr']              # Radial increment of radial finite-difference grid (m)
    OutDist = main['OutDist']         # List of downstream distances for wake output for an individual rotor
    WT     = main['WindTurbines']
    nWT    = len(WT)
    vr_bar = dr*np.array(iOut)/(D/2)
    vD     = np.array(OutDist)/D
    nr=len(vr_bar)
    nD=len(vD)
    # --- Opening ouputfile
    if df is None:
        df=weio.read(fastfarm_out).toDataFrame()

    # --- Extracting time series of radial data only
    colRadial = SensorsFARMRadial(nWT=nWT,nD=nD,nR=nr,signals=df.columns.values)
    colRadial=['Time_[s]']+colRadial
    dfRadialTime = df[colRadial] # TODO try to do some magic with it, display it with a slider

    # --- Averaging data
    dfAvg = fastlib.averageDF(df,avgMethod='constantwindow',avgParam=30)

    # --- Brute force storing of radial data
    Columns     = [vr_bar]
    if D==1:
        ColumnNames = ['r_[m]']
    else:
        ColumnNames = ['r/R_[-]']
    for iWT in range(nWT):
        Values=np.zeros((len(vr_bar),1))
        nCount=0
        col_out='CtT{:d}_[-]'.format(iWT+1)
        for ir in range(nr):
            col='CtT{:d}N{:02d}_[-]'.format(iWT+1,ir+1)
            if col in dfAvg.columns.values:
                Values[ir,0]=dfAvg[col]
                nCount+=1
        if nCount!=nr and nCount>0:
            print('[WARN] Not all values found for {}, found {}/{}'.format(col_out,nCount,nr))
        if nCount>0:
            Columns.append(Values)
            ColumnNames.append('CtT{:d}'.format(iWT+1))
    for iWT in range(nWT):
        for iD in range(nD):
            Values=np.zeros((len(vr_bar),1))
            nCount=0
            col_out='WkDfVxT{:d}D{:d}_[m/s]'.format(iWT+1,iD+1)
            for ir in range(nr):
                col='WkDfVxT{:d}N{:02d}D{:d}_[m/s]'.format(iWT+1,ir+1,iD+1)
                if col in dfAvg.columns.values:
                    Values[ir,0]=dfAvg[col]
                    nCount+=1
            if nCount!=nr and nCount>0:
                print('[WARN] Not all values found for {}, found {}/{}'.format(col_out,nCount,nr))
            if nCount>0:
                Columns.append(Values)
                ColumnNames.append(col_out)
    for iWT in range(nWT):
        for iD in range(nD):
            Values=np.zeros((len(vr_bar),1))
            nCount=0
            col_out='WkDfVrT{:d}D{:d}_[m/s]'.format(iWT+1,iD+1)
            for ir in range(nr):
                col='WkDfVrT{:d}N{:02d}D{:d}_[m/s]'.format(iWT+1,ir+1,iD+1)
                if col in dfAvg.columns.values:
                    Values[ir,0]=dfAvg[col]
                    nCount+=1
            if nCount!=nr and nCount>0:
                print('[WARN] Not all values found for {}, found {}/{}'.format(col_out,nCount,nr))
            if nCount>0:
                Columns.append(Values)
                ColumnNames.append(col_out)

    data=np.column_stack(Columns)
    dfRad = pd.DataFrame(data=data, columns=ColumnNames)
    return dfRad, dfRadialTime

