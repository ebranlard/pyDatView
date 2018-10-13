from .File import File
import numpy as np
import re
import pandas as pd


NUMTAB_FROM_VAL_DETECT   = ['HtFract' ,'TwrElev'  ,'BlFract' ,'Genspd_TLU','BlSpn'   ,'WndSpeed']
NUMTAB_FROM_VAL_DETECT_L = [s.lower() for s in NUMTAB_FROM_VAL_DETECT]
NUMTAB_FROM_VAL_DIM_VAR  = ['NTwInpSt','NumTwrNds','NBlInpSt','DLL_NumTrq','NumBlNds','NumCases']
NUMTAB_FROM_VAL_VARNAME  = ['TowProp' ,'TowProp'  ,'BldProp' ,'DLLProp'   ,'BldNodes','Cases']

NUMTAB_FROM_LAB_DETECT   = ['NumAlf' ,'F_X']
NUMTAB_FROM_LAB_DETECT_L = [s.lower() for s in NUMTAB_FROM_LAB_DETECT]
NUMTAB_FROM_LAB_DIM_VAR  = ['NumAlf' ,'NKInpSt']
NUMTAB_FROM_LAB_VARNAME  = ['AFCoeff','TMDspProp']

FMTTAB_FROM_VAL_DETECT   = ['RNodes']
FMTTAB_FROM_VAL_DETECT_L = [s.lower() for s in FMTTAB_FROM_VAL_DETECT]
FMTTAB_FROM_VAL_DIM_VAR  = ['BldNodes']
FMTTAB_FROM_VAL_VARNAME  = ['BldNodes']

FILTAB_FROM_LAB_DETECT   = ['FoilNm' ,'AFNames']
FILTAB_FROM_LAB_DETECT_L = [s.lower() for s in FILTAB_FROM_LAB_DETECT]
FILTAB_FROM_LAB_DIM_VAR  = ['NumFoil','NumAFfiles']
FILTAB_FROM_LAB_VARNAME  = ['FoilNm' ,'FoilNm']

TABTYPE_NOT_A_TAB          = 0
TABTYPE_NUM_WITH_HEADER    = 1
TABTYPE_NUM_WITH_HEADERCOM = 2
TABTYPE_FIL                = 3
TABTYPE_FMT                = 9999 # TODO






# --------------------------------------------------------------------------------}
# --- OUT FILE 
# --------------------------------------------------------------------------------{
class FastOutASCIIFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.out']

    @staticmethod
    def formatName():
        return 'FAST ASCII output file (.out)'

    def _read(self):
        # Read with panda
        self.data=pd.read_csv(self.filename, sep='\t', skiprows=[0,1,2,3,4,5,7])
        self.data.rename(columns=lambda x: x.strip(),inplace=True)

    #def _write(self): # TODO
    #    pass

    def _toDataFrame(self):
        return self.data




