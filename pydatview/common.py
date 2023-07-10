import numpy as np
import pandas as pd
import os
import platform
import datetime
import re
import inspect

CHAR={
'menu'     : u'\u2630',
'tridot'   : u'\u26EC',
'apply'    : u'\u1809',
'compute'  : u'\u2699', # gear
'close'    : u'\u274C',
'add'      : u'\u2795',
'add_small': u'\ufe62',
'clear'    : u'-',
'sun'      : u'\u2600',
'suncloud' : u'\u26C5',
'cloud'    : u'\u2601',
'check'    : u'\u2714',
'help'     : u'\u2753',
'pencil'   : u'\u270f', # draw
'pick'     : u'\u26cf',
'hammer'   : u'\U0001f528',
'wrench'   : u'\U0001f527',
'ruler'    : u'\U0001F4CF', # measure
'control_knobs'    : u'\U0001F39b', 
'python'   : u'\U0001F40D',
'chart'    : u'\U0001F4c8',
'chart_small': u'\U0001F5e0',
}
# --------------------------------------------------------------------------------}
# --- ellude
# --------------------------------------------------------------------------------{
def common_start(*strings):
    """ Returns the longest common substring
        from the beginning of the `strings`
    """
    if len(strings)==1:
        strings=tuple(strings[0])
    def _iter():
        for z in zip(*strings):
            if z.count(z[0]) == len(z):  # check all elements in `z` are the same
                yield z[0]
            else:
                return
    return ''.join(_iter())

def common_end(*strings):
    if len(strings)==1:
        strings=strings[0]
    else:
        strings=list(strings)
    strings = [s[-1::-1] for s in strings]
    return common_start(strings)[-1::-1]

def find_leftstop(s):
    for i,c in enumerate(reversed(s)):
        if c in ['.','_','|']:
            i=i+1
            return s[:len(s)-i]
    return s

def ellude_common(strings,minLength=2):
    """
    ellude the common parts of two strings

    minLength:
       if -1, string might be elluded up until there are of 0 length
       if 0 , if a string of zero length is obtained, it will be tried to be extended until a stop character is found

    """
    # Selecting only the strings that do not start with the safe '>' char
    S = [s for i,s in enumerate(strings) if ((len(s)>0) and (s[0]!= '>'))]
    if len(S)==0:
        pass
    elif len(S)==1:
        ns=S[0].rfind('|')+1
        ne=0;
    else:
        ss = common_start(S)
        se = common_end(S)
        iu = ss[:-1].rfind('_')
        ip = ss[:-1].rfind('_')
        if iu > 0:
            if ip>0:
                if iu>ip:
                    ss=ss[:iu+1]
            else:
                ss=ss[:iu+1]

        iu = se[:-1].find('_')
        if iu > 0:
            se=se[iu:]
        iu = se[:-1].find('.')
        if iu > 0:
            se=se[iu:]
        ns=len(ss)     
        ne=len(se)     

    # Reduce start length if some strings end up empty
    # Look if any of the strings will end up empty
        SSS=[len(s[ns:-ne].lstrip('_') if ne>0 else s[ns:].lstrip('_')) for s in S]
        currentMinLength=np.min(SSS)
        if currentMinLength<minLength:
            delta=minLength-currentMinLength
            #print('ss',ss,'ns',ns)
            if delta>0:
                ss=ss[:-delta]
                ns=len(ss)
            #print('ss',ss)
            ss=find_leftstop(ss)
            #print('ss',ss)
            if len(ss)==ns:
                ns=0
            else:
                ns=len(ss)+1

    for i,s in enumerate(strings):
        if len(s)>0 and s[0]=='>':
            strings[i]=s[1:]
        else:
            s=s[ns:-ne] if ne>0 else s[ns:]
            strings[i]=s.lstrip('_')
            if len(strings[i])==0:
                strings[i]='tab{}'.format(i)
    return strings


# --------------------------------------------------------------------------------}
# --- Key value 
# --------------------------------------------------------------------------------{
def extract_key_tuples(text):
    """
    all=(0.1,-2),b=(inf,0), c=(-inf,0.3e+10)
    """
    regex = re.compile(r'(?P<key>[\w\-]+)=\((?P<value1>[0-9+epinf.-]*?),(?P<value2>[0-9+epinf.-]*?)\)($|,)')
    return  {match.group("key"): (np.float(match.group("value1")),np.float(match.group("value2"))) for match in regex.finditer(text.replace(' ',''))}


def extract_key_num(text):
    """
    all=0.1, b=inf, c=-0.3e+10
    """
    regex = re.compile(r'(?P<key>[\w\-]+)=(?P<value>[0-9+epinf.-]*?)($|,)')
    return {match.group("key"): np.float(match.group("value")) for match in regex.finditer(text.replace(' ',''))}

