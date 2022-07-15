# --- For cmd.py
from __future__ import division, print_function
import os
import pandas as pd
import numpy as np
import re

# --- fast libraries
import pydatview.io as weio
from pydatview.io.fast_input_file import FASTInputFile
from pydatview.io.fast_output_file import FASTOutputFile
from pydatview.io.fast_input_deck import FASTInputDeck


# --------------------------------------------------------------------------------}
# --- Tools for IO 
# --------------------------------------------------------------------------------{
def ED_BldStations(ED):
    """ Returns ElastoDyn Blade Station positions, useful to know where the outputs are.
    INPUTS:
       - ED: either:
           - a filename of a ElastoDyn input file
           - an instance of FileCl, as returned by reading the file, ED = weio.read(ED_filename)

    OUTUPTS:
        - bld_fract: fraction of the blade length were stations are defined
        - r_nodes: spanwise position from the rotor apex of the Blade stations
    """
    if hasattr(ED,'startswith'): # if string
        ED = FASTInputFile(ED)

    nBldNodes    = ED['BldNodes']
    bld_fract    = np.arange(1./nBldNodes/2., 1, 1./nBldNodes)
    r_nodes      = bld_fract*(ED['TipRad']-ED['HubRad']) + ED['HubRad']
    return bld_fract, r_nodes

def ED_TwrStations(ED):
    """ Returns ElastoDyn Tower Station positions, useful to know where the outputs are.
    INPUTS:
       - ED: either:
           - a filename of a ElastoDyn input file
           - an instance of FileCl, as returned by reading the file, ED = weio.read(ED_filename)

    OUTPUTS:
        - r_fract: fraction of the towet length were stations are defined
        - h_nodes: height from the *ground* of the stations  (not from the Tower base)
    """
    if hasattr(ED,'startswith'): # if string
        ED = FASTInputFile(ED)

    nTwrNodes = ED['TwrNodes']
    twr_fract    = np.arange(1./nTwrNodes/2., 1, 1./nTwrNodes)
    h_nodes      = twr_fract*(ED['TowerHt']-ED['TowerBsHt']) + ED['TowerBsHt']
    return twr_fract, h_nodes

def ED_BldGag(ED):
    """ Returns the radial position of ElastoDyn blade gages 
    INPUTS:
       - ED: either:
           - a filename of a ElastoDyn input file
           - an instance of FileCl, as returned by reading the file, ED = weio.read(ED_filename)
    OUTPUTS:
       - r_gag: The radial positions of the gages, given from the rotor apex
    """
    if hasattr(ED,'startswith'): # if string
        ED = FASTInputFile(ED)
    _,r_nodes= ED_BldStations(ED)
    
    #     if ED.hasNodal:
    #         return r_nodes, None
    nOuts = ED['NBlGages']
    if nOuts<=0:
        return np.array([]), np.array([])
    if type(ED['BldGagNd']) is list:
        Inodes = np.asarray(ED['BldGagNd'])
    else:
        Inodes = np.array([ED['BldGagNd']])
    r_gag = r_nodes[ Inodes[:nOuts] -1]
    return r_gag, Inodes

def ED_TwrGag(ED):
    """ Returns the heights of ElastoDyn blade gages 
    INPUTS:
       - ED: either:
           - a filename of a ElastoDyn input file
           - an instance of FileCl, as returned by reading the file, ED = weio.read(ED_filename)
    OUTPUTS:
       - h_gag: The heights of the gages, given from the ground height (tower base + TowerBsHt)
    """
    if hasattr(ED,'startswith'): # if string
        ED = FASTInputFile(ED)
    _,h_nodes= ED_TwrStations(ED)
    nOuts = ED['NTwGages']
    if nOuts<=0:
        return np.array([])
    if type(ED['TwrGagNd']) is list:
        Inodes = np.asarray(ED['TwrGagNd'])
    else:
        Inodes = np.array([ED['TwrGagNd']])
    h_gag = h_nodes[ Inodes[:nOuts] -1]
    return h_gag


def AD14_BldGag(AD):
    """ Returns the radial position of AeroDyn 14 blade gages (based on "print" in column 6)
    INPUTS:
       - AD: either:
           - a filename of a AeroDyn input file
           - an instance of FileCl, as returned by reading the file, AD = weio.read(AD_filename)
    OUTPUTS:
       - r_gag: The radial positions of the gages, given from the blade root
    """
    if hasattr(ED,'startswith'): # if string
        AD = FASTInputFile(AD)

    Nodes=AD['BldAeroNodes']  
    if Nodes.shape[1]==6:
       doPrint= np.array([ n.lower().find('p')==0  for n in Nodes[:,5]])
    else:
       doPrint=np.array([ True  for n in Nodes[:,0]])

    r_gag = Nodes[doPrint,0].astype(float)
    IR    = np.arange(1,len(Nodes)+1)[doPrint]
    return r_gag, IR

def AD_BldGag(AD,AD_bld,chordOut=False):
    """ Returns the radial position of AeroDyn blade gages 
    INPUTS:
       - AD: either:
           - a filename of a AeroDyn input file
           - an instance of FileCl, as returned by reading the file, AD = weio.read(AD_filename)
       - AD_bld: either:
           - a filename of a AeroDyn Blade input file
           - an instance of FileCl, as returned by reading the file, AD_bld = weio.read(AD_bld_filename)
    OUTPUTS:
       - r_gag: The radial positions of the gages, given from the blade root
    """
    if hasattr(AD,'startswith'): # if string
        AD = FASTInputFile(AD)
    if hasattr(AD_bld,'startswith'): # if string
        AD_bld = FASTInputFile(AD_bld)
    #print(AD_bld.keys())

    nOuts=AD['NBlOuts']
    if nOuts<=0:
        if chordOut:
            return np.array([]), np.array([])
        else:
            return np.array([])
    INodes = np.array(AD['BlOutNd'][:nOuts])
    r_gag = AD_bld['BldAeroNodes'][INodes-1,0]
    if chordOut:
        chord_gag = AD_bld['BldAeroNodes'][INodes-1,5]
        return r_gag,chord_gag
    else:
        return r_gag

def BD_BldStations(BD, BDBld):
    """ Returns BeamDyn Blade Station positions, useful to know where the outputs are.
    INPUTS:
       - BD: either:
           - a filename of a ElastoDyn input file
           - an instance of FileCl, as returned by reading the file, BD = weio.read(BD_filename)
    OUTUPTS:
        - r_nodes: spanwise position from the balde root of the Blade stations
    """
    if hasattr(BD,'startswith'): # if string
        BD = FASTInputFile(BD)
    if hasattr(BD,'startswith'): # if string
        BDBld = FASTInputFile(BDBld)
        #  BD['BldFile'].replace('"',''))

    z_kp = BD['MemberGeom'][:,2]
    R    = z_kp[-1]-z_kp[0]
    r    = BDBld['BeamProperties']['span']*R
    quad = BD['quadrature']
    ref  = BD['refine']
    if 'default' in str(ref).lower():
        ref = 1
    dr   = np.diff(r)/ref
    rmid = np.concatenate( [r[:-1]+dr*(iref+1) for iref in np.arange(ref-1)  ])
    r    = np.concatenate( (r, rmid))
    r    = np.unique(np.sort(r))
    return r

def BD_BldGag(BD):
    """ Returns the radial position of BeamDyn blade gages 
    INPUTS:
       - BD: either:
           - a filename of a BeamDyn input file
           - an instance of FileCl, as returned by reading the file, BD = weio.read(BD_filename)
    OUTPUTS:
       - r_gag: The radial positions of the gages, given from the rotor apex
    """
    if hasattr(BD,'startswith'): # if string
        BD = FASTInputFile(BD)

    M       = BD['MemberGeom']
    r_nodes = M[:,2] # NOTE: we select the z axis here, and we don't take curvilenear coord
    nOuts = BD['NNodeOuts']
    if nOuts<=0:
        nOuts=0
    if type(BD['OutNd']) is list:
        Inodes = np.asarray(BD['OutNd'])
    else:
        Inodes = np.array([BD['OutNd']])
    r_gag = r_nodes[ Inodes[:nOuts] -1]
    return r_gag, Inodes, r_nodes

# 
# 
# 1, 7, 14, 21, 30, 36, 43, 52, 58 BldGagNd List of blade nodes that have strain gages [1 to BldNodes] (-) [unused if NBlGages=0]

