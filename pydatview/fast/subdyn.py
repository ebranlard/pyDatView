"""
Tools for SubDyn

- Setup a FEM model, compute Guyan and CB modes
- Returns position of outputs nodes pointsMJ and pointsMNout
- Returns average dataframe for each member outputs with proper coordinates
- Get a dataframe with properties
- More todo

"""


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy
import re
# Local 
from pydatview.io.fast_input_file import FASTInputFile
from pydatview.tools.tictoc import Timer

idGuyanDamp_None     = 0
idGuyanDamp_Rayleigh = 1
idGuyanDamp_66       = 2 

class SubDyn:

    def __init__(self, sdFilename_or_data=None, TP=None):
        """ 
        Initialize a SubDyn object either with:
          - sdFilename: a subdyn input file name
          - sdData: an instance of FASTInputFile
        """

        self._graph=None
        self.File=None

        # Read SubDyn file
        if sdFilename_or_data is not None:
            if hasattr(sdFilename_or_data,'startswith'): # if string
                self.File = FASTInputFile(sdFilename_or_data)
            else:
                self.File = sdFilename_or_data

        self.M_tip=None

        # Internal
        self._graph=None
        self._mgraph=None # Member graph
        self._FEM=None
        self._beamFEM=None
        self._TP = None

    def __repr__(self):
        s='<{} object>:\n'.format(type(self).__name__)
        s+='|properties:\n'
        s+='|- File: (input file data)\n'
        s+='|- TP  : {} \n'.format(self._TP)
        s+='|* graph: (Nodes/Elements/Members)\n'
        s+='|* pointsMJ, pointsMN, pointsMNout\n'
        s+='|methods:\n'
        s+='|- memberPostPro\n'
        s+='|- setTopMass\n'
        s+='|- beamDataFrame, beamFEM, beamModes\n'
        s+='|- toYAMSData\n'
        return s

    # --------------------------------------------------------------------------------}
    # --- Functions for general FEM model (jacket, flexible floaters)
    # --------------------------------------------------------------------------------{
    def init(self, TP=None, gravity = 9.81, verbose=False):
        """
        Initialize SubDyn FEM model 

        TP: position of transition point e.g. TP=(0,0,0)
        gravity: position of transition point
        """
        if TP is None:
            if self._TP is None:
                raise Exception('SubDyn: init: Please provide TP point')
            else:
                TP = self._TP

        import welib.FEM.fem_model as femm
        BC       = 'clamped-free' # TODO Boundary condition: free-free or clamped-free

        FEMMod = self.File['FEMMod']
        if FEMMod==1:
            mainElementType='frame3d'
        elif FEMMod==2:
            mainElementType='frame3dlin'
        elif FEMMod==3:
            mainElementType='timoshenko'
        else:
            raise NotImplementedError()
        # Get graph
        nModesCB = self.File['Nmodes']

        with Timer(f'SubDyn: Running SubDyn FEM nModesCB={nModesCB}'):
            graph = self.graph
            #print('>>> graph\n',graph)
            #graph.toJSON('_GRAPH.json')
            # Convert to FEM model
            with Timer('SubDyn: From graph', silent=not verbose):
                FEM = femm.FEMModel.from_graph(self.graph, mainElementType=mainElementType, refPoint=TP, gravity=gravity)
            #model.toJSON('_MODEL.json')
            with Timer('SubDyn: Assembly', silent=not verbose):
                FEM.assembly()
            with Timer('SubDyn: Internal constraints', silent=not verbose):
                FEM.applyInternalConstraints()
                FEM.partition()
            with Timer('SubDyn: BC', silent=not verbose):
                FEM.applyFixedBC()
            with Timer('SubDyn: EIG', silent=not verbose):
                Q, freq = FEM.eig(normQ='byMax')
            self._FEM = FEM # Store

            # --- Craig Bampton reduction
            self.applyCB(nModesCB=nModesCB, verbose=verbose)


        return FEM


    def applyCB(self, nModesCB, nModesFEMStore=30, verbose=False):
        """ Apply CB reduction, set and store associated data"""
        FEM = self._FEM

        with Timer('CB', silent=not verbose):
            FEM.CraigBampton(nModesCB = nModesCB)

        with Timer('Modes', silent=not verbose):
            FEM.setModes(nModesFEM=nModesFEMStore, nModesCB=nModesCB)
