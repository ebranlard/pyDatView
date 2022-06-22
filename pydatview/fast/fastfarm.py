import os
import glob
import numpy as np
import pandas as pd
from pydatview.io.fast_input_file import FASTInputFile
from pydatview.io.fast_output_file import FASTOutputFile
from pydatview.io.turbsim_file import TurbSimFile

from . import fastlib

# --------------------------------------------------------------------------------}
# --- Small helper functions
# --------------------------------------------------------------------------------{
def insertTN(s,i,nWT=1000):
    """ insert turbine number in name """
    if nWT<10:
        fmt='{:d}'
    elif nWT<100:
        fmt='{:02d}'
    else:
        fmt='{:03d}'
    if s.find('T1')>=0:
        s=s.replace('T1','T'+fmt.format(i))
    else:
        sp=os.path.splitext(s)
        s=sp[0]+'_T'+fmt.format(i)+sp[1]
    return s
def forceCopyFile (sfile, dfile):
    # ---- Handling error due to wrong mod
    if os.path.isfile(dfile):
        if not os.access(dfile, os.W_OK):
            os.chmod(dfile, stat.S_IWUSR)
    #print(sfile, ' > ', dfile)
    shutil.copy2(sfile, dfile)

# --------------------------------------------------------------------------------}
# --- Tools to create fast farm simulations
# --------------------------------------------------------------------------------{
def writeFSTandDLL(FstT1Name, nWT):
    """ 
    Write FST files for each turbine, with different ServoDyn files and DLL 
    FST files, ServoFiles, and DLL files will be written next to their turbine 1
    files, with name Ti. 

    FstT1Name: absolute or relative path to the Turbine FST file
    """ 

    FstT1Full = os.path.abspath(FstT1Name).replace('\\','/')
    FstDir  = os.path.dirname(FstT1Full)

    fst=FASTInputFile(FstT1Name)
    SrvT1Name    = fst['ServoFile'].strip('"')
    SrvT1Full    = os.path.join(FstDir, SrvT1Name).replace('\\','/')
    SrvDir       = os.path.dirname(SrvT1Full)
    SrvT1RelFst  = os.path.relpath(SrvT1Full,FstDir)
    if os.path.exists(SrvT1Full):
        srv=FASTInputFile(SrvT1Full)
        DLLT1Name = srv['DLL_FileName'].strip('"')
        DLLT1Full = os.path.join(SrvDir, DLLT1Name)
        if os.path.exists(DLLT1Full):
            servo=True
        else:
            print('[Info] DLL file not found, not copying servo and dll files ({})'.format(DLLT1Full))
            servo=False
    else:
        print('[Info] ServoDyn file not found, not copying servo and dll files ({})'.format(SrvT1Full))
        servo=False

    #print(FstDir)
    #print(FstT1Full)
    #print(SrvT1Name)
    #print(SrvT1Full)
    #print(SrvT1RelFst)

    for i in np.arange(2,nWT+1):
        FstName     = insertTN(FstT1Name,i,nWT)
        if servo:
            # TODO handle the case where T1 not present
            SrvName     = insertTN(SrvT1Name,i,nWT)
            DLLName     = insertTN(DLLT1Name,i,nWT)
            DLLFullName = os.path.join(SrvDir, DLLName)

        print('')
        print('FstName: ',FstName)
        if servo:
            print('SrvName: ',SrvName)
            print('DLLName: ',DLLName)
            print('DLLFull: ',DLLFullName)

        # Changing main file
        if servo:
            fst['ServoFile']='"'+SrvName+'"'
        fst.write(FstName)
        if servo:
            # Changing servo file
            srv['DLL_FileName']='"'+DLLName+'"'
            srv.write(SrvName)
            # Copying dll
            forceCopyFile(DLLT1Full, DLLFullName)