# --------------------------------------------------------------------------------}
# --- INPUT FILE 
# --------------------------------------------------------------------------------{
class FastFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.dat','.fst']

    @staticmethod
    def formatName():
        return 'FAST input file (.dat;.fst)'

    def getID(self,label):
        # brute force search
        for i in range(len(self.data)):
            d = self.data[i]
            if d['label']==label:
                return i
        raise KeyError('Variable '+ label+' not found')

    # Making it behave like a dictionary
    def __setitem__(self,key,item):
        i = self.getID(key)
        self.data[i]['value'] = item

    def __getitem__(self,key):
        i = self.getID(key)
        return self.data[i]['value']


    def _read(self):
        try: 
            with open(self.filename) as f:
                lines = f.read().splitlines()
            # Parsing line by line, storing each line into a disctionary
            self.data =[]
            i=0    
            while i<len(lines):
                d = parseFASTInputLine(lines[i],i)
                # HANDLING OF ALL SPECIAL CASES oOF TABLES...
                if isStr(d['value']) and d['value'].lower() in NUMTAB_FROM_VAL_DETECT_L:
                    ii             = NUMTAB_FROM_VAL_DETECT_L.index(d['value'].lower())
                    d['label']     = NUMTAB_FROM_VAL_VARNAME[ii]
                    d['tabDimVar'] = NUMTAB_FROM_VAL_DIM_VAR[ii]
                    d['tabType']   = TABTYPE_NUM_WITH_HEADER
                    nTabLines=0
                    #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                    nTabLines = self[d['tabDimVar']]
                    d['value'], d['tabColumnNames'], d['tabUnits'] = parseFASTNumTable(lines[i:i+nTabLines+2],nTabLines,i)
                    i += nTabLines+1
                elif isStr(d['label']) and d['label'].lower() in NUMTAB_FROM_LAB_DETECT_L:
                    ii      = NUMTAB_FROM_LAB_DETECT_L.index(d['label'].lower())
                    # Special case for airfoil data, the table follows NumAlf, so we add d first
                    if d['label'].lower()=='numalf':
                        d['tabType']=TABTYPE_NOT_A_TAB
                        self.data.append(d)
                        # Creating a new dictionary for the table
                        d = {'value':None, 'label':'NumAlf', 'isComment':False, 'descr':'', 'tabType':None}
                        i += 1
                    d['label']     = NUMTAB_FROM_LAB_VARNAME[ii]
                    d['tabDimVar'] = NUMTAB_FROM_LAB_DIM_VAR[ii]
                    if d['label'].lower()=='afcoeff' :
                        d['tabType']        = TABTYPE_NUM_WITH_HEADERCOM
                    else:
                        d['tabType']   = TABTYPE_NUM_WITH_HEADER
                    nTabLines = self[d['tabDimVar']]
                    #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                    d['value'], d['tabColumnNames'], d['tabUnits'] = parseFASTNumTable(lines[i:i+nTabLines+2],nTabLines,i)
                    i += nTabLines+1
                elif isStr(d['label']) and d['label'].lower() in FILTAB_FROM_LAB_DETECT_L:
                    ii             = FILTAB_FROM_LAB_DETECT_L.index(d['label'].lower())
                    d['label']     = FILTAB_FROM_LAB_VARNAME[ii]
                    d['tabDimVar'] = FILTAB_FROM_LAB_DIM_VAR[ii]
                    d['tabType']   = TABTYPE_FIL
                    nTabLines = self[d['tabDimVar']]
                    #print('Reading table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                    d['value'] = parseFASTFilTable(lines[i:i+nTabLines],nTabLines,i)
                    i += nTabLines-1
                elif isStr(d['value']) and d['value'].lower() in FMTTAB_FROM_VAL_DETECT_L:
                    raise NotImplementedError('Parsing for this table not implemented yet')
                    #ii             = FMTTAB_FROM_LAB_DETECT_L.index(d['value'].lower())
                    #d['label']     = FMTTAB_FROM_VAL_VARNAME[ii]
                    #d['tabDimVar'] = FMTTAB_FROM_VAL_DIM_VAR[ii]
                    #d['tabType']   = TABTYPE_NUM_WITH_HEADER
                    #nTabLines = self[d['tabDimVar']]
                    #d['value'], d['tabColumnNames'], d['tabUnits'] = parseFASTNumTable(lines[i:i+nTabLines+2],nTabLines,i)
                    #print('Detected table {} Dimension {} (based on {})'.format(d['label'],nTabLines,d['tabDimVar']));
                    #i += nTabLines+1
                else:
                    d['tabType'] = TABTYPE_NOT_A_TAB

                self.data.append(d)
                i += 1
        except Exception as e:    
            raise Exception('Airfoil File {}: '.format(self.filename)+e.args[0])
            

    def _write(self):
        with open(self.filename,'w') as f:
            for i in range(len(self.data)):
                d=self.data[i]
                if d['isComment']:
                    f.write('{}'.format(d['value']))
                elif d['tabType']==TABTYPE_NOT_A_TAB:
                    if isinstance(d['value'], list):
                        sList=', '.join([str(x) for x in d['value']])
                        f.write('{} {} {}'.format(sList,d['label'],d['descr']))
                    else:
                        f.write('{} {} {}'.format(d['value'],d['label'],d['descr']))
                elif d['tabType']==TABTYPE_NUM_WITH_HEADER:
                    f.write('{}\n'.format(' '.join(d['tabColumnNames'])))
                    f.write('{}'.format(' '.join(d['tabUnits'])))
                    if np.size(d['value'],0) > 0 :
                        f.write('\n')
                        f.write('\n'.join('\t'.join('%15.8e' %x for x in y) for y in d['value']))
                elif d['tabType']==TABTYPE_NUM_WITH_HEADERCOM:
                    f.write('! {}\n'.format(' '.join(d['tabColumnNames'])))
                    f.write('! {}\n'.format(' '.join(d['tabUnits'])))
                    f.write('\n'.join('\t'.join('%15.8e' %x for x in y) for y in d['value']))
                elif d['tabType']==TABTYPE_FIL:
                    f.write('{} {} {}\n'.format(d['value'][0],d['tabDetect'],d['descr']))
                    f.write('\n'.join(fil for fil in d['value'][1:]))
                else:
                    raise Exception('Unknown table type for variable {}',d)
                if i<len(self.data)-1:
                    f.write('\n')

    def _toDataFrame(self):
        isATab=False
        i=0
        while not isATab and i<len(self.data):
            d=self.data[i]
            isATab = d['tabType']==TABTYPE_NUM_WITH_HEADER or d['tabType']==TABTYPE_NUM_WITH_HEADERCOM
            i += 1

        if isATab:
            Val= d['value']
            Cols=d['tabColumnNames']
            return pd.DataFrame(data=Val,columns=Cols)
                    #  index=data[1:,0],    # 1st column as index
        else:
            return []


