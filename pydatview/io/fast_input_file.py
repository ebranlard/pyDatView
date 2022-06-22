from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from io import open
from builtins import range
from builtins import str
from future import standard_library
standard_library.install_aliases()
try:
    from .file import File, WrongFormatError, BrokenFormatError
except:
    # --- Allowing this file to be standalone..
    class WrongFormatError(Exception):
        pass
    class BrokenFormatError(Exception):
        pass
    File = dict
import os
import numpy as np
import re
import pandas as pd

__all__  = ['FASTInputFile']

TABTYPE_NOT_A_TAB          = 0
TABTYPE_NUM_WITH_HEADER    = 1
TABTYPE_NUM_WITH_HEADERCOM = 2
TABTYPE_NUM_NO_HEADER      = 4
TABTYPE_NUM_BEAMDYN        = 5
TABTYPE_MIX_WITH_HEADER    = 6
TABTYPE_FIL                = 3
TABTYPE_FMT                = 9999 # TODO

# --------------------------------------------------------------------------------}
# --- INPUT FILE 
# --------------------------------------------------------------------------------{
class FASTInputFile(File):
    """ 
    Read/write an OpenFAST input file. The object behaves like a dictionary.

    Main methods
    ------------
    - read, write, toDataFrame, keys

    Main keys
    ---------
    The keys correspond to the keys used in the file. For instance for a .fst file: 'DT','TMax'

    Examples
    --------

        filename = 'AeroDyn.dat'
        f = FASTInputFile(filename)
        f['TwrAero'] = True
        f['AirDens'] = 1.225
        f.write('AeroDyn_Changed.dat')

    """

    @staticmethod
    def defaultExtensions():
        return ['.dat','.fst','.txt','.fstf']

    @staticmethod
    def formatName():
        return 'FAST input file'

    def __init__(self, filename=None, **kwargs):
        self._size=None
        self._encoding=None
        if filename:
            self.filename = filename
            self.read()
        else:
            self.filename = None

    def keys(self):
        self.labels = [ d['label'] for d in self.data if not d['isComment'] ]
        return self.labels

    def getID(self,label):
        i=self.getIDSafe(label)
        if i<0:
            raise KeyError('Variable `'+ label+'` not found in FAST file:'+self.filename)
        else:
            return i

    def getIDs(self,label):
        I=[]
        # brute force search
        for i in range(len(self.data)):
            d = self.data[i]
            if d['label'].lower()==label.lower():
                I.append(i)
        if len(I)<0:
            raise KeyError('Variable `'+ label+'` not found in FAST file:'+self.filename)
        else:
            return I

    def getIDSafe(self,label):
        # brute force search
        for i in range(len(self.data)):
            d = self.data[i]
            if d['label'].lower()==label.lower():
                return i
        return -1

    # Making object an iterator
    def __iter__(self):
        self.iCurrent=-1
        self.iMax=len(self.data)-1
        return self

    def __next__(self): # Python 2: def next(self)
        if self.iCurrent > self.iMax:
            raise StopIteration
        else:
            self.iCurrent += 1
            return self.data[self.iCurrent]

    # Making it behave like a dictionary
    def __setitem__(self,key,item):
        I = self.getIDs(key)
        for i in I: 
            self.data[i]['value'] = item

    def __getitem__(self,key):
        i = self.getID(key)
        return self.data[i]['value']

    def __repr__(self):
        s ='Fast input file: {}\n'.format(self.filename)
        return s+'\n'.join(['{:15s}: {}'.format(d['label'],d['value']) for i,d in enumerate(self.data)])

    def addKeyVal(self,key,val,descr=None):
        d=getDict()
        d['label']=key
        d['value']=val
        if descr is not None:
            d['descr']=descr
        self.data.append(d)

    def read(self, filename=None):
        if filename:
            self.filename = filename
        if self.filename:
            if not os.path.isfile(self.filename):
                raise OSError(2,'File not found:',self.filename)
            if os.stat(self.filename).st_size == 0:
                raise EmptyFileError('File is empty:',self.filename)
            self._read()
        else:  
            raise Exception('No filename provided')

    def _read(self):

        # --- Tables that can be detected based on the "Value" (first entry on line)
        # TODO members for  BeamDyn with mutliple key point                                                                                                                                                                                                                                                                                                        ####### TODO PropSetID is Duplicate SubDyn and used in HydroDyn
        NUMTAB_FROM_VAL_DETECT  = ['HtFract'  , 'TwrElev'   , 'BlFract'  , 'Genspd_TLU' , 'BlSpn'        , 'WndSpeed' , 'HvCoefID' , 'AxCoefID' , 'JointID'  , 'Dpth'      , 'FillNumM'    , 'MGDpth'    , 'SimplCd'  , 'RNodes'       , 'kp_xr'      , 'mu1'           , 'TwrHtFr'   , 'TwrRe'  , 'WT_X']
        NUMTAB_FROM_VAL_DIM_VAR = ['NTwInpSt' , 'NumTwrNds' , 'NBlInpSt' , 'DLL_NumTrq' , 'NumBlNds'     , 'NumCases' , 'NHvCoef'  , 'NAxCoef'  , 'NJoints'  , 'NCoefDpth' , 'NFillGroups' , 'NMGDepths' , 1          , 'BldNodes'     , 'kp_total'   , 1               , 'NTwrHt'    , 'NTwrRe' , 'NumTurbines']
        NUMTAB_FROM_VAL_VARNAME = ['TowProp'  , 'TowProp'   , 'BldProp'  , 'DLLProp'    , 'BldAeroNodes' , 'Cases'    , 'HvCoefs'  , 'AxCoefs'  , 'Joints'   , 'DpthProp'  , 'FillGroups'  , 'MGProp'    , 'SmplProp' , 'BldAeroNodes' , 'MemberGeom' , 'DampingCoeffs' , 'TowerProp' , 'TowerRe', 'WindTurbines']
        NUMTAB_FROM_VAL_NHEADER = [2          , 2           , 2          , 2            , 2              , 2          , 2          , 2          , 2          , 2           , 2             , 2           , 2          , 1              , 2            , 2               , 1           , 1        , 2 ]
        NUMTAB_FROM_VAL_TYPE    = ['num'      , 'num'       , 'num'      , 'num'        , 'num'          , 'num'      , 'num'      , 'num'      , 'num'      , 'num'       , 'num'         , 'num'       , 'num'      , 'mix'          , 'num'        , 'num'           , 'num'       , 'num'    , 'mix']
        # SubDyn
        NUMTAB_FROM_VAL_DETECT  += [ 'RJointID'        , 'IJointID'        , 'COSMID'             , 'CMJointID'         ]
        NUMTAB_FROM_VAL_DIM_VAR += [ 'NReact'          , 'NInterf'         , 'NCOSMs'             , 'NCmass'            ]
        NUMTAB_FROM_VAL_VARNAME += [ 'BaseJoints'      , 'InterfaceJoints' , 'MemberCosineMatrix' , 'ConcentratedMasses']
        NUMTAB_FROM_VAL_NHEADER += [ 2                 , 2                 , 2                    , 2                   ]
        NUMTAB_FROM_VAL_TYPE    += [ 'mix'             , 'num'             , 'num'                , 'num'               ]


        # --- Tables that can be detected based on the "Label" (second entry on line)
        # NOTE: MJointID1, used by SubDyn and HydroDyn
        NUMTAB_FROM_LAB_DETECT   = ['NumAlf'  , 'F_X'       , 'MemberCd1'    , 'MJointID1' , 'NOutLoc'    , 'NOutCnt'    , 'PropD'       ,'Diam'       ,'Type'           ,'LineType' ]
        NUMTAB_FROM_LAB_DIM_VAR  = ['NumAlf'  , 'NKInpSt'   , 'NCoefMembers' , 'NMembers'  , 'NMOutputs'  , 'NMOutputs'  , 'NPropSets'   ,'NTypes'     ,'NConnects'      ,'NLines'   ]
        NUMTAB_FROM_LAB_VARNAME  = ['AFCoeff' , 'TMDspProp' , 'MemberProp'   , 'Members'   , 'MemberOuts' , 'MemberOuts' , 'SectionProp' ,'LineTypes'  ,'ConnectionProp' ,'LineProp' ]
        NUMTAB_FROM_LAB_NHEADER  = [2         , 2           , 2              , 2           , 2            , 2            , 2             , 2           , 2               , 2         ]
        NUMTAB_FROM_LAB_NOFFSET  = [0         , 0           , 0              , 0           , 0            , 0            , 0             , 0           , 0               , 0         ]
        NUMTAB_FROM_LAB_TYPE     = ['num'     , 'num'       , 'num'          , 'mix'       , 'num'        , 'num'        , 'num'         ,'mix'        ,'mix'            ,'mix'      ]
        # SubDyn
        NUMTAB_FROM_LAB_DETECT   += ['GuyanDampSize'     , 'YoungE'   , 'YoungE'    , 'EA'             , 'MatDens'       ]
        NUMTAB_FROM_LAB_DIM_VAR  += [6                   , 'NPropSets', 'NXPropSets', 'NCablePropSets' , 'NRigidPropSets']
        NUMTAB_FROM_LAB_VARNAME  += ['GuyanDampMatrix'   , 'BeamProp' , 'BeamPropX' , 'CableProp'      , 'RigidProp'     ]
        NUMTAB_FROM_LAB_NHEADER  += [0                   , 2          , 2           , 2                , 2               ]
        NUMTAB_FROM_LAB_NOFFSET  += [1                   , 0          , 0           , 0                , 0               ]
        NUMTAB_FROM_LAB_TYPE     += ['num'               , 'num'      , 'num'       , 'num'            , 'num'           ]
        # OLAF
        NUMTAB_FROM_LAB_DETECT   += ['GridName'   ]
        NUMTAB_FROM_LAB_DIM_VAR  += ['nGridOut'   ]
        NUMTAB_FROM_LAB_VARNAME  += ['GridOutputs']
        NUMTAB_FROM_LAB_NHEADER  += [0            ]
        NUMTAB_FROM_LAB_NOFFSET  += [2            ]
        NUMTAB_FROM_LAB_TYPE     += ['mix'        ]

        FILTAB_FROM_LAB_DETECT   = ['FoilNm' ,'AFNames']
        FILTAB_FROM_LAB_DIM_VAR  = ['NumFoil','NumAFfiles']
        FILTAB_FROM_LAB_VARNAME  = ['FoilNm' ,'AFNames']

        # Using lower case to be more tolerant..
        NUMTAB_FROM_VAL_DETECT_L = [s.lower() for s in NUMTAB_FROM_VAL_DETECT]
        NUMTAB_FROM_LAB_DETECT_L = [s.lower() for s in NUMTAB_FROM_LAB_DETECT]                                         
        FILTAB_FROM_LAB_DETECT_L = [s.lower() for s in FILTAB_FROM_LAB_DETECT]

        self.data   = []
        self.hasNodal=False
        self.module = None
        #with open(self.filename, 'r', errors="surrogateescape") as f:
        with open(self.filename, 'r', errors="surrogateescape") as f:
            lines=f.read().splitlines()
        # IF NEEDED> DO THE FOLLOWING FORMATTING:
            #lines = [str(l).encode('utf-8').decode('ascii','ignore') for l in f.read().splitlines()]

        # Fast files start with ! or -
        #if lines[0][0]!='!' and lines[0][0]!='-':
        #    raise Exception('Fast file do not start with ! or -, is it the right format?')

        # Special filetypes
        if self.detectAndReadExtPtfmSE(lines):
            return
        if self.detectAndReadAirfoil(lines):
            return

        # Parsing line by line, storing each line into a dictionary
        i=0    
        nComments  = 0
        nWrongLabels = 0
        allowSpaceSeparatedList=False
        while i<len(lines):
            line = lines[i]

            # --- Read special sections
            if line.upper().find('ADDITIONAL OUTPUTS')>0 \
            or line.upper().find('MESH-BASED OUTPUTS')>0 \
            or line.upper().find('OUTPUT CHANNELS'   )>0: # "OutList - The next line(s) contains a list of output parameters. See OutListParameters.xlsx for a listing of available output channels, (-)'"
                # TODO, lazy implementation so far, MAKE SUB FUNCTION
                parts = re.match(r'^\W*\w+', line)
                if parts:
                    firstword = parts.group(0).strip()
                else:
                    raise NotImplementedError
                remainer  = re.sub(r'^\W*\w+\W*', '', line)
                # Parsing outlist, and then we continue at a new "i" (to read END etc.)
                OutList,i = parseFASTOutList(lines,i+1) 
                d = getDict()
                if self.hasNodal:
                    d['label']   = firstword+'_Nodal'
                else:
                    d['label']   = firstword
                d['descr']   = remainer
                d['tabType'] = TABTYPE_FIL # TODO
                d['value']   = ['']+OutList
                self.data.append(d)
                if i>=len(lines):
                    break
                # --- Here we cheat and force an exit of the input file
                # The reason for this is that some files have a lot of things after the END, which will result in the file being intepreted as a wrong format due to too many comments
                if i+2<len(lines) and (lines[i+2].lower().find('bldnd_bladesout')>0 or lines[i+2].lower().find('bldnd_bloutnd')>0):
                    self.hasNodal=True
                else:
                    self.data.append(parseFASTInputLine('END of input file (the word "END" must appear in the first 3 columns of this last OutList line)',i+1))
                    self.data.append(parseFASTInputLine('---------------------------------------------------------------------------------------',i+2))
                    break
            elif line.upper().find('SSOUTLIST'   )>0 or line.upper().find('SDOUTLIST'   )>0:
                # SUBDYN Outlist doesn not follow regular format
                self.data.append(parseFASTInputLine(line,i))
                # OUTLIST Exception for BeamDyn
                OutList,i = parseFASTOutList(lines,i+1) 
                # TODO
                for o in OutList:
                    d = getDict()
                    d['isComment'] = True
                    d['value']=o
                    self.data.append(d)
                # --- Here we cheat and force an exit of the input file
                self.data.append(parseFASTInputLine('END of input file (the word "END" must appear in the first 3 columns of this last OutList line)',i+1))
                self.data.append(parseFASTInputLine('---------------------------------------------------------------------------------------',i+2))
                break
            elif line.upper().find('ADDITIONAL STIFFNESS')>0:
                # TODO, lazy implementation so far, MAKE SUB FUNCTION
                self.data.append(parseFASTInputLine(line,i))
                i +=1
                KDAdd = []
                for _ in range(19):
                    KDAdd.append(lines[i])
                    i +=1
                d = getDict()
                d['label']   = 'KDAdd'   # TODO
                d['tabType'] = TABTYPE_FIL # TODO
                d['value']   = KDAdd
                self.data.append(d)
                if i>=len(lines):
                    break
            elif line.upper().find('DISTRIBUTED PROPERTIES')>0:
                self.data.append(parseFASTInputLine(line,i));
                i+=1;
                self.readBeamDynProps(lines,i)
                return

            # --- Parsing of standard lines: value(s) key comment
            line = lines[i]
            d = parseFASTInputLine(line,i,allowSpaceSeparatedList)

            # --- Handling of special files
            if d['label'].lower()=='kp_total':
                # BeamDyn has weird space speparated list around keypoint definition
                allowSpaceSeparatedList=True
            elif d['label'].lower()=='numcoords':
                # TODO, lazy implementation so far, MAKE SUB FUNCTION
                if isStr(d['value']):
                    if d['value'][0]=='@':
                        # it's a ref to the airfoil coord file
                        pass
                else:
                    if not strIsInt(d['value']): 
                        raise WrongFormatError('Wrong value of NumCoords')
                    if int(d['value'])<=0:
                        pass
                    else:
                        self.data.append(d); i+=1;
                        # 3 comment lines
                        self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                        self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                        self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                        splits=cleanAfterChar(cleanLine(lines[i]),'!').split()
                        # Airfoil ref point
                        try:
                            pos=[float(splits[0]), float(splits[1])]
                        except:
                            raise WrongFormatError('Wrong format while reading coordinates of airfoil reference')
                        i+=1
                        d = getDict()
                        d['label'] = 'AirfoilRefPoint'
                        d['value'] = pos
                        self.data.append(d)
                        # 2 comment lines
                        self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                        self.data.append(parseFASTInputLine(lines[i],i)); i+=1;
                        # Table of coordinats itself
                        d = getDict()
                        d['label']     = 'AirfoilCoord'
                        d['tabDimVar'] = 'NumCoords'
                        d['tabType']   = TABTYPE_NUM_WITH_HEADERCOM
                        nTabLines = self[d['tabDimVar']]-1  # SOMEHOW ONE DATA POINT LESS
                        d['value'], d['tabColumnNames'],_  = parseFASTNumTable(self.filename,lines[i:i+nTabLines+1],nTabLines,i,1)
                        d['tabUnits'] = ['(-)','(-)']
                        self.data.append(d)
                        break



            #print('label>',d['label'],'<',type(d['label']));
            #print('value>',d['value'],'<',type(d['value']));
            #print(isStr(d['value']))
            #if isStr(d['value']):
            #    print(d['value'].lower() in NUMTAB_FROM_VAL_DETECT_L)

                
            # --- Handling of tables
            if isStr(d['value']) and d['value'].lower() in NUMTAB_FROM_VAL_DETECT_L:
                # Table with numerical values, 
                ii             = NUMTAB_FROM_VAL_DETECT_L.index(d['value'].lower())
                tab_type       = NUMTAB_FROM_VAL_TYPE[ii]
                if tab_type=='num':
                    d['tabType']   = TABTYPE_NUM_WITH_HEADER
                else:
                    d['tabType']   = TABTYPE_MIX_WITH_HEADER
                d['label']     = NUMTAB_FROM_VAL_VARNAME[ii]
                d['tabDimVar'] = NUMTAB_FROM_VAL_DIM_VAR[ii]
                nHeaders       = NUMTAB_FROM_VAL_NHEADER[ii]
                nTabLines=0
                if isinstance(d['tabDimVar'],int):
                    nTabLines = d['tabDimVar']
                else:
                    nTabLines = self[d['tabDimVar']]
                #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                d['value'], d['tabColumnNames'], d['tabUnits'] = parseFASTNumTable(self.filename,lines[i:i+nTabLines+nHeaders], nTabLines, i, nHeaders, tableType=tab_type, varNumLines=d['tabDimVar'])
                i += nTabLines+nHeaders-1

                # --- Temporary hack for e.g. SubDyn, that has duplicate table, impossible to detect in the current way...
                # So we remove the element form the list one read
                del NUMTAB_FROM_VAL_DETECT[ii]  
                del NUMTAB_FROM_VAL_DIM_VAR[ii] 
                del NUMTAB_FROM_VAL_VARNAME[ii] 
                del NUMTAB_FROM_VAL_NHEADER[ii] 
                del NUMTAB_FROM_VAL_TYPE   [ii] 
                del NUMTAB_FROM_VAL_DETECT_L[ii]  

            elif isStr(d['label']) and d['label'].lower() in NUMTAB_FROM_LAB_DETECT_L:
                ii      = NUMTAB_FROM_LAB_DETECT_L.index(d['label'].lower())
                tab_type       = NUMTAB_FROM_LAB_TYPE[ii]
                # Special case for airfoil data, the table follows NumAlf, so we add d first
                if d['label'].lower()=='numalf':
                    d['tabType']=TABTYPE_NOT_A_TAB
                    self.data.append(d)
                    # Creating a new dictionary for the table
                    d = {'value':None, 'label':'NumAlf', 'isComment':False, 'descr':'', 'tabType':None}
                    i += 1
                nHeaders       = NUMTAB_FROM_LAB_NHEADER[ii]
                nOffset        = NUMTAB_FROM_LAB_NOFFSET[ii]
                if nOffset>0:
                    # Creating a dictionary for that entry
                    dd = {'value':d['value'], 'label':d['label'], 'isComment':False, 'descr':d['descr'], 'tabType':TABTYPE_NOT_A_TAB}
                    self.data.append(dd)

                d['label']     = NUMTAB_FROM_LAB_VARNAME[ii]
                d['tabDimVar'] = NUMTAB_FROM_LAB_DIM_VAR[ii]
                if d['label'].lower()=='afcoeff' :
                    d['tabType']        = TABTYPE_NUM_WITH_HEADERCOM
                else:
                    if tab_type=='num':
                        d['tabType']   = TABTYPE_NUM_WITH_HEADER
                    else:
                        d['tabType']   = TABTYPE_MIX_WITH_HEADER
                if isinstance(d['tabDimVar'],int):
                    nTabLines = d['tabDimVar']
                else:
                    nTabLines = self[d['tabDimVar']]
                #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                d['value'], d['tabColumnNames'], d['tabUnits'] = parseFASTNumTable(self.filename,lines[i:i+nTabLines+nHeaders+nOffset],nTabLines,i, nHeaders, tableType=tab_type, nOffset=nOffset, varNumLines=d['tabDimVar'])
                i += nTabLines+1-nOffset

                # --- Temporary hack for e.g. SubDyn, that has duplicate table, impossible to detect in the current way...
                # So we remove the element form the list one read
                del NUMTAB_FROM_LAB_DETECT[ii]  
                del NUMTAB_FROM_LAB_DIM_VAR[ii] 
                del NUMTAB_FROM_LAB_VARNAME[ii] 
                del NUMTAB_FROM_LAB_NHEADER[ii] 
                del NUMTAB_FROM_LAB_NOFFSET[ii] 
                del NUMTAB_FROM_LAB_TYPE   [ii] 
                del NUMTAB_FROM_LAB_DETECT_L[ii]  

            elif isStr(d['label']) and d['label'].lower() in FILTAB_FROM_LAB_DETECT_L:
                ii             = FILTAB_FROM_LAB_DETECT_L.index(d['label'].lower())
                d['label']     = FILTAB_FROM_LAB_VARNAME[ii]
                d['tabDimVar'] = FILTAB_FROM_LAB_DIM_VAR[ii]
                d['tabType']   = TABTYPE_FIL
                nTabLines = self[d['tabDimVar']]
                #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                d['value'] = parseFASTFilTable(lines[i:i+nTabLines],nTabLines,i)
                i += nTabLines-1



            self.data.append(d)
            i += 1
            # --- Safety checks
            if d['isComment']:
                #print(line)
                nComments +=1
            else:
                if hasSpecialChars(d['label']):
                    nWrongLabels +=1
                    #print('label>',d['label'],'<',type(d['label']),line);
                    if i>3: # first few lines may be comments, we allow it
                        #print('Line',i,'Label:',d['label'])
                        raise WrongFormatError('Special Character found in Label: `{}`, for line: `{}`'.format(d['label'],line))
                if len(d['label'])==0:
                    nWrongLabels +=1
            if nComments>len(lines)*0.35:
                #print('Comment fail',nComments,len(lines),self.filename)
                raise WrongFormatError('Most lines were read as comments, probably not a FAST Input File')
            if nWrongLabels>len(lines)*0.10:
                #print('Label fail',nWrongLabels,len(lines),self.filename)
                raise WrongFormatError('Too many lines with wrong labels, probably not a FAST Input File')

        # --- PostReading checks
        labels = self.keys()
        duplicates = set([x for x in labels if (labels.count(x) > 1) and x!='OutList' and x.strip()!='-'])
        if len(duplicates)>0:
            print('[WARN] Duplicate labels found in file: '+self.filename)
            print('       Duplicates: '+', '.join(duplicates))
            print('       It\'s strongly recommended to make them unique! ')