#             FEM.nodesDisp(Q)

        # --- SubDyn partition/notations
        FEM.MBB = FEM.MM_CB[np.ix_(FEM.DOF_Leader_CB  , FEM.DOF_Leader_CB)]
        FEM.KBB = FEM.KK_CB[np.ix_(FEM.DOF_Leader_CB  , FEM.DOF_Leader_CB)]
        FEM.MBM = FEM.MM_CB[np.ix_(FEM.DOF_Leader_CB  , FEM.DOF_Follower_CB)]
        FEM.KMM = FEM.KK_CB[np.ix_(FEM.DOF_Follower_CB, FEM.DOF_Follower_CB)]
        zeta =self.File['JDampings']/100
        if not hasattr(zeta,'__len__'):
            zeta = [zeta]*FEM.nModesCB
            FEM.CMM = 2*np.array(zeta) * FEM.f_CB * 2 * np.pi

        # --- Matrices wrt TP point
        TI=FEM.T_refPoint
        MBBt = TI.T.dot(FEM.MBB).dot(TI)
        KBBt = TI.T.dot(FEM.KBB).dot(TI)
        MBBt[np.abs(MBBt)<1e-4] =0
        KBBt[np.abs(KBBt)<1e-4] =0
        FEM.MBBt = MBBt
        FEM.KBBt = KBBt

        # --- Set Damping
        dampMod = self.File['GuyanDampMod']  
        alpha_Rayleigh, beta_Rayleigh = None, None
        # 6x6 Guyan Damping matrix
        CC_CB_G = None
        if  dampMod == idGuyanDamp_None:
            FEM.CBBt = np.zeros((6,6))
        elif dampMod == idGuyanDamp_Rayleigh:
            # Rayleigh Damping
            alpha_Rayleigh, beta_Rayleigh = self.File['RayleighDamp']
            FEM.CBBt = alpha_Rayleigh * FEM.MBBt + beta_Rayleigh * FEM.KBBt
        elif dampMod == idGuyanDamp_66: 
            FEM.CBBt = self.File['GuyanDampMatrix']
        else:
            raise Exception()

        # --- Compute rigid body equivalent
        FEM.rigidBodyEquivalent()

        return FEM


    def setTopMass(self, Mtop=0):
        """ Mtop = 50000  # Top mass [kg] """
        # TODO
        # TODO
        # TODO
        # TODO Unfinished
        #
        #
        # Add an optional top mass and ineria
        if TopMass:
            # NOTE: you can use welib.yams.windturbine to compute RNA mass and inertia
            M_tip= rigidBodyMassMatrixAtP(m=Mtop, J_G=None, Ref2COG=None)
        else:
            M_tip=None
        self.M_tip = M_tip


    def getGraph(self, nDiv=1):
        # See welib.weio.fast_input_file_graph.py to see how SubDyn files are converted to graph 
        # See welib.fem.graph.py for Graph interface
        _graph = self.File.toGraph().divideElements(nDiv,
                    excludeDataKey='Type', excludeDataList=['Cable','Rigid'], method='insert',
                    keysNotToCopy=['IBC','RBC','addedMassMatrix'] # Very important
                    )

        if len(_graph.Members)==0:
            raise Exception('Problem in graph subdivisions, no members found.')
        # Sanitization
        #idBC_Fixed    =  0 # Fixed BC
        #idBC_Internal = 10 # Free/Internal BC
        #idBC_Leader   = 20 # Leader DOF
        MapIBC={0:0, 1:20} # 1 in the input file is leader
        MapRBC={0:10, 1:0} # 1 in the input file is fixed
        for n in _graph.Nodes:
            #print(n)
            if 'IBC' in n.data.keys():
                IBC = n.data['IBC'].copy()
                n.data['IBC'] = [MapIBC[i] for i in IBC[:6]]
            if 'RBC' in n.data.keys():
                RBC = n.data['RBC'].copy()
                n.data['RBC'] = [MapRBC[i] for i in RBC[:6]]
                if any(RBC[:6])==0:
                    print('RBC        ',RBC)
                    print('n.data[RBC]',n.data['RBC'] )
                    print('n          ',n )
                    raise NotImplementedError('SSI')

        return _graph

    @property
    def graph(self):
        if self._graph is None:
            self._graph = self.getGraph(nDiv = self.File['NDiv'])
        return copy.deepcopy(self._graph)

    @property
    def concentrated_masses(self):
        from welib.yams.utils import identifyRigidBodyMM
        if self._FEM is not None:
            return self._FEM.concentrated_masses
        else:
            CM = []
            for n in self.graph.Nodes:
                if 'addedMassMatrix' in n.data:
                    MM = n.data['addedMassMatrix']
                    mass, J_G, ref2COG = identifyRigidBodyMM(n.data['addedMassMatrix'])
                    CM.append( {'nodeID':n.ID, 'mass':mass, 'J_G':J_G, 'rho_G':ref2COG, 'MM':MM} )
            return CM



    @property
    def pointsMJ(self):
        """ return a dataframe with the coordinates of all members and joints
        The index corresponds to the SubDyn outputs "M_J_XXX"
        """
        Joints=[]
        labels =[]
        graph = self.graph
        for ie,M in enumerate(graph.Members): # loop on members
            Nodes = M.getNodes(graph)
            for iN,N in enumerate([Nodes[0], Nodes[-1]]):
                s='M{}J{}'.format(ie+1, iN+1)
                Joints.append([N.x,N.y,N.z])
                labels.append(s)
        df = pd.DataFrame(data=np.asarray(Joints), index=labels, columns=['x','y','z'])
        return df

    @property
    def pointsMN(self):
        """ return a dataframe with the coordinates of all members and nodes
        The index would correspond to the SubDyn outputs "M_N_XXX *prior* to the user selection"
        """
        Nodes=[]
        labels =[]
        graph = self.graph
        for im,M in enumerate(graph.Members): # loop on members
            nodes = M.getNodes(graph)
            for iN,N in enumerate(nodes): # Loop on member nodes
                s='M{}N{}'.format(im+1, iN+1)
                Nodes.append([N.x,N.y,N.z])
                labels.append(s)
        df =pd.DataFrame(data=np.asarray(Nodes), index=labels, columns=['x','y','z'])
        return df

    @property
    def pointsMNout(self):
        """ return a dataframe with the coordinates of members and nodes requested by user
        The index corresponds to the SubDyn outputs "M_N_XXX selected by the user"
        """
        Nodes=[]
        labels =[]
        graph = self.graph
        for im, out in enumerate(self.File['MemberOuts']):
            mID = out[0] # Member ID
            iNodes = np.array(out[2:])-1 # Node positions within member (-1 for python indexing)
            nodes = graph.getMemberNodes(mID)
            nodes = np.array(nodes)[iNodes]
            for iN,N in enumerate(nodes): # Loop on selected nodes
                s='M{}N{}'.format(im+1, iN+1)
                Nodes.append([N.x,N.y,N.z])
                labels.append(s)
        df =pd.DataFrame(data=np.asarray(Nodes), index=labels, columns=['x','y','z'])
        return df


    def memberPostPro(self, dfAvg):
        """
        Convert a dataframe of SubDyn/OpenFAST outputs (time-averaged)
        with columns such as: M_N_* and M_J_* 
        into a dataframe that is organized by main channel name and nodal coordinates.
        The scripts taken into account with member ID and node the user requested as outputs channels.
        Discretization (nDIV) is also taken into account.

        For instance:
            dfAvg with columns = ['M1N1MKye_[N*m]', 'M1N2MKye_[N*m]', 'M1N1TDxss_[m]']
        returns:
            MNout with columns ['x', 'y', 'z', 'MKye_[Nm]', 'TDxss_[m]']
               and index    ['M1N1', 'M1N2']
               with x,y,z the undisplaced nodal positions (accounting for discretization)

        INPUTS: 
          -  dfAvg: a dataframe of time-averaged SubDyn/OpenFAST outputs, for instance obtained as:
              df    = FASTInputFile(filename).toDataFrame()
              dfAvg = postpro.averageDF(df, avgMethod=avgMethod ,avgParam=avgParam)
        OUTPUTS
          - MNout: dataframe of members outputs (requested by the user)
          - MJout: dataframe of joints outputs
        """
        import welib.fast.postpro as postpro # Import done here to avoid circular dependency

        # --- Get Points where output are requested
        MJ = self.pointsMJ
        MNo= self.pointsMNout
        MJ.columns = ['x_[m]','y_[m]', 'z_[m]']
        MNo.columns = ['x_[m]','y_[m]', 'z_[m]']

        # --- Requested Member Outputs
        Map={}
        Map['^'+r'M(\d*)N(\d*)TDxss_\[m\]']   = 'TDxss_[m]'
        Map['^'+r'M(\d*)N(\d*)TDyss_\[m\]']   = 'TDyss_[m]'
        Map['^'+r'M(\d*)N(\d*)TDzss_\[m\]']   = 'TDzss_[m]'
        Map['^'+r'M(\d*)N(\d*)RDxe_\[rad\]']  = 'RDxe_[deg]' # NOTE rescale needed
        Map['^'+r'M(\d*)N(\d*)RDye_\[rad\]']  = 'RDye_[deg]' # NOTE rescale needed
        Map['^'+r'M(\d*)N(\d*)RDze_\[rad\]']  = 'RDze_[deg]' # NOTE rescale needed
        Map['^'+r'M(\d*)N(\d*)FKxe_\[N\]'] = 'FKxe_[N]'
        Map['^'+r'M(\d*)N(\d*)FKye_\[N\]'] = 'FKye_[N]'
        Map['^'+r'M(\d*)N(\d*)FKze_\[N\]'] = 'FKze_[N]'
        Map['^'+r'M(\d*)N(\d*)MKxe_\[N\*m\]'] = 'MKxe_[Nm]'
        Map['^'+r'M(\d*)N(\d*)MKye_\[N\*m\]'] = 'MKye_[Nm]'
        Map['^'+r'M(\d*)N(\d*)MKze_\[N\*m\]'] = 'MKze_[Nm]'
        ColsInfo, _, _ = postpro.find_matching_columns(dfAvg.columns, Map, ignore_case=True)
        nCols = len(ColsInfo)
        if nCols>0:
            newCols=[c['name'] for c in ColsInfo ]
            ValuesM = pd.DataFrame(index=MNo.index, columns=newCols)
            for ic,c in enumerate(ColsInfo):
                Idx, cols, colname = c['Idx'], c['cols'], c['name']
                labels = [re.match(r'(^M\d*N\d*)', s)[0] for s in cols] 
                ValuesM.loc[labels,colname] = dfAvg[cols].values.flatten()
                if 'deg' in colname and 'rad' in cols[0]:
                    ValuesM[colname] *= 180/np.pi
            # We remove lines that are all NaN
            Values = ValuesM.dropna(axis = 0, how = 'all')
            MNo2 = MNo.loc[Values.index]
            MNout = pd.concat((MNo2, Values), axis=1)
        else:
            MNout = None

        # --- Joint Outputs
        Map={}
        Map['^'+r'M(\d*)J(\d*)FKxe_\[N\]']   ='FKxe_[N]'
        Map['^'+r'M(\d*)J(\d*)FKye_\[N\]']   ='FKye_[N]'
        Map['^'+r'M(\d*)J(\d*)FKze_\[N\]']   ='FKze_[N]'
        Map['^'+r'M(\d*)J(\d*)MKxe_\[N\*m\]']='MKxe_[Nm]'
        Map['^'+r'M(\d*)J(\d*)MKye_\[N\*m\]']='MKye_[Nm]'
        Map['^'+r'M(\d*)J(\d*)MKze_\[N\*m\]']='MKze_[Nm]'
        Map['^'+r'M(\d*)J(\d*)FMxe_\[N\]']   ='FMxe_[N]'
        Map['^'+r'M(\d*)J(\d*)FMye_\[N\]']   ='FMye_[N]'
        Map['^'+r'M(\d*)J(\d*)FMze_\[N\]']   ='FMze_[N]'
        Map['^'+r'M(\d*)J(\d*)MMxe_\[N\*m\]']='MMxe_[Nm]'
        Map['^'+r'M(\d*)J(\d*)MMye_\[N\*m\]']='MMye_[Nm]'
        Map['^'+r'M(\d*)J(\d*)MMze_\[N\*m\]']='MMze_[Nm]'
        ColsInfo, _, _ = postpro.find_matching_columns(dfAvg.columns, Map, ignore_case=True)
        nCols = len(ColsInfo)
        if nCols>0:
            newCols=[c['name'] for c in ColsInfo ]
            ValuesJ = pd.DataFrame(index=MJ.index, columns=newCols)
            for ic,c in enumerate(ColsInfo):
                Idx, cols, colname = c['Idx'], c['cols'], c['name']
                labels = [re.match(r'(^M\d*J\d*)', s)[0] for s in cols] 
                ValuesJ.loc[labels,colname] = dfAvg[cols].values.flatten()
            # We remove lines that are all NaN
            Values = ValuesJ.dropna(axis = 0, how = 'all')
            MJ2 = MJ.loc[Values.index]
            MJout = pd.concat((MJ2, Values), axis=1)
        else:
            MJout = None
        return MNout, MJout




    # --------------------------------------------------------------------------------}
    # --- Functions for beam-like structure (Spar, Monopile)
    # --------------------------------------------------------------------------------{
    def beamDataFrame(self, equispacing=False):
        """ """
        # --- Parameters
        UseSubDynModel=True
        TopMass = False


        # Convert to "welib.fem.Graph" class to easily handle the model (overkill for a monopile)
        locgraph = self.graph.sortNodesBy('z')
        # Add nodal properties from propsets (NOTE: Not done anymore by SubDyn because a same node can have different diameters...)
        for e in locgraph.Elements:
            locgraph.setElementNodalProp(e, propset=e.propset, propIDs=e.propIDs)
        df = locgraph.nodalDataFrame()

        if equispacing:
            from welib.tools.pandalib import pd_interp1
            # Interpolate dataframe to equispaced values
            xOld  = df['z']    # NOTE: FEM uses "x" as main axis
            nSpan = len(xOld)
            x = np.linspace(np.min(xOld),np.max(xOld), nSpan)
            df = pd_interp1(x, 'z', df)

        #x   = df['z'] # NOTE: FEM uses "x" as main axis
        D   = df['D'] # Diameter [m]
        t   = df['t'] # thickness [m]
        # Derive section properties for a hollow cylinder based on diameter and thickness
        A        = np.pi*( (D/2)**2 - (D/2-t)**2) # Area for annulus [m^2]
        I        = np.pi/64*(D**4-(D-2*t)**4)     # Second moment of area for annulus (m^4)
        Kt       = I                              # Torsion constant, same as I for annulus [m^4]
        Ip       = 2*I                            # Polar second moment of area [m^4]
        df['A']  = A
        df['I']  = I
        df['Kt'] = Kt
        df['Ip'] = Ip
        df['m']  = df['rho'].values*A

        return df

    def beamFEM(self, df=None, force=False, method='cbeam', verbose=False):
        """ return FEM model for beam-like structures, like Spar/Monopile"""
        import welib.FEM.fem_beam as femb

        print(f'[INFO] SubDyn: beamFEM: method {method}')
        if method =='cbeam':
            if self._beamFEM is not None and (not force):
                return self._beamFEM

            BC       = 'clamped-free' # TODO Boundary condition: free-free or clamped-free
            element  = 'frame3d'      # Type of element used in FEM

            if df is None:
                df = self.beamDataFrame()
            x   = df['z']              # NOTE: FEM uses "x" as main axis
            E   = df['E']              # Young modules [N/m^2]
            G   = df['G']              # Shear modules [N/m^2]
            rho = df['rho']            # material density [kg/m^3]
            Ip  = df['Ip']
            I   = df['I']
            A   = df['A']
            Kt  = df['Kt']

            # --- Compute FEM model and mode shapes
            with Timer('Setting up FEM model'):
                FEM=femb.cbeam(x,m=rho*A,EIx=E*Ip,EIy=E*I,EIz=E*I,EA=E*A,A=A,E=E,G=G,Kt=Kt,
                            element=element, BC=BC, M_tip=self.M_tip)
            self._beamFEM = FEM
        else:
            # For the sake of it, we return the same kind of "dictionary" as cbeam...
            if self._FEM is None:
                raise Exception('Call `init()` before calling `beamFEM`')
            FF = self._FEM

            dispFEM, posFEM, INodesFEM = FF.nodesDisp(FF.Q, sortDim=2)
            if len(np.unique(posFEM[:,0]))>1 or  len(np.unique(posFEM[:,1]))>1:
                raise Exception('beamFEM expect a model where all nodes are along the same z-line')