def rectangularLayoutSubDomains(D,Lx,Ly):
    """ Retuns position of turbines in a rectangular layout 
    TODO, unfinished function parameters
    """
    # --- Parameters
    D          = 112  # turbine diameter [m]
    Lx         = 3840 # x dimension of precusor
    Ly         = 3840 # y dimension of precusor
    Height     = 0    # Height above ground, likely 0 [m]
    nDomains_x = 2    # number of domains in x
    nDomains_y = 2    # number of domains in y
    # --- 36 WT
    nx         = 3    # number of turbines to be placed along x in one precursor domain
    ny         = 3    # number of turbines to be placed along y in one precursor domain
    StartX     = 1/2  # How close do we start from the x boundary
    StartY     = 1/2  # How close do we start from the y boundary
    # --- Derived parameters
    Lx_Domain = Lx * nDomains_x   # Full domain size
    Ly_Domain = Ly * nDomains_y
    DeltaX = Lx / (nx)          # Turbine spacing
    DeltaY = Ly / (ny)
    xWT = np.arange(DeltaX*StartX,Lx_Domain,DeltaX) # Turbine positions 
    yWT = np.arange(DeltaY*StartY,Ly_Domain,DeltaY)

    print('Full domain size [D]  :  {:.2f} x {:.2f}  '.format(Lx_Domain/D, Ly_Domain/D))
    print('Turbine spacing  [D]  : {:.2f} x  {:.2f} '.format(DeltaX/D,DeltaX/D))
    print('Number of turbines    : {:d} x {:d} = {:d}'.format(len(xWT),len(yWT),len(xWT)*len(yWT)))

    XWT,YWT=np.meshgrid(xWT,yWT)
    ZWT=XWT*0+Height

    # --- Export coordinates only
    M=np.column_stack((XWT.ravel(),YWT.ravel(),ZWT.ravel()))
    np.savetxt('Farm_Coordinates.csv', M, delimiter=',',header='X_[m], Y_[m], Z_[m]')
    print(M)

    return XWT, YWT, ZWT