#         except WrongFormatError as e:    
#             raise WrongFormatError('Fast File {}: '.format(self.filename)+'\n'+e.args[0])
#         except Exception as e:    
#             raise e
# #             print(e)
#             raise Exception('Fast File {}: '.format(self.filename)+'\n'+e.args[0])

            
    def toString(self):
        s=''
        # Special file formats, TODO subclass
        if self.module=='ExtPtfm':
            s+='!Comment\n'
            s+='!Comment Flex 5 Format\n'
            s+='!Dimension: {}\n'.format(self['nDOF'])
            s+='!Time increment in simulation: {}\n'.format(self['dt'])
            s+='!Total simulation time in file: {}\n'.format(self['T'])

            s+='\n!Mass Matrix\n'
            s+='!Dimension: {}\n'.format(self['nDOF'])
            s+='\n'.join(''.join('{:16.8e}'.format(x) for x in y) for y in self['MassMatrix'])

            s+='\n\n!Stiffness Matrix\n'
            s+='!Dimension: {}\n'.format(self['nDOF'])
            s+='\n'.join(''.join('{:16.8e}'.format(x) for x in y) for y in self['StiffnessMatrix'])

            s+='\n\n!Damping Matrix\n'
            s+='!Dimension: {}\n'.format(self['nDOF'])
            s+='\n'.join(''.join('{:16.8e}'.format(x) for x in y) for y in self['DampingMatrix'])

            s+='\n\n!Loading and Wave Elevation\n'
            s+='!Dimension: 1 time column -  {} force columns\n'.format(self['nDOF'])
            s+='\n'.join(''.join('{:16.8e}'.format(x) for x in y) for y in self['Loading'])
            return s

        def toStringVLD(val,lab,descr):
            val='{}'.format(val)
            lab='{}'.format(lab)
            if len(val)<13:
                val='{:13s}'.format(val)
            if len(lab)<13:
                lab='{:13s}'.format(lab)
            return val+' '+lab+' - '+descr.strip().strip('-').strip()+'\n'

        def beamdyn_section_mat_tostring(x,K,M):
            def mat_tostring(M,fmt='24.16e'):
                return '\n'.join(['   '+' '.join(['{:24.16E}'.format(m) for m in M[i,:]]) for i in range(np.size(M,1))])
            s=''
            s+='{:.6f}\n'.format(x)
            s+=mat_tostring(K)
            #s+=np.array2string(K)
            s+='\n'
            s+='\n'
            s+=mat_tostring(M)
            #s+=np.array2string(M)
            s+='\n'
            s+='\n'
            return s


        for i in range(len(self.data)):
            d=self.data[i]
            if d['isComment']:
                s+='{}'.format(d['value'])
            elif d['tabType']==TABTYPE_NOT_A_TAB:
                if isinstance(d['value'], list):
                    sList=', '.join([str(x) for x in d['value']])
                    s+='{} {} {}'.format(sList,d['label'],d['descr'])
                else:
                    s+=toStringVLD(d['value'],d['label'],d['descr']).strip()
            elif d['tabType']==TABTYPE_NUM_WITH_HEADER:
                if d['tabColumnNames'] is not None:
                    s+='{}'.format(' '.join(['{:15s}'.format(s) for s in d['tabColumnNames']]))
                #s+=d['descr'] # Not ready for that
                    if d['tabUnits'] is not None:
                        s+='\n'
                        s+='{}'.format(' '.join(['{:15s}'.format(s) for s in d['tabUnits']]))
                    newline='\n'
                else:
                    newline=''
                if np.size(d['value'],0) > 0 :
                    s+=newline
                    s+='\n'.join('\t'.join( ('{:15.0f}'.format(x) if int(x)==x else '{:15.8e}'.format(x) )  for x in y) for y in d['value'])
            elif d['tabType']==TABTYPE_MIX_WITH_HEADER:
                s+='{}'.format(' '.join(['{:15s}'.format(s) for s in d['tabColumnNames']]))
                if d['tabUnits'] is not None:
                    s+='\n'
                    s+='{}'.format(' '.join(['{:15s}'.format(s) for s in d['tabUnits']]))
                if np.size(d['value'],0) > 0 :
                    s+='\n'
                    s+='\n'.join('\t'.join('{}'.format(x) for x in y) for y in d['value'])
            elif d['tabType']==TABTYPE_NUM_WITH_HEADERCOM:
                s+='! {}\n'.format(' '.join(['{:15s}'.format(s) for s in d['tabColumnNames']]))
                s+='! {}\n'.format(' '.join(['{:15s}'.format(s) for s in d['tabUnits']]))
                s+='\n'.join('\t'.join('{:15.8e}'.format(x) for x in y) for y in d['value'])
            elif d['tabType']==TABTYPE_FIL:
                #f.write('{} {} {}\n'.format(d['value'][0],d['tabDetect'],d['descr']))
                s+='{} {} {}\n'.format(d['value'][0],d['label'],d['descr']) # TODO?
                s+='\n'.join(fil for fil in d['value'][1:])
            elif d['tabType']==TABTYPE_NUM_BEAMDYN:
                data = d['value']
                Cols =['Span'] 
                Cols+=['K{}{}'.format(i+1,j+1) for i in range(6) for j in range(6)] 
                Cols+=['M{}{}'.format(i+1,j+1) for i in range(6) for j in range(6)] 
                for i in np.arange(len(data['span'])):
                    x = data['span'][i]
                    K = data['K'][i]
                    M = data['M'][i]
                    s += beamdyn_section_mat_tostring(x,K,M)
            else:
                raise Exception('Unknown table type for variable {}'.format(d))
            if i<len(self.data)-1:
                s+='\n'
        return s

    def write(self, filename=None):
        if filename:
            self.filename = filename
        if self.filename:
            self._write()
        else:
            raise Exception('No filename provided')

    def _write(self):
        with open(self.filename,'w') as f:
            f.write(self.toString())

    def _toDataFrame(self):
        dfs={}
        # Special types, TODO Subclass
        if self.module=='ExtPtfm':
            nDOF=self['nDOF']
            Cols=['Time_[s]','InpF_Fx_[N]', 'InpF_Fy_[N]', 'InpF_Fz_[N]', 'InpF_Mx_[Nm]', 'InpF_My_[Nm]', 'InpF_Mz_[Nm]']
            Cols+=['CBF_{:03d}_[-]'.format(iDOF+1) for iDOF in np.arange(nDOF)]
            Cols=Cols[:nDOF+1]
            #dfs['Loading']         = pd.DataFrame(data = self['Loading'],columns  = Cols)
            dfs = pd.DataFrame(data = self['Loading'],columns  = Cols)

            #Cols=['SurgeAcc_[m/s]', 'SwayAcc_[m/s]', 'HeaveAcc_[m/s]', 'RollAcc_[rad/s]', 'PitchAcc_[rad/s]', 'YawAcc_[rad/s]']
            #Cols+=['CBQD_{:03d}_[-]'.format(iDOF+1) for iDOF in np.arange(nDOF)]
            #Cols=Cols[:nDOF]
            #dfs['MassMatrix']      = pd.DataFrame(data = self['MassMatrix'], columns=Cols)

            #Cols=['SurgeVel_[m/s]', 'SwayVel_[m/s]', 'HeaveVel_[m/s]', 'RollVel_[rad/s]', 'PitchVel_[rad/s]', 'YawVel_[rad/s]']
            #Cols+=['CBQD_{:03d}_[-]'.format(iDOF+1) for iDOF in np.arange(nDOF)]
            #Cols=Cols[:nDOF]
            #dfs['DampingMatrix']   = pd.DataFrame(data = self['DampingMatrix'], columns=Cols)

            #Cols=['Surge_[m]', 'Sway_[m]', 'Heave_[m]', 'Roll_[rad]', 'Pitch_[rad]', 'Yaw_[rad]']
            #Cols+=['CBQ_{:03d}_[-]'.format(iDOF+1) for iDOF in np.arange(nDOF)]
            #Cols=Cols[:nDOF]
            #dfs['StiffnessMatrix'] = pd.DataFrame(data = self['StiffnessMatrix'], columns=Cols)
            return dfs

        for i in range(len(self.data)): 
            d=self.data[i]
            if d['tabType'] in [TABTYPE_NUM_WITH_HEADER, TABTYPE_NUM_WITH_HEADERCOM, TABTYPE_NUM_NO_HEADER, TABTYPE_MIX_WITH_HEADER]:
                Val= d['value']
                if d['tabUnits'] is None:
                    Cols=d['tabColumnNames']
                else:
                    Cols=['{}_{}'.format(c,u.replace('(','[').replace(')',']')) for c,u in zip(d['tabColumnNames'],d['tabUnits'])]
                #print(Val)
                #print(Cols)

                # --- Adding some useful tabulated data for some files (Shapefunctions, polar)
                if self.getIDSafe('BldFl1Sh(2)')>0:
                    # Hack for blade files, we add the modes
                    x=Val[:,0]
                    Modes=np.zeros((x.shape[0],3))
                    Modes[:,0] = x**2 * self['BldFl1Sh(2)'] \
                               + x**3 * self['BldFl1Sh(3)'] \
                               + x**4 * self['BldFl1Sh(4)'] \
                               + x**5 * self['BldFl1Sh(5)'] \
                               + x**6 * self['BldFl1Sh(6)'] 
                    Modes[:,1] = x**2 * self['BldFl2Sh(2)'] \
                               + x**3 * self['BldFl2Sh(3)'] \
                               + x**4 * self['BldFl2Sh(4)'] \
                               + x**5 * self['BldFl2Sh(5)'] \
                               + x**6 * self['BldFl2Sh(6)'] 
                    Modes[:,2] = x**2 * self['BldEdgSh(2)'] \
                               + x**3 * self['BldEdgSh(3)'] \
                               + x**4 * self['BldEdgSh(4)'] \
                               + x**5 * self['BldEdgSh(5)'] \
                               + x**6 * self['BldEdgSh(6)'] 
                    Val = np.hstack((Val,Modes))
                    Cols = Cols + ['ShapeFlap1_[-]','ShapeFlap2_[-]','ShapeEdge1_[-]']
                  
                elif self.getIDSafe('TwFAM1Sh(2)')>0:
                    # Hack for tower files, we add the modes
                    x=Val[:,0]
                    Modes=np.zeros((x.shape[0],4))
                    Modes[:,0] = x**2 * self['TwFAM1Sh(2)'] \
                               + x**3 * self['TwFAM1Sh(3)'] \
                               + x**4 * self['TwFAM1Sh(4)'] \
                               + x**5 * self['TwFAM1Sh(5)'] \
                               + x**6 * self['TwFAM1Sh(6)'] 
                    Modes[:,1] = x**2 * self['TwFAM2Sh(2)'] \
                               + x**3 * self['TwFAM2Sh(3)'] \
                               + x**4 * self['TwFAM2Sh(4)'] \
                               + x**5 * self['TwFAM2Sh(5)'] \
                               + x**6 * self['TwFAM2Sh(6)'] 
                    Modes[:,2] = x**2 * self['TwSSM1Sh(2)'] \
                               + x**3 * self['TwSSM1Sh(3)'] \
                               + x**4 * self['TwSSM1Sh(4)'] \
                               + x**5 * self['TwSSM1Sh(5)'] \
                               + x**6 * self['TwSSM1Sh(6)'] 
                    Modes[:,3] = x**2 * self['TwSSM2Sh(2)'] \
                               + x**3 * self['TwSSM2Sh(3)'] \
                               + x**4 * self['TwSSM2Sh(4)'] \
                               + x**5 * self['TwSSM2Sh(5)'] \
                               + x**6 * self['TwSSM2Sh(6)'] 
                    Val = np.hstack((Val,Modes))
                    Cols = Cols + ['ShapeForeAft1_[-]','ShapeForeAft2_[-]','ShapeSideSide1_[-]','ShapeSideSide2_[-]']
                elif d['label']=='AFCoeff':
                    try:
                        pol   = d['value']
                        alpha = pol[:,0]*np.pi/180.
                        Cl    = pol[:,1]
                        Cd    = pol[:,2]
                        Cd0   = self['Cd0']
                        # Cn (with or without Cd0)
                        Cn1 = Cl*np.cos(alpha)+ (Cd-Cd0)*np.sin(alpha) 
                        Cn  = Cl*np.cos(alpha)+ Cd*np.sin(alpha) 
                        Val=np.column_stack((Val,Cn));  Cols+=['Cn_[-]']
                        Val=np.column_stack((Val,Cn1)); Cols+=['Cn_Cd0off_[-]']

                        CnLin = self['C_nalpha']*(alpha-self['alpha0']*np.pi/180.)
                        CnLin[alpha<-20*np.pi/180]=np.nan
                        CnLin[alpha> 30*np.pi/180]=np.nan
                        Val=np.column_stack((Val,CnLin)); Cols+=['Cn_pot_[-]']

                        # Highlighting points surrounding 0 1 2 Cn points
                        CnPoints = Cn*np.nan
                        iBef2 = np.where(alpha<self['alpha2']*np.pi/180.)[0][-1]
                        iBef1 = np.where(alpha<self['alpha1']*np.pi/180.)[0][-1]
                        iBef0 = np.where(alpha<self['alpha0']*np.pi/180.)[0][-1]
                        CnPoints[iBef2:iBef2+2] = Cn[iBef2:iBef2+2]
                        CnPoints[iBef1:iBef1+2] = Cn[iBef1:iBef1+2]
                        CnPoints[iBef0:iBef0+2] = Cn[iBef0:iBef0+2]
                        Val=np.column_stack((Val,CnPoints)); Cols+=['Cn_012_[-]']
                    except:
                        pass

                name=d['label']

                if name=='DampingCoeffs':
                    pass
                else:
                    dfs[name]=pd.DataFrame(data=Val,columns=Cols)
            elif d['tabType'] in [TABTYPE_NUM_BEAMDYN]:
                span = d['value']['span']
                M    = d['value']['M']
                K    = d['value']['K']
                nSpan=len(span)
                MM=np.zeros((nSpan,1+36+36))
                MM[:,0]    = span
                MM[:,1:37] = K.reshape(nSpan,36)
                MM[:,37:]  = M.reshape(nSpan,36)
                Cols =['Span'] 
                Cols+=['K{}{}'.format(i+1,j+1) for i in range(6) for j in range(6)] 
                Cols+=['M{}{}'.format(i+1,j+1) for i in range(6) for j in range(6)] 
                # Putting the main terms first
                IAll = range(1+36+36)
                IMain= [0] + [i*6+i+1 for i in range(6)] + [i*6+i+37 for i in range(6)]
                IOrg = IMain + [i for i in range(1+36+36) if i not in IMain]
                Cols = [Cols[i] for i in IOrg]
                data = MM[:,IOrg]
                name=d['label']
                dfs[name]=pd.DataFrame(data=data,columns=Cols)
        if len(dfs)==1:
            dfs=dfs[list(dfs.keys())[0]]
        return dfs

    def toGraph(self):
        from .fast_input_file_graph import fastToGraph
        return fastToGraph(self)
        


