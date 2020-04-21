
# --- For cmd.py
from __future__ import division, print_function
import os
import subprocess
import multiprocessing

import collections
import glob
import pandas as pd
import numpy as np
import distutils.dir_util
import shutil 
import stat
import re

# --- External library for io
try:
    import weio
except:
    try:
        import welib.weio as weio
        print('Using `weio` from `welib`')
    except:
        raise Exception('Fastlib needs the package `weio` to be installed from https://github.com/ebranlard/weio/`')
    


FAST_EXE='openfast'

# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
def createStepWind(filename,WSstep=1,WSmin=3,WSmax=25,tstep=100,dt=0.5,tmin=0,tmax=999):
    f = weio.FASTWndFile()
    Steps= np.arange(WSmin,WSmax+WSstep,WSstep)
    print(Steps)
    nCol = len(f.colNames)
    nRow = len(Steps)*2
    M = np.zeros((nRow,nCol));
    M[0,0] = tmin
    M[0,1] = WSmin
    for i,s in enumerate(Steps[:-1]):
        M[2*i+1,0] = tmin + (i+1)*tstep-dt 
        M[2*i+2,0] = tmin + (i+1)*tstep
        M[2*i+1,1] = Steps[i]
        if i<len(Steps)-1:
            M[2*i+2,1] = Steps[i+1]
        else:
            M[2*i+2,1] = Steps[-1]
    M[-1,0]= max(tmax, (len(Steps)+1)*tstep)
    M[-1,1]= WSmax
    f.data=pd.DataFrame(data=M,columns=f.colNames)
    #
    print(f.data)
    f.write(filename)
    #plt.plot(M[:,0],M[:,1])
    #plt.show()

    #print(f.toDataFrame())
    #pass
#createStepWind('test.wnd',tstep=200,WSmax=28)
# createStepWind('test.wnd',tstep=200,WSmin=5,WSmax=7,WSstep=2)


# --------------------------------------------------------------------------------}
# --- Tools for executing FAST
# --------------------------------------------------------------------------------{
# --- START cmd.py
def run_cmds(inputfiles, exe, parallel=True, ShowOutputs=True, nCores=None, ShowCommand=True): 
    """ Run a set of simple commands of the form `exe input_file`
    By default, the commands are run in "parallel" (though the method needs to be improved)
    The stdout and stderr may be displayed on screen (`ShowOutputs`) or hidden. 
    A better handling is yet required.
    """
    Failed=[]
    def _report(p):
        if p.returncode==0:
            print('[ OK ] Input    : ',p.input_file)
        else:
            Failed.append(p)
            print('[FAIL] Input    : ',p.input_file)
            print('       Directory: '+os.getcwd())
            print('       Command  : '+p.cmd)
            print('       Use `ShowOutputs=True` to debug, or run the command above.')
            #out, err = p.communicate()
            #print('StdOut:\n'+out)
            #print('StdErr:\n'+err)
    ps=[]
    iProcess=0
    if nCores is None:
        nCores=multiprocessing.cpu_count()
    if nCores<0:
        nCores=len(inputfiles)+1
    for i,f in enumerate(inputfiles):
        #print('Process {}/{}: {}'.format(i+1,len(inputfiles),f))
        ps.append(run_cmd(f, exe, wait=(not parallel), ShowOutputs=ShowOutputs, ShowCommand=ShowCommand))
        iProcess += 1
        # waiting once we've filled the number of cores
        # TODO: smarter method with proper queue, here processes are run by chunks
        if parallel:
            if iProcess==nCores:
                for p in ps:
                    p.wait()
                for p in ps:
                    _report(p)
                ps=[]
                iProcess=0
    # Extra process if not multiptle of nCores (TODO, smarter method)
    for p in ps:
        p.wait()
    for p in ps:
        _report(p)
    # --- Giving a summary
    if len(Failed)==0:
        print('[ OK ] All simulations run successfully.')
        return True
    else:
        print('[FAIL] {}/{} simulations failed:'.format(len(Failed),len(inputfiles)))
        for p in Failed:
            print('      ',p.input_file)
        return False

def run_cmd(input_file, exe, wait=True, ShowOutputs=False, ShowCommand=True):
    """ Run a simple command of the form `exe input_file`  """
    # TODO Better capture STDOUT
    if not os.path.isabs(input_file):
        input_file_abs=os.path.abspath(input_file)
    else:
        input_file_abs=input_file
    if not os.path.exists(exe):
        raise Exception('Executable not found: {}'.format(exe))
    args= [exe,input_file]
    #args = 'cd '+workdir+' && '+ exe +' '+basename
    shell=False
    if ShowOutputs:
        STDOut= None
    else:
        STDOut= open(os.devnull, 'w') 
    if ShowCommand:
        print('Running: '+' '.join(args))
    if wait:
        p=subprocess.call(args , stdout=STDOut, stderr=subprocess.STDOUT, shell=shell)
    else:
        p=subprocess.Popen(args, stdout=STDOut, stderr=subprocess.STDOUT, shell=shell)
    # Storing some info into the process
    p.cmd            = ' '.join(args)
    p.args           = args
    p.input_file     = input_file
    p.input_file_abs = input_file_abs
    p.exe            = exe
    return p
# --- END cmd.py

def run_fastfiles(fastfiles, fastExe=None, parallel=True, ShowOutputs=True, nCores=None, ShowCommand=True, ReRun=True):
    if fastExe is None:
        fastExe=FAST_EXE
    if not ReRun:
        # Figure out which files exist
        newfiles=[]
        for f in fastfiles:
            base=os.path.splitext(f)[0]
            if os.path.exists(base+'.outb') or os.path.exists(base+'.out'):
                print('>>> Skipping existing simulation for: ',f)
                pass
            else:
                newfiles.append(f)
        fastfiles=newfiles

    return run_cmds(fastfiles, fastExe, parallel=parallel, ShowOutputs=ShowOutputs, nCores=nCores, ShowCommand=ShowCommand)