#             for iMode in range(min(dispFEM.shape[2], nModesFEM)):
#                 self.addMode(displ=dispFEM[:,:,iMode], name='FEM{:d}'.format(iMode+1), freq=self.freq[iMode], group='FEM')
            FEM = {}
            FEM['xNodes']  = posFEM[:,2]
            #, 'MM':MM, 'KK':KK, 'Tr':Tr,
            FEM['MM_full'] = FF.MM
            FEM['KK_full'] = FF.KK
#                 'IFull2BC':IFull2BC, 'IBC2Full':IBC2Full,
#                 'Elem2Nodes':Elem2Nodes, 'Nodes2DOF':Nodes2DOF, 'Elem2DOF':Elem2DOF,
            #
            FEM['Q']       = FF.Q
            FEM['freq']    = FF.freq
            #  'modeNames':modeNames}


        return FEM


    def beamSecOutputs(self, df, verbose=False):
        """ 
        Given an OpenFAST output dataFrame
        return arrays of section loads and section motion for each height of a beam
        INPUTS:
         - df: OpenFAST output dataframe, e.g. FASTOutputFile('main.outb').toDataFrame()
        OUTPUTS:
         - zBeam: z nodes
         - F_sec: array of shape (6 x nz x nt): Fx, Fy, Fz, Mx, My, Mz
         - r_sec: array of shape (6 x nz x nt): tx, ty, tz, rx, ry, rz
        """
        df_columns_bkp = df.columns.copy()
        df.columns = [  v.split('_[')[0].lower() for v in df.columns.values]  # Removing units

        MN = self.pointsMN
        MJ = self.pointsMJ
        MNo= self.pointsMNout
        # Note: zBeam include subdivisions
        zBeam = np.array(sorted(MN['z'].unique()))
        #if verbose:
        #    print('SubDyn: zBeam: ', zBeam)

        F_sec = np.zeros((6,len(zBeam),len(df)))*np.nan
        r_sec = np.zeros((6,len(zBeam),len(df)))*np.nan
        # --- React
        # Note: coordinate system is different...
        izb = np.argmin(zBeam - np.min(zBeam))
        nReact=0
        if '-reactfxss' in df and verbose:
            print('SubDyn: Reaction present in output')
        if '-reactfxss' in df: F_sec[0, izb, :] = df['-reactfxss']
        if '-reactfyss' in df: F_sec[1, izb, :] = df['-reactfyss']
        if '-reactfzss' in df: F_sec[2, izb, :] = df['-reactfzss']
        if '-reactmxss' in df: F_sec[3, izb, :] = df['-reactmxss']
        if '-reactmyss' in df: F_sec[4, izb, :] = df['-reactmyss']
        if '-reactmzss' in df: F_sec[5, izb, :] = df['-reactmzss']
        # --- First Member outputs
        if verbose:
            print('SubDyn: Number of MNoutput points:', len(MNo))
        for iz, z in enumerate(zBeam):
            inds = MNo.index[MNo['z'] == z]
            if len(inds)==0:
                continue
            ind = inds[0].lower()  # first index found
            if '{}fkxe' .format(ind) in df.columns: F_sec[0, iz, :] = df['{}fkxe' .format(ind)]
            if '{}fkye' .format(ind) in df.columns: F_sec[1, iz, :] = df['{}fkye' .format(ind)]
            if '{}fkze' .format(ind) in df.columns: F_sec[2, iz, :] = df['{}fkze' .format(ind)]
            if '{}mkxe' .format(ind) in df.columns: F_sec[3, iz, :] = df['{}mkxe' .format(ind)]
            if '{}mkye' .format(ind) in df.columns: F_sec[4, iz, :] = df['{}mkye' .format(ind)]
            if '{}mkze' .format(ind) in df.columns: F_sec[5, iz, :] = df['{}mkze' .format(ind)]
            if '{}tdxss'.format(ind) in df.columns: r_sec[0, iz, :] = df['{}tdxss'.format(ind)]
            if '{}tdyss'.format(ind) in df.columns: r_sec[1, iz, :] = df['{}tdyss'.format(ind)]
            if '{}tdzss'.format(ind) in df.columns: r_sec[2, iz, :] = df['{}tdzss'.format(ind)]
            if '{}rdxe' .format(ind) in df.columns: r_sec[3, iz, :] = df['{}rdxe' .format(ind)]
            if '{}rdye' .format(ind) in df.columns: r_sec[4, iz, :] = df['{}rdye' .format(ind)]
            if '{}rdze' .format(ind) in df.columns: r_sec[5, iz, :] = df['{}rdze' .format(ind)]
        # --- MJ All Out
        # Erase if present)
        if 'm1j1fkxe' in df:
            if verbose:
                print('SubDyn: MJ output present')
                print('SubDyn: Number of MJoutput points:', len(MJ))
            for iz, z in enumerate(zBeam):
                inds = MJ.index[MJ['z']==z]
                if len(inds)==0:
                    continue
                ind = inds[0].lower()  # first index found
                F_sec[0, iz, :] = df['{}fkxe'.format(ind)] # Fx
                F_sec[1, iz, :] = df['{}fkye'.format(ind)] # Fy
                F_sec[2, iz, :] = df['{}fkze'.format(ind)] # Fz
                F_sec[3, iz, :] = df['{}mkxe'.format(ind)] # Mx
                F_sec[4, iz, :] = df['{}mkye'.format(ind)] # My
                F_sec[5, iz, :] = df['{}mkze'.format(ind)] # Mz

        # Restore columns
        df.columns = df_columns_bkp

        return zBeam, F_sec, r_sec


    def beamModes(self, nCB=None, FEM = None, method='cbeam', verbose=False):
        """ Returns mode shapes for beam-like structures, like Spar/Monopile """
        import welib.FEM.fem_beam as femb
        if nCB is None:
            nCB = self.File['Nmodes']
        if method == 'cbeam':
            element  = 'frame3d'      # Type of element used in FEM
            if FEM is None:
                if self._beamFEM is None:
                    FEM = self.beamFEM()
                else:
                    FEM = self._beamFEM
            # --- Perform Craig-Bampton reduction, fixing the top node of the beam
            with Timer('FEM eigenvalue analysis'):
                Q_G,_Q_CB, df_G, df_CB, Modes_G, Modes_CB, CB = femb.CB_topNode(FEM, nCB=nCB, element=element, main_axis='x')

            df_G = xBeam_To_zBeam(df_G, prefix='G')
            df_CB = xBeam_To_zBeam(df_CB, prefix='CB')
            #print(df_G.columns)
            #print(df_CB.columns)
            # df_CB.to_csv('_CB.csv',index=False)
            # df_G.to_csv('_Guyan.csv',index=False)
            return  Q_G,_Q_CB, df_G, df_CB, Modes_G, Modes_CB, CB 
        else:
            if FEM is not None:
                raise Exception('Using internal FEM, do not provide FEM with method==full')
            if self._FEM is None:
                raise Exception('Call `init()` before calling `beamModes`')
            else:
                FEM = self._FEM

            nModesCB = len(FEM.f_CB)
            if len(FEM.f_CB)<nCB:
                print(f'[INFO] SubDyn: We have to apply CB again with nCB={nCB}')
                self.applyCB(nModesCB=nCB, verbose=False)
                FEM = self._FEM


            dispGy, rotGy, posGy, INodesGy, dispCB, rotCB, posCB, INodesCB = FEM.getModes(scale=True, maxAmplitude=1, sortDim=2, outputRot=True)
            #dispGy, posGy, INodesGy = FEM.nodesDisp(FEM.Q_G, sortDim=2)
            #dispCB, posCB, INodesCB = self.nodesDisp(self.Q_CB, sortDim=2)

            if len(np.unique(posGy[:,0]))>1 or len(np.unique(posGy[:,1]))>1:
                raise Exception('beamFEM expect a model where all nodes are along the same z-line')

            # --- Returning same datastructure as cbeam method
            CB=dict()
            CB['MM']     = FEM.MM_CB
            CB['KK']     = FEM.KK_CB
            CB['Phi_G']  = FEM.Phi_G
            CB['Phi_CB'] = FEM.Phi_CB
            CB['f_G']    = FEM.f_G
            CB['f_CB']   = FEM.f_CB
            #     # Identify modes for convenience
            #     _, names_G= identifyAndNormalizeModes(Q_G, element=element, normalize=False)
            #     _, names_CB= identifyAndNormalizeModes(Q_CB, element=element, normalize=False)

            DN = ['ux','uy','uz','tx','ty','tz'] 
            # --- Guyan Modes
            M = posGy[:,2]
            Modes_G=dict()
            names_G = ['G{}'.format(i+1) for i in np.arange(len(FEM.f_G))]
            for i,mn in enumerate(names_G):
                if i==0:
                    scale = dispGy[-1,0,i]
                    dispGy[:,:,i] /= scale
                    rotGy [:,:,i] /= scale
                elif i==1:
                    scale = dispGy[-1,1,i]
                    dispGy[:,:,i] /= scale
                    rotGy [:,:,i] /= scale
                elif i==3:
                    scale = rotGy[-1,0,i]
                    dispGy[:,:,i] /= scale
                    rotGy [:,:,i] /= scale
                elif i==4:
                    scale = rotGy[-1,1,i]
                    dispGy[:,:,i] /= scale
                    rotGy [:,:,i] /= scale