# --------------------------------------------------------------------------------}
# --- SubReaders /detectors
# --------------------------------------------------------------------------------{
    def detectAndReadExtPtfmSE(self,lines):
        def readmat(n,m,lines,iStart):
            M=np.zeros((n,m))
            for j in np.arange(n):
                i=iStart+j
                M[j,:]=np.array(lines[i].split()).astype(float)
            return M
        if len(lines)<10:
            return False
        if not (lines[0][0]=='!' and lines[1][0]=='!'):
            return False
        if lines[1].lower().find('flex')<0:
            return
        if  lines[2].lower().find('!dimension')<0:
            return
        # --- At this stage we assume it's in the proper format
        self.module='ExtPtfm'
        nDOFCommon = -1
        i=2;
        try:
            while i<len(lines):
                l=lines[i].lower()
                if l.find('!mass')==0:
                    l=lines[i+1]
                    nDOF=int(l.split(':')[1])
                    if nDOF<-1 or nDOF!=nDOFCommon:
                        raise BrokenFormatError('ExtPtfm stiffness matrix nDOF issue. nDOF common: {}, nDOF provided: {}'.format(nDOFCommon,nDOF))
                    self.addKeyVal('MassMatrix',readmat(nDOF,nDOF,lines,i+2))
                    i=i+1+nDOF
                elif l.find('!stiffness')==0:
                    l=lines[i+1]
                    nDOF=int(l.split(':')[1])
                    if nDOF<-1 or nDOF!=nDOFCommon:
                        raise BrokenFormatError('ExtPtfm stiffness matrix nDOF issue nDOF common: {}, nDOF provided: {}'.format(nDOFCommon,nDOF))
                    self.addKeyVal('StiffnessMatrix',readmat(nDOF,nDOF,lines,i+2))
                    i=i+1+nDOF
                elif l.find('!damping')==0:
                    l=lines[i+1]
                    nDOF=int(l.split(':')[1])
                    if nDOF<-1 or nDOF!=nDOFCommon:
                        raise BrokenFormatError('ExtPtfm damping matrix nDOF issue nDOF common: {}, nDOF provided: {}'.format(nDOFCommon,nDOF))
                    self.addKeyVal('DampingMatrix',readmat(nDOF,nDOF,lines,i+2))
                    i=i+1+nDOF
                elif l.find('!loading')==0:
                    try: 
                        nt=int(self['T']/self['dt'])+1
                    except:
                        raise BrokenFormatError('Cannot read loading since time step and simulation time not properly set.')
                    self.addKeyVal('Loading',readmat(nt,nDOFCommon+1,lines,i+2))
                    i=i+nt+1
                elif len(l)>0:
                    if l[0]=='!':
                        if l.find('!dimension')==0:
                            self.addKeyVal('nDOF',int(l.split(':')[1]))
                            nDOFCommon=self['nDOF']
                        elif l.find('!time increment')==0:
                            self.addKeyVal('dt',float(l.split(':')[1]))
                        elif l.find('!total simulation time')==0:
                            self.addKeyVal('T',float(l.split(':')[1]))
                    elif len(l.strip())==0:
                        pass
                    else:
                        raise BrokenFormatError('Unexcepted content found on line {}'.format(i))
                i+=1
        except BrokenFormatError as e:
            raise e
        except: 
            raise


        return True
        


    def detectAndReadAirfoil(self,lines):
        if len(lines)<14:
            return False
        # Reading number of tables
        L3 = lines[2].strip().split()
        if len(L3)<=0:
            return False
        if not strIsInt(L3[0]):
            return False
        nTables=int(L3[0])
        # Reading table ID
        L4 = lines[3].strip().split()
        if len(L4)<=nTables:
            return False
        TableID=L4[:nTables]
        if nTables==1:
            TableID=['']
        # Keywords for file format
        KW1=lines[12].strip().split()
        KW2=lines[13].strip().split()
        if len(KW1)>nTables and len(KW2)>nTables:
            if KW1[nTables].lower()=='angle' and KW2[nTables].lower()=='minimum':
                d = getDict(); d['isComment'] = True; d['value'] = lines[0]; self.data.append(d);
                d = getDict(); d['isComment'] = True; d['value'] = lines[1]; self.data.append(d);
                for i in range(2,14):
                    splits = lines[i].split()
                    #print(splits)
                    d = getDict()
                    d['label'] = ' '.join(splits[1:]) # TODO
                    d['descr'] = ' '.join(splits[1:]) # TODO
                    d['value'] = float(splits[0])
                    self.data.append(d)
                #pass
                #for i in range(2,14):
                nTabLines=0
                while 14+nTabLines<len(lines) and  len(lines[14+nTabLines].strip())>0 :
                    nTabLines +=1
                #data = np.array([lines[i].strip().split() for i in range(14,len(lines)) if len(lines[i])>0]).astype(float)
                #data = np.array([lines[i].strip().split() for i in takewhile(lambda x: len(lines[i].strip())>0, range(14,len(lines)-1))]).astype(float)
                data = np.array([lines[i].strip().split() for i in range(14,nTabLines+14)]).astype(float)
                #print(data)
                d = getDict()
                d['label']     = 'Polar'
                d['tabDimVar'] = nTabLines
                d['tabType']   = TABTYPE_NUM_NO_HEADER
                d['value']     = data
                if np.size(data,1)==1+nTables*3:
                    d['tabColumnNames'] = ['Alpha']+[n+l for l in TableID for n in ['Cl','Cd','Cm']]
                    d['tabUnits']       = ['(deg)']+['(-)' , '(-)' , '(-)']*nTables
                elif np.size(data,1)==1+nTables*2:
                    d['tabColumnNames'] = ['Alpha']+[n+l for l in TableID for n in ['Cl','Cd']]
                    d['tabUnits']       = ['(deg)']+['(-)' , '(-)']*nTables
                else:
                    d['tabColumnNames'] = ['col{}'.format(j) for j in range(np.size(data,1))]
                self.data.append(d)
                return True

    def readBeamDynProps(self,lines,iStart):
        nStations=self['station_total']
        #M=np.zeros((nStations,1+36+36))
        M    = np.zeros((nStations,6,6))
        K    = np.zeros((nStations,6,6))
        span = np.zeros(nStations)
        i=iStart;
        try:
            for j in range(nStations):
                # Read span location
                span[j]=float(lines[i]); i+=1;
                # Read stiffness matrix
                K[j,:,:]=np.array((' '.join(lines[i:i+6])).split()).astype(float).reshape(6,6)
                i+=7
                # Read mass matrix
                M[j,:,:]=np.array((' '.join(lines[i:i+6])).split()).astype(float).reshape(6,6)
                i+=7
        except: 
            raise WrongFormatError('An error occured while reading section {}/{}'.format(j+1,nStations))

        d = getDict()
        d['label']   = 'BeamProperties'
        d['descr']   = ''
        d['tabType'] = TABTYPE_NUM_BEAMDYN
        d['value']   = {'span':span, 'K':K, 'M':M}
        self.data.append(d)