def getDt(x):
    """ returns dt in s """
    def myisnat(dt):
        if isinstance(dt,pd._libs.tslibs.timedeltas.Timedelta):
            try:
                dt=pd.to_timedelta(dt) # pandas 1.0
            except:
                dt=pd.to_timedelta(dt,box=False) # backward compatibility
                
        elif isinstance(dt,datetime.timedelta):
            dt=np.array([dt],dtype='timedelta64')[0]
        return pd.isna(dt)
#         try:
#             print('>>>', dt,type(dt))
#             isnat=np.isnat(dt)
#         except:
#             print(type(dt),type(dx))
#             isnat=False
#             raise
#         return isnat



    if len(x)<=1:
        return np.NaN
    if isinstance(x[0],float):
        return x[1]-x[0]
    if isinstance(x[0],int) or isinstance(x[0],np.int32) or isinstance(x[0],np.int64):
        return x[1]-x[0]
    # first try with seconds
    #print('')
    #print('getDT: dx:',x[1]-x[0])
    dx = x[1]-x[0]
    #print(type(dx))
    if myisnat(dx):
        # we try the last values (or while loop, but may take a while)
        dx = x[-1]-x[-2]
        if myisnat(dx):
            return np.nan
    dt=np.timedelta64(dx,'s').item().total_seconds()
    if dt<1:
        # try higher resolution
        dt=np.timedelta64(dx,'ns').item()/10.**9
    # TODO if dt> int res... do something
    return dt

def getTabCommonColIndices(tabs):
    cleanedColLists = [ [cleanCol(s) for s in t.columns] for t in tabs]
    nCols = np.array([len(cols) for cols in cleanedColLists])
    # Common columns between all column lists
    commonCols = cleanedColLists[0]
    for i in np.arange(1,len(cleanedColLists)):
        commonCols = list( set(commonCols) & set( cleanedColLists[i]))
    # Keep original order
    commonCols =[c for c in cleanedColLists[0] if c in commonCols] # Might have duplicates..
    IMissPerTab=[]
    IKeepPerTab=[]
    IDuplPerTab=[] # Duplicates amongst the "common"
    for cleanedCols in cleanedColLists:
        IKeep=[]
        IMiss=[]
        IDupl=[]
        # Ugly for loop here since we have to account for dupplicates
        for comcol in commonCols:
            I = [i for i, c in enumerate(cleanedCols) if c == comcol]
            if len(I)==0:
                pass
            else:
                if I[0] not in IKeep:
                    IKeep.append(I[0])
                    if len(I)>1:
                        IDupl=IDupl+I[1:]
        IMiss=[i for i,_  in enumerate(cleanedCols) if (i not in IKeep) and (i not in IDupl)]
        IMissPerTab.append(IMiss)
        IKeepPerTab.append(IKeep)
        IDuplPerTab.append(IDupl)
    return IKeepPerTab, IMissPerTab, IDuplPerTab, nCols


# --------------------------------------------------------------------------------}
# --- Units 
# --------------------------------------------------------------------------------{
def cleanCol(s):
    s=no_unit(s).strip()
    s=no_unit(s.replace('(',' [').replace(')',']'))
    s=s.lower().strip().replace('_','').replace(' ','').replace('-','')
    return s

def no_unit(s):
    s=s.replace('_[',' [')
    iu=s.rfind(' [')
    if iu>0:
        return s[:iu]
    else:
        return s

def unit(s):
    iu=s.rfind('[')
    if iu>0:
        return s[iu+1:].replace(']','')
    else:
        return ''

def splitunit(s):
    iu=s.rfind('[')
    if iu>0:
        return s[:iu], s[iu+1:].replace(']','')
    else:
        return s, ''

def inverse_unit(s):
    u=unit(s).strip()
    if u=='':
        return ''
    elif u=='-':
        return '-'
    elif len(u)==1:
        return '1/'+u;
    elif u=='m/s':
        return 's/m';
    elif u=='deg':
        return '1/deg';
    else:
        return '1/('+u+')'



def filter_list(L, string):
    """ simple (not regex or fuzzy) filtering of a list of strings
    Returns matched indices and strings
    """
    ignore_case = string==string.lower()
    if ignore_case:
        I=[i for i,s in enumerate(L) if string in s.lower()]
    else:
        I=[i for i,s in enumerate(L) if string in s]
    L_found =np.array(L)[I]
    return L_found, I

def unique(l):
    """ Return unique values of a list"""
    used=set()
    return [x for x in l if x not in used and (used.add(x) or True)]

# --------------------------------------------------------------------------------}
# --- geometry 
# --------------------------------------------------------------------------------{
def rectangleOverlap(BLx1, BLy1, TRx1, TRy1, BLx2, BLy2, TRx2, TRy2):
    """ returns true if two rectangles overlap 
    BL: Bottom left
    TR: top right
    "1" rectangle 1
    "2" rectangle 2
    """
    return not (TRx1 < BLx2 or BLx1 > TRx2 or TRy1 < BLy2 or BLy1> TRy2)
# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
def pretty_time(t):
    # fPrettyTime: returns a 6-characters string corresponding to the input time in seconds.
    #   fPrettyTime(612)=='10m12s'
    # AUTHOR: E. Branlard
    if np.isnan(t):
        return 'NaT';
    if(t<0):
        return '------';
    elif (t<1) :
        c=np.floor(t*100);
        s='{:2d}.{:02d}s'.format(0,int(c))
    elif(t<60) :
        s=np.floor(t);
        c=np.floor((t-s)*100);
        s='{:2d}.{:02d}s'.format(int(s),int(c))
    elif(t<3600) :
        m=np.floor(t/60);
        s=np.mod( np.floor(t), 60);
        s='{:2d}m{:02d}s'.format(int(m),int(s))
    elif(t<86400) :
        h=np.floor(t/3600);
        m=np.floor(( np.mod( np.floor(t) , 3600))/60);
        s='{:2d}h{:02d}m'.format(int(h),int(m))
    elif(t<8553600) : #below 3month
        d=np.floor(t/86400);
        h=np.floor( np.mod(np.floor(t), 86400)/3600);
        s='{:2d}d{:02d}h'.format(int(d),int(h))
    elif(t<31536000):
        m=t/(3600*24*30.5);
        s='{:4.1f}mo'.format(m)
        #s='+3mon.';
    else:
        y=t/(3600*24*365.25);
        s='{:.1f}y'.format(y)
    return s

def pretty_num(x):
    if np.isnan(x):
        return 'NA'
    if abs(x)<1000 and abs(x)>1e-4:
        return "{:9.4f}".format(x)
    else:
        return '{:.3e}'.format(x)

def pretty_num_short(x,digits=3):
    if digits==4:
        if abs(x)<1000 and abs(x)>1e-1:
            return "{:.4f}".format(x)
        else:
           return "{:.4e}".format(x)
    elif digits==3:
        if abs(x)<1000 and abs(x)>1e-1:
            return "{:.3f}".format(x)
        else:
           return "{:.3e}".format(x)
    elif digits==2:
        if abs(x)<1000 and abs(x)>1e-1:
            return "{:.2f}".format(x)
        else:
           return "{:.2e}".format(x)

# --------------------------------------------------------------------------------}
# --- Chinese characters  
# --------------------------------------------------------------------------------{
cjk_ranges = [
        ( 0x4E00,  0x62FF),
        ( 0x6300,  0x77FF),
        ( 0x7800,  0x8CFF),
        ( 0x8D00,  0x9FCC),
        ( 0x3400,  0x4DB5),
        (0x20000, 0x215FF),
        (0x21600, 0x230FF),
        (0x23100, 0x245FF),
        (0x24600, 0x260FF),
        (0x26100, 0x275FF),
        (0x27600, 0x290FF),
        (0x29100, 0x2A6DF),
        (0x2A700, 0x2B734),
        (0x2B740, 0x2B81D),
        (0x2B820, 0x2CEAF),
        (0x2CEB0, 0x2EBEF),
        (0x2F800, 0x2FA1F)
    ]

def has_chinese_char(s):
    def is_cjk(char):
        char = ord(char)
        for bottom, top in cjk_ranges:
            if char >= bottom and char <= top:
                return True
        return False
    for c in s:
        char=ord(c)
        for bottom, top in cjk_ranges:
            if char >= bottom and char <= top:
                return True
    return False


# --------------------------------------------------------------------------------}
# --- Helper functions
# --------------------------------------------------------------------------------{
def YesNo(parent, question, caption = 'Yes or no?'):
    import wx
    dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal() == wx.ID_YES
    dlg.Destroy()
    return result
def Info(parent, message, caption = 'Info'):
    import wx
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()
def Warn(parent, message, caption = 'Warning!'):
    import wx
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_WARNING)
    dlg.ShowModal()
    dlg.Destroy()
def Error(parent, message, caption = 'Error!'):
    import wx
    dlg = wx.MessageDialog(parent, message, caption, wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()
    dlg.Destroy()



# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{

def isString(x):
    b = x.dtype == object and isinstance(x.values[0], str)
    return b 

def isDate(x):
    return np.issubdtype(x.dtype, np.datetime64)



# Create a Dummy Main Frame Class for testing purposes (e.g. of plugins)

class DummyMainFrame():
    def __init__(self, parent): self.parent=parent; 
    def addAction            (self, *args, **kwargs): Info(self.parent, 'This is dummy '+inspect.stack()[0][3])
    def removeAction         (self, *args, **kwargs): Info(self.parent, 'This is dummy '+inspect.stack()[0][3])
    def load_dfs             (self, *args, **kwargs): Info(self.parent, 'This is dummy '+inspect.stack()[0][3])
    def mainFrameUpdateLayout(self, *args, **kwargs): Info(self.parent, 'This is dummy '+inspect.stack()[0][3])
    def redraw               (self, *args, **kwargs): Info(self.parent, 'This is dummy '+inspect.stack()[0][3])