def run_fast(input_file, fastExe=None, wait=True, ShowOutputs=False, ShowCommand=True):
    if fastExe is None:
        fastExe=FAST_EXE
    return run_cmd(input_file, fastExe, wait=wait, ShowOutputs=ShowOutputs, ShowCommand=ShowCommand)


def writeBatch(batchfile, fastfiles, fastExe=None):
    """ Write batch file, everything is written relative to the batch file"""
    if fastExe is None:
        fastExe=FAST_EXE
    fastExe_abs   = os.path.abspath(fastExe)
    batchfile_abs = os.path.abspath(batchfile)
    batchdir      = os.path.dirname(batchfile_abs)
    fastExe_rel   = os.path.relpath(fastExe_abs, batchdir)
    with open(batchfile,'w') as f:
        for ff in fastfiles:
            ff_abs = os.path.abspath(ff)
            ff_rel = os.path.relpath(ff_abs, batchdir)
            l = fastExe_rel + ' '+ ff_rel
            f.write("%s\n" % l)


def removeFASTOuputs(workdir):
    # Cleaning folder
    for f in glob.glob(os.path.join(workdir,'*.out')):
        os.remove(f)
    for f in glob.glob(os.path.join(workdir,'*.outb')):
        os.remove(f)
    for f in glob.glob(os.path.join(workdir,'*.ech')):
        os.remove(f)
    for f in glob.glob(os.path.join(workdir,'*.sum')):
        os.remove(f)

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
    if not isinstance(ED,weio.FASTInFile):
        ED = weio.FASTInFile(ED)

    nBldNodes = ED['BldNodes']
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
    if not isinstance(ED,weio.FASTInFile):
        ED = weio.FASTInFile(ED)

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
    if not isinstance(ED,weio.FASTInFile):
        ED = weio.FASTInFile(ED)
    _,r_nodes= ED_BldStations(ED)
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
    if not isinstance(ED,weio.FASTInFile):
        ED = weio.FASTInFile(ED)
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
    if not isinstance(AD,weio.FASTInFile):
        AD = weio.FASTInFile(AD)

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
    if not isinstance(AD,weio.FASTInFile):
        AD = weio.FASTInFile(AD)
    if not isinstance(AD_bld,weio.FASTInFile):
        AD_bld = weio.FASTInFile(AD_bld)
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

def BD_BldGag(BD):
    """ Returns the radial position of BeamDyn blade gages 
    INPUTS:
       - BD: either:
           - a filename of a BeamDyn input file
           - an instance of FileCl, as returned by reading the file, BD = weio.read(BD_filename)
    OUTPUTS:
       - r_gag: The radial positions of the gages, given from the rotor apex
    """
    if not isinstance(BD,weio.FASTInFile):
        BD = weio.FASTInFile(BD)

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

def insert_radial_columns(df, vr, R=None, IR=None):
    """
    Add some columns to the radial data
    """
    if df is None:
        return df
    if df.shape[1]==0:
        return None
    nrMax=len(df)
    ids=np.arange(nrMax)
    if vr is None:
        # Radial position unknown
        vr_bar = ids/(nrMax-1)
        df.insert(0, 'i/n_[-]', vr_bar)
    else:
        vr_bar=vr/R
        if (nrMax)<len(vr_bar):
            vr_bar=vr_bar[1:nrMax]
        elif (nrMax)>len(vr_bar):
            raise Exception('Inconsitent length between radial stations and max index present in output chanels')
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
    return pd.DataFrame(data=Values, columns=ColNames)

def spanwiseColBD(Cols):
    """ Return column info, available columns and indices that contain BD spanwise data"""
    BDSpanMap=dict()
    for sB in ['B1','B2','B3']:
        BDSpanMap['^'+sB+'N(\d)TDxr_\[m\]']=sB+'TDxr_[m]'
        BDSpanMap['^'+sB+'N(\d)TDyr_\[m\]']=sB+'TDyr_[m]'
        BDSpanMap['^'+sB+'N(\d)TDzr_\[m\]']=sB+'TDzr_[m]'
    return find_matching_columns(Cols, BDSpanMap)

def spanwiseColED(Cols):
    """ Return column info, available columns and indices that contain ED spanwise data"""
    EDSpanMap=dict()
    for sB in ['b1','b2','b3']:
        SB=sB.upper()
        EDSpanMap['^Spn(\d)ALx'+sB+'_\[m/s^2\]']=SB+'ALx_[m/s^2]'
        EDSpanMap['^Spn(\d)ALy'+sB+'_\[m/s^2\]']=SB+'ALy_[m/s^2]'
        EDSpanMap['^Spn(\d)ALz'+sB+'_\[m/s^2\]']=SB+'ALz_[m/s^2]'
        EDSpanMap['^Spn(\d)TDx'+sB+'_\[m\]'    ]=SB+'TDx_[m]'
        EDSpanMap['^Spn(\d)TDy'+sB+'_\[m\]'    ]=SB+'TDy_[m]'
        EDSpanMap['^Spn(\d)TDz'+sB+'_\[m\]'    ]=SB+'TDz_[m]'
        EDSpanMap['^Spn(\d)RDx'+sB+'_\[deg\]'  ]=SB+'RDx_[deg]'
        EDSpanMap['^Spn(\d)RDy'+sB+'_\[deg\]'  ]=SB+'RDy_[deg]'
        EDSpanMap['^Spn(\d)RDz'+sB+'_\[deg\]'  ]=SB+'RDz_[deg]'
        EDSpanMap['^Spn(\d)FLx'+sB+'_\[kN\]'   ]=SB+'FLx_[kN]'
        EDSpanMap['^Spn(\d)FLy'+sB+'_\[kN\]'   ]=SB+'FLy_[kN]'
        EDSpanMap['^Spn(\d)FLz'+sB+'_\[kN\]'   ]=SB+'FLz_[kN]'
        EDSpanMap['^Spn(\d)MLy'+sB+'_\[kN-m\]' ]=SB+'MLx_[kN-m]'
        EDSpanMap['^Spn(\d)MLx'+sB+'_\[kN-m\]' ]=SB+'MLy_[kN-m]'  
        EDSpanMap['^Spn(\d)MLz'+sB+'_\[kN-m\]' ]=SB+'MLz_[kN-m]'
    return find_matching_columns(Cols, EDSpanMap)