# --------------------------------------------------------------------------------}
# --- Helper functions 
# --------------------------------------------------------------------------------{
def isStr(s):
    # Python 2 and 3 compatible
    # Two options below
    # NOTE: all this avoided since we import str from builtins
    # --- Version 2
    #     isString = False;
    #     if(isinstance(s, str)):
    #         isString = True;
    #     try:
    #         if(isinstance(s, basestring)): # todo unicode as well
    #             isString = True;
    #     except NameError:
    #         pass; 
    #     return isString
    # --- Version 1
    #     try: 
    #        basestring # python 2
    #        return isinstance(s, basestring) or isinstance(s,unicode)
    #     except NameError:
    #          basestring=str #python 3
    #     return isinstance(s, str)
   return isinstance(s, str)

def strIsFloat(s):
    #return s.replace('.',',1').isdigit()
    try:
        float(s)
        return True
    except:
        return False

def strIsBool(s):
    return s.lower() in ['true','false','t','f']

def strIsInt(s):
    s = str(s)
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()    

def strToBool(s):
    return s.lower() in ['true','t']

def hasSpecialChars(s):
    # fast allows for parenthesis
    # For now we allow for - but that's because of BeamDyn geometry members 
    return not re.match("^[\"\'a-zA-Z0-9_()-]*$", s)