# --------------------------------------------------------------------------------}
# --- Helper functions for radial data  
# --------------------------------------------------------------------------------{
def _HarmonizeSpanwiseData(Name, Columns, vr, R, IR=None) :
    """ helper function to use with spanwiseAD and spanwiseED """
    # --- Data present
    data     = [c for _,c in Columns if c is not None]
    ColNames = [n for n,_ in Columns if n is not None]
    Lengths  = [len(d) for d in data]
    if len(data)<=0:
        print('[WARN] No spanwise data for '+Name)
        return None, None, None

    # --- Harmonize data so that they all have the same length
    nrMax = np.max(Lengths)
    ids=np.arange(nrMax)
    if vr is None:
        bFakeVr=True
        vr_bar = ids/(nrMax-1)
    else:
        vr_bar=vr/R
        bFakeVr=False
        if (nrMax)<len(vr_bar):
            vr_bar=vr_bar[1:nrMax]
        elif (nrMax)>len(vr_bar):
            raise Exception('Inconsitent length between radial stations and max index present in output chanels')

    for i in np.arange(len(data)):
        d=data[i]
        if len(d)<nrMax:
            Values = np.zeros((nrMax,1))
            Values[:] = np.nan
            Values[1:len(d)] = d
            data[i] = Values

    # --- Combine data and remove 
    dataStack = np.column_stack([d for d in data])
    ValidRow = np.logical_not([np.isnan(dataStack).all(axis=1)])
    dataStack = dataStack[ValidRow[0],:]
    ids       = ids      [ValidRow[0]]
    vr_bar    = vr_bar   [ValidRow[0]]

    # --- Create a dataframe
    dfRad = pd.DataFrame(data= dataStack, columns = ColNames)

    if bFakeVr:
        dfRad.insert(0, 'i/n_[-]', vr_bar)
    else:
        dfRad.insert(0, 'r/R_[-]', vr_bar)
        if R is not None:
            r = vr_bar*R
    if IR is not None:
        dfRad['Node_[#]']=IR[:nrMax]
    dfRad['i_[#]']=ids+1
    if not bFakeVr:
        dfRad['r_[m]'] = r

    return dfRad,  nrMax, ValidRow

def insert_radial_columns(df, vr=None, R=None, IR=None):
    """
    Add some columns to the radial data
    df: dataframe
    """
    if df is None:
        return df
    if df.shape[1]==0:
        return None
    nrMax=len(df)
    ids=np.arange(nrMax)
    if vr is None or R is None:
        # Radial position unknown
        vr_bar = ids/(nrMax-1)
        df.insert(0, 'i/n_[-]', vr_bar)
    else:
        vr_bar=vr/R
        if (nrMax)<=len(vr_bar):
            vr_bar=vr_bar[:nrMax]
        elif (nrMax)>len(vr_bar):
            raise Exception('Inconsitent length between radial stations ({:d}) and max index present in output chanels ({:d})'.format(len(vr_bar),nrMax))
        df.insert(0, 'r/R_[-]', vr_bar)

    if IR is not None:
        df['Node_[#]']=IR[:nrMax]
    df['i_[#]']=ids+1
    if vr is not None:
        df['r_[m]'] = vr[:nrMax]
    return df

def find_matching_columns(Cols, PatternMap):
    ColsInfo=[]
    nrMax=0
    for colpattern,colmap in PatternMap.items():
        # Extracting columns matching pattern
        cols, sIdx = find_matching_pattern(Cols, colpattern)
        if len(cols)>0:
            # Sorting by ID
            cols  = np.asarray(cols)
            Idx   = np.array([int(s) for s in sIdx])
            Isort = np.argsort(Idx)
            Idx   = Idx[Isort]
            cols  = cols[Isort]
            col={'name':colmap,'Idx':Idx,'cols':cols}
            nrMax=max(nrMax,np.max(Idx))
            ColsInfo.append(col)
    return ColsInfo,nrMax

def extract_spanwise_data(ColsInfo, nrMax, df=None,ts=None):
    """ 
    Extract spanwise data based on some column info
    ColsInfo: see find_matching_columns
    """
    nCols = len(ColsInfo)
    if nCols==0:
        return None
    if ts is not None:
        Values = np.zeros((nrMax,nCols))
        Values[:] = np.nan
    elif df is not None:
        raise NotImplementedError()

    ColNames =[c['name'] for c in ColsInfo]

    for ic,c in enumerate(ColsInfo):
        Idx, cols, colname = c['Idx'], c['cols'], c['name']
        for idx,col in zip(Idx,cols):
            Values[idx-1,ic]=ts[col]
        nMissing = np.sum(np.isnan(Values[:,ic]))
        if len(cols)<nrMax:
            #print(Values)
            print('[WARN] Not all values found for {}, missing {}/{}'.format(colname,nMissing,nrMax))
        if len(cols)>nrMax:
            print('[WARN] More values found for {}, found {}/{}'.format(colname,len(cols),nrMax))
    df = pd.DataFrame(data=Values, columns=ColNames)
    df = df.reindex(sorted(df.columns), axis=1)
    return df