def fastFarmTurbSimExtent(TurbSimFilename, HubHeight, D, xWT, yWT, Cmeander=1.9, Chord_max=3, extent_X=1.2, extent_Y=1.2):
    """ 
    Determines "Ambient Wind" box parametesr for FastFarm, based on a TurbSimFile ('bts')
    """
    # --- TurbSim data
    ts      = TurbSimFile(TurbSimFilename)
    #iy,iz   = ts.closestPoint(y=0,z=HubHeight)
    #iy,iz   = ts.closestPoint(y=0,z=HubHeight)
    zMid, uMid =  ts.midValues()
    #print('uMid',uMid)
    #meanU   = ts['u'][0,:,iy,iz].mean()
    meanU   = uMid
    dY_High = ts['y'][1]-ts['y'][0]
    dZ_High = ts['z'][1]-ts['z'][0]
    Z0_Low  = ts['z'][0]
    Z0_High = ts['z'][0] # we start at lowest to include tower
    Width   = ts['y'][-1]-ts['y'][0]
    Height  = ts['z'][-1]-ts['z'][0]
    dT_High = ts['dt']
    #effSimLength = ts['t'][-1]-ts['t'][0] + Width/meanU
    effSimLength = ts['t'][-1]-ts['t'][0]

    # Desired resolution, rule of thumbs
    dX_High_desired = Chord_max             
    dX_Low_desired  = Cmeander*D*meanU/150.0
    dt_des          = Cmeander*D/(10.0*meanU)

    # --- High domain
    ZMax_High = HubHeight+extent_Y*D/2.0
    # high-box extent in x and y [D]
    Xdist_High = extent_X*D
    Ydist_High = extent_Y*D
    Zdist_High = ZMax_High-Z0_High # we include the tower
    X0_rel     = Xdist_High/2.0
    Y0_rel     = Ydist_High/2.0
    Length     = effSimLength*meanU
    nx         = int(round(effSimLength/dT_High))
    dx_TS      = Length/(nx-1)
    #print('dx_TS',dx_TS)
    dX_High    = round(dX_High_desired/dx_TS)*dx_TS
    #print('dX_High_desired',dX_High_desired, dX_High)
    
    nX_High = int(round(Xdist_High/dX_High)+1)
    nY_High = int(round(Ydist_High/dY_High)+1)
    nZ_High = int(round(Zdist_High/dZ_High)+1)

    # --- High extent per turbine
    nTurbs = len(xWT)
    X0_des = np.asarray(xWT)-X0_rel
    Y0_des = np.asarray(yWT)-Y0_rel
    X0_High = np.around(np.round(X0_des/dX_High)*dX_High,3)
    Y0_High = np.around(np.round(Y0_des/dY_High)*dY_High,3)

    # --- Low domain
    dT_Low = round(dt_des/dT_High)*dT_High
    dx_des = dX_Low_desired
    dy_des = dX_Low_desired
    dz_des = dX_Low_desired
    X0_Low = round( (min(xWT)-2*D)/dX_High) *dX_High
    Y0_Low = round( -Width/2      /dY_High) *dY_High
    dX_Low = round( dx_des        /dX_High)*dX_High
    dY_Low = round( dy_des        /dY_High)*dY_High
    dZ_Low = round( dz_des        /dZ_High)*dZ_High
    Xdist  = max(xWT)+8.0*D-X0_Low  # Maximum extent
    Ydist  = Width
    Zdist  = Height
    #print('dX_Low',dX_Low, dX_Low/dx_TS, dX_High/dx_TS)

    nX_Low = int(Xdist/dX_Low)+1; 
    nY_Low = int(Ydist/dY_Low)+1;
    nZ_Low = int(Zdist/dZ_Low)+1;

    if (nX_Low*dX_Low>Xdist):
        nX_Low=nX_Low-1 
    if (nY_Low*dY_Low>Ydist):
        nY_Low=nY_Low-1 
    if (nZ_Low*dZ_Low>Zdist):
        nZ_Low=nZ_Low-1 

    d = dict()
    d['DT']      = np.around(dT_Low ,3)
    d['DT_High'] = np.around(dT_High,3)
    d['NX_Low']  = int(nX_Low)
    d['NY_Low']  = int(nY_Low)
    d['NZ_Low']  = int(nZ_Low)
    d['X0_Low']  = np.around(X0_Low,3)
    d['Y0_Low']  = np.around(Y0_Low,3)
    d['Z0_Low']  = np.around(Z0_Low,3)
    d['dX_Low']  = np.around(dX_Low,3)
    d['dY_Low']  = np.around(dY_Low,3)
    d['dZ_Low']  = np.around(dZ_Low,3)
    d['NX_High'] = int(nX_High)
    d['NY_High'] = int(nY_High)
    d['NZ_High'] = int(nZ_High)
    # --- High extent info for turbine outputs
    d['dX_High'] = np.around(dX_High,3)
    d['dY_High'] = np.around(dY_High,3)
    d['dZ_High'] = np.around(dZ_High,3)
    d['X0_High'] = X0_High
    d['Y0_High'] = Y0_High
    d['Z0_High'] = np.around(Z0_High,3)

    return d

def writeFastFarm(outputFile, templateFile, xWT, yWT, zWT, FFTS=None, OutListT1=None):
    """ Write FastFarm input file based on a template, a TurbSimFile and the Layout
    
    outputFile: .fstf file to be written
    templateFile: .fstf file that will be used to generate the output_file
    XWT,YWT,ZWT: positions of turbines
    FFTS: FastFarm TurbSim parameters as returned by fastFarmTurbSimExtent
    """
    # --- Read template fast farm file
    fst=FASTInputFile(templateFile)
    # --- Replace box extent values
    if FFTS is not None:
        fst['Mod_AmbWind'] = 2
        for k in ['DT', 'DT_High', 'NX_Low', 'NY_Low', 'NZ_Low', 'X0_Low', 'Y0_Low', 'Z0_Low', 'dX_Low', 'dY_Low', 'dZ_Low', 'NX_High', 'NY_High', 'NZ_High']:
            if isinstance(FFTS[k],int):
                fst[k] = FFTS[k] 
            else:
                fst[k] = np.around(FFTS[k],3)
        fst['WrDisDT'] = FFTS['DT']

    # --- Set turbine names, position, and box extent
    nWT = len(xWT)
    fst['NumTurbines'] = nWT
    if FFTS is not None:
        nCol= 10
    else:
        nCol = 4
    ref_path = fst['WindTurbines'][0,3]
    WT = np.array(['']*nWT*nCol,dtype='object').reshape((nWT,nCol))
    for iWT,(x,y,z) in enumerate(zip(xWT,yWT,zWT)):
        WT[iWT,0]=x
        WT[iWT,1]=y
        WT[iWT,2]=z
        WT[iWT,3]=insertTN(ref_path,iWT+1,nWT)
        if FFTS is not None:
            WT[iWT,4]=FFTS['X0_High'][iWT]
            WT[iWT,5]=FFTS['Y0_High'][iWT]
            WT[iWT,6]=FFTS['Z0_High']
            WT[iWT,7]=FFTS['dX_High']
            WT[iWT,8]=FFTS['dY_High']
            WT[iWT,9]=FFTS['dZ_High']
    fst['WindTurbines']=WT

    fst.write(outputFile)
    if OutListT1 is not None:
        setFastFarmOutputs(outputFile, OutListT1)