#                     dispGy[:,0,i], dispGy[:,1,i], dispGy[:,2,i], rotGy[:,0,i], rotGy[:,1,i], rotGy[:,2,i]
                    #df_G['G1_ux'].values
                    #df_G['G1_ty'].values # TODO p/m
                ModeComp = [dispGy[:,0,i], dispGy[:,1,i], dispGy[:,2,i], rotGy[:,0,i], rotGy[:,1,i], rotGy[:,2,i]]
                Modes_G[mn]          = dict()
                Modes_G[mn]['label'] = names_G[i]
                Modes_G[mn]['comp']  = np.column_stack(ModeComp)
                #Modes_G[mn]['raw']   = Q_G[:,i]
                M= np.column_stack([M]+ModeComp)
            colnames=['z']+[m+'_'+d for m in names_G for d in DN]
            df_G=pd.DataFrame(data=M, columns=colnames)
            # Manual normalization

            # --- CB Modes
            M = posCB[:,2]
            Modes_CB=dict()
            names_CB = ['CB{}'.format(i+1) for i in np.arange(len(FEM.f_CB))]
            for i,mn in enumerate(names_CB):
                # TODO normalization
                ModeComp = [dispCB[:,0,i], dispCB[:,1,i], dispCB[:,2,i], rotCB[:,0,i], rotCB[:,1,i], rotCB[:,2,i]]
                Modes_G[mn]          = dict()
                Modes_G[mn]['label'] = names_CB[i]
                Modes_G[mn]['comp']  = np.column_stack(ModeComp)
                #Modes_G[mn]['raw']   = Q_G[:,i]
                M= np.column_stack([M]+ModeComp)
            colnames=['z']+[m+'_'+d for m in names_CB for d in DN]
            df_CB=pd.DataFrame(data=M, columns=colnames)

            # df_CB.to_csv('_CB.csv',index=False)
            #return Q_G,_Q_CB, df_G, df_CB, Modes_G, Modes_CB, CB 
            return None, None, df_G, df_CB, Modes_G, Modes_CB, CB

    def beamModesPlot(self, FEM=None):
        """ """
        if FEM is None:
            if self._beamFEM is None:
                FEM = self.beamFEM()
            else:
                FEM = self._beamFEM
        # TODO
        nModesPlot=8
        # --- Show frequencies to screen
        print('Mode   Frequency  Label ')
        for i in np.arange(8):
            print('{:4d} {:10.3f}   {:s}'.format(i+1,FEM['freq'][i],FEM['modeNames'][i]))

        # --- Plot mode components for first few modes
        #Q=FEM['Q'] ; modeNames = FEM['modeNames']
        #Q=Q_CB ;modeNames = names_CB
        Modes=Modes_CB
        nModesPlot=min(len(Modes),nModesPlot)

        fig,axes = plt.subplots(1, nModesPlot, sharey=False, figsize=(12.4,2.5))
        fig.subplots_adjust(left=0.04, right=0.98, top=0.91, bottom=0.11, hspace=0.40, wspace=0.30)
        for i in np.arange(nModesPlot):
            key= list(Modes.keys())[i]

            axes[i].plot(x, Modes[key]['comp'][:,0]  ,'-'  , label='ux')
            axes[i].plot(x, Modes[key]['comp'][:,1]  ,'-'  , label='uy')
            axes[i].plot(x, Modes[key]['comp'][:,2]  ,'-'  , label='uz')
            axes[i].plot(x, Modes[key]['comp'][:,3]  ,':'  , label='vx')
            axes[i].plot(x, Modes[key]['comp'][:,4]  ,':'  , label='vy')
            axes[i].plot(x, Modes[key]['comp'][:,5]  ,':'  , label='vz')
            axes[i].set_xlabel('')
            axes[i].set_ylabel('')
            axes[i].set_title(Modes[key]['label'])
            if i==0:
                axes[i].legend()




    # --------------------------------------------------------------------------------}
    # --- IO/Converters
    # --------------------------------------------------------------------------------{
    def toYAML(self, filename):
        if self._FEM is None:
            raise Exception('Call `init()` before calling `toYAML`')
        subdyntoYAMLSum(self._FEM, filename, more = self.File['OutAll'])


    def toYAMSData(self, shapes=[0,4], main_axis='z', method='cbeam', equispacing=True):
        """ 
        Convert to Data needed to setup a Beam Model in YAMS (see bodies.py in yams)
        """
        from welib.mesh.gradient import gradient_regular
        from welib.yams.utils import translateRigidBodyMassMatrix        
        print('SubDyn: toYamsDATA, method:', method)

        dfOut=None
        if method is None:
            method ='cbeam'

        if method.lower() == 'cbeam':
            # --- Use Beam FEM representation
            # Get beam data frame
            df = self.beamDataFrame(equispacing=equispacing)
            if np.any(df['y']!=0): 
                raise NotImplementedError('FASTBeamBody for substructure only support monopile, structure not fully vertical in file: {}'.format(self.File.filename))
            if np.any(df['x']!=0): 
                raise NotImplementedError('FASTBeamBody for substructure only support monopile, structure not fully vertical in file: {}'.format(self.File.filename))

            # --- Perform Craig-Bampton reduction, fixing the top node of the beam
            FEM = self.beamFEM(df, method=method)
            Q_G,_Q_CB, df_G, df_CB, Modes_G, Modes_CB, CB = self.beamModes(nCB=None, FEM=FEM, method=method)

            x     = df['z'].values
            nSpan = len(x)

        else:
            df = self.beamDataFrame(equispacing=False)

            Q_G,_Q_CB, df_G, df_CB, Modes_G, Modes_CB, CB = self.beamModes(nCB=None, method=method)

            x     = df_G['z'].values
            nSpan = len(x)

            if len(df)!=len(df_G):
                raise Exception('Inconsistency in df shapes')

        dfOut = pd.concat([df.reset_index(drop=True), df_G.reset_index(drop=True)], axis=1)

        # TODO TODO finda way to use these matrices instead of the ones computed with flexibility
        #print('CB MM\n',CB['MM'])
        #print('CB KK\n',CB['KK'])

        # --- Setup shape functions
        if main_axis=='x':
            raise NotImplementedError('')
        else:
            pass
            # we need to swap the CB modes
        nShapes=len(shapes)
        PhiU = np.zeros((nShapes,3,nSpan)) # Shape
        PhiV = np.zeros((nShapes,3,nSpan)) # Shape
        PhiK = np.zeros((nShapes,3,nSpan)) # Shape
        dx=np.unique(np.around(np.diff(x),4))
        irregular = len(dx)>1
        if irregular:
            raise Exception('Implement irregular gradient')
        for iShape, idShape in enumerate(shapes):
            if idShape==0:
                # shape i=0, G1, ux  
                PhiU[iShape][0,:] = df_G['G1_ux'].values
                PhiV[iShape][0,:] = df_G['G1_ty'].values # TODO p/m
                if irregular:
                    pass
                else:
                    PhiK[iShape][0,:] = gradient_regular(PhiV[iShape][0,:],dx=dx[0],order=4)
            elif idShape==1:
                # shape i=1, G2, uy
                PhiU[iShape][1,:] = df_G['G2_uy'].values
                PhiV[iShape][1,:] = df_G['G2_tx'].values # TODO p/m
                print('TODO not sure about sign for PhiV for shape Guyan uy')
                if irregular:
                    pass
                else:
                    PhiK[iShape][1,:] = gradient_regular(PhiV[iShape][1,:],dx=dx[0],order=4)
        
                # shape i=2, G3, uz
            elif idShape==3:
                # shape i=3, G4, vx
                PhiU[iShape][1,:] = df_G['G5_uy'].values
                PhiV[iShape][1,:] = df_G['G5_tx'].values # TODO p/m
                if irregular:
                    pass
                else:
                    PhiK[iShape][1,:] = gradient_regular(PhiV[iShape][1,:],dx=dx[0],order=4)
            elif idShape==4:
                # shape i=4, G5 vy
                PhiU[iShape][0,:] = df_G['G5_ux'].values
                PhiV[iShape][0,:] = df_G['G5_ty'].values
                if irregular:
                    pass
                else:
                    PhiK[iShape][0,:] = gradient_regular(PhiV[iShape][0,:],dx=dx[0],order=4)
            elif idShape==6:
                PhiU[iShape][0,:] = df_CB['CB1_ux'].values
                PhiU[iShape][1,:] = df_CB['CB1_uy'].values
                PhiV[iShape][0,:] = df_CB['CB1_ty'].values
                PhiV[iShape][1,:] = df_CB['CB1_tx'].values

            elif idShape==7:
                PhiU[iShape][0,:] = df_CB['CB2_ux'].values
                PhiU[iShape][1,:] = df_CB['CB2_uy'].values
                PhiV[iShape][0,:] = df_CB['CB2_ty'].values
                PhiV[iShape][1,:] = df_CB['CB2_tx'].values

            else:
                raise NotImplementedError(f'SubDyn: idShape {idShape}')
            dfU = pd.DataFrame(data=PhiU[iShape].T, columns=[f'PhiU{iShape}'+s for s in ['x','y','z']])
            dfV = pd.DataFrame(data=PhiV[iShape].T, columns=[f'PhiV{iShape}'+s for s in ['x','y','z']])
            dfOut = pd.concat([dfOut, dfU, dfV], axis=1)