def _BDSpanMap():
    BDSpanMap=dict()
    for sB in ['B1','B2','B3']:
        # Old nodal outputs
        BDSpanMap['^'+sB+r'N(\d)TDxr_\[m\]']         = sB+'TDxr_[m]'
        BDSpanMap['^'+sB+r'N(\d)TDyr_\[m\]']         = sB+'TDyr_[m]'
        BDSpanMap['^'+sB+r'N(\d)TDzr_\[m\]']         = sB+'TDzr_[m]'
        # New nodal outputs
        BDSpanMap['^'+sB+r'N(\d*)_FxL_\[N\]']        = sB+'FxL_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FxL_\[N\]']        = sB+'FxL_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FxL_\[N\]']        = sB+'FxL_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_MxL_\[N-m\]']      = sB+'MxL_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MxL_\[N-m\]']      = sB+'MxL_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MxL_\[N-m\]']      = sB+'MxL_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_Fxr_\[N\]']        = sB+'Fxr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_Fxr_\[N\]']        = sB+'Fxr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_Fxr_\[N\]']        = sB+'Fxr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_Mxr_\[N-m\]']      = sB+'Mxr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_Mxr_\[N-m\]']      = sB+'Mxr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_Mxr_\[N-m\]']      = sB+'Mxr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_TDxr_\[m\]']       = sB+'TDxr_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_TDyr_\[m\]']       = sB+'TDyr_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_TDzr_\[m\]']       = sB+'TDzr_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_RDxr_\[-\]']       = sB+'RDxr_[-]'
        BDSpanMap['^'+sB+r'N(\d*)_RDyr_\[-\]']       = sB+'RDyr_[-]'
        BDSpanMap['^'+sB+r'N(\d*)_RDzr_\[-\]']       = sB+'RDzr_[-]'
        BDSpanMap['^'+sB+r'N(\d*)_AbsXg_\[m\]']      = sB+'AbsXg_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_AbsYg_\[m\]']      = sB+'AbsYg_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_AbsZg_\[m\]']      = sB+'AbsZg_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_AbsXr_\[m\]']      = sB+'AbsXr_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_AbsYr_\[m\]']      = sB+'AbsYr_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_AbsZr_\[m\]']      = sB+'AbsZr_[m]'
        BDSpanMap['^'+sB+r'N(\d*)_TVxg_\[m/s\]']     = sB+'TVxg_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVyg_\[m/s\]']     = sB+'TVyg_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVzg_\[m/s\]']     = sB+'TVzg_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVxl_\[m/s\]']     = sB+'TVxl_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVyl_\[m/s\]']     = sB+'TVyl_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVzl_\[m/s\]']     = sB+'TVzl_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVxr_\[m/s\]']     = sB+'TVxr_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVyr_\[m/s\]']     = sB+'TVyr_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TVzr_\[m/s\]']     = sB+'TVzr_[m/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVxg_\[deg/s\]']   = sB+'RVxg_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVyg_\[deg/s\]']   = sB+'RVyg_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVzg_\[deg/s\]']   = sB+'RVzg_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVxl_\[deg/s\]']   = sB+'RVxl_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVyl_\[deg/s\]']   = sB+'RVyl_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVzl_\[deg/s\]']   = sB+'RVzl_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVxr_\[deg/s\]']   = sB+'RVxr_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVyr_\[deg/s\]']   = sB+'RVyr_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_RVzr_\[deg/s\]']   = sB+'RVzr_[deg/s]'
        BDSpanMap['^'+sB+r'N(\d*)_TAxl_\[m/s^2\]']   = sB+'TAxl_[m/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_TAyl_\[m/s^2\]']   = sB+'TAyl_[m/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_TAzl_\[m/s^2\]']   = sB+'TAzl_[m/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_TAxr_\[m/s^2\]']   = sB+'TAxr_[m/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_TAyr_\[m/s^2\]']   = sB+'TAyr_[m/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_TAzr_\[m/s^2\]']   = sB+'TAzr_[m/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_RAxl_\[deg/s^2\]'] = sB+'RAxl_[deg/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_RAyl_\[deg/s^2\]'] = sB+'RAyl_[deg/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_RAzl_\[deg/s^2\]'] = sB+'RAzl_[deg/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_RAxr_\[deg/s^2\]'] = sB+'RAxr_[deg/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_RAyr_\[deg/s^2\]'] = sB+'RAyr_[deg/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_RAzr_\[deg/s^2\]'] = sB+'RAzr_[deg/s^2]'
        BDSpanMap['^'+sB+r'N(\d*)_PFxL_\[N\]']       = sB+'PFxL_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_PFyL_\[N\]']       = sB+'PFyL_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_PFzL_\[N\]']       = sB+'PFzL_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_PMxL_\[N-m\]']     = sB+'PMxL_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_PMyL_\[N-m\]']     = sB+'PMyL_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_PMzL_\[N-m\]']     = sB+'PMzL_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_DFxL_\[N/m\]']     = sB+'DFxL_[N/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DFyL_\[N/m\]']     = sB+'DFyL_[N/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DFzL_\[N/m\]']     = sB+'DFzL_[N/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DMxL_\[N-m/m\]']   = sB+'DMxL_[N-m/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DMyL_\[N-m/m\]']   = sB+'DMyL_[N-m/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DMzL_\[N-m/m\]']   = sB+'DMzL_[N-m/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DFxR_\[N/m\]']     = sB+'DFxR_[N/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DFyR_\[N/m\]']     = sB+'DFyR_[N/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DFzR_\[N/m\]']     = sB+'DFzR_[N/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DMxR_\[N-m/m\]']   = sB+'DMxR_[N-m/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DMyR_\[N-m/m\]']   = sB+'DMyR_[N-m/m]'
        BDSpanMap['^'+sB+r'N(\d*)_DMzR_\[N-m/m\]']   = sB+'DMzR_[N-m/m]'
        BDSpanMap['^'+sB+r'N(\d*)_FFbxl_\[N\]']       = sB+'FFbxl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFbyl_\[N\]']       = sB+'FFbyl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFbzl_\[N\]']       = sB+'FFbzl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFbxr_\[N\]']       = sB+'FFbxr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFbyr_\[N\]']       = sB+'FFbyr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFbzr_\[N\]']       = sB+'FFbzr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_MFbxl_\[N-m\]']     = sB+'MFbxl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFbyl_\[N-m\]']     = sB+'MFbyl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFbzl_\[N-m\]']     = sB+'MFbzl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFbxr_\[N-m\]']     = sB+'MFbxr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFbyr_\[N-m\]']     = sB+'MFbyr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFbzr_\[N-m\]']     = sB+'MFbzr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_FFcxl_\[N\]']       = sB+'FFcxl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFcyl_\[N\]']       = sB+'FFcyl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFczl_\[N\]']       = sB+'FFczl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFcxr_\[N\]']       = sB+'FFcxr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFcyr_\[N\]']       = sB+'FFcyr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFczr_\[N\]']       = sB+'FFczr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_MFcxl_\[N-m\]']     = sB+'MFcxl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFcyl_\[N-m\]']     = sB+'MFcyl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFczl_\[N-m\]']     = sB+'MFczl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFcxr_\[N-m\]']     = sB+'MFcxr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFcyr_\[N-m\]']     = sB+'MFcyr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFczr_\[N-m\]']     = sB+'MFczr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_FFdxl_\[N\]']       = sB+'FFdxl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFdyl_\[N\]']       = sB+'FFdyl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFdzl_\[N\]']       = sB+'FFdzl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFdxr_\[N\]']       = sB+'FFdxr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFdyr_\[N\]']       = sB+'FFdyr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFdzr_\[N\]']       = sB+'FFdzr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_MFdxl_\[N-m\]']     = sB+'MFdxl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFdyl_\[N-m\]']     = sB+'MFdyl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFdzl_\[N-m\]']     = sB+'MFdzl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFdxr_\[N-m\]']     = sB+'MFdxr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFdyr_\[N-m\]']     = sB+'MFdyr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFdzr_\[N-m\]']     = sB+'MFdzr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_FFgxl_\[N\]']       = sB+'FFgxl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFgyl_\[N\]']       = sB+'FFgyl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFgzl_\[N\]']       = sB+'FFgzl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFgxr_\[N\]']       = sB+'FFgxr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFgyr_\[N\]']       = sB+'FFgyr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFgzr_\[N\]']       = sB+'FFgzr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_MFgxl_\[N-m\]']     = sB+'MFgxl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFgyl_\[N-m\]']     = sB+'MFgyl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFgzl_\[N-m\]']     = sB+'MFgzl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFgxr_\[N-m\]']     = sB+'MFgxr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFgyr_\[N-m\]']     = sB+'MFgyr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFgzr_\[N-m\]']     = sB+'MFgzr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_FFixl_\[N\]']       = sB+'FFixl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFiyl_\[N\]']       = sB+'FFiyl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFizl_\[N\]']       = sB+'FFizl_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFixr_\[N\]']       = sB+'FFixr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFiyr_\[N\]']       = sB+'FFiyr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_FFizr_\[N\]']       = sB+'FFizr_[N]'
        BDSpanMap['^'+sB+r'N(\d*)_MFixl_\[N-m\]']     = sB+'MFixl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFiyl_\[N-m\]']     = sB+'MFiyl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFizl_\[N-m\]']     = sB+'MFizl_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFixr_\[N-m\]']     = sB+'MFixr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFiyr_\[N-m\]']     = sB+'MFiyr_[N-m]'
        BDSpanMap['^'+sB+r'N(\d*)_MFizr_\[N-m\]']     = sB+'MFizr_[N-m]'
    return BDSpanMap


def spanwiseColBD(Cols):
    """ Return column info, available columns and indices that contain BD spanwise data"""
    BDSpanMap = _BDSpanMap()
    return find_matching_columns(Cols, BDSpanMap)

def spanwiseColED(Cols):
    """ Return column info, available columns and indices that contain ED spanwise data"""
    EDSpanMap=dict()
    # All Outs
    for sB in ['B1','B2','B3']:
        EDSpanMap['^[A]*'+sB+r'N(\d*)ALx_\[m/s^2\]' ] = sB+'ALx_[m/s^2]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)ALy_\[m/s^2\]' ] = sB+'ALy_[m/s^2]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)ALz_\[m/s^2\]' ] = sB+'ALz_[m/s^2]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)TDx_\[m\]'     ] = sB+'TDx_[m]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)TDy_\[m\]'     ] = sB+'TDy_[m]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)TDz_\[m\]'     ] = sB+'TDz_[m]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)RDx_\[deg\]'   ] = sB+'RDx_[deg]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)RDy_\[deg\]'   ] = sB+'RDy_[deg]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)RDz_\[deg\]'   ] = sB+'RDz_[deg]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)MLx_\[kN-m\]'  ] = sB+'MLx_[kN-m]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)MLy_\[kN-m\]'  ] = sB+'MLy_[kN-m]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)MLz_\[kN-m\]'  ] = sB+'MLz_[kN-m]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)FLx_\[kN\]'    ] = sB+'FLx_[kN]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)FLy_\[kN\]'    ] = sB+'FLy_[kN]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)FLz_\[kN\]'    ] = sB+'FLz_[kN]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)FLxNT_\[kN\]'  ] = sB+'FLxNT_[kN]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)FLyNT_\[kN\]'  ] = sB+'FLyNT_[kN]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)FlyNT_\[kN\]'  ] = sB+'FLyNT_[kN]'   # <<< Unfortunate
        EDSpanMap['^[A]*'+sB+r'N(\d*)MLxNT_\[kN-m\]'] = sB+'MLxNT_[kN-m]'
        EDSpanMap['^[A]*'+sB+r'N(\d*)MLyNT_\[kN-m\]'] = sB+'MLyNT_[kN-m]'
    # Old
    for sB in ['b1','b2','b3']:
        SB=sB.upper()
        EDSpanMap[r'^Spn(\d)ALx'+sB+r'_\[m/s^2\]']=SB+'ALx_[m/s^2]'
        EDSpanMap[r'^Spn(\d)ALy'+sB+r'_\[m/s^2\]']=SB+'ALy_[m/s^2]'
        EDSpanMap[r'^Spn(\d)ALz'+sB+r'_\[m/s^2\]']=SB+'ALz_[m/s^2]'
        EDSpanMap[r'^Spn(\d)TDx'+sB+r'_\[m\]'    ]=SB+'TDx_[m]'
        EDSpanMap[r'^Spn(\d)TDy'+sB+r'_\[m\]'    ]=SB+'TDy_[m]'
        EDSpanMap[r'^Spn(\d)TDz'+sB+r'_\[m\]'    ]=SB+'TDz_[m]'
        EDSpanMap[r'^Spn(\d)RDx'+sB+r'_\[deg\]'  ]=SB+'RDx_[deg]'
        EDSpanMap[r'^Spn(\d)RDy'+sB+r'_\[deg\]'  ]=SB+'RDy_[deg]'
        EDSpanMap[r'^Spn(\d)RDz'+sB+r'_\[deg\]'  ]=SB+'RDz_[deg]'
        EDSpanMap[r'^Spn(\d)FLx'+sB+r'_\[kN\]'   ]=SB+'FLx_[kN]'
        EDSpanMap[r'^Spn(\d)FLy'+sB+r'_\[kN\]'   ]=SB+'FLy_[kN]'
        EDSpanMap[r'^Spn(\d)FLz'+sB+r'_\[kN\]'   ]=SB+'FLz_[kN]'
        EDSpanMap[r'^Spn(\d)MLy'+sB+r'_\[kN-m\]' ]=SB+'MLx_[kN-m]'
        EDSpanMap[r'^Spn(\d)MLx'+sB+r'_\[kN-m\]' ]=SB+'MLy_[kN-m]'  
        EDSpanMap[r'^Spn(\d)MLz'+sB+r'_\[kN-m\]' ]=SB+'MLz_[kN-m]'
    return find_matching_columns(Cols, EDSpanMap)

