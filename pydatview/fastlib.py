
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

def run_fastfiles(fastfiles, fastExe=None, parallel=True, ShowOutputs=True, nCores=None, ShowCommand=True):
    if fastExe is None:
        fastExe=FAST_EXE
    return run_cmds(fastfiles, fastExe, parallel=parallel, ShowOutputs=ShowOutputs, nCores=nCores, ShowCommand=ShowCommand)

def run_fast(input_file, fastExe=None, wait=True, ShowOutputs=False, ShowCommand=True):
    if fastExe is None:
        fastExe=FAST_EXE
    return run_cmd(input_file, fastExe, wait=wait, ShowOutputs=ShowOutputs, ShowCommand=ShowCommand)


def writeBatch(batchfile, fastfiles, fastExe=None):
    if fastExe is None:
        fastExe=FAST_EXE
    with open(batchfile,'w') as f:
        for l in [fastExe + ' '+ os.path.basename(f) for f in fastfiles]:
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
        return np.array([])
    if type(ED['BldGagNd']) is list:
        Inodes = np.asarray(ED['BldGagNd'])
    else:
        Inodes = np.array([ED['BldGagNd']])
    r_gag = r_nodes[ Inodes[:nOuts] -1]
    return r_gag

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

def AD_BldGag(AD,AD_bld):
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
        AD_bld = weio.FASTInFile(AD_bld)
    #print(AD_bld.keys())

    nOuts=AD['NBlOuts']
    if nOuts<=0:
        return np.array([])
    INodes = np.array(AD['BlOutNd'][:nOuts])
    r_gag = AD_bld['BldAeroNodes'][INodes-1,0]
    return r_gag

# 
# 
# 1, 7, 14, 21, 30, 36, 43, 52, 58 BldGagNd List of blade nodes that have strain gages [1 to BldNodes] (-) [unused if NBlGages=0]

