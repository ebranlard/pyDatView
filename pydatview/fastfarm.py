import os
import glob
import numpy as np
import pandas as pd
try:
    import weio
except:
    raise Exception('Python package `weio` not found, please install it from https://github.com/ebranlard/weio ')

from . import fastlib



def spanwiseColFastFarm(Cols, nWT=9, nD=9):
    """ Return column info, available columns and indices that contain AD spanwise data"""
    FFSpanMap=dict()
    for i in np.arange(nWT):
        FFSpanMap['^CtT{:d}N(\d*)_\[-\]'.format(i+1)]='CtT{:d}_[-]'.format(i+1)
    for i in np.arange(nWT):
        for k in np.arange(nD):
            FFSpanMap['^WkDfVxT{:d}N(\d*)D{:d}_\[m/s\]'.format(i+1,k+1) ]='WkDfVxT{:d}D{:d}_[m/s]'.format(i+1, k+1)  
    for i in np.arange(nWT):
        for k in np.arange(nD):
            FFSpanMap['^WkDfVrT{:d}N(\d*)D{:d}_\[m/s\]'.format(i+1,k+1) ]='WkDfVrT{:d}D{:d}_[m/s]'.format(i+1, k+1)  

    return fastlib.find_matching_columns(Cols, FFSpanMap)

def diameterwiseColFastFarm(Cols, nWT=9):
    """ Return column info, available columns and indices that contain AD spanwise data"""
    FFDiamMap=dict()
    for i in np.arange(nWT):
        for x in ['X','Y','Z']:
            FFDiamMap['^WkAxs{}T{:d}D(\d*)_\[-\]'.format(x,i+1)]   ='WkAxs{}T{:d}_[-]'.format(x,i+1) 
    for i in np.arange(nWT):
        for x in ['X','Y','Z']:
            FFDiamMap['^WkPos{}T{:d}D(\d*)_\[m\]'.format(x,i+1)]   ='WkPos{}T{:d}_[m]'.format(x,i+1)
    for i in np.arange(nWT):
        for x in ['X','Y','Z']:
            FFDiamMap['^WkVel{}T{:d}D(\d*)_\[m/s\]'.format(x,i+1)] ='WkVel{}T{:d}_[m/s]'.format(x,i+1) 
    for i in np.arange(nWT):
        for x in ['X','Y','Z']:
            FFDiamMap['^WkDiam{}T{:d}D(\d*)_\[m\]'.format(x,i+1)]  ='WkDiam{}T{:d}_[m]'.format(x,i+1)
    return fastlib.find_matching_columns(Cols, FFDiamMap)

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
    # --- Opening ouputfile
    if df is None:
        df=weio.read(fastfarm_out).toDataFrame()

    # --- Opening input file and extracting inportant variables
    if fastfarm_input is None:
        # We don't have an input file, guess numbers of turbine, diameters, Nodes...
        cols, sIdx = fastlib.find_matching_pattern(df.columns.values, 'T(\d+)')
        nWT = np.array(sIdx).astype(int).max()
        cols, sIdx = fastlib.find_matching_pattern(df.columns.values, 'D(\d+)')
        nD = np.array(sIdx).astype(int).max()
        cols, sIdx = fastlib.find_matching_pattern(df.columns.values, 'N(\d+)')
        nr = np.array(sIdx).astype(int).max()
        vr=None
        vD=None
        D=0
    else:
        main=weio.FASTInFile(fastfarm_input)
        iOut    = main['OutRadii']
        dr      = main['dr']              # Radial increment of radial finite-difference grid (m)
        OutDist = main['OutDist']         # List of downstream distances for wake output for an individual rotor
        WT     = main['WindTurbines']
        nWT    = len(WT)
        vr     = dr*np.array(iOut)
        vD     = np.array(OutDist)
        nr=len(iOut)
        nD=len(vD)


    # --- Extracting time series of radial data only
    colRadial = SensorsFARMRadial(nWT=nWT,nD=nD,nR=nr,signals=df.columns.values)
    colRadial=['Time_[s]']+colRadial
    dfRadialTime = df[colRadial] # TODO try to do some magic with it, display it with a slider

    # --- Averaging data
    dfAvg = fastlib.averageDF(df,avgMethod=avgMethod,avgParam=avgParam)

    # --- Extract radial data
    ColsInfo, nrMax = spanwiseColFastFarm(df.columns.values, nWT=nWT, nD=nD)
    dfRad        = fastlib.extract_spanwise_data(ColsInfo, nrMax, df=None, ts=dfAvg.iloc[0])
    #dfRad       = fastlib.insert_radial_columns(dfRad, vr)
    if vr is None: 
        dfRad.insert(0, 'i_[#]', np.arange(nrMax)+1)
    else:
        dfRad.insert(0, 'r_[m]', vr[:nrMax])
    dfRad['i/n_[-]']=np.arange(nrMax)/nrMax

    # --- Extract downstream data
    ColsInfo, nDMax = diameterwiseColFastFarm(df.columns.values, nWT=nWT)
    dfDiam       = fastlib.extract_spanwise_data(ColsInfo, nDMax, df=None, ts=dfAvg.iloc[0])
    #dfDiam      = fastlib.insert_radial_columns(dfDiam)
    if vD is None:
        dfDiam.insert(0, 'i_[#]', np.arange(nDMax)+1)
    else:
        dfDiam.insert(0, 'x_[m]', vD[:nDMax])
    dfDiam['i/n_[-]'] = np.arange(nDMax)/nDMax
    return dfRad, dfRadialTime, dfDiam