#             import pdb; pdb.set_trace()

        # --- Dictionary structure for YAMS
        p=dict()
        p['s_span']=x-np.min(x)
        p['s_P0']=np.zeros((3,nSpan))
        if main_axis=='z':
            p['s_P0'][2,:]=x-np.min(x)
            p['r_O']   = (df['x'].values[0], df['y'].values[0], df['z'].values[0])
            p['R_b2g'] = np.eye(3)
        else:
            raise NotImplementedError()
        p['m']  = df['m'].values
        p['EI'] = np.zeros((3,nSpan))
        if main_axis=='z':
            p['EI'][0,:]=df['E'].values*df['I'].values
            p['EI'][1,:]=df['E'].values*df['I'].values
        else:
            raise NotImplementedError()
        p['jxxG']  = df['rho']*df['Ip']          # TODO verify
        p['s_min'] = p['s_span'][0]
        p['s_max'] = p['s_span'][-1]
        p['PhiU']  = PhiU
        p['PhiV']  = PhiV
        p['PhiK']  = PhiK

        # --- Concentrated inertias mapped to beam nodes
        concentrated_inertias = []
        axis_map = {'x': 0, 'y': 1, 'z': 2}
        i_axis = axis_map.get(main_axis, 2)
        z0 = np.min(x)

        graph_nodes = {n.ID: np.array([n.x, n.y, n.z]) for n in self.graph.Nodes}
        for cm in self.concentrated_masses:
            if 'MM' not in cm:
                continue
            node_id = cm['nodeID']
            if node_id not in graph_nodes:
                raise Exception('node_id not in graph for concentrated mass')
                continue

            xyz_cm = graph_nodes[node_id]
            s_cm = xyz_cm[i_axis] - z0
            iNode = int(np.argmin(np.abs(p['s_span'] - s_cm)))

            MM_node = np.asarray(cm['MM']).copy()
            s_node = p['s_span'][iNode]
            ds = s_node - s_cm
            if abs(ds) > 0:
                r_old_to_new = np.zeros(3)
                r_old_to_new[i_axis] = ds
                MM_node = translateRigidBodyMassMatrix(MM_node, r_old_to_new)

            concentrated_inertias.append({
                'iNode': iNode,
                's': s_cm,
                'MM': MM_node,
                'nodeID': node_id,
            })

        p['concentrated_inertias'] = concentrated_inertias

        # --- Damping
        damp_zeta     = None
        RayleighCoeff = None
        DampMat       = None
        if self.File['GuyanDampMod']==1:
            # Rayleigh Damping
            RayleighCoeff=self.File['RayleighDamp']
            #if RayleighCoeff[0]==0:
            #    damp_zeta=omega*RayleighCoeff[1]/2. 
        elif self.File['GuyanDampMod']==2:
            # Full matrix
            DampMat = self.File['GuyanDampMatrix']
            DampMat=DampMat[np.ix_(shapes,shapes)]

        return p, damp_zeta, RayleighCoeff, DampMat, dfOut


# --------------------------------------------------------------------------------}
# --- Export of summary file and Misc FEM variables used by SubDyn
# --------------------------------------------------------------------------------{
def yaml_array(var, M, Fmt='{:15.6e}', comment=''):
    M = np.atleast_2d(M)
    if len(comment)>0:
        s='{}: # {} x {} {}\n'.format(var, M.shape[0], M.shape[1], comment)
    else:
        s='{}: # {} x {}\n'.format(var, M.shape[0], M.shape[1])

    if M.shape[0]==1:
        if M.shape[1]==0:
            s+= '  - [ ]\n'
        else:
            for l in M:
                s+= '  - [' + ','.join([Fmt.format(le) for le in l]) + ',]\n'
    else:
        for l in M:
            s+= '  - [' + ','.join([Fmt.format(le) for le in l]) + ']\n'
    s = s.replace('e+','E+').replace('e-','E-')
    return s