def setFastFarmOutputs(fastFarmFile, OutListT1):
    """ Duplicate the output list, by replacing "T1" with T1->Tn """
    fst = FASTInputFile(fastFarmFile)
    nWTOut = min(fst['NumTurbines'],9) # Limited to 9 turbines
    OutList=['']
    for s in OutListT1:
        s=s.strip('"')  
        if s.find('T1'):
            OutList+=['"'+s.replace('T1','T{:d}'.format(iWT+1))+'"' for iWT in np.arange(nWTOut) ]
        else:
            OutList+='"'+s+'"'
    fst['OutList']=OutList
    fst.write(fastFarmFile)


def plotFastFarmSetup(fastFarmFile):
    """ """
    import matplotlib.pyplot as plt
    fst=FASTInputFile(fastFarmFile)

    fig = plt.figure(figsize=(13.5,10))
    ax  = fig.add_subplot(111,aspect="equal")

    WT=fst['WindTurbines']
    x       = WT[:,0].astype(float)
    y       = WT[:,1].astype(float)

    if fst['Mod_AmbWind'] == 2:
        xmax_low = fst['X0_Low']+fst['DX_Low']*fst['NX_Low']
        ymax_low = fst['Y0_Low']+fst['DY_Low']*fst['NY_Low']
        # low-res box
        ax.plot([fst['X0_Low'],xmax_low,xmax_low,fst['X0_Low'],fst['X0_Low']],
                [fst['Y0_Low'],fst['Y0_Low'],ymax_low,ymax_low,fst['Y0_Low']],'--k',lw=2,label='Low')
        X0_High = WT[:,4].astype(float)
        Y0_High = WT[:,5].astype(float)
        dX_High = WT[:,7].astype(float)[0]
        dY_High = WT[:,8].astype(float)[0]
        nX_High = fst['NX_High']
        nY_High = fst['NY_High']
        # high-res boxes
        for wt in range(len(x)):
            xmax_high = X0_High[wt]+dX_High*nX_High
            ymax_high = Y0_High[wt]+dY_High*nY_High
            ax.plot([X0_High[wt],xmax_high,xmax_high,X0_High[wt],X0_High[wt]],
                    [Y0_High[wt],Y0_High[wt],ymax_high,ymax_high,Y0_High[wt]],
                    '-',
                    label="HighT{0}".format(wt+1))
            ax.plot(x[wt],y[wt],'x',ms=8,mew=2,label="WT{0}".format(wt+1))
    else:
        for wt in range(len(x)):
            ax.plot(x[wt],y[wt],'x',ms=8,mew=2,label="WT{0}".format(wt+1))
        # 
    plt.legend(bbox_to_anchor=(1.05,1.015),frameon=False)
    ax.set_xlabel("x-location [m]")
    ax.set_ylabel("y-location [m]")
    fig.tight_layout
    # fig.savefig('FFarmLayout.pdf',bbox_to_inches='tight',dpi=500)

# --------------------------------------------------------------------------------}
# --- Tools for postpro 
# --------------------------------------------------------------------------------{

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
        df=FASTOutputFile(fastfarm_out).toDataFrame()

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
        main=FASTInputFile(fastfarm_input)
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