def cleanLine(l):
    # makes a string single space separated
    l = l.replace('\t',' ')
    l = ' '.join(l.split())
    l = l.strip()
    return l

def cleanAfterChar(l,c):
    # remove whats after a character
    n = l.find(c);
    if n>0:
        return l[:n]
    else:
        return l

def getDict():
    return {'value':None, 'label':'', 'isComment':False, 'descr':'', 'tabType':TABTYPE_NOT_A_TAB}

def _merge_value(splits):

    merged = splits.pop(0)
    if merged[0] == '"':
        while merged[-1] != '"':
            merged += " "+splits.pop(0)
    splits.insert(0, merged)




def parseFASTInputLine(line_raw,i,allowSpaceSeparatedList=False):
    d = getDict()
    #print(line_raw)
    try:
        # preliminary cleaning (Note: loss of formatting)
        line = cleanLine(line_raw)
        # Comment
        if any(line.startswith(c) for c in ['#','!','--','==']) or len(line)==0:
            d['isComment']=True
            d['value']=line_raw
            return d
        if line.lower().startswith('end'):
            sp =line.split()
            if len(sp)>2 and sp[1]=='of':
                d['isComment']=True
                d['value']=line_raw

        # Detecting lists
        List=[];
        iComma=line.find(',')
        if iComma>0 and iComma<30:
            fakeline=line.replace(' ',',')
            fakeline=re.sub(',+',',',fakeline)
            csplits=fakeline.split(',')
            # Splitting based on comma and looping while it's numbers of booleans
            ii=0
            s=csplits[ii]
            #print(csplits)
            while strIsFloat(s) or strIsBool(s) and ii<len(csplits):
                if strIsInt(s):
                    List.append(int(s))
                elif strIsFloat(s):
                    List.append(float(s))
                elif strIsBool(s):
                    List.append(strToBool(s))
                else:
                    raise WrongFormatError('Lists of strings not supported.')
                ii =ii+1
                if ii>=len(csplits):
                    raise WrongFormatError('Wrong number of list values')
                s = csplits[ii]
            #print('[INFO] Line {}: Found list: '.format(i),List)
        # Defining value and remaining splits
        if len(List)>=2:
            d['value']=List
            line_remaining=line
            # eating line, removing each values
            for iii in range(ii):
                sValue=csplits[iii]
                ipos=line_remaining.find(sValue)
                line_remaining = line_remaining[ipos+len(sValue):]
            splits=line_remaining.split()
            iNext=0
        else:
            # It's not a list, we just use space as separators
            splits=line.split(' ')
            _merge_value(splits)
            s=splits[0]

            if strIsInt(s):
                d['value']=int(s)
                if allowSpaceSeparatedList and len(splits)>1:
                    if strIsInt(splits[1]):
                        d['value']=splits[0]+ ' '+splits[1]
            elif strIsFloat(s):
                d['value']=float(s)
            elif strIsBool(s):
                d['value']=strToBool(s)
            else:
                d['value']=s
            iNext=1
            #import pdb  ; pdb.set_trace();

        # Extracting label (TODO, for now only second split)
        bOK=False
        while (not bOK) and iNext<len(splits):
            # Nasty handling of !XXX: comments
            if splits[iNext][0]=='!' and splits[iNext][-1]==':': 
                iNext=iNext+2
                continue
            # Nasty handling of the fact that sometimes old values are repeated before the label
            if strIsFloat(splits[iNext]):
                iNext=iNext+1
                continue
            else:
                bOK=True
        if bOK:
            d['label']= splits[iNext].strip()
            iNext = iNext+1
        else:
            #print('[WARN] Line {}: No label found -> comment assumed'.format(i+1))
            d['isComment']=True
            d['value']=line_raw
            iNext = len(splits)+1
        
        # Recombining description
        if len(splits)>=iNext+1:
            d['descr']=' '.join(splits[iNext:])
    except WrongFormatError as e:
        raise WrongFormatError('Line {}: '.format(i+1)+e.args[0])
    except Exception as e:
        raise Exception('Line {}: '.format(i+1)+e.args[0])

    return d