# --------------------------------------------------------------------------------}
# --- Helper functions 
# --------------------------------------------------------------------------------{
def isStr(s):
    # Python 2 and 3 compatible
    try: 
       basestring # python 2
    except NameError:
       basestring=str #python 3
    return isinstance(s, basestring)

def strIsFloat(s):
    #return s.replace('.',',1').isdigit()
    try:
        float(s)
        return True
    except:
        return False

def strIsBool(s):
    return (s.lower() is 'true') or (s.lower() is 'false')

def strIsInt(s):
    s = str(s)
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()    

def cleanLine(l):
    # makes a string single space separated
    l = l.replace('\t',' ')
    l = ' '.join(l.split())
    l = l.strip()
    return l

def parseFASTInputLine(line_raw,i):
    try:
        d = {'value':None, 'label':'', 'isComment':False, 'descr':''}
        # preliminary cleaning (Note: loss of formatting)
        line = cleanLine(line_raw)
        # Comment
        if any(line.startswith(c) for c in ['#','!','--','==']) or len(line)==0:
            d['isComment']=True
            d['value']=line_raw
            return d

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
            while strIsFloat(s) or strIsBool(s) and ii<len(csplits):
                if strIsInt(s):
                    List.append(int(s))
                elif strIsFloat(s):
                    List.append(float(s))
                elif strIsBool(s):
                    List.append(bool(s))
                ii +=+1
                s = csplits[ii]
            #print('[INFO] Line {}: Found list: '.format(i),List)
        # Defining value and remaining splits
        if len(List)>=2:
            d['value']=List
            sLast=csplits[ii-1]
            ipos=line.find(sLast)
            line_remaining = line[ipos+len(sLast):]
            splits=line_remaining.split()
            iNext=0
        else:
            # It's not a list, we just use space as separators
            splits=line.split(' ')
            s=splits[0]

            if strIsInt(s):
                d['value']=int(s)
            elif strIsFloat(s):
                d['value']=float(s)
            elif strIsBool(s):
                d['value']=bool(s)
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
            d['label']=splits[iNext]
            iNext = iNext+1
        else:
            print('[WARN] Line {}: No label found -> comment assumed'.format(i+1))
            d['isComment']=True
            d['value']=line_raw
            iNext = len(splits)+1
        
        # Recombining description
        if len(splits)>=iNext+1:
            d['descr']=' '.join(splits[iNext:])
    except Exception as e:
        raise Exception('Line {}: '.format(i+1)+e.args[0])

    return d

def parseFASTNumTable(lines,n,iStart):
    Tab = None
    ColNames = None
    Units = None
    nHeaders = 2
    if len(lines)!=n+nHeaders:
        raise Exception('Not enough lines in table: {} lines instead of {}'.format(len(lines)-nHeaders,n))

    try:
        # Extract column names
        i = 0
        sTmp = cleanLine(lines[i])
        if sTmp.startswith('!'):
            sTmp=sTmp[1:].strip()
        ColNames=sTmp.split()
        # Extract units
        i = 1
        sTmp = cleanLine(lines[i])
        if sTmp.startswith('!'):
            sTmp=sTmp[1:].strip()
        Units=sTmp.split()

        # Forcing user to match number of units and column names
        nCols=len(ColNames)
        if nCols != len(Units):
            raise Exception('Number of column names different from number of units in table')

        Tab = np.zeros((n, len(ColNames))) 
        for i in range(nHeaders,n+nHeaders):
            l = lines[i]
            v = l.split()
            if len(v) > nCols:
                print('[WARN] Line {}: number of data different from number of column names'.format(iStart+i+1))
            if len(v) < nCols:
                raise Exception('Number of data is lower than number of column names')
            v = [float(s) for s in v[0:nCols]]
            if len(v) < nCols:
                raise Exception('Number of data is lower than number of column names')
            Tab[i-nHeaders,:] = v
            
    except Exception as e:    
        raise Exception('Line {}: '.format(iStart+i+1)+e.args[0])
    return Tab, ColNames, Units


def parseFASTFilTable(lines,n,iStart):
    Tab = []
    try:
        i=0
        if len(lines)!=n:
            raise Exception('Not enough lines in table: {} lines instead of {}'.format(len(lines),n))
        for i in range(n):
            l = lines[i].split()
            #print(l[0].strip())
            Tab.append(l[0].strip())
            
    except Exception as e:    
        raise Exception('Line {}: '.format(iStart+i+1)+e.args[0])
    return Tab