def subdynPartitionVars(model):
    from welib.FEM.fem_elements import idDOF_Leader, idDOF_Fixed, idDOF_Internal
    # --- Count nodes per types
    nNodes    = len(model.Nodes)
    nNodes_I  = len(model.interfaceNodes)
    nNodes_C  = len(model.reactionNodes)
    nNodes_L  = len(model.internalNodes)

    # --- Partition Nodes:  Nodes_L = IAll - NodesR
    Nodes_I = [n.ID for n in model.interfaceNodes]
    Nodes_C = [n.ID for n in model.reactionNodes]
    Nodes_R = Nodes_I + Nodes_C
    Nodes_L = [n.ID for n in model.Nodes if n.ID not in Nodes_R]

    # --- Count DOFs - NOTE: we count node by node
    nDOF___  = sum([len(n.data['DOFs_c'])                                 for n in model.Nodes])
    # Interface DOFs
    nDOFI__  = sum([len(n.data['DOFs_c'])              for n in model.interfaceNodes])
    nDOFI_B = sum([sum(np.array(n.data['IBC'])==idDOF_Leader)   for n in model.interfaceNodes])
    nDOFI_F  = sum([sum(np.array(n.data['IBC'])==idDOF_Fixed )   for n in model.interfaceNodes])
    if nDOFI__!=nDOFI_B+nDOFI_F: raise Exception('Wrong distribution of interface DOFs')
    # DOFs of reaction nodes
    nDOFC__ = sum([len(n.data['DOFs_c'])              for n in model.reactionNodes]) 
    nDOFC_B = sum([sum(np.array(n.data['RBC'])==idDOF_Leader)   for n in model.reactionNodes])
    nDOFC_F = sum([sum(np.array(n.data['RBC'])==idDOF_Fixed)    for n in model.reactionNodes])
    nDOFC_L = sum([sum(np.array(n.data['RBC'])==idDOF_Internal) for n in model.reactionNodes])
    if nDOFC__!=nDOFC_B+nDOFC_F+nDOFC_L: raise Exception('Wrong distribution of reaction DOFs')
    # DOFs of reaction + interface nodes
    nDOFR__ = nDOFI__ + nDOFC__ # Total number, used to be called "nDOFR"
    # DOFs of internal nodes
    nDOFL_L  = sum([len(n.data['DOFs_c']) for n in model.internalNodes])
    if nDOFL_L!=nDOF___-nDOFR__: raise Exception('Wrong distribution of internal DOF')
    # Total number of DOFs in each category:
    nDOF__B = nDOFC_B + nDOFI_B
    nDOF__F = nDOFC_F + nDOFI_F          
    nDOF__L = nDOFC_L           + nDOFL_L 

    # --- Distibutes the I, L, C nodal DOFs into  B, F, L sub-categories 
    # NOTE: order is importatn for compatibility with SubDyn
    IDI__ = []
    IDI_B = []
    IDI_F = []
    for n in model.interfaceNodes:
        IDI__ += n.data['DOFs_c'] # NOTE: respects order
        IDI_B += [dof for i,dof in enumerate(n.data['DOFs_c']) if n.data['IBC'][i]==idDOF_Leader]
        IDI_F += [dof for i,dof in enumerate(n.data['DOFs_c']) if n.data['IBC'][i]==idDOF_Fixed ]
    IDI__ = IDI_B+IDI_F
    IDC__ = []
    IDC_B = []
    IDC_L = []
    IDC_F = []
    for n in model.reactionNodes:
        IDC__ += n.data['DOFs_c'] # NOTE: respects order
        IDC_B += [dof for i,dof in enumerate(n.data['DOFs_c']) if n.data['RBC'][i]==idDOF_Leader  ]
        IDC_L += [dof for i,dof in enumerate(n.data['DOFs_c']) if n.data['RBC'][i]==idDOF_Internal]
        IDC_F += [dof for i,dof in enumerate(n.data['DOFs_c']) if n.data['RBC'][i]==idDOF_Fixed   ]
    IDR__=IDC__+IDI__
    IDL_L = []
    for n in model.internalNodes:
        IDL_L += n.data['DOFs_c']

    # Storing variables similar to SubDyn
    SD_Vars={}
    SD_Vars['nDOF___']=nDOF___;
    SD_Vars['nDOFI__']=nDOFI__; SD_Vars['nDOFI_B']=nDOFI_B; SD_Vars['nDOFI_F']=nDOFI_F;
    SD_Vars['nDOFC__']=nDOFC__; SD_Vars['nDOFC_B']=nDOFC_B; SD_Vars['nDOFC_F']=nDOFC_F; SD_Vars['nDOFC_L']=nDOFC_L;
    SD_Vars['nDOFR__']=nDOFR__; SD_Vars['nDOFL_L']=nDOFL_L;
    SD_Vars['nDOF__B']=nDOF__B; SD_Vars['nDOF__F']=nDOF__F; SD_Vars['nDOF__L']=nDOF__L;
    SD_Vars['IDC__']=IDC__;
    SD_Vars['IDC_B']=IDC_B;
    SD_Vars['IDC_F']=IDC_F;
    SD_Vars['IDC_L']=IDC_L;
    SD_Vars['IDI__']=IDI__;
    SD_Vars['IDR__']=IDR__;
    SD_Vars['IDI_B']=IDI_B;
    SD_Vars['IDI_F']=IDI_F;
    SD_Vars['IDL_L']=IDL_L;
    SD_Vars['ID__B']=model.DOFc_Leader
    SD_Vars['ID__F']=model.DOFc_Fixed
    SD_Vars['ID__L']=model.DOFc_Follower
    return SD_Vars