def spanwiseColAD(Cols):
    """ Return column info, available columns and indices that contain AD spanwise data"""
    ADSpanMap=dict()
    for sB in ['B1','B2','B3']:
        ADSpanMap['^[A]*'+sB+r'N(\d*)Alpha_\[deg\]']=sB+'Alpha_[deg]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)AOA_\[deg\]'  ]=sB+'Alpha_[deg]' # DBGOuts
        ADSpanMap['^[A]*'+sB+r'N(\d*)AxInd_\[-\]'  ]=sB+'AxInd_[-]'  
        ADSpanMap['^[A]*'+sB+r'N(\d*)TnInd_\[-\]'  ]=sB+'TnInd_[-]'  
        ADSpanMap['^[A]*'+sB+r'N(\d*)AIn_\[deg\]'  ]=sB+'AxInd_[-]'   # DBGOuts NOTE BUG Unit
        ADSpanMap['^[A]*'+sB+r'N(\d*)ApI_\[deg\]'  ]=sB+'TnInd_[-]'   # DBGOuts NOTE BUG Unit
        ADSpanMap['^[A]*'+sB+r'N(\d*)AIn_\[-\]'    ]=sB+'AxInd_[-]'   # DBGOuts
        ADSpanMap['^[A]*'+sB+r'N(\d*)ApI_\[-\]'    ]=sB+'TnInd_[-]'   # DBGOuts
        ADSpanMap['^[A]*'+sB+r'N(\d*)Uin_\[m/s\]'  ]=sB+'Uin_[m/s]'     # DBGOuts
        ADSpanMap['^[A]*'+sB+r'N(\d*)Uit_\[m/s\]'  ]=sB+'Uit_[m/s]'     # DBGOuts
        ADSpanMap['^[A]*'+sB+r'N(\d*)Uir_\[m/s\]'  ]=sB+'Uir_[m/s]'     # DBGOuts
        ADSpanMap['^[A]*'+sB+r'N(\d*)Cl_\[-\]'     ]=sB+'Cl_[-]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Cd_\[-\]'     ]=sB+'Cd_[-]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Cm_\[-\]'     ]=sB+'Cm_[-]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Cx_\[-\]'     ]=sB+'Cx_[-]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Cy_\[-\]'     ]=sB+'Cy_[-]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Cn_\[-\]'     ]=sB+'Cn_[-]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Ct_\[-\]'     ]=sB+'Ct_[-]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Re_\[-\]'     ]=sB+'Re_[-]' 
        ADSpanMap['^[A]*'+sB+r'N(\d*)Vrel_\[m/s\]' ]=sB+'Vrel_[m/s]' 
        ADSpanMap['^[A]*'+sB+r'N(\d*)Theta_\[deg\]']=sB+'Theta_[deg]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Phi_\[deg\]'  ]=sB+'Phi_[deg]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Twst_\[deg\]' ]=sB+'Twst_[deg]' #DBGOuts
        ADSpanMap['^[A]*'+sB+r'N(\d*)Curve_\[deg\]']=sB+'Curve_[deg]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Vindx_\[m/s\]']=sB+'Vindx_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Vindy_\[m/s\]']=sB+'Vindy_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Fx_\[N/m\]'   ]=sB+'Fx_[N/m]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Fy_\[N/m\]'   ]=sB+'Fy_[N/m]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Fl_\[N/m\]'   ]=sB+'Fl_[N/m]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Fd_\[N/m\]'   ]=sB+'Fd_[N/m]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Fn_\[N/m\]'   ]=sB+'Fn_[N/m]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Ft_\[N/m\]'   ]=sB+'Ft_[N/m]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)VUndx_\[m/s\]']=sB+'VUndx_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)VUndy_\[m/s\]']=sB+'VUndy_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)VUndz_\[m/s\]']=sB+'VUndz_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)VDisx_\[m/s\]']=sB+'VDisx_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)VDisy_\[m/s\]']=sB+'VDisy_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)VDisz_\[m/s\]']=sB+'VDisz_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)STVx_\[m/s\]' ]=sB+'STVx_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)STVy_\[m/s\]' ]=sB+'STVy_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)STVz_\[m/s\]' ]=sB+'STVz_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Vx_\[m/s\]'   ]=sB+'Vx_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Vy_\[m/s\]'   ]=sB+'Vy_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)Vz_\[m/s\]'   ]=sB+'Vz_[m/s]'
        ADSpanMap['^[A]*'+sB+r'N(\d*)DynP_\[Pa\]'  ]=sB+'DynP_[Pa]' 
        ADSpanMap['^[A]*'+sB+r'N(\d*)M_\[-\]'      ]=sB+'M_[-]' 
        ADSpanMap['^[A]*'+sB+r'N(\d*)Mm_\[N-m/m\]' ]=sB+'Mm_[N-m/m]'   
        ADSpanMap['^[A]*'+sB+r'N(\d*)Gam_\['       ]=sB+'Gam_[m^2/s]' #DBGOuts
    # --- AD 14
    ADSpanMap[r'^Alpha(\d*)_\[deg\]'  ]='Alpha_[deg]'  
    ADSpanMap[r'^DynPres(\d*)_\[Pa\]' ]='DynPres_[Pa]' 
    ADSpanMap[r'^CLift(\d*)_\[-\]'    ]='CLift_[-]'    
    ADSpanMap[r'^CDrag(\d*)_\[-\]'    ]='CDrag_[-]'    
    ADSpanMap[r'^CNorm(\d*)_\[-\]'    ]='CNorm_[-]'    
    ADSpanMap[r'^CTang(\d*)_\[-\]'    ]='CTang_[-]'    
    ADSpanMap[r'^CMomt(\d*)_\[-\]'    ]='CMomt_[-]'    
    ADSpanMap[r'^Pitch(\d*)_\[deg\]'  ]='Pitch_[deg]'  
    ADSpanMap[r'^AxInd(\d*)_\[-\]'    ]='AxInd_[-]'    
    ADSpanMap[r'^TanInd(\d*)_\[-\]'   ]='TanInd_[-]'   
    ADSpanMap[r'^ForcN(\d*)_\[N\]'    ]='ForcN_[N]'    
    ADSpanMap[r'^ForcT(\d*)_\[N\]'    ]='ForcT_[N]'    
    ADSpanMap[r'^Pmomt(\d*)_\[N-m\]'  ]='Pmomt_[N-N]'  
    ADSpanMap[r'^ReNum(\d*)_\[x10^6\]']='ReNum_[x10^6]'
    ADSpanMap[r'^Gamma(\d*)_\[m^2/s\]']='Gamma_[m^2/s]'

    return find_matching_columns(Cols, ADSpanMap)

def insert_extra_columns_AD(dfRad, tsAvg, vr=None, rho=None, R=None, nB=None, chord=None):
    # --- Compute additional values (AD15 only)
    if dfRad is None:
        return None
    if dfRad.shape[1]==0:
        return dfRad
    if chord is not None:
        if vr is not None:
            chord =chord[0:len(dfRad)]
    for sB in ['B1','B2','B3']:
        try:
            vr_bar=vr/R
            Fx = dfRad[sB+'Fx_[N/m]']
            U0 = tsAvg['Wind1VelX_[m/s]']
            Ct=nB*Fx/(0.5 * rho * 2 * U0**2 * np.pi * vr)
            Ct[vr<0.01*R] = 0
            dfRad[sB+'Ctloc_[-]'] = Ct
            CT=2*np.trapz(vr_bar*Ct,vr_bar)
            dfRad[sB+'CtAvg_[-]']= CT*np.ones(vr.shape)
        except:
            pass
        try:
            dfRad[sB+'Gamma_[m^2/s]'] = 1/2 * chord*  dfRad[sB+'Vrel_[m/s]'] * dfRad[sB+'Cl_[-]'] 
        except:
            pass
        try: 
            if not sB+'Vindx_[m/s]' in dfRad.columns:
                dfRad[sB+'Vindx_[m/s]']= -dfRad[sB+'AxInd_[-]'].values * dfRad[sB+'Vx_[m/s]'].values 
                dfRad[sB+'Vindy_[m/s]']=  dfRad[sB+'TnInd_[-]'].values * dfRad[sB+'Vy_[m/s]'].values 
        except:
            pass
    return dfRad



