from __future__ import division, print_function
import os
import collections
import glob
import pandas as pd
import numpy as np
import shutil 
import stat
import re

# --- Misc fast libraries
import pydatview.io.fast_input_file as fi
import pydatview.fast.runner as runner
import pydatview.fast.postpro as postpro
from pydatview.io.fast_wind_file import FASTWndFile

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


def forceCopyFile (sfile, dfile):
    # ---- Handling error due to wrong mod
    if os.path.isfile(dfile):
        if not os.access(dfile, os.W_OK):
            os.chmod(dfile, stat.S_IWUSR)
    #print(sfile, ' > ', dfile)
    shutil.copy2(sfile, dfile)

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


def templateReplaceGeneral(PARAMS, templateDir=None, outputDir=None, main_file=None, removeAllowed=False, removeRefSubFiles=False, oneSimPerDir=False):
    """ Generate inputs files by replacing different parameters from a template file.
    The generated files are placed in the output directory `outputDir` 
    The files are read and written using the library `weio`. 
    The template file is read and its content can be changed like a dictionary.
    Each item of `PARAMS` correspond to a set of parameters that will be replaced
    in the template file to generate one input file.

    For "FAST" input files, parameters can be changed recursively.
    

    INPUTS:
      PARAMS: list of dictionaries. Each key of the dictionary should be a key present in the 
              template file when read with `weio` (see: weio.read(main_file).keys() )

               PARAMS[0]={'DT':0.1, 'EDFile|GBRatio':1, 'ServoFile|GenEff':0.8}

      templateDir: if provided, this directory and its content will be copied to `outputDir` 
                      before doing the parametric substitution

      outputDir  : directory where files will be generated. 
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

    def rebaseFileName(org_filename, workDir, strID):
            new_filename_full = rebase_rel(workDir, org_filename,'_'+strID)
            new_filename      = os.path.relpath(new_filename_full,workDir).replace('\\','/')
            return new_filename, new_filename_full

    def replaceRecurse(templatename_or_newname, FileKey, ParamKey, ParamValue, Files, strID, workDir, TemplateFiles):
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
            newfilename      = os.path.relpath(newfilename_full,workDir).replace('\\','/')

        else:
            templatefilename              = templatename_or_newname
            templatefilename_full         = os.path.join(workDir,templatefilename)
            TemplateFiles.append(templatefilename_full)
            if FileKey=='Root':
                # Root files, we start from strID
                ext = os.path.splitext(templatefilename)[-1]
                newfilename_full = os.path.join(wd,strID+ext)
                newfilename      = strID+ext
            else:
                newfilename, newfilename_full = rebaseFileName(templatefilename, workDir, strID)
            #print('--------------------------------------------------------------')
            #print('TemplateFile    :', templatefilename)
            #print('TemplateFileFull:', templatefilename_full)
            #print('NewFile         :', newfilename)
            #print('NewFileFull     :', newfilename_full)
            shutil.copyfile(templatefilename_full, newfilename_full)
            f= fi.FASTInputFile(newfilename_full) # open the template file for that filekey 
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
            workDir = os.path.join(workDir, baseparent)

            #  
            newchildFilename, Files = replaceRecurse(child_templatefilename, NewFileKey, ChildrenKey, ParamValue, Files, strID, workDir, TemplateFiles)
            #print('Setting', FileKey, '|',NewFileKey, 'to',newchildFilename)
            f[NewFileKey] = '"'+newchildFilename+'"'

        return newfilename, Files


    # --- Safety checks
    if templateDir is None and outputDir is None:
        raise Exception('Provide at least a template directory OR an output directory')

    if templateDir is not None:
        if not os.path.exists(templateDir):
            raise Exception('Template directory does not exist: '+templateDir)

        # Default value of outputDir if not provided
        if templateDir[-1]=='/'  or templateDir[-1]=='\\' :
            templateDir=templateDir[0:-1]
        if outputDir is None:
            outputDir=templateDir+'_Parametric'

    # --- Main file use as "master"
    if templateDir is not None:
        main_file=os.path.join(outputDir, os.path.basename(main_file))
    else:
        main_file=main_file

    # Params need to be a list
    if not isinstance(PARAMS,list):
        PARAMS=[PARAMS]

    if oneSimPerDir:
        workDirS=[os.path.join(outputDir,get_strID(p)) for p in PARAMS]
    else:
        workDirS=[outputDir]*len(PARAMS)
    # --- Creating outputDir - Copying template folder to outputDir if necessary
    # Copying template folder to workDir
    for wd in list(set(workDirS)):
        if removeAllowed:
            removeFASTOuputs(wd)
        if os.path.exists(wd) and removeAllowed:
            shutil.rmtree(wd, ignore_errors=False, onerror=handleRemoveReadonlyWin)
        copyTree(templateDir, wd)
        if removeAllowed:
            removeFASTOuputs(wd)


    TemplateFiles=[]
    files=[]
    for ip,(wd,p) in enumerate(zip(workDirS,PARAMS)):
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
    if removeRefSubFiles:
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

def templateReplace(PARAMS, templateDir, outputDir=None, main_file=None, removeAllowed=False, removeRefSubFiles=False, oneSimPerDir=False):
    """ Replace parameters in a fast folder using a list of dictionaries where the keys are for instance:
        'DT', 'EDFile|GBRatio', 'ServoFile|GenEff'
    """
    # --- For backward compatibility, remove "FAST|" from the keys
    for p in PARAMS:
        old_keys=[ k for k,_ in p.items() if k.find('FAST|')==0]
        for k_old in old_keys:
            k_new=k_old.replace('FAST|','')
            p[k_new] = p.pop(k_old)
    
    return templateReplaceGeneral(PARAMS, templateDir, outputDir=outputDir, main_file=main_file, 
            removeAllowed=removeAllowed, removeRefSubFiles=removeRefSubFiles, oneSimPerDir=oneSimPerDir)

def removeFASTOuputs(workDir):
    # Cleaning folder
    for f in glob.glob(os.path.join(workDir,'*.out')):
        os.remove(f)
    for f in glob.glob(os.path.join(workDir,'*.outb')):
        os.remove(f)
    for f in glob.glob(os.path.join(workDir,'*.ech')):
        os.remove(f)
    for f in glob.glob(os.path.join(workDir,'*.sum')):
        os.remove(f)

# --------------------------------------------------------------------------------}
# --- Tools for template replacement 
# --------------------------------------------------------------------------------{
def paramsSteadyAero(p=None):
    p = dict() if p is None else p
    p['AeroFile|AFAeroMod']=1 # remove dynamic effects dynamic
    p['AeroFile|WakeMod']=1 # remove dynamic inflow dynamic
    p['AeroFile|TwrPotent']=0 # remove tower shadow
    return p

def paramsNoGen(p=None):
    p = dict() if p is None else p
    p['EDFile|GenDOF' ]  = 'False'
    return p

def paramsGen(p=None):
    p = dict() if p is None else p
    p['EDFile|GenDOF' ]  = 'True'
    return p

def paramsNoController(p=None):
    p = dict() if p is None else p
    p['ServoFile|PCMode']   = 0;
    p['ServoFile|VSContrl'] = 0;
    p['ServoFile|YCMode']   = 0;
    return p

def paramsControllerDLL(p=None):
    p = dict() if p is None else p
    p['ServoFile|PCMode']   = 5;
    p['ServoFile|VSContrl'] = 5;
    p['ServoFile|YCMode']   = 5;
    p['EDFile|GenDOF']      = 'True';
    return p


def paramsStiff(p=None):
    p = dict() if p is None else p
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

def paramsWS_RPM_Pitch(WS, RPM, Pitch, baseDict=None, flatInputs=False):
    """ 
    Generate OpenFAST "parameters" (list of dictionaries with "address")
    chaing the inputs in ElastoDyn, InflowWind for different wind speed, RPM and Pitch
    """
    # --- Ensuring everythin is an iterator
    def iterify(x):
        if not isinstance(x, collections.Iterable): x = [x]
        return x
    WS    = iterify(WS)
    RPM   = iterify(RPM)
    Pitch = iterify(Pitch)
    # --- If inputs are not flat but different vectors to length through, we flatten them (TODO: meshgrid and ravel?)
    if not flatInputs :
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
        if baseDict is None:
            p=dict()
        else:
            p = baseDict.copy()
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

def paramsLinearTrim(p=None):
    p = dict() if p is None else p

    # Set a few DOFs, move this to main file
    p['Linearize']              = True
    p['CalcSteady']             = True
    p['TrimGain']               = 1e-4
    p['TrimTol']                = 1e-5
    p['CompMooring']            = 0
    p['CompHydro']              = 0
    p['LinOutJac']              = False
    p['LinOutMod']              = False
    p['OutFmt']                 = '"ES20.12E3"'  # Important for decent resolution

    p['AeroFile|AFAeroMod']     = 1
    p['AeroFile|CavitCheck']    = 'False'
    p['AeroFile|CompAA']        = 'False'
    
    p['ServoFile|PCMode']       = 0
    p['ServoFile|VSContrl']     = 1

    p['ServoFile|CompNTMD']      = 'False'
    p['ServoFile|CompTTMD']      = 'False'

    # Set all DOFs off, enable as desired
    p['EDFile|FlapDOF1']        = 'False'
    p['EDFile|FlapDOF2']        = 'False'
    p['EDFile|EdgeDOF']         = 'False'
    p['EDFile|TeetDOF']         = 'False'
    p['EDFile|DrTrDOF']         = 'False'
    p['EDFile|GenDOF']          = 'False'
    p['EDFile|YawDOF']          = 'False'
    p['EDFile|TwFADOF1']        = 'False'
    p['EDFile|TwFADOF2']        = 'False'
    p['EDFile|TwSSDOF1']        = 'False'
    p['EDFile|TwSSDOF2']        = 'False'
    p['EDFile|PtfmSgDOF']       = 'False'
    p['EDFile|PtfmSwDOF']       = 'False'
    p['EDFile|PtfmHvDOF']       = 'False'
    p['EDFile|PtfmRDOF']        = 'False'
    p['EDFile|PtfmPDOF']        = 'False'
    p['EDFile|PtfmYDOF']        = 'False'


    return p

# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
def createStepWind(filename,WSstep=1,WSmin=3,WSmax=25,tstep=100,dt=0.5,tmin=0,tmax=999):
    f = FASTWndFile()
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
# --- Tools for typical wind turbine study 
# --------------------------------------------------------------------------------{
def CPCT_LambdaPitch(refdir,main_fastfile,Lambda=None,Pitch=np.linspace(-10,40,5),WS=None,Omega=None, # operating conditions
          TMax=20,bStiff=True,bNoGen=True,bSteadyAero=True, # simulation options
          reRun=True, 
          fastExe=None,showOutputs=True,nCores=4): # execution options
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
    fst = fi.FASTInputFile(os.path.join(refdir,main_fastfile))
    ed  = fi.FASTInputFile(os.path.join(refdir,fst['EDFile'].replace('"','')))
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
    baseDict={'TMax': TMax, 'DT': 0.01, 'DT_Out': 0.1} # NOTE: Tmax should be at least 2pi/Omega
    baseDict = paramsNoController(baseDict)
    if bStiff:
        baseDict = paramsStiff(baseDict)
    if bNoGen:
        baseDict = paramsNoGen(baseDict)
    if bSteadyAero:
        baseDict = paramsSteadyAero(baseDict)

    # --- Creating set of parameters to be changed
    # TODO: verify that RtAeroCp and RtAeroCt are present in AeroDyn outlist
    PARAMS = paramsWS_RPM_Pitch(WS_flat,RPM_flat,Pitch_flat,baseDict=baseDict, flatInputs=True)

    # --- Generating all files in a workDir
    workDir = refdir.strip('/').strip('\\')+'_CPLambdaPitch'
    print('>>> Generating inputs files in {}'.format(workDir))
    RemoveAllowed=reRun # If the user want to rerun, we can remove, otherwise we keep existing simulations
    fastFiles=templateReplace(PARAMS, refdir, outputDir=workDir,removeRefSubFiles=True,removeAllowed=RemoveAllowed,main_file=main_fastfile)

    # --- Running fast simulations
    print('>>> Running {} simulations...'.format(len(fastFiles)))
    runner.run_fastfiles(fastFiles, showOutputs=showOutputs, fastExe=fastExe, nCores=nCores, reRun=reRun)

    # --- Postpro - Computing averages at the end of the simluation
    print('>>> Postprocessing...')
    outFiles = [os.path.splitext(f)[0]+'.outb' for f in fastFiles]
    # outFiles = glob.glob(os.path.join(workDir,'*.outb'))
    ColKeepStats  = ['RotSpeed_[rpm]','BldPitch1_[deg]','RtAeroCp_[-]','RtAeroCt_[-]','Wind1VelX_[m/s]']
    result = postpro.averagePostPro(outFiles,avgMethod='periods',avgParam=1,ColKeep=ColKeepStats,ColSort='RotSpeed_[rpm]')
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


if __name__=='__main__':
    # --- Test of templateReplace
    PARAMS                          = {}
    PARAMS['TMax']             = 10
    PARAMS['__name__']             =  'MyName'
    PARAMS['DT']               = 0.01
    PARAMS['DT_Out']           = 0.1
    PARAMS['EDFile|RotSpeed']       = 100
    PARAMS['EDFile|BlPitch(1)']     = 1
    PARAMS['EDFile|GBoxEff']        = 0.92
    PARAMS['ServoFile|VS_Rgn2K']    = 0.00038245
    PARAMS['ServoFile|GenEff']      = 0.95
    PARAMS['InflowFile|HWindSpeed'] = 8
    templateReplace(PARAMS,refDir,RemoveRefSubFiles=True)