def subdyntoYAMLSum(model, filename, more=False):
    """ 
    Write a YAML summary file, similar to SubDyn
    """
    # --- Helper functions
    def nodeID(nodeID):
        if hasattr(nodeID,'__len__'):
            return [model.Nodes.index(model.getNode(n))+1 for n in nodeID]
        else:
            return model.Nodes.index(model.getNode(nodeID))+1

    def elemID(elemID):
        #e=model.getElement(elemID)
        for ie,e in enumerate(model.Elements):
            if e.ID==elemID:
                return ie+1
    def elemType(elemType):
        from welib.FEM.fem_elements import idMemberBeam, idMemberCable, idMemberRigid
        return {'SubDynBeam3d':idMemberBeam, 'SubDynFrame3d':idMemberBeam, 'Beam':idMemberBeam, 'Frame3d':idMemberBeam,
                'SubDynTimoshenko3d':idMemberBeam,
                'SubDynCable3d':idMemberCable, 'Cable':idMemberCable,
                'Rigid':idMemberRigid,
                'SubDynRigid3d':idMemberRigid}[elemType]

    def propID(propID, propset):
        prop = model.NodePropertySets[propset]
        for ip, p in enumerate(prop):
            if p.ID == propID:
                return ip+1

    SD_Vars = subdynPartitionVars(model)

    # --- Helper functions
    s=''
    s += '#____________________________________________________________________________________________________\n'
    s += '# RIGID BODY EQUIVALENT DATA\n'
    s += '#____________________________________________________________________________________________________\n'
    s0 = 'Mass: {:15.6e} # Total Mass\n'.format(model.M_O[0,0])
    s += s0.replace('e+','E+').replace('e-','E-')
    s0 = 'CM_point: [{:15.6e},{:15.6e},{:15.6e},] # Center of mass coordinates (Xcm,Ycm,Zcm)\n'.format(model.center_of_mass[0],model.center_of_mass[1],model.center_of_mass[2])
    s += s0.replace('e+','E+').replace('e-','E-')
    s0 = 'TP_point: [{:15.6e},{:15.6e},{:15.6e},] # Transition piece reference point\n'.format(model.refPoint[0],model.refPoint[1],model.refPoint[2])
    s += s0.replace('e+','E+').replace('e-','E-')
    s += yaml_array('MRB',  model.M_O,  comment = 'Rigid Body Equivalent Mass Matrix w.r.t. (0,0,0).')
    s += yaml_array('M_P' , model.M_ref,comment = 'Rigid Body Equivalent Mass Matrix w.r.t. TP Ref point')
    s += yaml_array('M_G' , model.M_G,  comment = 'Rigid Body Equivalent Mass Matrix w.r.t. CM (Xcm,Ycm,Zcm).')
    s += '#____________________________________________________________________________________________________\n'
    s += '# GUYAN MATRICES at the TP reference point\n'
    s += '#____________________________________________________________________________________________________\n'
    s += yaml_array('KBBt' , model.KBBt,  comment = '')
    s += yaml_array('MBBt' , model.MBBt,  comment = '')
    s += yaml_array('CBBt' , model.CBBt,  comment = '(user Guyan Damping + potential joint damping from CB-reduction)')
    s += '#____________________________________________________________________________________________________\n'
    s += '# SYSTEM FREQUENCIES\n'
    s += '#____________________________________________________________________________________________________\n'
    s += '#Eigenfrequencies [Hz] for full system, with reaction constraints (+ Soil K/M + SoilDyn K0) \n'
    s += yaml_array('Full_frequencies', model.freq)
    s += '#Frequencies of Guyan modes [Hz]\n'
    s += yaml_array('GY_frequencies', model.f_G)
    s += '#Frequencies of Craig-Bampton modes [Hz]\n'
    s += yaml_array('CB_frequencies', model.f_CB)
    s += '#____________________________________________________________________________________________________\n'
    s += '# Internal FEM representation\n'
    s += '#____________________________________________________________________________________________________\n'
    s += 'nNodes_I: {:7d} # Number of Nodes: "interface" (I)\n'.format(len(model.interfaceNodes))
    s += 'nNodes_C: {:7d} # Number of Nodes: "reactions" (C)\n'.format(len(model.reactionNodes))
    s += 'nNodes_L: {:7d} # Number of Nodes: "internal"  (L)\n'.format(len(model.internalNodes))
    s += 'nNodes  : {:7d} # Number of Nodes: total   (I+C+L)\n'.format(len(model.Nodes))
    if more:
        s += 'nDOFI__ : {:7d} # Number of DOFs: "interface"          (I__)\n'.format(len(SD_Vars['IDI__']))
        s += 'nDOFI_B : {:7d} # Number of DOFs: "interface" retained (I_B)\n'.format(len(SD_Vars['IDI_B']))
        s += 'nDOFI_F : {:7d} # Number of DOFs: "interface" fixed    (I_F)\n'.format(len(SD_Vars['IDI_F']))
        s += 'nDOFC__ : {:7d} # Number of DOFs: "reactions"          (C__)\n'.format(len(SD_Vars['IDC__']))
        s += 'nDOFC_B : {:7d} # Number of DOFs: "reactions" retained (C_B)\n'.format(len(SD_Vars['IDC_B']))
        s += 'nDOFC_L : {:7d} # Number of DOFs: "reactions" internal (C_L)\n'.format(len(SD_Vars['IDC_L']))
        s += 'nDOFC_F : {:7d} # Number of DOFs: "reactions" fixed    (C_F)\n'.format(len(SD_Vars['IDC_F']))
        s += 'nDOFR__ : {:7d} # Number of DOFs: "intf+react"         (__R)\n'.format(len(SD_Vars['IDR__']))
        s += 'nDOFL_L : {:7d} # Number of DOFs: "internal"  internal (L_L)\n'.format(len(SD_Vars['IDL_L']))
    s += 'nDOF__B : {:7d} # Number of DOFs:             retained (__B)\n'.format(SD_Vars['nDOF__B'])
    s += 'nDOF__L : {:7d} # Number of DOFs:             internal (__L)\n'.format(SD_Vars['nDOF__L'])
    s += 'nDOF__F : {:7d} # Number of DOFs:             fixed    (__F)\n'.format(SD_Vars['nDOF__F'])
    s += 'nDOF_red: {:7d} # Number of DOFs: total\n'                     .format(SD_Vars['nDOF___'])
    s += yaml_array('Nodes_I', nodeID([n.ID for n in model.interfaceNodes]), Fmt='{:7d}', comment='"interface" nodes"');
    s += yaml_array('Nodes_C', nodeID([n.ID for n in model.reactionNodes ]), Fmt='{:7d}', comment='"reaction" nodes"');
    s += yaml_array('Nodes_L', nodeID([n.ID for n in model.internalNodes ]), Fmt='{:7d}', comment='"internal" nodes"');
    if more:
        s += yaml_array('DOF_I__', np.array(SD_Vars['IDI__'])+1,   Fmt='{:7d}', comment = '"interface"           DOFs"')
        s += yaml_array('DOF_I_B', np.array(SD_Vars['IDI_B'])+1,   Fmt='{:7d}', comment = '"interface" retained  DOFs')
        s += yaml_array('DOF_I_F', np.array(SD_Vars['IDI_F'])+1,   Fmt='{:7d}', comment = '"interface" fixed     DOFs')
        s += yaml_array('DOF_C__', np.array(SD_Vars['IDC__'])+1,   Fmt='{:7d}', comment = '"reaction"            DOFs"')
        s += yaml_array('DOF_C_B', np.array(SD_Vars['IDC_B'])+1,   Fmt='{:7d}', comment = '"reaction"  retained  DOFs')
        s += yaml_array('DOF_C_L', np.array(SD_Vars['IDC_L'])+1,   Fmt='{:7d}', comment = '"reaction"  internal  DOFs')
        s += yaml_array('DOF_C_F', np.array(SD_Vars['IDC_F'])+1,   Fmt='{:7d}', comment = '"reaction"  fixed     DOFs')
        s += yaml_array('DOF_L_L', np.array(SD_Vars['IDL_L'])+1,   Fmt='{:7d}', comment = '"internal"  internal  DOFs')
        s += yaml_array('DOF_R_' , np.array(SD_Vars['IDR__'])+1,   Fmt='{:7d}', comment = '"interface&reaction"  DOFs')
    s += yaml_array('DOF___B', np.array(model.DOFc_Leader  )+1, Fmt='{:7d}',  comment='all         retained  DOFs');
    s += yaml_array('DOF___F', np.array(model.DOFc_Fixed   )+1, Fmt='{:7d}',  comment='all         fixed     DOFs');
    s += yaml_array('DOF___L', np.array(model.DOFc_Follower)+1, Fmt='{:7d}',  comment='all         internal  DOFs');
    s += '\n'
    s += '#Index map from DOF to nodes\n'
    s += '#     Node No.,  DOF/Node,   NodalDOF\n'
    s += 'DOF2Nodes: # {} x 3 (nDOFRed x 3, for each constrained DOF, col1: node index, col2: number of DOF, col3: DOF starting from 1)\n'.format(model.nDOFc)
    DOFc2Nodes = model.DOFc2Nodes
    for l in DOFc2Nodes:
        s +='  - [{:7d},{:7d},{:7d}] # {}\n'.format(l[1]+1, l[2], l[3], l[0]+1 )
    s += '#     Node_[#]          X_[m]           Y_[m]           Z_[m]       JType_[-]       JDirX_[-]       JDirY_[-]       JDirZ_[-]  JStff_[Nm/rad]\n'
    s += 'Nodes: # {} x 9\n'.format(len(model.Nodes))
    for n in model.Nodes:
        s += '  - [{:7d}.,{:15.3f},{:15.3f},{:15.3f},{:14d}.,   0.000000E+00,   0.000000E+00,   0.000000E+00,   0.000000E+00]\n'.format(nodeID(n.ID), n.x, n.y, n.z, int(n.data['Type']) )
    s += '#    Elem_[#]    Node_1   Node_2   Prop_1   Prop_2     Type     Length_[m]      Area_[m^2]  Dens._[kg/m^3]        E_[N/m2]        G_[N/m2]       kappa_x_[-]       kappa_y_[-]       Ixx_[m^4]       Iyy_[m^4]       Jzz_[m^4]       Jt_[m^4]          T0_[N]\n'
    s += 'Elements: # {} x 18\n'.format(len(model.Elements))
    for e in model.Elements:
        I = e.inertias
        s0='  - [{:7d}.,{:7d}.,{:7d}.,{:7d}.,{:7d}.,{:7d}.,{:15.3f},{:15.3f},{:15.3f},{:15.6e},{:15.6e},{:15.6e},{:15.6e},{:15.6e},{:15.6e},{:15.6e},{:15.6e},{:15.6e}]\n'.format(
            elemID(e.ID), nodeID(e.nodeIDs[0]), nodeID(e.nodeIDs[1]), propID(e.propIDs[0], e.propset), propID(e.propIDs[1], e.propset), elemType(e.data['Type']), 
            e.length, e.area, e.rho, e.E, e.G, e.kappa_x, e.kappa_y, I[0], I[1], I[2], e.Jt, e.T0)
        s += s0.replace('e+','E+').replace('e-','E-')
    s += '#____________________________________________________________________________________________________\n'
    s += '#User inputs\n'
    s += '\n'
    s += '#Number of properties (NProps):{:6d}\n'.format(len(model.NodePropertySets['Beam']))
    s += '#Prop No         YoungE         ShearG        MatDens          XsecD          XsecT\n'
    for ip,p in enumerate(model.NodePropertySets['Beam']):
        s0='#{:8d}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}\n'.format(p.ID, p['E'],p['G'],p['rho'],p['D'],p['t'])
        s +=  s0.replace('e+','E+').replace('e-','E-')
    s +='\n'
    s += '#No. of Reaction DOFs:{:6d}\n'.format(len(SD_Vars['IDC__']) )
    s += '#React. DOF_ID    BC\n'
    s += '\n'.join(['#{:10d}{:10s}'.format(idof+1,'     Fixed' ) for idof in SD_Vars['IDC_F']])
    s += '\n'.join(['#{:10d}{:10s}'.format(idof+1,'     Free'  ) for idof in SD_Vars['IDC_L']])
    s += '\n'.join(['#{:10d}{:10s}'.format(idof+1,'     Leader') for idof in SD_Vars['IDC_B']])
    s += '\n\n'
    s += '#No. of Interface DOFs:{:6d}\n'.format(len(SD_Vars['IDI__']))
    s += '#Interf. DOF_ID    BC\n'
    s += '\n'.join(['#{:10d}{:10s}'.format(idof+1,'    Fixed' ) for idof in SD_Vars['IDI_F']])
    s += '\n'.join(['#{:10d}{:10s}'.format(idof+1,'    Leader') for idof in SD_Vars['IDI_B']])
    s += '\n\n'
    CM = model.concentrated_masses # list of dict with keys: # {'nodeID':n.ID, 'mass':mass, 'J_G':J_G, 'rho_G':ref2COG, 'MM':MM} )
    s += '#Number of concentrated masses (NCMass):{:6d}\n'.format(len(CM))
    s += '#JointCMas           Mass            JXX            JYY            JZZ            JXY            JXZ            JYZ           MCGX           MCGY           MCGZ\n'
    for cm in CM:
        JG = cm['J_G']
        rhoG = cm['rho_G']
        s0 = '# {:9.0f}.{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}\n'.format(
                nodeID(cm['nodeID']),  cm['mass'], JG[0,0], JG[1,1], JG[2,2], JG[0,1], JG[0,2], JG[1,2],rhoG[0],rhoG[1],rhoG[2]
                )
        s += s0.replace('e+','E+').replace('e-','E-')
    s += '\n'
    #s += '#Number of members    18\n'
    #s += '#Number of nodes per member:     2\n'
    #s += '#Member I Joint1_ID Joint2_ID    Prop_I    Prop_J           Mass         Length     Node IDs...\n'
    #s += '#       77        61        60        11        11   1.045888E+04   2.700000E+00       19    18\n'
    #s += '#____________________________________________________________________________________________________\n'
    #s += '#Direction Cosine Matrices for all Members: GLOBAL-2-LOCAL. No. of 3x3 matrices=    18\n'
    #s += '#Member I        DC(1,1)        DC(1,2)        DC(1,3)        DC(2,1)        DC(2,2)        DC(2,3)        DC(3,1)        DC(3,2)        DC(3,3)\n'
    #s += '#       77  1.000E+00  0.000E+00  0.000E+00  0.000E+00 -1.000E+00  0.000E+00  0.000E+00  0.000E+00 -1.000E+00\n'
    s += '#____________________________________________________________________________________________________\n'
    s += '#FEM Eigenvectors ({} x {}) [m or rad], full system with reaction constraints (+ Soil K/M + SoilDyn K0)\n'.format(*model.Q.shape)
    s += yaml_array('Full_Modes', model.Q)
    s += '#____________________________________________________________________________________________________\n'
    s += '#CB Matrices (PhiM,PhiR) (reaction constraints applied)\n'
    s += yaml_array('PhiM', model.Phi_CB[:,:model.nModesCB] ,comment='(CB modes)')
    s += yaml_array('PhiR', model.Phi_G,  comment='(Guyan modes)')
    s += '\n'
    if more:
        s += '#____________________________________________________________________________________________________\n'
        s += '# ADDITIONAL DEBUGGING INFORMATION\n'
        s += '#____________________________________________________________________________________________________\n'
        s +=  ''
        e = model.Elements[0]
        rho=e.rho
        A = e.area
        L = e.length
        t= rho*A*L
        s0 = '{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}{:15.6e}\n'.format(model.gravity,e.area, e.length, e.inertias[0], e.inertias[1], e.inertias[2], e.kappa_x, e.kappa_y, e.E, e.G, e.rho, t)
        s0 = s0.replace('e+','E+').replace('e-','E-')
        s += s0
        s += yaml_array('KeLocal' +str(), model.Elements[0].Ke(local=True))

        for ie,e in enumerate(model.Elements):
            s += yaml_array('DC' +str(ie+1), e.DCM.transpose())
            s += yaml_array('Ke' +str(ie+1), e.Ke())
            s += yaml_array('Me' +str(ie+1), e.Me())
            s += yaml_array('FGe'+str(ie+1), e.Fe_g(model.gravity))
            s += yaml_array('FCe'+str(ie+1), e.Fe_o())

            s += yaml_array('KeLocal' +str(ie+1), e.Ke(local=True))
            s += yaml_array('MeLocal' +str(ie+1), e.Me(local=True))
            s += yaml_array('FGeLocal'+str(ie+1), e.Fe_g(model.gravity, local=True))
            s += yaml_array('FCeLocal'+str(ie+1), e.Fe_o(local=True))

        s += '#____________________________________________________________________________________________________\n'
        e = model.Elements[0]
        s += yaml_array('Ke', e.Ke(local=True), comment='First element stiffness matrix'); # TODO not in local
        s += yaml_array('Me', e.Me(local=True), comment='First element mass matrix');
        s += yaml_array('FGe', e.Fe_g(model.gravity,local=True), comment='First element gravity vector');
        s += yaml_array('FCe', e.Fe_o(local=True), comment='First element cable pretension');
        s += '#____________________________________________________________________________________________________\n'
        s += '#FULL FEM K and M matrices. TOTAL FEM TDOFs:    {}\n'.format(model.nDOF); # NOTE: wrong in SubDyn, should be nDOFc
        s += yaml_array('K', model.KK, comment='Stiffness matrix');
        s += yaml_array('M', model.MM, comment='Mass matrix');
        s += '#____________________________________________________________________________________________________\n'
        s += '#Gravity and cable loads applied at each node of the system (before DOF elimination with T matrix)\n'
        s += yaml_array('FG', model.FF_init, comment=' ');
        s += '#____________________________________________________________________________________________________\n'
        s += '#Additional CB Matrices (MBB,MBM,KBB) (constraint applied)\n'
        s += yaml_array('MBB'    , model.MBB, comment='');
        s += yaml_array('MBM'    , model.MBM[:,:model.nModesCB], comment='');
        s += yaml_array('CMMdiag', model.CMM, comment='(2 Zeta OmegaM)');
        s += yaml_array('KBB'    , model.KBB, comment='');
        s += yaml_array('KMM'    , np.diag(model.KMM), comment='(diagonal components, OmegaL^2)');
        s += yaml_array('KMMdiag', np.diag(model.KMM)[:model.nModesCB], comment='(diagonal components, OmegaL^2)');
        s += yaml_array('PhiL'   , model.Phi_CB, comment='');
        s += 'PhiLOm2-1: # 18 x 18 \n'
        s += 'KLL^-1: # 18 x 18 \n'
    s += '#____________________________________________________________________________________________________\n'
    s += yaml_array('T_red', model.T_c, Fmt = '{:9.2e}', comment='(Constraint elimination matrix)');
    s += 'AA: # 16 x 16 (State matrix dXdx)\n'
    s += 'BB: # 16 x 48 (State matrix dXdu)\n'
    s += 'CC: # 6 x 16 (State matrix dYdx)\n'
    s += 'DD: # 6 x 48 (State matrix dYdu)\n'
    s += '#____________________________________________________________________________________________________\n'
    s += yaml_array('TI', model.T_refPoint,  Fmt = '{:9.2e}',comment='(TP refpoint Transformation Matrix TI)');
    if filename is not None:
        with open(filename, 'w') as f:
            f.write(s)