def spanwisePostPro(FST_In=None,avgMethod='constantwindow',avgParam=5,out_ext='.outb',df=None):
    """
    Postprocess FAST radial data. Average the time series, return a dataframe nr x nColumns

    INPUTS:
        - FST_IN: Fast .fst input file
        - avgMethod='periods', avgParam=2:  average over 2 last periods, Needs Azimuth sensors!!!
        - avgMethod='constantwindow', avgParam=5:  average over 5s of simulation
        - postprofile: outputfile to write radial data
    """
    # --- Opens Fast output  and performs averaging
    if df is None:
        df = FASTOutputFile(FST_In.replace('.fst',out_ext).replace('.dvr',out_ext)).toDataFrame()
        returnDF=True
    else:
        returnDF=False
    # NOTE: spanwise script doest not support duplicate columns
    df = df.loc[:,~df.columns.duplicated()]
    dfAvg = averageDF(df,avgMethod=avgMethod ,avgParam=avgParam) # NOTE: average 5 last seconds

    # --- Extract info (e.g. radial positions) from Fast input file
    # We don't have a .fst input file, so we'll rely on some default values for "r"
    rho         = 1.225
    chord       = None
    # --- Extract radial positions of output channels
    r_AD, r_ED, r_BD, IR_AD, IR_ED, IR_BD, R, r_hub, fst = FASTRadialOutputs(FST_In, OutputCols=df.columns.values)
    if R is None: 
        R=1
    try:
        chord  = fst.AD.Bld1['BldAeroNodes'][:,5] # Full span
    except:
        pass
    try:
        rho = fst.AD['Rho']
    except:
        try:
            rho = fst.AD['AirDens']
        except:
            pass
    #print('r_AD:', r_AD)
    #print('r_ED:', r_ED)
    #print('r_BD:', r_BD)
    #print('I_AD:', IR_AD)
    #print('I_ED:', IR_ED)
    #print('I_BD:', IR_BD)
    # --- Extract radial data and export to csv if needed
    dfRad_AD    = None
    dfRad_ED    = None
    dfRad_BD    = None
    Cols=dfAvg.columns.values
    # --- AD
    ColsInfoAD, nrMaxAD = spanwiseColAD(Cols)
    dfRad_AD            = extract_spanwise_data(ColsInfoAD, nrMaxAD, df=None, ts=dfAvg.iloc[0])
    dfRad_AD            = insert_extra_columns_AD(dfRad_AD, dfAvg.iloc[0], vr=r_AD, rho=rho, R=R, nB=3, chord=chord)
    dfRad_AD            = insert_radial_columns(dfRad_AD, r_AD, R=R, IR=IR_AD)
    # --- ED
    ColsInfoED, nrMaxED = spanwiseColED(Cols)
    dfRad_ED            = extract_spanwise_data(ColsInfoED, nrMaxED, df=None, ts=dfAvg.iloc[0])
    dfRad_ED            = insert_radial_columns(dfRad_ED, r_ED, R=R, IR=IR_ED)
    # --- BD
    ColsInfoBD, nrMaxBD = spanwiseColBD(Cols)
    dfRad_BD            = extract_spanwise_data(ColsInfoBD, nrMaxBD, df=None, ts=dfAvg.iloc[0])
    dfRad_BD            = insert_radial_columns(dfRad_BD, r_BD, R=R, IR=IR_BD)
    if returnDF:
        return dfRad_ED , dfRad_AD, dfRad_BD, df
    else:
        return dfRad_ED , dfRad_AD, dfRad_BD



def spanwisePostProRows(df, FST_In=None):
    """ 
    Returns a 3D matrix: n x nSpan x nColumn where df is of size n x mColumn

    NOTE: this is really not optimal. Spanwise columns should be extracted only once..
    """
    # --- Extract info (e.g. radial positions) from Fast input file
    # We don't have a .fst input file, so we'll rely on some default values for "r"
    rho         = 1.225
    chord       = None
    # --- Extract radial positions of output channels
    r_AD, r_ED, r_BD, IR_AD, IR_ED, IR_BD, R, r_hub, fst = FASTRadialOutputs(FST_In, OutputCols=df.columns.values)
    #print('r_AD:', r_AD)
    #print('r_ED:', r_ED)
    #print('r_BD:', r_BD)
    if R is None: 
        R=1
    try:
        chord  = fst.AD.Bld1['BldAeroNodes'][:,5] # Full span
    except:
        pass
    try:
        rho = fst.AD['Rho']
    except:
        try:
            rho = fst.AD['AirDens']
        except:
            print('[WARN] Using default air density (1.225)')
            pass
    # --- Extract radial data for each azimuthal average
    M_AD=None
    M_ED=None
    M_BD=None
    Col_AD=None
    Col_ED=None
    Col_BD=None
    v = df.index.values

    # --- Getting Column info
    Cols=df.columns.values
    if r_AD is not None:
        ColsInfoAD, nrMaxAD = spanwiseColAD(Cols)
    if r_ED is not None:
        ColsInfoED, nrMaxED = spanwiseColED(Cols)
    if r_BD is not None:
        ColsInfoBD, nrMaxBD = spanwiseColBD(Cols)
    for i,val in enumerate(v):
        if r_AD is not None:
            dfRad_AD = extract_spanwise_data(ColsInfoAD, nrMaxAD, df=None, ts=df.iloc[i])
            dfRad_AD = insert_extra_columns_AD(dfRad_AD, df.iloc[i], vr=r_AD, rho=rho, R=R, nB=3, chord=chord)
            dfRad_AD = insert_radial_columns(dfRad_AD, r_AD, R=R, IR=IR_AD)
            if i==0:
                M_AD = np.zeros((len(v), len(dfRad_AD), len(dfRad_AD.columns)))
                Col_AD=dfRad_AD.columns.values
            M_AD[i, :, : ] = dfRad_AD.values
        if r_ED is not None and len(r_ED)>0:
            dfRad_ED = extract_spanwise_data(ColsInfoED, nrMaxED, df=None, ts=df.iloc[i])
            dfRad_ED = insert_radial_columns(dfRad_ED, r_ED, R=R, IR=IR_ED)
            if i==0:
                M_ED = np.zeros((len(v), len(dfRad_ED), len(dfRad_ED.columns)))
                Col_ED=dfRad_ED.columns.values
            M_ED[i, :, : ] = dfRad_ED.values
        if r_BD is not None and len(r_BD)>0:
            dfRad_BD = extract_spanwise_data(ColsInfoBD, nrMaxBD, df=None, ts=df.iloc[i])
            dfRad_BD = insert_radial_columns(dfRad_BD, r_BD, R=R, IR=IR_BD)
            if i==0:
                M_BD = np.zeros((len(v), len(dfRad_BD), len(dfRad_BD.columns)))
                Col_BD=dfRad_BD.columns.values
            M_BD[i, :, : ] = dfRad_BD.values
    return M_AD, Col_AD, M_ED, Col_ED, M_BD, Col_BD