def parseFASTOutList(lines,iStart):
    OutList=[]
    i = iStart
    MAX=200
    while i<len(lines) and lines[i].upper().find('END')!=0:
        OutList.append(lines[i]) #TODO better parsing
        #print('OutList',lines[i])
        i += 1
        if i-iStart>MAX :
            raise Exception('More that 200 lines found in outlist')
        if i>=len(lines):
            print('[WARN] End of file reached while reading Outlist')
    #i=min(i+1,len(lines))
    return OutList,iStart+len(OutList)


def extractWithinParenthesis(s):
    mo = re.search(r'\((.*)\)', s)
    if mo:
        return mo.group(1)
    return ''

def extractWithinBrackets(s):
    mo = re.search(r'\((.*)\)', s)
    if mo:
        return mo.group(1)
    return ''

def detectUnits(s,nRef):
    nPOpen=s.count('(')
    nPClos=s.count(')')
    nBOpen=s.count('[')
    nBClos=s.count(']')

    sep='!#@#!'
    if (nPOpen == nPClos) and (nPOpen>=nRef):
        #that's pretty good
        Units=s.replace('(','').replace(')',sep).split(sep)[:-1]
    elif (nBOpen == nBClos) and (nBOpen>=nRef):
        Units=s.replace('[','').replace(']',sep).split(sep)[:-1]
    else:
        Units=s.split()
    return Units