def spanwise(tsAvg,vr_bar,R,postprofile=None):
    nr=len(vr_bar)
    Columns     = [('r/R_[-]', vr_bar)]
    Columns.append(extractSpanTS(tsAvg,nr,'Spn{:d}FLxb1_[kN]'   ,'FLxb1_[kN]'))
    Columns.append(extractSpanTS(tsAvg,nr,'Spn{:d}MLyb1_[kN-m]' ,'MLxb1_[kN-m]'  ))
    Columns.append(extractSpanTS(tsAvg,nr,'Spn{:d}MLxb1_[kN-m]' ,'MLyb1_[kN-m]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'Spn{:d}MLzb1_[kN-m]' ,'MLzb1_[kN-m]'   ))
    Columns.append(('r_[m]', vr_bar*R))

    data     = np.column_stack([c for _,c in Columns if c is not None])
    ColNames = [n for n,_ in Columns if n is not None]

    # --- Export to dataframe and csv
    if len(ColNames)<=2:
        print('[WARN] No elastodyn spanwise data found.')
        return None
    else:
        dfRad = pd.DataFrame(data= data, columns = ColNames)
        if postprofile is not None:
            dfRad.to_csv(postprofile,sep='\t',index=False)
    return dfRad

def spanwiseAD(tsAvg,vr_bar,rho,R,nB,postprofile=None,IR=None):
    nr=len(vr_bar)
    Columns     = [('r/R_[-]', vr_bar)]
    # --- Extract radial data
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Alpha_[deg]','B1Alpha_[deg]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}AxInd_[-]'  ,'B1AxInd_[-]'  ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}TnInd_[-]'  ,'B1TnInd_[-]'  ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Cl_[-]'     ,'B1Cl_[-]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Cd_[-]'     ,'B1Cd_[-]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Cm_[-]'     ,'B1Cm_[-]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Cx_[-]'     ,'B1Cx_[-]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Cy_[-]'     ,'B1Cy_[-]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Cn_[-]'     ,'B1Cn_[-]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Ct_[-]'     ,'B1Ct_[-]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Re_[-]' ,'B1Re_[-]' ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Vrel_[m/s]' ,'B1Vrel_[m/s]' ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Theta_[deg]','B1Theta_[deg]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Phi_[deg]','B1Phi_[deg]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Curve_[deg]','B1Curve_[deg]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Vindx_[m/s]','B1Vindx_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Vindy_[m/s]','B1Vindy_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Fx_[N/m]'   ,'B1Fx_[N/m]'   ))
    # Adding Ct value
    if Columns[-1][1] is not None:
        try:
            r=vr_bar*R
            Fx =Columns[-1][1]
            U0=tsAvg['Wind1VelX_[m/s]']
            Ct=nB*Fx/(0.5 * rho * 2 * U0**2 * np.pi * r)
            Ct[vr_bar<0.01] = 0
            Columns.append(('B1Ct_[-]', Ct))
        except:
            pass
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Fy_[N/m]'   ,'B1Fy_[N/m]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Fl_[N/m]'   ,'B1Fl_[N/m]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Fd_[N/m]'   ,'B1Fd_[N/m]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Fn_[N/m]'   ,'B1Fn_[N/m]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Ft_[N/m]'   ,'B1Ft_[N/m]'   ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}VUndx_[m/s]','B1VUndx_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}VUndy_[m/s]','B1VUndy_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}VUndz_[m/s]','B1VUndz_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}VDisx_[m/s]','B1VDisx_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}VDisy_[m/s]','B1VDisy_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}VDisz_[m/s]','B1VDisz_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Vx_[m/s]','B1Vx_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Vy_[m/s]','B1Vy_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Vz_[m/s]','B1Vz_[m/s]'))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}DynP_[Pa]' ,'B1DynP_[Pa]' ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}M_[-]' ,'B1M_[-]' ))
    Columns.append(extractSpanTS(tsAvg,nr,'B1N{:d}Mm_[N-m/m]'   ,'B1Mm_[N-m/m]'   ))

    # AD 14
    Columns.append(extractSpanTS(tsAvg,nr,'Alpha{:02d}_[deg]'    ,'Alpha_[deg]'  ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'DynPres{:02d}_[Pa]'   ,'DynPres_[Pa]' ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'CLift{:02d}_[-]'      ,'CLift_[-]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'CDrag{:02d}_[-]'      ,'CDrag_[-]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'CNorm{:02d}_[-]'      ,'CNorm_[-]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'CTang{:02d}_[-]'      ,'CTang_[-]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'CMomt{:02d}_[-]'      ,'CMomt_[-]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'Pitch{:02d}_[deg]'    ,'Pitch_[deg]'  ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'AxInd{:02d}_[-]'      ,'AxInd_[-]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'TanInd{:02d}_[-]'     ,'TanInd_[-]'   ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'ForcN{:02d}_[N]'      ,'ForcN_[N]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'ForcT{:02d}_[N]'      ,'ForcT_[N]'    ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'Pmomt{:02d}_[N-m]'    ,'Pmomt_[N-N]'  ,  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'ReNum{:02d}_[x10^6]'  ,'ReNum_[x10^6]',  IR=IR))
    Columns.append(extractSpanTS(tsAvg,nr,'Gamma{:02d}_[m^2/s]'  ,'Gamma_[m^2/s]',  IR=IR))

    Columns.append(('r_[m]', vr_bar*R))

    data     = np.column_stack([c for _,c in Columns if c is not None])
    ColNames = [n for n,_ in Columns if n is not None]

    # --- Export to dataframe and csv
    if len(ColNames)<=2:
        print('[WARN] No spanwise aero data')
        return None
    else:
        dfRad = pd.DataFrame(data= data, columns = ColNames)
        if postprofile is not None:
            dfRad.to_csv(postprofile,sep='\t',index=False)
    return dfRad



def spanwisePostPro(FST_In,avgMethod='constantwindow',avgParam=5,out_ext='.outb',postprofile=None,df=None):
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
        df    = weio.read(FST_In.replace('.fst',out_ext)).toDataFrame()
    else:
        pass
    # NOTE: spanwise script doest not support duplicate columns
    df = df.loc[:,~df.columns.duplicated()]
    dfAvg = averageDF(df,avgMethod=avgMethod ,avgParam=avgParam) # NOTE: average 5 last seconds

    # --- Extract info (e.g. radial positions) from Fast input file
    fst = weio.FASTInputDeck(FST_In)
    if fst.version == 'F7':
        # --- FAST7
        if  not hasattr(fst,'AD'):
            raise Exception('The AeroDyn file couldn''t be found or read, from main file: '+FST_In)
        r_FST_aero,IR   = AD14_BldGag(fst.AD)
        R   = fst.fst['TipRad']
        try:
            rho = fst.AD['Rho']
        except:
            rho = fst.AD['AirDens']
        r_FST_struct = None
    else:
        # --- OpenFAST 2
        if  not hasattr(fst,'ED'):
            raise Exception('The Elastodyn file couldn''t be found or read, from main file: '+FST_In)
        if  not hasattr(fst,'AD'):
            raise Exception('The AeroDyn file couldn''t be found or read, from main file: '+FST_In)

        if fst.ADversion == 'AD15':
            if  not hasattr(fst.AD,'Bld1'):
                raise Exception('The AeroDyn blade file couldn''t be found or read, from main file: '+FST_In)
            rho        = fst.AD['AirDens']
            r_FST_aero = AD_BldGag(fst.AD,fst.AD.Bld1) + fst.ED['HubRad']
            IR         = None

        elif fst.ADversion == 'AD14':
            try:
                rho = fst.AD['Rho']
            except:
                rho = fst.AD['AirDens']
            r_FST_aero,IR   = AD14_BldGag(fst.AD)

        else:
            raise Exception('AeroDyn version unknown')

        R   = fst.ED ['TipRad']
        r_FST_struct = ED_BldGag(fst.ED)
        #print('r struct:',r_FST_struct)
        #print('r aero  :',r_FST_aero)
        #print('IR      :',IR)

        # --- Extract radial data and export to csv if needed
        dfAeroRad   = spanwiseAD(dfAvg.iloc[0], r_FST_aero/R, rho , R, nB=3, postprofile=postprofile, IR=IR)
        if r_FST_struct is None:
            dfStructRad=None
        else:
            dfStructRad = spanwise(dfAvg.iloc[0]  , r_FST_struct/R, R=R, postprofile=postprofile)

    return dfStructRad , dfAeroRad



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


def templateReplaceGeneral(template_dir, PARAMS, workdir=None, main_file=None, name_function=None, RemoveAllowed=False):
    """ Replace parameters in a fast folder using a list of dictionaries where the keys are for instance:
        'FAST|DT', 'EDFile|GBRatio', 'ServoFile|GenEff'
    """
    def fileID(s):
        if s.find('|')<=0:
            return 'ROOT'
        else:
            return s.split('|')[0]
    def basename(s):
        return os.path.splitext(os.path.basename(s))[0]
    def rebase(s,sid):
        split = os.path.splitext(os.path.basename(s))
        return os.path.join(workdir,split[0]+sid+split[1])
    def rebase_rel(s,sid):
        split = os.path.splitext(s)
        return os.path.join(workdir,split[0]+sid+split[1])
    # --- Saafety checks
    if not os.path.exists(template_dir):
        raise Exception('Template directory does not exist: '+template_dir)

    # Default value of workdir if not provided
    if template_dir[-1]=='/'  or template_dir[-1]=='\\' :
        template_dir=template_dir[0:-1]
    if workdir is None:
        workdir=template_dir+'_Parametric'

    # Copying template folder to workdir
    if os.path.exists(workdir) and RemoveAllowed:
        shutil.rmtree(workdir, ignore_errors=False, onerror=handleRemoveReadonlyWin)
    copyTree(template_dir, workdir)

    # --- Fast main file use as "master"
    main_file=os.path.join(workdir, os.path.basename(main_file))

    # Params need to be a list
    if not isinstance(PARAMS,list):
        PARAMS=[PARAMS]

    files=[]
    # TODO: Recursive loop splitting at the pipes '|', for now only 1 level supported...
    for ip,p in enumerate(PARAMS):
        if '__index__' not in p.keys():
            p['__index__']=ip
        if name_function is None:
            if '__name__' in p.keys():
                strID=p['__name__']
            else:
                raise Exception('When calling `templateReplace`, either provide a naming function or profile the key `__name_` in the parameter dictionaries')
        else:
            strID =name_function(p)
        FileTypes = set([fileID(k) for k in list(p.keys()) if (k!='__index__' and k!='__name__')])
        FileTypes = set(list(FileTypes)+['ROOT']) # Enforcing ROOT in list, so the main file is written

        # ---Copying main file and reading it
        #fst_full = rebase(main_file,strID)
        ext = os.path.splitext(main_file)[-1]
        fst_full = os.path.join(workdir,strID+ext)
        shutil.copyfile(main_file, fst_full )
        Files=dict()
        Files['ROOT']=weio.FASTInFile(fst_full)
        # --- Looping through required files and opening them
        for t in FileTypes: 
            # Doing a naive if
            # The reason is that we want to account for more complex file types in the future
            if t=='ROOT':
                continue
            org_filename      = Files['ROOT'][t].strip('"')
            org_filename_full = os.path.join(workdir,org_filename)
            new_filename_full = rebase_rel(org_filename,'_'+strID)
            new_filename      = os.path.relpath(new_filename_full,workdir)
#             print('org_filename',org_filename)
#             print('org_filename',org_filename_full)
#             print('New_filename',new_filename_full)
#             print('New_filename',new_filename)
            shutil.copyfile(org_filename_full, new_filename_full)
            Files['ROOT'][t] = '"'+new_filename+'"'
            # Reading files
            Files[t]=weio.FASTInFile(new_filename_full)
        # --- Replacing in files
        for k,v in p.items():
            if k =='__index__' or k=='__name__':
                continue
            sp= k.split('|')
            kk=sp[0]
            if len(sp)==1:
                Files['ROOT'][kk]=v
            elif len(sp)==2:
                Files[sp[0]][sp[1]]=v
            else:
                raise Exception('Multi-level not supported')
        # --- Rewritting all files
        for t in FileTypes:
            Files[t].write()

        files.append(fst_full)
    # --- Remove extra files at the end
    os.remove(main_file)

    return files

def templateReplace(template_dir, PARAMS, workdir=None, main_file=None, name_function=None, RemoveAllowed=False, RemoveRefSubFiles=False):
    """ Replace parameters in a fast folder using a list of dictionaries where the keys are for instance:
        'FAST|DT', 'EDFile|GBRatio', 'ServoFile|GenEff'
    """
    def fileID(s):
        return s.split('|')[0]
    def basename(s):
        return os.path.splitext(os.path.basename(s))[0]
    def rebase(s,sid):
        split = os.path.splitext(os.path.basename(s))
        return os.path.join(workdir,split[0]+sid+split[1])
    def rebase_rel(s,sid):
        split = os.path.splitext(s)
        return os.path.join(workdir,split[0]+sid+split[1])
    # --- Saafety checks
    if not os.path.exists(template_dir):
        raise Exception('Template directory does not exist: '+template_dir)

    # Default value of workdir if not provided
    if template_dir[-1]=='/'  or template_dir[-1]=='\\' :
        template_dir=template_dir[0:-1]
    if workdir is None:
        workdir=template_dir+'_Parametric'

    # Copying template folder to workdir
    if os.path.exists(workdir) and RemoveAllowed:
        shutil.rmtree(workdir, ignore_errors=False, onerror=handleRemoveReadonlyWin)
#     distutils.dir_util.copy_tree(template_dir, workdir)
    #distutils.dir_util.copy_tree(template_dir, workdir)
    #shutil.copytree(template_dir, workdir, ignore=ignore_patterns('.git'))
    #files=glob.glob(os.path.join(template_dir,'*'))
    #for f in files:
    #    if os.path.isdir(f):
    #        subfold=os.path.basename(f)
    #        print('Copying subdirectory ',f,subfold)
    #        copyTree(f, os.path.join(workdir,subfold))
    copyTree(template_dir, workdir)
    if RemoveAllowed:
        removeFASTOuputs(workdir)

    # --- Fast main file use as "master"
    if main_file is None:
        FstFiles=set(glob.glob(os.path.join(template_dir,'*.fst'))+glob.glob(os.path.join(template_dir,'*.FST')))
        if len(FstFiles)>1:
            print(FstFiles)
            raise Exception('More than one fst file found in template folder, provide `main_file` or ensure there is only one `.fst` file') 
        main_file=rebase(FstFiles.pop(),'')
    else:
        #main_file=os.path.join(template_dir, os.path.basename(main_file))
        main_file=os.path.join(workdir, os.path.basename(main_file))

    # Params need to be a list
    if not isinstance(PARAMS,list):
        PARAMS=[PARAMS]

    fastfiles=[]
    # TODO: Recursive loop splitting at the pipes '|', for now only 1 level supported...
    for ip,p in enumerate(PARAMS):
        if '__index__' not in p.keys():
            p['__index__']=ip
        if name_function is None:
            if '__name__' in p.keys():
                strID=p['__name__']
            else:
                raise Exception('When calling `templateReplace`, either provide a naming function or profile the key `__name_` in the parameter dictionaries')
        else:
            strID =name_function(p)
        FileTypes = set([fileID(k) for k in list(p.keys()) if (k!='__index__' and k!='__name__')])
        FileTypes = set(list(FileTypes)+['FAST']) # Enforcing FAST in list, so the main fst file is written

        # ---Copying main file and reading it
        #fst_full = rebase(main_file,strID)
        fst_full = os.path.join(workdir,strID+'.fst')
        shutil.copyfile(main_file, fst_full )
        Files=dict()
        Files['FAST']=weio.FASTInFile(fst_full)
        # 
#         fst=weio.FASTInputDeck(main_file)
#         for k,v in fst.inputfiles.items():
#             rel = os.path.relpath(v,template_dir)
#             if rel.find('/')<0 or rel.find('\\')<0:
#                 print('Copying ',k,rel)
#                 shutil.copyfile(os.path.join(template_dir,rel), os.path.join(workdir,rel))

        # --- Looping through required files and opening them
        for t in FileTypes: 
            # Doing a naive if
            # The reason is that we want to account for more complex file types in the future
            if t=='FAST':
                continue
            org_filename   = Files['FAST'][t].strip('"')
#             org_filename_full =os.path.join(template_dir,org_filename)
            org_filename_full =os.path.join(workdir,org_filename)
            new_filename_full = rebase_rel(org_filename,'_'+strID)
            new_filename      = os.path.relpath(new_filename_full,workdir)
#             print('org_filename',org_filename)
#             print('org_filename',org_filename_full)
#             print('New_filename',new_filename_full)
#             print('New_filename',new_filename)
            shutil.copyfile(org_filename_full, new_filename_full)
            Files['FAST'][t] = '"'+new_filename+'"'
            # Reading files
#             Files[t]=weio.FASTInFile(org_filename_full)
            Files[t]=weio.FASTInFile(new_filename_full)
        # --- Replacing in files
        for k,v in p.items():
            if k =='__index__' or k=='__name__':
                continue
            t,kk=k.split('|')
            Files[t][kk]=v
            #print(t+'|'+kk+'=',v)
        # --- Rewritting all files
        for t in FileTypes:
            Files[t].write()

        fastfiles.append(fst_full)
    # --- Remove extra files at the end
    if RemoveRefSubFiles:
        FST = weio.FASTInFile(main_file)
        for t in FileTypes:
            if t=='FAST':
                continue
            filename   = FST[t].strip('"')
            #fullname   = rebase(filename,'')
            fullname   = os.path.join(workdir,filename)
            os.remove(fullname)
    os.remove(main_file)

    return fastfiles


# --------------------------------------------------------------------------------}
# --- Tools for template replacement 
# --------------------------------------------------------------------------------{
def paramsSteadyAero(p=dict()):
    p['AeroFile|AFAeroMod']=1 # remove dynamic effects dynamic
    #p['AeroFile|TwrPotent']=0 # remove tower shadow
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
    # --- Naming function appropriate for such parametric study
    def default_naming(p): # TODO TODO CHANGE ME
        return '{:03d}_ws{:04.1f}_pt{:04.2f}_om{:04.2f}'.format(p['__index__'],p['InflowFile|HWindSpeed'],p['EDFile|BlPitch(1)'],p['EDFile|RotSpeed'])

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
        p['__name__']   = default_naming(p)
        i=i+1
        PARAMS.append(p)
    return PARAMS, default_naming


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
        tEnd = time[iBef[-1]]
        if avgParam is None:
            tStart=time[iBef[0]]
        else:
            avgParam=int(avgParam) 
            if len(iBef)-1<avgParam:
                print('[WARN] Not enough periods found ({}) compared to number requested to average ({})!'.format(len(iBef)-1,avgParam))
                avgParam=len(iBef)-1
               
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
          fastExe=None,ShowOutputs=True,nCores=4): # execution options
    """ Computes CP and CT as function of tip speed ratio (lambda) and pitch.
    There are two main ways to define the inputs:
      - Option 1: provide Lambda and Pitch (deg)
      - Option 2: provide WS (m/s), Omega (in rpm) and Pitch (deg), in which case len(WS)==len(Omega)
    """

    WS_default=5 # If user does not provide a wind speed vector, wind speed used

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
    PARAMS,naming = paramsWS_RPM_Pitch(WS_flat,RPM_flat,Pitch_flat,BaseDict=BaseDict, FlatInputs=True)

    # --- Generating all files in a workdir
    workdir = refdir.strip('/').strip('\\')+'_CPLambdaPitch'
    print('>>> Generating inputs files in {}'.format(workdir))
    fastFiles=templateReplace(refdir,PARAMS,workdir=workdir,name_function=naming,RemoveRefSubFiles=True,RemoveAllowed=True,main_file=main_fastfile)

    # --- Running fast simulations
    print('>>> Running {} simulations...'.format(len(fastFiles)))
    run_fastfiles(fastFiles, ShowOutputs=ShowOutputs, fastExe=fastExe, nCores=nCores)

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
    def naming(p):
        return '_ws_'+str(p['InflowFile|HWindSpeed'])
    PARAMS                          = {}
    PARAMS['FAST|TMax']             = 10
    PARAMS['FAST|DT']               = 0.01
    PARAMS['FAST|DT_Out']           = 0.1
    PARAMS['EDFile|RotSpeed']       = 100
    PARAMS['EDFile|BlPitch(1)']     = 1
    PARAMS['EDFile|GBoxEff']        = 0.92
    PARAMS['ServoFile|VS_Rgn2K']    = 0.00038245
    PARAMS['ServoFile|GenEff']      = 0.95
    PARAMS['InflowFile|HWindSpeed'] = 8
    templateReplace(ref_dir,PARAMS,name_function=naming,RemoveRefSubFiles=True)