def FASTRadialOutputs(FST_In, OutputCols=None):
    """ Returns radial positions where FAST has outputs
    INPUTS:
       FST_In: fast input file (.fst)
    OUTPUTS:
       r_AD: radial positions of FAST Outputs from the rotor center
    """
    R           = None
    r_hub =0
    r_AD        = None 
    r_ED        = None
    r_BD        = None
    IR_ED       = None
    IR_AD       = None
    IR_BD       = None
    fst=None
    if FST_In is not None:
        fst = FASTInputDeck(FST_In, readlist=['AD','ADbld','ED','BD','BDbld'])
        # NOTE: all this below should be in FASTInputDeck
        if fst.version == 'F7':
            # --- FAST7
            if  not hasattr(fst,'AD'):
                raise Exception('The AeroDyn file couldn''t be found or read, from main file: '+FST_In)
            r_AD,IR_AD = AD14_BldGag(fst.AD)
            R   = fst.fst['TipRad']
            try:
                rho = fst.AD['Rho']
            except:
                rho = fst.AD['AirDens']
        else:
            # --- OpenFAST 2
            R = None

            # --- ElastoDyn
            if 'NumTurbines' in fst.fst.keys():
                # AeroDyn driver...
                if 'HubRad(1)' in fst.fst.keys():
                    r_hub       = fst.fst['HubRad(1)']
                else:
                    r_hub       = fst.fst['BldHubRad_bl(1_1)']

            elif  not hasattr(fst,'ED'):
                print('[WARN] The Elastodyn file couldn''t be found or read, from main file: '+FST_In)
                #raise Exception('The Elastodyn file couldn''t be found or read, from main file: '+FST_In)
            else:
                R           = fst.ED['TipRad']
                r_hub       = fst.ED['HubRad']
                if fst.ED.hasNodal:
                    _, r_ED = ED_BldStations(fst.ED)
                    IR_ED =None
                else:
                    r_ED, IR_ED = ED_BldGag(fst.ED)

            # --- BeamDyn
            if  fst.BD is not None:
                if R is None:
                    R = r_BD_All[-1] # just in case ED file missing
                if fst.BD.hasNodal:
                    r_BD = BD_BldStations(fst.BD, fst.BDbld)
                else:
                    r_BD, IR_BD, r_BD_All = BD_BldGag(fst.BD)
                r_BD= r_BD+r_hub

            # --- AeroDyn
            if  fst.AD is None:
                print('[WARN] The AeroDyn file couldn''t be found or read, from main file: '+FST_In)
                #raise Exception('The AeroDyn file couldn''t be found or read, from main file: '+FST_In)
            else:
                if fst.ADversion == 'AD15':
                    if  fst.AD.Bld1 is None:
                        raise Exception('The AeroDyn blade file couldn''t be found or read, from main file: '+FST_In)
                    
                    if 'B1N001Cl_[-]' in OutputCols or np.any(np.char.find(list(OutputCols),'AB1N')==0):
                        # This was compiled with all outs
                        r_AD   = fst.AD.Bld1['BldAeroNodes'][:,0] # Full span
                        r_AD   += r_hub
                        IR_AD  = None
                    else:
                        r_AD,_ = AD_BldGag(fst.AD,fst.AD.Bld1, chordOut = True) # Only at Gages locations
                        r_AD   += r_hub

                    if R is None:
                        # ElastoDyn was not read, we use R from AD
                        R = fst.AD.Bld1['BldAeroNodes'][-1,0]

                elif fst.ADversion == 'AD14':
                    r_AD,IR_AD = AD14_BldGag(fst.AD)

                else:
                    raise Exception('AeroDyn version unknown')
    return r_AD, r_ED, r_BD, IR_AD, IR_ED, IR_BD, R, r_hub, fst



def addToOutlist(OutList, Signals):
    if not isinstance(Signals,list):
        raise Exception('Signals must be a list')
    for s in Signals:
        ss=s.split()[0].strip().strip('"').strip('\'')
        AlreadyIn = any([o.find(ss)==1 for o in OutList ])
        if not AlreadyIn:
            OutList.append(s)
    return OutList



# --------------------------------------------------------------------------------}
# --- Generic df 
# --------------------------------------------------------------------------------{
def remap_df(df, ColMap, bColKeepNewOnly=False, inPlace=False, dataDict=None, verbose=False):
    """ Add/rename columns of a dataframe, potentially perform operations between columns

    dataDict: dicitonary of data to be made available as "variable" in the column mapping

    Example:

        ColumnMap={
          'WS_[m/s]'         : '{Wind1VelX_[m/s]}'             , # create a new column from existing one
          'RtTSR_[-]'        : '{RtTSR_[-]} * 2  +  {RtAeroCt_[-]}'    , # change value of column
          'RotSpeed_[rad/s]' : '{RotSpeed_[rpm]} * 2*np.pi/60 ', # new column [rpm] -> [rad/s]
        }
        # Read
        df = weio.read('FASTOutBin.outb').toDataFrame()
        # Change columns based on formulae, potentially adding new columns
        df = fastlib.remap_df(df, ColumnMap, inplace=True)

    """
    # Insert dataDict into namespace
    if dataDict is not None:
        for k,v in dataDict.items():
            exec('{:s} = dataDict["{:s}"]'.format(k,k))


    if not inPlace:
        df=df.copy()
    ColMapMiss=[]
    ColNew=[]
    RenameMap=dict()
    # Loop for expressions
    for k0,v in ColMap.items():
        k=k0.strip()
        v=v.strip()
        if v.find('{')>=0:
            search_results = re.finditer(r'\{.*?\}', v)
            expr=v
            if verbose:
                print('Attempt to insert column {:15s} with expr {}'.format(k,v))
            # For more advanced operations, we use an eval
            bFail=False
            for item in search_results:
                col=item.group(0)[1:-1]
                if col not in df.columns:
                    ColMapMiss.append(col)
                    bFail=True
                expr=expr.replace(item.group(0),'df[\''+col+'\']')
            #print(k0, '=', expr)
            if not bFail:
                df[k]=eval(expr)
                ColNew.append(k)
            else:
                print('[WARN] Column not present in dataframe, cannot evaluate: ',expr)
        else:
            #print(k0,'=',v)
            if v not in df.columns:
                ColMapMiss.append(v)
                print('[WARN] Column not present in dataframe: ',v)
            else:
                RenameMap[k]=v

    # Applying renaming only now so that expressions may be applied in any order
    for k,v in RenameMap.items():
        if verbose:
            print('Renaming column {:15s} > {}'.format(v,k))
        k=k.strip()
        iCol = list(df.columns).index(v)
        df.columns.values[iCol]=k
        ColNew.append(k)
    df.columns = df.columns.values # Hack to ensure columns are updated

    if len(ColMapMiss)>0:
        print('[FAIL] The following columns were not found in the dataframe:',ColMapMiss)
        #print('Available columns are:',df.columns.values)

    if bColKeepNewOnly:
        ColNew = [c for c,_ in ColMap.items() if c in ColNew]# Making sure we respec order from user
        ColKeepSafe = [c for c in ColNew if c in df.columns.values]
        ColKeepMiss = [c for c in ColNew if c not in df.columns.values]
        if len(ColKeepMiss)>0:
            print('[WARN] Signals missing and omitted for ColKeep:\n       '+'\n       '.join(ColKeepMiss))
        df=df[ColKeepSafe]
    return df


# --------------------------------------------------------------------------------}
# --- Tools for PostProcessing one or several simulations
# --------------------------------------------------------------------------------{
def _zero_crossings(y,x=None,direction=None):
    """
      Find zero-crossing points in a discrete vector, using linear interpolation.
      direction: 'up' or 'down', to select only up-crossings or down-crossings
      Returns: 
          x values xzc such that y(yzc)==0
          indexes izc, such that the zero is between y[izc] (excluded) and y[izc+1] (included)
      if direction is not provided, also returns:
              sign, equal to 1 for up crossing
    """
    y=np.asarray(y)
    if x is None:
        x=np.arange(len(y))

    if np.any((x[1:] - x[0:-1]) <= 0.0):
        raise Exception('x values need to be in ascending order')

    # Indices before zero-crossing
    iBef = np.where(y[1:]*y[0:-1] < 0.0)[0]
    
    # Find the zero crossing by linear interpolation
    xzc = x[iBef] - y[iBef] * (x[iBef+1] - x[iBef]) / (y[iBef+1] - y[iBef])
    
    # Selecting points that are exactly 0 and where neighbor change sign
    iZero = np.where(y == 0.0)[0]
    iZero = iZero[np.where((iZero > 0) & (iZero < x.size-1))]
    iZero = iZero[np.where(y[iZero-1]*y[iZero+1] < 0.0)]

    # Concatenate 
    xzc  = np.concatenate((xzc, x[iZero]))
    iBef = np.concatenate((iBef, iZero))

    # Sort
    iSort = np.argsort(xzc)
    xzc, iBef = xzc[iSort], iBef[iSort]

    # Return up-crossing, down crossing or both
    sign = np.sign(y[iBef+1]-y[iBef])
    if direction == 'up':
        I= np.where(sign==1)[0]
        return xzc[I],iBef[I]
    elif direction == 'down':
        I= np.where(sign==-1)[0]
        return xzc[I],iBef[I]
    elif direction is not None:
        raise Exception('Direction should be either `up` or `down`')
    return xzc, iBef, sign

def find_matching_pattern(List, pattern, sort=False, integers=True):
    r""" Return elements of a list of strings that match a pattern
        and return the first matching group

    Example:

        find_matching_pattern(['Misc','TxN1_[m]', 'TxN20_[m]'], 'TxN(\d+)_\[m\]')
        returns: Matches = 1,20
    """
    reg_pattern=re.compile(pattern)
    MatchedElements=[]
    Matches=[]
    for l in List:
        match=reg_pattern.search(l)
        if match:
            MatchedElements.append(l)
            if len(match.groups(1))>0:
                Matches.append(match.groups(1)[0])
            else:
                Matches.append('')

    MatchedElements = np.asarray(MatchedElements)
    Matches         = np.asarray(Matches)

    if integers:
        Matches  = Matches.astype(int)

    if sort:
        # Sorting by Matched string, NOTE: assumes that MatchedStrings are int.
        # that's probably not necessary since alphabetical/integer sorting should be the same
        # but it might be useful if number of leading zero differs, which would skew the sorting..
        Isort = np.argsort(Matches)
        MatchedElements = MatchedElements[Isort]
        Matches         = Matches[Isort]

    return MatchedElements, Matches

        