def spanwiseColAD(Cols):
    """ Return column info, available columns and indices that contain AD spanwise data"""
    ADSpanMap=dict()
    for sB in ['B1','B2','B3']:
        ADSpanMap['^'+sB+'N(\d*)Alpha_\[deg\]']=sB+'Alpha_[deg]'
        ADSpanMap['^'+sB+'N(\d*)AOA_\[deg\]'  ]=sB+'Alpha_[deg]' # DBGOuts
        ADSpanMap['^'+sB+'N(\d*)AxInd_\[-\]'  ]=sB+'AxInd_[-]'  
        ADSpanMap['^'+sB+'N(\d*)TnInd_\[-\]'  ]=sB+'TnInd_[-]'  
        ADSpanMap['^'+sB+'N(\d*)AIn_\[deg\]'  ]=sB+'AxInd_[-]'   # DBGOuts NOTE BUG Unit
        ADSpanMap['^'+sB+'N(\d*)ApI_\[deg\]'  ]=sB+'TnInd_[-]'   # DBGOuts NOTE BUG Unit
        ADSpanMap['^'+sB+'N(\d*)AIn_\[-\]'    ]=sB+'AxInd_[-]'   # DBGOuts
        ADSpanMap['^'+sB+'N(\d*)ApI_\[-\]'    ]=sB+'TnInd_[-]'   # DBGOuts
        ADSpanMap['^'+sB+'N(\d*)Uin_\[m/s\]'  ]=sB+'Uin_[m/s]'     # DBGOuts
        ADSpanMap['^'+sB+'N(\d*)Uit_\[m/s\]'  ]=sB+'Uit_[m/s]'     # DBGOuts
        ADSpanMap['^'+sB+'N(\d*)Uir_\[m/s\]'  ]=sB+'Uir_[m/s]'     # DBGOuts
        ADSpanMap['^'+sB+'N(\d*)Cl_\[-\]'     ]=sB+'Cl_[-]'   
        ADSpanMap['^'+sB+'N(\d*)Cd_\[-\]'     ]=sB+'Cd_[-]'   
        ADSpanMap['^'+sB+'N(\d*)Cm_\[-\]'     ]=sB+'Cm_[-]'   
        ADSpanMap['^'+sB+'N(\d*)Cx_\[-\]'     ]=sB+'Cx_[-]'   
        ADSpanMap['^'+sB+'N(\d*)Cy_\[-\]'     ]=sB+'Cy_[-]'   
        ADSpanMap['^'+sB+'N(\d*)Cn_\[-\]'     ]=sB+'Cn_[-]'   
        ADSpanMap['^'+sB+'N(\d*)Ct_\[-\]'     ]=sB+'Ct_[-]'   
        ADSpanMap['^'+sB+'N(\d*)Re_\[-\]'     ]=sB+'Re_[-]' 
        ADSpanMap['^'+sB+'N(\d*)Vrel_\[m/s\]' ]=sB+'Vrel_[m/s]' 
        ADSpanMap['^'+sB+'N(\d*)Theta_\[deg\]']=sB+'Theta_[deg]'
        ADSpanMap['^'+sB+'N(\d*)Phi_\[deg\]'  ]=sB+'Phi_[deg]'
        ADSpanMap['^'+sB+'N(\d*)Twst_\[deg\]' ]=sB+'Twst_[deg]' #DBGOuts
        ADSpanMap['^'+sB+'N(\d*)Curve_\[deg\]']=sB+'Curve_[deg]'
        ADSpanMap['^'+sB+'N(\d*)Vindx_\[m/s\]']=sB+'Vindx_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)Vindy_\[m/s\]']=sB+'Vindy_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)Fx_\[N/m\]'   ]=sB+'Fx_[N/m]'   
        ADSpanMap['^'+sB+'N(\d*)Fy_\[N/m\]'   ]=sB+'Fy_[N/m]'   
        ADSpanMap['^'+sB+'N(\d*)Fl_\[N/m\]'   ]=sB+'Fl_[N/m]'   
        ADSpanMap['^'+sB+'N(\d*)Fd_\[N/m\]'   ]=sB+'Fd_[N/m]'   
        ADSpanMap['^'+sB+'N(\d*)Fn_\[N/m\]'   ]=sB+'Fn_[N/m]'   
        ADSpanMap['^'+sB+'N(\d*)Ft_\[N/m\]'   ]=sB+'Ft_[N/m]'   
        ADSpanMap['^'+sB+'N(\d*)VUndx_\[m/s\]']=sB+'VUndx_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)VUndy_\[m/s\]']=sB+'VUndy_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)VUndz_\[m/s\]']=sB+'VUndz_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)VDisx_\[m/s\]']=sB+'VDisx_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)VDisy_\[m/s\]']=sB+'VDisy_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)VDisz_\[m/s\]']=sB+'VDisz_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)Vx_\[m/s\]'   ]=sB+'Vx_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)Vy_\[m/s\]'   ]=sB+'Vy_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)Vz_\[m/s\]'   ]=sB+'Vz_[m/s]'
        ADSpanMap['^'+sB+'N(\d*)DynP_\[Pa\]'  ]=sB+'DynP_[Pa]' 
        ADSpanMap['^'+sB+'N(\d*)M_\[-\]'      ]=sB+'M_[-]' 
        ADSpanMap['^'+sB+'N(\d*)Mm_\[N-m/m\]' ]=sB+'Mm_[N-m/m]'   
        ADSpanMap['^'+sB+'N(\d*)Gam_\['       ]=sB+'Gam_[m^2/s]' #DBGOuts
    # --- AD 14
    ADSpanMap['^Alpha(\d*)_\[deg\]'  ]='Alpha_[deg]'  
    ADSpanMap['^DynPres(\d*)_\[Pa\]' ]='DynPres_[Pa]' 
    ADSpanMap['^CLift(\d*)_\[-\]'    ]='CLift_[-]'    
    ADSpanMap['^CDrag(\d*)_\[-\]'    ]='CDrag_[-]'    
    ADSpanMap['^CNorm(\d*)_\[-\]'    ]='CNorm_[-]'    
    ADSpanMap['^CTang(\d*)_\[-\]'    ]='CTang_[-]'    
    ADSpanMap['^CMomt(\d*)_\[-\]'    ]='CMomt_[-]'    
    ADSpanMap['^Pitch(\d*)_\[deg\]'  ]='Pitch_[deg]'  
    ADSpanMap['^AxInd(\d*)_\[-\]'    ]='AxInd_[-]'    
    ADSpanMap['^TanInd(\d*)_\[-\]'   ]='TanInd_[-]'   
    ADSpanMap['^ForcN(\d*)_\[N\]'    ]='ForcN_[N]'    
    ADSpanMap['^ForcT(\d*)_\[N\]'    ]='ForcT_[N]'    
    ADSpanMap['^Pmomt(\d*)_\[N-m\]'  ]='Pmomt_[N-N]'  
    ADSpanMap['^ReNum(\d*)_\[x10^6\]']='ReNum_[x10^6]'
    ADSpanMap['^Gamma(\d*)_\[m^2/s\]']='Gamma_[m^2/s]'

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
    Postprocess FAST radial data

    INPUTS:
        - FST_IN: Fast .fst input file
        - avgMethod='periods', avgParam=2:  average over 2 last periods, Needs Azimuth sensors!!!
        - avgMethod='constantwindow', avgParam=5:  average over 5s of simulation
        - postprofile: outputfile to write radial data
    """
    # --- Opens Fast output  and performs averaging
    if df is None:
        df = weio.read(FST_In.replace('.fst',out_ext)).toDataFrame()
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
    Returns a 3D matrix: n x nSpan x nColumn where df is of size n x nColumn

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
        fst = weio.FASTInputDeck(FST_In, readlist=['AD','ED','BD'])
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
            if  not hasattr(fst,'ED'):
                print('[WARN] The Elastodyn file couldn''t be found or read, from main file: '+FST_In)
                #raise Exception('The Elastodyn file couldn''t be found or read, from main file: '+FST_In)
            else:
                R           = fst.ED['TipRad']
                r_hub       = fst.ED['HubRad']
                r_ED, IR_ED = ED_BldGag(fst.ED)

            # --- BeamDyn
            if  hasattr(fst,'BD'):
                r_BD, IR_BD, r_BD_All = BD_BldGag(fst.BD)
                r_BD= r_BD+r_hub
                if R is None:
                    R = r_BD_All[-1] # just in case ED file missing

            # --- AeroDyn
            if  not hasattr(fst,'AD'):
                print('[WARN] The AeroDyn file couldn''t be found or read, from main file: '+FST_In)
                #raise Exception('The AeroDyn file couldn''t be found or read, from main file: '+FST_In)
            else:

                if fst.ADversion == 'AD15':
                    if  not hasattr(fst.AD,'Bld1'):
                        raise Exception('The AeroDyn blade file couldn''t be found or read, from main file: '+FST_In)
                    
                    if 'B1N001Cl_[-]' in OutputCols:
                        # This was compiled with all outs
                        r_AD   = fst.AD.Bld1['BldAeroNodes'][:,0] # Full span
                        r_AD   += r_hub
                        IR_AD  = None
                    else:
                        r_AD,_ = AD_BldGag(fst.AD,fst.AD.Bld1, chordOut = True) # Only at Gages locations

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
def remap_df(df, ColMap, bColKeepNewOnly=False, inPlace=False):
    """ Add/rename columns of a dataframe, potentially perform operations between columns
    """
    if not inPlace:
        df=df.copy()
    ColMapMiss=[]
    ColNew=[]
    RenameMap=dict()
    for k0,v in ColMap.items():
        k=k0.strip()
        v=v.strip()
        if v.find('{')>=0:
            search_results = re.finditer(r'\{.*?\}', v)
            expr=v
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
# --- Template replace 
# --------------------------------------------------------------------------------{
def handleRemoveReadonlyWin(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.
    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.
    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


def copyTree(src, dst):
    """ 
    Copy a directory to another one, overwritting files if necessary.
    copy_tree from distutils and copytree from shutil fail on Windows (in particular on git files)
    """
    def forceMergeFlatDir(srcDir, dstDir):
        if not os.path.exists(dstDir):
            os.makedirs(dstDir)
        for item in os.listdir(srcDir):
            srcFile = os.path.join(srcDir, item)
            dstFile = os.path.join(dstDir, item)
            forceCopyFile(srcFile, dstFile)

    def forceCopyFile (sfile, dfile):
        # ---- Handling error due to wrong mod
        if os.path.isfile(dfile):
            if not os.access(dfile, os.W_OK):
                os.chmod(dfile, stat.S_IWUSR)
        #print(sfile, ' > ', dfile)
        shutil.copy2(sfile, dfile)

    def isAFlatDir(sDir):
        for item in os.listdir(sDir):
            sItem = os.path.join(sDir, item)
            if os.path.isdir(sItem):
                return False
        return True

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isfile(s):
            if not os.path.exists(dst):
                os.makedirs(dst)
            forceCopyFile(s,d)
        if os.path.isdir(s):
            isRecursive = not isAFlatDir(s)
            if isRecursive:
                copyTree(s, d)
            else:
                forceMergeFlatDir(s, d)


def templateReplaceGeneral(PARAMS, template_dir=None, output_dir=None, main_file=None, RemoveAllowed=False, RemoveRefSubFiles=False, oneSimPerDir=False):
    """ Generate inputs files by replacing different parameters from a template file.
    The generated files are placed in the output directory `output_dir` 
    The files are read and written using the library `weio`. 
    The template file is read and its content can be changed like a dictionary.
    Each item of `PARAMS` correspond to a set of parameters that will be replaced
    in the template file to generate one input file.

    For "FAST" input files, parameters can be changed recursively.
    

    INPUTS:
      PARAMS: list of dictionaries. Each key of the dictionary should be a key present in the 
              template file when read with `weio` (see: weio.read(main_file).keys() )

               PARAMS[0]={'FAST|DT':0.1, 'EDFile|GBRatio':1, 'ServoFile|GenEff':0.8}

      template_dir: if provided, this directory and its content will be copied to `output_dir` 
                      before doing the parametric substitution

      output_dir  : directory where files will be generated. 
    """
    # --- Helper functions
    def rebase_rel(wd,s,sid):
        split = os.path.splitext(s)
        return os.path.join(wd,split[0]+sid+split[1])
    def get_strID(p) :
        if '__name__' in p.keys():
            strID=p['__name__']
        else:
            raise Exception('When calling `templateReplace`, provide the key `__name_` in the parameter dictionaries')
        return strID

    def splitAddress(sAddress):
        sp = sAddress.split('|')
        if len(sp)==1:
            return sp[0],[]
        else:
            return sp[0],sp[1:]

    def rebaseFileName(org_filename, WorkDir, strID):
            new_filename_full = rebase_rel(WorkDir, org_filename,'_'+strID)
            new_filename      = os.path.relpath(new_filename_full,WorkDir).replace('\\','/')
            return new_filename, new_filename_full

    def replaceRecurse(templatename_or_newname, FileKey, ParamKey, ParamValue, Files, strID, WorkDir, TemplateFiles):
        """ 
        FileKey: a single key defining which file we are currently modifying e.g. :'AeroFile', 'EDFile','FVWInputFileName'
        ParamKey: the address key of the parameter to be changed, relative to the current FileKey
                  e.g. 'EDFile|IntMethod' (if FileKey is '') 
                       'IntMethod' (if FileKey is 'EDFile') 
        ParamValue: the value to be used
        Files: dict of files, as returned by weio, keys are "FileKeys" 
        """
        # --- Special handling for the root
        if FileKey=='':
            FileKey='Root'
        # --- Open (or get if already open) file where a parameter needs to be changed
        if FileKey in Files.keys():
            # The file was already opened, it's stored
            f = Files[FileKey]
            newfilename_full = f.filename
            newfilename      = os.path.relpath(newfilename_full,WorkDir).replace('\\','/')

        else:
            templatefilename              = templatename_or_newname
            templatefilename_full         = os.path.join(WorkDir,templatefilename)
            TemplateFiles.append(templatefilename_full)
            if FileKey=='Root':
                # Root files, we start from strID
                ext = os.path.splitext(templatefilename)[-1]
                newfilename_full = os.path.join(wd,strID+ext)
                newfilename      = strID+ext
            else:
                newfilename, newfilename_full = rebaseFileName(templatefilename, WorkDir, strID)
            #print('--------------------------------------------------------------')
            #print('TemplateFile    :', templatefilename)
            #print('TemplateFileFull:', templatefilename_full)
            #print('NewFile         :', newfilename)
            #print('NewFileFull     :', newfilename_full)
            shutil.copyfile(templatefilename_full, newfilename_full)
            f= weio.FASTInFile(newfilename_full) # open the template file for that filekey 
            Files[FileKey]=f # store it

        # --- Changing parameters in that file
        NewFileKey_or_Key, ChildrenKeys = splitAddress(ParamKey)
        if len(ChildrenKeys)==0:
            # A simple parameter is changed 
            Key    = NewFileKey_or_Key
            #print('Setting', FileKey, '|',Key, 'to',ParamValue)
            if Key=='OutList':
                OutList=f[Key]
                f[Key]=addToOutlist(OutList, ParamValue)
            else:
                f[Key] = ParamValue
        else:
            # Parameters needs to be changed in subfiles (children)
            NewFileKey                = NewFileKey_or_Key
            ChildrenKey            = '|'.join(ChildrenKeys)
            child_templatefilename = f[NewFileKey].strip('"') # old filename that will be used as a template
            baseparent = os.path.dirname(newfilename)
            #print('Child templatefilename:',child_templatefilename)
            #print('Parent base dir       :',baseparent)
            WorkDir = os.path.join(WorkDir, baseparent)

            #  
            newchildFilename, Files = replaceRecurse(child_templatefilename, NewFileKey, ChildrenKey, ParamValue, Files, strID, WorkDir, TemplateFiles)
            #print('Setting', FileKey, '|',NewFileKey, 'to',newchildFilename)
            f[NewFileKey] = '"'+newchildFilename+'"'

        return newfilename, Files


    # --- Safety checks
    if template_dir is None and output_dir is None:
        raise Exception('Provide at least a template directory OR an output directory')

    if template_dir is not None:
        if not os.path.exists(template_dir):
            raise Exception('Template directory does not exist: '+template_dir)

        # Default value of output_dir if not provided
        if template_dir[-1]=='/'  or template_dir[-1]=='\\' :
            template_dir=template_dir[0:-1]
        if output_dir is None:
            output_dir=template_dir+'_Parametric'

    # --- Main file use as "master"
    if template_dir is not None:
        main_file=os.path.join(output_dir, os.path.basename(main_file))
    else:
        main_file=main_file

    # Params need to be a list
    if not isinstance(PARAMS,list):
        PARAMS=[PARAMS]

    if oneSimPerDir:
        WORKDIRS=[os.path.join(output_dir,get_strID(p)) for p in PARAMS]
    else:
        WORKDIRS=[output_dir]*len(PARAMS)
    # --- Creating output_dir - Copying template folder to output_dir if necessary
    # Copying template folder to workdir
    for wd in list(set(WORKDIRS)):
        if RemoveAllowed:
            removeFASTOuputs(wd)
        if os.path.exists(wd) and RemoveAllowed:
            shutil.rmtree(wd, ignore_errors=False, onerror=handleRemoveReadonlyWin)
        copyTree(template_dir, wd)
        if RemoveAllowed:
            removeFASTOuputs(wd)


    TemplateFiles=[]
    files=[]
    for ip,(wd,p) in enumerate(zip(WORKDIRS,PARAMS)):
        if '__index__' not in p.keys():
            p['__index__']=ip

        main_file_base = os.path.basename(main_file)
        strID          = get_strID(p)
        # --- Setting up files for this simulation
        Files=dict()
        for k,v in p.items():
            if k =='__index__' or k=='__name__':
                continue
            new_mainFile, Files = replaceRecurse(main_file_base, '', k, v, Files, strID, wd, TemplateFiles)

        # --- Writting files
        for k,f in Files.items():
            if k=='Root':
                files.append(f.filename)
            f.write()

    # --- Remove extra files at the end
    if RemoveRefSubFiles:
        TemplateFiles, nCounts = np.unique(TemplateFiles, return_counts=True)
        if not oneSimPerDir:
            # we can only detele template files that were used by ALL simulations
            TemplateFiles=[t for nc,t in zip(nCounts, TemplateFiles) if nc==len(PARAMS)]
        for tf in TemplateFiles:
            try:
                os.remove(tf)
            except:
                print('[FAIL] Removing '+tf)
                pass
    return files

def templateReplace(PARAMS, template_dir, workdir=None, main_file=None, RemoveAllowed=False, RemoveRefSubFiles=False, oneSimPerDir=False):
    """ Replace parameters in a fast folder using a list of dictionaries where the keys are for instance:
        'FAST|DT', 'EDFile|GBRatio', 'ServoFile|GenEff'
    """
    # --- For backward compatibility, remove "FAST|" from the keys
    for p in PARAMS:
        old_keys=[ k for k,_ in p.items() if k.find('FAST|')==0]
        for k_old in old_keys:
            k_new=k_old.replace('FAST|','')
            p[k_new] = p.pop(k_old)
    
    return templateReplaceGeneral(PARAMS, template_dir, output_dir=workdir, main_file=main_file, 
            RemoveAllowed=RemoveAllowed, RemoveRefSubFiles=RemoveRefSubFiles, oneSimPerDir=oneSimPerDir)

# --------------------------------------------------------------------------------}
# --- Tools for template replacement 
# --------------------------------------------------------------------------------{
def paramsSteadyAero(p=dict()):
    p['AeroFile|AFAeroMod']=1 # remove dynamic effects dynamic
    p['AeroFile|WakeMod']=1 # remove dynamic inflow dynamic
    p['AeroFile|TwrPotent']=0 # remove tower shadow
    return p

def paramsNoGen(p=dict()):
    p['EDFile|GenDOF' ]  = 'False'
    return p

def paramsGen(p=dict()):
    p['EDFile|GenDOF' ]  = 'True'
    return p

def paramsNoController(p=dict()):
    p['ServoFile|PCMode']   = 0;
    p['ServoFile|VSContrl'] = 0;
    p['ServoFile|YCMode']   = 0;
    return p

def paramsControllerDLL(p=dict()):
    p['ServoFile|PCMode']   = 5;
    p['ServoFile|VSContrl'] = 5;
    p['ServoFile|YCMode']   = 5;
    p['EDFile|GenDOF']      = 'True';
    return p


def paramsStiff(p=dict()):
    p['EDFile|FlapDOF1']  = 'False'
    p['EDFile|FlapDOF2']  = 'False'
    p['EDFile|EdgeDOF' ]  = 'False'
    p['EDFile|TeetDOF' ]  = 'False'
    p['EDFile|DrTrDOF' ]  = 'False'
    p['EDFile|YawDOF'  ]  = 'False'
    p['EDFile|TwFADOF1']  = 'False'
    p['EDFile|TwFADOF2']  = 'False'
    p['EDFile|TwSSDOF1']  = 'False'
    p['EDFile|TwSSDOF2']  = 'False'
    p['EDFile|PtfmSgDOF'] = 'False'
    p['EDFile|PtfmSwDOF'] = 'False'
    p['EDFile|PtfmHvDOF'] = 'False'
    p['EDFile|PtfmRDOF']  = 'False'
    p['EDFile|PtfmPDOF']  = 'False'
    p['EDFile|PtfmYDOF']  = 'False'
    return p

def paramsWS_RPM_Pitch(WS,RPM,Pitch,BaseDict=None,FlatInputs=False):
    """ """
    # --- Ensuring everythin is an iterator
    def iterify(x):
        if not isinstance(x, collections.Iterable): x = [x]
        return x
    WS    = iterify(WS)
    RPM   = iterify(RPM)
    Pitch = iterify(Pitch)
    # --- If inputs are not flat but different vectors to length through, we flatten them (TODO: meshgrid and ravel?)
    if not FlatInputs :
        WS_flat    = []
        Pitch_flat = []
        RPM_flat   = []
        for pitch in Pitch:
            for rpm in RPM:
                for ws in WS:
                    WS_flat.append(ws)
                    RPM_flat.append(rpm)
                    Pitch_flat.append(pitch)
    else:
        WS_flat, Pitch_flat, RPM_flat = WS, Pitch, RPM

    # --- Defining the parametric study 
    PARAMS=[]
    i=0
    for ws,rpm,pitch in zip(WS_flat,RPM_flat,Pitch_flat):
        if BaseDict is None:
            p=dict()
        else:
            p = BaseDict.copy()
        p['EDFile|RotSpeed']       = rpm
        p['InflowFile|HWindSpeed'] = ws
        p['InflowFile|WindType']   = 1 # Setting steady wind
        p['EDFile|BlPitch(1)']     = pitch
        p['EDFile|BlPitch(2)']     = pitch
        p['EDFile|BlPitch(3)']     = pitch

        p['__index__']  = i
        p['__name__']   = '{:03d}_ws{:04.1f}_pt{:04.2f}_om{:04.2f}'.format(p['__index__'],p['InflowFile|HWindSpeed'],p['EDFile|BlPitch(1)'],p['EDFile|RotSpeed'])
        i=i+1
        PARAMS.append(p)
    return PARAMS


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

def find_matching_pattern(List, pattern):
    """ Return elements of a list of strings that match a pattern
        and return the first matching group
    """
    reg_pattern=re.compile(pattern)
    MatchedElements=[]
    MatchedStrings=[]
    for l in List:
        match=reg_pattern.search(l)
        if match:
            MatchedElements.append(l)
            MatchedStrings.append(match.groups(1)[0])
    return MatchedElements, MatchedStrings

        

def extractSpanTSReg(ts, col_pattern, colname, IR=None):
    """ Helper function to extract spanwise results, like B1N1Cl B1N2Cl etc. 

    Example
        col_pattern: 'B1N(\d*)Cl_\[-\]'
        colname    : 'B1Cl_[-]'
    """
    # Extracting columns matching pattern
    cols, sIdx = find_matching_pattern(ts.keys(), col_pattern)
    if len(cols) ==0:
        return (None,None)

    # Sorting by ID
    cols = np.asarray(cols)
    Idx  = np.array([int(s) for s in sIdx])
    Isort = np.argsort(Idx)
    Idx  = Idx[Isort]
    cols = cols[Isort]

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

def extractSpanTS(ts, nr, col_pattern, colname, IR=None):
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
    for i,f in enumerate(outFiles):
        df=weio.read(f).toDataFrame()
        postpro=averageDF(df, avgMethod=avgMethod, avgParam=avgParam, ColMap=ColMap, ColKeep=ColKeep,ColSort=ColSort,stats=stats)
        MeanValues=postpro # todo
        if i==0:
            result = MeanValues.copy()
        else:
            result=result.append(MeanValues, ignore_index=True)
    if ColSort is not None:
        # Sorting 
        result.sort_values([ColSort],inplace=True,ascending=True)
        result.reset_index(drop=True,inplace=True) 
    return result 

# --------------------------------------------------------------------------------}
# --- Tools for typical wind turbine study 
# --------------------------------------------------------------------------------{
def CPCT_LambdaPitch(refdir,main_fastfile,Lambda=None,Pitch=np.linspace(-10,40,5),WS=None,Omega=None, # operating conditions
          TMax=20,bStiff=True,bNoGen=True,bSteadyAero=True, # simulation options
          ReRun=True, 
          fastExe=None,ShowOutputs=True,nCores=4): # execution options
    """ Computes CP and CT as function of tip speed ratio (lambda) and pitch.
    There are two main ways to define the inputs:
      - Option 1: provide Lambda and Pitch (deg)
      - Option 2: provide WS (m/s), Omega (in rpm) and Pitch (deg), in which case len(WS)==len(Omega)
    """

    WS_default=5 # If user does not provide a wind speed vector, wind speed used

    # if the user provided a full path to the main file, we scrap the directory. TODO, should be cleaner
    if len(os.path.dirname(main_fastfile))>0:
        main_fastfile=os.path.basename(main_fastfile)

    # --- Reading main fast file to get rotor radius 
    fst = weio.FASTInFile(os.path.join(refdir,main_fastfile))
    ed  = weio.FASTInFile(os.path.join(refdir,fst['EDFile'].replace('"','')))
    R = ed['TipRad']

    # --- Making sure we have 
    if (Omega is not None):
        if (Lambda is not None):
            WS = np.ones(Omega.shape)*WS_default
        elif (WS is not None):
            if len(WS)!=len(Omega):
                raise Exception('When providing Omega and WS, both vectors should have the same dimension')
        else:
            WS = np.ones(Omega.shape)*WS_default
    else:
        Omega = WS_default * Lambda/R*60/(2*np.pi) # TODO, use more realistic combinations of WS and Omega
        WS    = np.ones(Omega.shape)*WS_default


    # --- Defining flat vectors of operating conditions
    WS_flat    = []
    RPM_flat   = []
    Pitch_flat = []
    for pitch in Pitch:
        for (rpm,ws) in zip(Omega,WS):
            WS_flat.append(ws)
            RPM_flat.append(rpm)
            Pitch_flat.append(pitch)
    # --- Setting up default options
    BaseDict={'FAST|TMax': TMax, 'FAST|DT': 0.01, 'FAST|DT_Out': 0.1} # NOTE: Tmax should be at least 2pi/Omega
    BaseDict = paramsNoController(BaseDict)
    if bStiff:
        BaseDict = paramsStiff(BaseDict)
    if bNoGen:
        BaseDict = paramsNoGen(BaseDict)
    if bSteadyAero:
        BaseDict = paramsSteadyAero(BaseDict)

    # --- Creating set of parameters to be changed
    # TODO: verify that RtAeroCp and RtAeroCt are present in AeroDyn outlist
    PARAMS = paramsWS_RPM_Pitch(WS_flat,RPM_flat,Pitch_flat,BaseDict=BaseDict, FlatInputs=True)

    # --- Generating all files in a workdir
    workdir = refdir.strip('/').strip('\\')+'_CPLambdaPitch'
    print('>>> Generating inputs files in {}'.format(workdir))
    RemoveAllowed=ReRun # If the user want to rerun, we can remove, otherwise we keep existing simulations
    fastFiles=templateReplace(PARAMS, refdir, workdir=workdir,RemoveRefSubFiles=True,RemoveAllowed=RemoveAllowed,main_file=main_fastfile)

    # --- Running fast simulations
    print('>>> Running {} simulations...'.format(len(fastFiles)))
    run_fastfiles(fastFiles, ShowOutputs=ShowOutputs, fastExe=fastExe, nCores=nCores, ReRun=ReRun)

    # --- Postpro - Computing averages at the end of the simluation
    print('>>> Postprocessing...')
    outFiles = [os.path.splitext(f)[0]+'.outb' for f in fastFiles]
    # outFiles = glob.glob(os.path.join(workdir,'*.outb'))
    ColKeepStats  = ['RotSpeed_[rpm]','BldPitch1_[deg]','RtAeroCp_[-]','RtAeroCt_[-]','Wind1VelX_[m/s]']
    result = averagePostPro(outFiles,avgMethod='periods',avgParam=1,ColKeep=ColKeepStats,ColSort='RotSpeed_[rpm]')
    # print(result)        

    # --- Adding lambda, sorting and keeping only few columns
    result['lambda_[-]'] = result['RotSpeed_[rpm]']*R*2*np.pi/60/result['Wind1VelX_[m/s]']
    result.sort_values(['lambda_[-]','BldPitch1_[deg]'],ascending=[True,True],inplace=True)
    ColKeepFinal=['lambda_[-]','BldPitch1_[deg]','RtAeroCp_[-]','RtAeroCt_[-]']
    result=result[ColKeepFinal]
    print('>>> Done')

    #  --- Converting to a matrices
    CP = result['RtAeroCp_[-]'].values
    CT = result['RtAeroCt_[-]'].values
    MCP =CP.reshape((len(Lambda),len(Pitch)))
    MCT =CT.reshape((len(Lambda),len(Pitch)))
    LAMBDA, PITCH = np.meshgrid(Lambda, Pitch)
    #  --- CP max
    i,j = np.unravel_index(MCP.argmax(), MCP.shape)
    MaxVal={'CP_max':MCP[i,j],'lambda_opt':LAMBDA[j,i],'pitch_opt':PITCH[j,i]}

    return  MCP,MCT,Lambda,Pitch,MaxVal,result


# def detectFastFiles(workdir):
#     FstFiles=glob.glob(os.path.join(workdir,'*.fst'))+glob.glob(os.path.join(workdir,'*.FST'))
#     DatFiles=glob.glob(os.path.join(workdir,'*.dat'))+glob.glob(os.path.join(workdir,'*.DAT'))
#     Files=dict()
#     Files['Main']      = FstFiles
#     Files['Inflow']    = None
#     Files['Aero']      = None
#     Files['Tower']     = None
#     Files['Blade']     = None
#     Files['AeroBlade'] = None
#     Files['ServoDyn']  = None
#     for f in DatFiles:
#         b = os.path.basename(f).lower()
#         if b.find('inflow'):
#             Files['Inflow'] = f
#     windfile_ref = 'InflowWind.dat';
#     fastfile_ref = 'Turbine.fst';
#     elasfile_ref = 'ElastoDyn.dat';
#         remove
   


if __name__=='__main__':
    pass
    # --- Test of templateReplace
    PARAMS                          = {}
    PARAMS['FAST|TMax']             = 10
    PARAMS['__name__']             =  'MyName'
    PARAMS['FAST|DT']               = 0.01
    PARAMS['FAST|DT_Out']           = 0.1
    PARAMS['EDFile|RotSpeed']       = 100
    PARAMS['EDFile|BlPitch(1)']     = 1
    PARAMS['EDFile|GBoxEff']        = 0.92
    PARAMS['ServoFile|VS_Rgn2K']    = 0.00038245
    PARAMS['ServoFile|GenEff']      = 0.95
    PARAMS['InflowFile|HWindSpeed'] = 8
    templateReplace(PARAMS,ref_dir,RemoveRefSubFiles=True)