def xBeam_To_zBeam(df, prefix='G'):
    # Define mapping from old component names to (new component name, sign)
    comp_map = {
        "ux": ("uz", 1),  # old ux becomes new uz with negative sign
        "uy": ("uy", -1),  # old uy stays new uy with positive sign
        "uz": ("ux", 1),  # old uz becomes new ux with positive sign
        "tx": ("tz", 1),  # old tx becomes new tz with negative sign
        "ty": ("ty", -1),  # old ty stays new ty with positive sign
        "tz": ("tx", 1),  # old tz becomes new tx with positive sign
    }
    dof_map = { 1: 3, 2: 2, 3: 1, 4: 6, 5: 5, 6: 4}
    guyan_mode_sign = {
        1: 1,   # ux -> uz (+1)
        2: -1,  # uy -> -uy (-1, flip mode to keep driving DOF at +1)
        3: 1,   # uz -> ux (+1)
        4: 1,   # tx -> tz (+1)
        5: -1,  # ty -> -ty (-1, flip mode to keep driving DOF at +1)
        6: 1,   # tz -> tx (+1)
    }



    # Identify grid prefixes (e.g., 'G1', 'G2', ...)
    grid_prefixes = sorted( list({col.split("_")[0] for col in df.columns if col.startswith(prefix)}))

    # New column ordering sequence per grid point
    desired_comp_order = ["ux", "uy", "uz", "tx", "ty", "tz"]

    df_new = pd.DataFrame(index=df.index)

    # Set new spatial coordinate axis (old x becomes new z)

    # Transform each grid point
    for grid in grid_prefixes:
        for new_comp in desired_comp_order:
            # Find corresponding old component and sign factor
            for old_comp, (target_comp, sign) in comp_map.items():
                mode_scale = 1
                if target_comp == new_comp:
                    old_col = f"{grid}_{old_comp}"
                    if grid.startswith('G'):
                        old_dof = int(grid[1])
                        new_dof = str(dof_map[old_dof])
                        new_col = f"G{new_dof}_{new_comp}"
                        mode_scale = guyan_mode_sign[old_dof]
                    else:
                        new_col = f"{grid}_{new_comp}"
                    #print(f'>>> {old_col} {new_col} {sign}')
                    df_new[new_col] = df[old_col] * sign * mode_scale
                    break

    desired_comp_order = ["ux", "uy", "uz", "tx", "ty", "tz"]
    if prefix=='G':
        g_cols = sorted(
            [c for c in df_new.columns if c.startswith(prefix)],
            key=lambda c: (
                int(c.split("_")[0][1:]),
                desired_comp_order.index(c.split("_")[1]),
            ),
        )
        df_new = df_new[g_cols]
    df_new.insert(0, 'z', df["x"].values)
    return df_new



if __name__ == '__main__':
    from welib.weio.fast_input_file import FASTInputFile
    sdFilename = 'C:/Users/ebranlard/Documents/Work/2024-10-OESI-Digitwin/DigiTwinMonopile/simulations_wt/IEA-22-280-RWT/SD.dat'
#     sd = FASTInputFile(sdFilename, verbose=True)
#     dfs = sd.toDataFrame()
#     print(dfs['Members'])
#     print(dfs['Members']['MemberID_[-]'])
#     print(dfs['Members']['MType_[-]'])
    sd = SubDyn(sdFilename)
    print(sd)
    graph = sd.getGraph(nDiv=2)
    print(graph)