def extractSpanTS(df, pattern):
    r"""
    Extract spanwise time series of a given "type" (e.g. Cl for each radial node)
    Return a dataframe of size nt x nr 

    NOTE: time is not inserted in the output dataframe 

    To find "r" use FASTRadialOutputs, it is different for AeroDyn/ElastoDyn/BeamDyn/
    There is no guarantee that the number of columns matching pattern will exactly
    corresponds to the number of radial stations. That's the responsability of the 
    OpenFAST user.

    INPUTS:
     - df : a dataframe of size nt x nColumns
     - pattern: Pattern used to find "radial" columns amongst the dataframe columns
            r'B1N(\d*)Cl_\[-\]'
            r'^AB1N(\d*)Cl_\[-\]' -> to match AB1N001Cl_[-], AB1N002Cl_[-], etc.
     OUTPUTS:
     - dfOut : a dataframe of size nt x nr where nr is the number of radial stations matching the pattern. The radial stations are sorted.
    """
    cols, sIdx = find_matching_pattern(df.columns, pattern, sort=True)
    return df[cols]
    

def _extractSpanTSReg_Legacy(ts, col_pattern, colname, IR=None):
    r""" Helper function to extract spanwise results, like B1N1Cl B1N2Cl etc. 

    Example
        col_pattern: r'B1N(\d*)Cl_\[-\]'
        colname    : r'B1Cl_[-]'
    """
    # Extracting columns matching pattern
    cols, sIdx = find_matching_pattern(ts.keys(), col_pattern, sort=True)
    if len(cols) ==0:
        return (None,None)

    nrMax =  np.max(Idx)
    Values = np.zeros((nrMax,1))
    Values[:] = np.nan
#     if IR is None:
#         cols   = [col_pattern.format(ir+1) for ir in range(nr)]
#     else:
#         cols   = [col_pattern.format(ir) for ir in IR]
    for idx,col in zip(Idx,cols):
        Values[idx-1]=ts[col]
    nMissing = np.sum(np.isnan(Values))
    if nMissing==nrMax:
        return (None,None)
    if len(cols)<nrMax:
        #print(Values)
        print('[WARN] Not all values found for {}, missing {}/{}'.format(colname,nMissing,nrMax))
    if len(cols)>nrMax:
        print('[WARN] More values found for {}, found {}/{}'.format(colname,len(cols),nrMax))
    return (colname,Values)

def _extractSpanTS_Legacy(ts, nr, col_pattern, colname, IR=None):
    """ Helper function to extract spanwise results, like B1N1Cl B1N2Cl etc. 

    Example
        col_pattern: 'B1N{:d}Cl_[-]'
        colname    : 'B1Cl_[-]'
    """
    Values=np.zeros((nr,1))
    if IR is None:
        cols   = [col_pattern.format(ir+1) for ir in range(nr)]
    else:
        cols   = [col_pattern.format(ir) for ir in IR]
    colsExist  = [c for c in cols if c in ts.keys() ]
    if len(colsExist)==0:
        return (None,None)

    Values = [ts[c] if c in ts.keys() else np.nan for c in cols  ]
    nMissing = np.sum(np.isnan(Values))
    #Values = ts[cols].T
    #nCoun=len(Values)
    if nMissing==nr:
        return (None,None)
    if len(colsExist)<nr:
        print(Values)
        print('[WARN] Not all values found for {}, missing {}/{}'.format(colname,nMissing,nr))
    if len(colsExist)>nr:
        print('[WARN] More values found for {}, found {}/{}'.format(colname,len(cols),nr))
    return (colname,Values)

def radialInterpTS(df, r, varName, r_ref, blade=1, bldFmt='AB{:d}', ndFmt='N{:03d}', method='interp'):
    """ 
    Interpolate a time series at a given radial position for a given variable (varName)
    INPUTS:
     - df     : a dataframe (typically with OpenFAST time series)
     - r      : radial positions of node where data is to be interpolated
     - varName: variable name (and unit) to be interpolated. 
                The dataframe column will be assumed to be "BldFmt"+"ndFmt"+varName
     - r_ref  : radial position of nodal data present in the dataframe
     - bldFmt : format for blade number, e.g. 'B{:d}' or 'AB{:d}'
     - ndFmt  : format for node number, e.g.  'N{:d}' or 'N{:03d}'
    OUTPUT:
      - interpolated time series
    """
    # --- Sanity checks
    r_ref = np.asarray(r_ref)
    if not np.all(r_ref[:-1] <= r_ref[1:]):
        raise Exception('This function only works for ascending radial values')

    # No extrapolation
    if r<np.min(r_ref) or r>np.max(r_ref):
        raise Exception('Extrapolation not supported')

    # Exactly on first or last nodes
    if r==r_ref[0]:
        col=bldFmt.format(blade) + ndFmt.format(1) + varName
        if col in df.columns.values:
            return df[col]
        else:
            raise Exception('Column {} not found in dataframe'.format(col))
    elif r==r_ref[-1]:
        col=bldFmt.format(blade) + ndFmt.format(len(r_ref)+1) + varName
        if col in df.columns.values:
            return df[col]
        else:
            raise Exception('Column {} not found in dataframe'.format(col))

    if method=='interp':
        # Interpolation
        iBef = np.where(r_ref<r)[0][-1]
        iAft = iBef+1
        #print(r_ref[iBef], r,  r_ref[iAft], '          ',iBef+1, iAft+1)
        fact= np.interp(r, r_ref[iBef:iAft+1], [0,1])
        col=bldFmt.format(blade) + ndFmt.format(iBef+1) + varName
        if col in df.columns.values:
            bef=df[bldFmt.format(blade) + ndFmt.format(iBef+1) + varName]
            aft=df[bldFmt.format(blade) + ndFmt.format(iAft+1) + varName]
        else:
            raise Exception('Column {} not found in dataframe'.format(col))
        return bef*(1-fact) + aft*fact
    else: 
        raise NotImplementedError()



def bin_mean_DF(df, xbins, colBin ):
    """ 
    Perform bin averaging of a dataframe
    """
    if colBin not in df.columns.values:
        raise Exception('The column `{}` does not appear to be in the dataframe'.format(colBin))
    xmid      = (xbins[:-1]+xbins[1:])/2
    df['Bin'] = pd.cut(df[colBin], bins=xbins, labels=xmid ) # Adding a column that has bin attribute
    df2       = df.groupby('Bin').mean()                     # Average by bin
    # also counting
    df['Counts'] = 1
    dfCount=df[['Counts','Bin']].groupby('Bin').sum()
    df2['Counts'] = dfCount['Counts']
    # Just in case some bins are missing (will be nan)
    df2       = df2.reindex(xmid)
    return df2

def azimuthal_average_DF(df, psiBin=None, colPsi='Azimuth_[deg]', tStart=None, colTime='Time_[s]'):
    """ 
    Average a dataframe based on azimuthal value
    Returns a dataframe with same amount of columns as input, and azimuthal values as index
    """
    if psiBin is None: 
        psiBin = np.arange(0,360+1,10)

    if tStart is not None:
        if colTime not in df.columns.values:
            raise Exception('The column `{}` does not appear to be in the dataframe'.format(colTime))
        df=df[ df[colTime]>tStart].copy()

    dfPsi= bin_mean_DF(df, psiBin, colPsi)
    if np.any(dfPsi['Counts']<1):
        print('[WARN] some bins have no data! Increase the bin size.')

    return dfPsi