def parseFASTNumTable(filename,lines,n,iStart,nHeaders=2,tableType='num',nOffset=0, varNumLines=''):
    """ 
    First lines of data starts at: nHeaders+nOffset
    
    """
    Tab = None
    ColNames = None
    Units = None
    

    if len(lines)!=n+nHeaders+nOffset:
        raise BrokenFormatError('Not enough lines in table: {} lines instead of {}\nFile:{}'.format(len(lines)-nHeaders,n,filename))
    try:
        if nHeaders==0:
            # Extract number of values from number of numerical values on first line
            numeric_const_pattern = r'[-+]? (?: (?: \d* \. \d+ ) | (?: \d+ \.? ) )(?: [Ee] [+-]? \d+ ) ?'
            rx = re.compile(numeric_const_pattern, re.VERBOSE)
            header = cleanAfterChar(lines[nOffset], '!')
            if tableType=='num':
                dat= np.array(rx.findall(header)).astype(float)
                ColNames=['C{}'.format(j) for j in range(len(dat))]
            else:
                raise NotImplementedError('Reading FAST tables with no headers for type different than num not implemented yet')

        elif nHeaders>=1:
            # Extract column names
            i = 0
            sTmp = cleanLine(lines[i])
            sTmp = cleanAfterChar(sTmp,'[')
            sTmp = cleanAfterChar(sTmp,'(')
            sTmp = cleanAfterChar(sTmp,'!')
            sTmp = cleanAfterChar(sTmp,'#')
            if sTmp.startswith('!'):
                sTmp=sTmp[1:].strip()
            ColNames=sTmp.split()
        if nHeaders>=2:
            # Extract units
            i = 1
            sTmp = cleanLine(lines[i])
            sTmp = cleanAfterChar(sTmp,'!')
            sTmp = cleanAfterChar(sTmp,'#')
            if sTmp.startswith('!'):
                sTmp=sTmp[1:].strip()

            Units = detectUnits(sTmp,len(ColNames))
            Units = ['({})'.format(u.strip()) for u in Units]
            # Forcing user to match number of units and column names
            if len(ColNames) != len(Units):
                print(ColNames)
                print(Units)
                print('[WARN] {}: Line {}: Number of column names different from number of units in table'.format(filename, iStart+i+1))

        nCols=len(ColNames)

        if tableType=='num':
            if n==0:
                Tab = np.zeros((n, nCols))
            for i in range(nHeaders+nOffset,n+nHeaders+nOffset):
                l = cleanAfterChar(lines[i].lower(),'!')
                l = cleanAfterChar(l,'#')
                v = l.split()
                if len(v) != nCols:
                    # Discarding SubDyn special cases
                    if ColNames[-1].lower() not in ['nodecnt']:
                        print('[WARN] {}: Line {}: number of data different from number of column names. ColumnNames: {}'.format(filename, iStart+i+1, ColNames))
                if i==nHeaders+nOffset:
                    # Node Cnt
                    if len(v) != nCols:
                        if ColNames[-1].lower()== 'nodecnt':
                            ColNames = ColNames+['Col']*(len(v)-nCols)
                            Units    = Units+['Col']*(len(v)-nCols)

                    nCols=len(v)
                    Tab = np.zeros((n, nCols))
                # Accounting for TRUE FALSE and converting to float
                v = [s.replace('true','1').replace('false','0').replace('noprint','0').replace('print','1') for s in v]
                v = [float(s) for s in v[0:nCols]]
                if len(v) < nCols:
                    raise Exception('Number of data is lower than number of column names')
                Tab[i-nHeaders-nOffset,:] = v
        elif tableType=='mix':
            # a mix table contains a mixed of strings and floats
            # For now, we are being a bit more relaxed about the number of columns
            if n==0:
                Tab = np.zeros((n, nCols)).astype(object)
            for i in range(nHeaders+nOffset,n+nHeaders+nOffset):
                l = lines[i]
                l = cleanAfterChar(l,'!')
                l = cleanAfterChar(l,'#')
                v = l.split()
                if l.startswith('---'):
                    raise BrokenFormatError('Error reading line {} while reading table. Is the variable `{}` set correctly?'.format(iStart+i+1, varNumLines))
                if len(v) != nCols:
                    # Discarding SubDyn special cases
                    if ColNames[-1].lower() not in ['cosmid', 'ssifile']:
                        print('[WARN] {}: Line {}: Number of data is different than number of column names. Column Names: {}'.format(filename,iStart+1+i, ColNames))
                if i==nHeaders+nOffset:
                    if len(v)>nCols:
                        ColNames = ColNames+['Col']*(len(v)-nCols)
                        Units    = Units+['Col']*(len(v)-nCols)
                    nCols=len(v)
                    Tab = np.zeros((n, nCols)).astype(object)
                v=v[0:min(len(v),nCols)]
                Tab[i-nHeaders-nOffset,0:len(v)] = v
            # If all values are float, we convert to float
            if all([strIsFloat(x) for x in Tab.ravel()]):
                Tab=Tab.astype(float)
        else:
            raise Exception('Unknown table type')

        ColNames = ColNames[0:nCols]
        if Units is not None:
            Units    = Units[0:nCols]
            Units    = ['('+u.replace('(','').replace(')','')+')' for u in Units]
        if nHeaders==0:
            ColNames=None
            
    except Exception as e:    
        raise BrokenFormatError('Line {}: {}'.format(iStart+i+1,e.args[0]))
    return Tab, ColNames, Units


def parseFASTFilTable(lines,n,iStart):
    Tab = []
    try:
        i=0
        if len(lines)!=n:
            raise WrongFormatError('Not enough lines in table: {} lines instead of {}'.format(len(lines),n))
        for i in range(n):
            l = lines[i].split()
            #print(l[0].strip())
            Tab.append(l[0].strip())
            
    except Exception as e:    
        raise Exception('Line {}: '.format(iStart+i+1)+e.args[0])
    return Tab


if __name__ == "__main__":
    pass
    #B=FASTIn('Turbine.outb')