def averageDF(df,avgMethod='periods',avgParam=None,ColMap=None,ColKeep=None,ColSort=None,stats=['mean']):
    """
    See average PostPro for documentation, same interface, just does it for one dataframe
    """
    def renameCol(x):
        for k,v in ColMap.items():
            if x==v:
                return k
        return x
    # Before doing the colomn map we store the time
    time = df['Time_[s]'].values
    timenoNA = time[~np.isnan(time)]
    # Column mapping
    if ColMap is not None:
        ColMapMiss = [v for _,v in ColMap.items() if v not in df.columns.values]
        if len(ColMapMiss)>0:
            print('[WARN] Signals missing and omitted for ColMap:\n       '+'\n       '.join(ColMapMiss))
        df.rename(columns=renameCol,inplace=True)
    ## Defining a window for stats (start time and end time)
    if avgMethod.lower()=='constantwindow':
        tEnd = timenoNA[-1]
        if avgParam is None:
            tStart=timenoNA[0]
        else:
            tStart =tEnd-avgParam
    elif avgMethod.lower()=='periods':
        # --- Using azimuth to find periods
        if 'Azimuth_[deg]' not in df.columns:
            raise Exception('The sensor `Azimuth_[deg]` does not appear to be in the output file. You cannot use the averaging method by `periods`, use `constantwindow` instead.')
        # NOTE: potentially we could average over each period and then average
        psi=df['Azimuth_[deg]'].values
        _,iBef = _zero_crossings(psi-psi[-10],direction='up')
        if len(iBef)==0:
            _,iBef = _zero_crossings(psi-180,direction='up')
        if len(iBef)==0:
            print('[WARN] Not able to find a zero crossing!')
            tEnd = time[-1]
            iBef=[0]
        else:
            tEnd = time[iBef[-1]]

        if avgParam is None:
            tStart=time[iBef[0]]
        else:
            avgParam=int(avgParam) 
            if len(iBef)-1<avgParam:
                print('[WARN] Not enough periods found ({}) compared to number requested to average ({})!'.format(len(iBef)-1,avgParam))
                avgParam=len(iBef)-1
            if avgParam==0:
                tStart = time[0]
                tEnd   = time[-1]
            else:
                tStart=time[iBef[-1-avgParam]]
    elif avgMethod.lower()=='periods_omega':
        # --- Using average omega to find periods
        if 'RotSpeed_[rpm]' not in df.columns:
            raise Exception('The sensor `RotSpeed_[rpm]` does not appear to be in the output file. You cannot use the averaging method by `periods_omega`, use `periods` or `constantwindow` instead.')
        Omega=df['RotSpeed_[rpm]'].mean()/60*2*np.pi
        Period = 2*np.pi/Omega 
        if avgParam is None:
            nRotations=np.floor(tEnd/Period)
        else:
            nRotations=avgParam
        tStart =tEnd-Period*nRotations
    else:
        raise Exception('Unknown averaging method {}'.format(avgMethod))
    # Narrowind number of columns here (azimuth needed above)
    if ColKeep is not None:
        ColKeepSafe = [c for c in ColKeep if c in df.columns.values]
        ColKeepMiss = [c for c in ColKeep if c not in df.columns.values]
        if len(ColKeepMiss)>0:
            print('[WARN] Signals missing and omitted for ColKeep:\n       '+'\n       '.join(ColKeepMiss))
        df=df[ColKeepSafe]
    if tStart<time[0]:
        print('[WARN] Simulation time ({}) too short compared to required averaging window ({})!'.format(tEnd-time[0],tStart-tEnd))
    IWindow    = np.where((time>=tStart) & (time<=tEnd) & (~np.isnan(time)))[0]
    iEnd   = IWindow[-1]
    iStart = IWindow[0]
    ## Absolute and relative differences at window extremities
    DeltaValuesAbs=(df.iloc[iEnd]-df.iloc[iStart]).abs()
#         DeltaValuesRel=(df.iloc[iEnd]-df.iloc[iStart]).abs()/df.iloc[iEnd]
    DeltaValuesRel=(df.iloc[IWindow].max()-df.iloc[IWindow].min())/df.iloc[IWindow].mean()
    #EndValues=df.iloc[iEnd]
    #if avgMethod.lower()=='periods_omega':
    #    if DeltaValuesRel['RotSpeed_[rpm]']*100>5:
    #        print('[WARN] Rotational speed vary more than 5% in averaging window ({}%) for simulation: {}'.format(DeltaValuesRel['RotSpeed_[rpm]']*100,f))
    ## Stats values during window
    # MeanValues = df[IWindow].mean()
    # StdValues  = df[IWindow].std()
    if 'mean' in stats:
        MeanValues = pd.DataFrame(df.iloc[IWindow].mean()).transpose()
    else:
        raise NotImplementedError()
    return MeanValues



def averagePostPro(outFiles,avgMethod='periods',avgParam=None,ColMap=None,ColKeep=None,ColSort=None,stats=['mean']):
    """ Opens a list of FAST output files, perform average of its signals and return a panda dataframe
    For now, the scripts only computes the mean within a time window which may be a constant or a time that is a function of the rotational speed (see `avgMethod`).
    The script only computes the mean for now. Other stats will be added

    `ColMap` :  dictionary where the key is the new column name, and v the old column name.
                Default: None, output is not sorted
                NOTE: the mapping is done before sorting and `ColKeep` is applied
                ColMap = {'WS':Wind1VelX_[m/s], 'RPM': 'RotSpeed_[rpm]'}
    `ColKeep` : List of strings corresponding to the signals to analyse. 
                Default: None, all columns are analysed
                Example: ColKeep=['RotSpeed_[rpm]','BldPitch1_[deg]','RtAeroCp_[-]']
                     or: ColKeep=list(ColMap.keys())
    `avgMethod` : string defining the method used to determine the extent of the averaging window:
                - 'periods': use a number of periods(`avgParam`), determined by the azimuth. 
                - 'periods_omega': use a number of periods(`avgParam`), determined by the mean RPM
                - 'constantwindow': the averaging window is constant (defined by `avgParam`).
    `avgParam`: based on `avgMethod` it is either
                - for 'periods_*': the number of revolutions for the window. 
                   Default: None, as many period as possible are used
                - for 'constantwindow': the number of seconds for the window
                   Default: None, full simulation length is used
    """
    result=None
    invalidFiles =[]
    # Loop trough files and populate result
    for i,f in enumerate(outFiles):
        try:
            df=weio.read(f).toDataFrame()
            #df=FASTOutputFile(f).toDataFrame()A # For pyFAST
        except:
            invalidFiles.append(f)
            continue
        postpro=averageDF(df, avgMethod=avgMethod, avgParam=avgParam, ColMap=ColMap, ColKeep=ColKeep,ColSort=ColSort,stats=stats)
        MeanValues=postpro # todo
        if result is None:
            # We create a dataframe here, now that we know the colums
            columns = MeanValues.columns
            result = pd.DataFrame(np.nan, index=np.arange(len(outFiles)), columns=columns)
        result.iloc[i,:] = MeanValues.copy().values

    if ColSort is not None:
        # Sorting 
        result.sort_values([ColSort],inplace=True,ascending=True)
        result.reset_index(drop=True,inplace=True) 

    if len(invalidFiles)==len(outFiles):
        raise Exception('None of the files can be read (or exist)!')
    elif len(invalidFiles)>0:
        print('[WARN] There were {} missing/invalid files: {}'.format(len(invalidFiles),invalidFiles))


    return result 


def integrateMoment(r, F):
    """ 
    Integrate moment from force and radial station
        M_j =  \int_{r_j}^(r_n) f(r) * (r-r_j) dr  for j=1,nr
    TODO: integrate analytically the "r" part
    """
    M = np.zeros(len(r)-1)
    for ir,_ in enumerate(r[:-1]):
        M[ir] = np.trapz(F[ir:]*(r[ir:]-r[ir]), r[ir:]-r[ir])
    return M

def integrateMomentTS(r, F):
    """
    Integrate moment from time series of forces at nr radial stations

    Compute 
        M_j =  \int_{r_j}^(r_n) f(r) * (r-r_j) dr  for j=1,nr
        M_j =  \int_{r_j}^(r_n) f(r) *r*dr  - r_j * \int_(r_j}^{r_n} f(r) dr
      j are the columns of M

    NOTE: simply trapezoidal integration is used. 
    The "r" term is not integrated analytically. This can be improved!

    INPUTS:
      - r: array of size nr, of radial stations (ordered)
      - F: array nt x nr of time series of forces at each radial stations
    OUTPUTS:
      - M: array nt x nr of integrated moment at each radial station

    """
    import scipy.integrate as si
    # Compute \int_{r_j}^{r_n} f(r) dr, with "j" each column 
    IF = np.fliplr(-si.cumtrapz(np.fliplr(F), r[-1::-1]))
    # Compute \int_{r_j}^{r_n} f(r)*r dr, with "j" each column 
    FR  = F * r 
    IFR = np.fliplr(-si.cumtrapz(np.fliplr(FR), r[-1::-1]))
    # Compute x_j * \int_{r_j}^(r_n) f(r) * r dr
    R_IF = IF * r[:-1]
    # \int_{r_j}^(r_n) f(r) * (r-r_j) dr  = IF + IFR
    M = IFR - R_IF


    # --- Sanity checks
    M0  = integrateMoment(r, F[0,:])
    Mm1 = integrateMoment(r, F[-1,:])
    if np.max(np.abs(M0-M[0,:]))>1e-8:
        raise Exception('>>> Inaccuracies in integrateMomentTS')
    if np.max(np.abs(Mm1-M[-1,:]))>1e-8:
        raise Exception('>>> Inaccuracies in integrateMomentTS')

    return M

if __name__ == '__main__':
    main()
