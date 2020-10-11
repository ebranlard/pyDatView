import numpy as np
from .common import no_unit, unit, inverse_unit, has_chinese_char
from .common import isString, isDate
from .common import unique
from .common import yMin, yMax, yStd, yMean # TODO put these directly into this class maybe




class PlotData():
    """ 
    Class for plot data

    For now, relies on some "indices" related to Tables/Columns/ and maybe Selection panel
    Not really elegant. These dependencies should be removed in the future
    """
    def __init__(PD, x=None, y=None, sx='', sy=''):
        """ Dummy init for now """
        PD.id=-1
        PD.it=-1 # tablx index
        PD.ix=-1 # column index
        PD.iy=-1 # column index
        PD.sx='' # x label
        PD.sy='' # y label
        PD.st='' # table label
        PD.syl='' # y label for legend
        PD.filename = ''
        PD.tabname = ''
        PD.x        =[]     # x data
        PD.y        =[]     # y data
        PD.xIsString=False  # true if strings
        PD.xIsDate  =False  # true if dates
        PD.yIsString=False  # true if strings
        PD.yIsDate  =False  # true if dates

        if x is not None and y is not None:
            PD.fromXY(x,y,sx,sy)

    def fromIDs(PD, tabs, i, idx, SameCol):
        """ Nasty initialization of plot data from "IDs" """
        PD.id = i
        PD.it = idx[0] # table index
        PD.ix = idx[1] # x index
        PD.iy = idx[2] # y index
        PD.sx = idx[3] # x label
        PD.sy = idx[4] # y label
        PD.syl = ''    # y label for legend
        PD.st = idx[5] # table label
        PD.filename = tabs[PD.it].filename
        PD.tabname  = tabs[PD.it].active_name
        PD.SameCol  = SameCol
        PD.x, PD.xIsString, PD.xIsDate,_ = tabs[PD.it].getColumn(PD.ix)  # actual x data, with info
        PD.y, PD.yIsString, PD.yIsDate,c = tabs[PD.it].getColumn(PD.iy)  # actual y data, with info
        PD.c =c  # raw values, used by PDF

        PD._post_init()


    def fromXY(PD, x, y, sx='', sy=''):
        PD.x  = x
        PD.y  = y
        PD.sx = sx
        PD.sy = sy
        PD.xIsString = isString(x)
        PD.yIsString = isString(y)
        PD.xIsDate   = isDate  (x)
        PD.yIsDate   = isDate  (y)

        PD._post_init()


    def _post_init(PD):
        n=len(PD.y)
        if n>1000:
            if (PD.xIsString):
                raise Exception('Error: x values contain more than 1000 string. This is not suitable for plotting.\n\nPlease select another column for table: {}\nProblematic column: {}\n'.format(PD.st,PD.sx))
            if (PD.yIsString):
                raise Exception('Error: y values contain more than 1000 string. This is not suitable for plotting.\n\nPlease select another column for table: {}\nProblematic column: {}\n'.format(PD.st,PD.sy))
        PD.needChineseFont = has_chinese_char(PD.sy) or has_chinese_char(PD.sx)
        # Stats of the raw data (computed once and for all, since it can be expensive for large dataset
        #PD.x0Min  = xMin(d)
        #PD.x0Max  = xMax(d)
        PD.y0Min  = yMin(PD)  # Min from original data (might be modified by FFT/PDF/MinMax
        PD.y0Max  = yMax(PD)  # Max from orignial data
        PD.y0Std  = yStd(PD)
        PD.y0Mean = yMean(PD)
        PD.n0     = (n,'{:d}'.format(n))



    def __repr__(s):
        s1='id:{}, it:{}, ix:{}, iy:{}, sx:"{}", sy:"{}", st:{}, syl:{}'.format(s.id,s.it,s.ix,s.iy,s.sx,s.sy,s.st,s.syl)
        return s1


    def toPDF(PD, nBins=30, smooth=False):
        """ Convert y-data to Probability density function (PDF) as function of x 
        Uses "stats" library  (from welib/pybra)
        NOTE: inPlace
        """
        from .utils.stats import pdf_gaussian_kde, pdf_histogram

        n=len(PD.y)
        if PD.yIsString:
            if n>100:
                raise Exception('Warn: Dataset has string format and is too large to display')
            vc = c.value_counts().sort_index()
            PD.x = vc.keys().tolist()
            PD.y = vc/n # TODO counts/PDF option
            PD.yIsString=False
            PD.xIsString=True
        elif PD.yIsDate:
            raise Exception('Warn: Cannot plot PDF of dates')
        else:
            if nBins>=n:
                nBins=n
            if smooth:
                PD.x, PD.y = pdf_gaussian_kde(PD.y, nOut=nBins)
            else:
                PD.x, PD.y = pdf_histogram(PD.y, nBins=nBins, norm=True, count=False)

        PD.sx = PD.sy;
        PD.sy = 'PDF('+no_unit(PD.sy)+')'
        iu = inverse_unit(PD.sy)
        if len(iu)>0:
            PD.sy += ' ['+ iu +']'

        return nBins


    def toMinMax(PD, xScale=False, yScale=True):
        """ Convert plot data to MinMax data based on GUI options
        NOTE: inPlace
        """
        if yScale:
            if PD.yIsString:
                raise Exception('Warn: Cannot compute min-max for strings')
            mi = PD.y0Min[0] #mi= np.nanmin(PD.y)
            mx = PD.y0Max[0] #mx= np.nanmax(PD.y)
            if mi == mx:
                PD.y=PD.y*0
            else:
                PD.y = (PD.y-mi)/(mx-mi)
        if xScale:
            if PD.xIsString:
                raise Exception('Warn: Cannot compute min-max for strings')
            mi= np.nanmin(PD.x) # NOTE: currently not precomputed for performance.. but might as well..
            mx= np.nanmax(PD.x)
            if mi == mx:
                PD.x=PD.x*0
            else:
                PD.x = (PD.x-mi)/(mx-mi)



    def toFFT(PD, yType='Amplitude', xType='1/x', avgMethod='Welch', avgWindow='Hamming', bDetrend=True, nExp=8):
        """ 
        Uses spectral.fft_wrap to generate a "FFT" plot data, with various options:
           yType      : amplitude, PSD, f x PSD
           xType      : 1/x, x, 2pi/x
           avgMethod : None, Welch
           avgWindow : Hamming, Hann, Rectangular
        see module spectral for more

        NOTE: inplace (modifies itself), does not return a new instance
        """
        from .spectral import fft_wrap

        # --- TODO, make this independent of GUI
        if PD.yIsString or PD.yIsDate:
            raise Exception('Warn: Cannot plot FFT of dates or strings')
        elif PD.xIsString:
            raise Exception('Warn: Cannot plot FFT if x axis is string')
        else:
            dt=None
            if PD.xIsDate:
                dt = getDt(PD.x)
            # --- Computing fft - x is freq, y is Amplitude
            PD.x, PD.y, Info = fft_wrap(PD.x, PD.y, dt=dt, output_type=yType,averaging=avgMethod, averaging_window=avgWindow,detrend=bDetrend,nExp=nExp)
            # --- Setting plot options
            PD.Info=Info
            PD.xIsDate=False
            # y label
            if yType=='PSD':
                PD.sy= 'PSD({}) [({})^2/{}]'.format(no_unit(PD.sy), unit(PD.sy), unit(PD.sx))
            elif yType=='f x PSD':
                PD.sy= 'f-weighted PSD({}) [({})^2]'.format(no_unit(PD.sy), unit(PD.sy))
            elif yType=='Amplitude':
                PD.sy= 'FFT({}) [{}]'.format(no_unit(PD.sy), unit(PD.sy))
            else:
                raise Exception('Unsupported FFT type {} '.format(yType))
            # x label
            if xType=='1/x':
                if unit(PD.sx)=='s':
                    PD.sx= 'Frequency [Hz]'
                else:
                    PD.sx= ''
            elif xType=='x':
                PD.x=1/PD.x
                if unit(PD.sx)=='s':
                    PD.sx= 'Period [s]'
                else:
                    PD.sx= ''
            elif xType=='2pi/x':
                PD.x=2*np.pi*PD.x
                if unit(PD.sx)=='s':
                    PD.sx= 'Cyclic frequency [rad/s]'
                else:
                    PD.sx= ''
            else:
                raise Exception('Unsupported x-type {} '.format(xType))

            return Info



# --------------------------------------------------------------------------------}
# ---  
# --------------------------------------------------------------------------------{
def compareMultiplePD(PD, mode, sComp):
    """ 
    PD: list of PlotData
    sComp: string in ['Relative', '|Relative|', 'Ratio', 'Absolute' 
    mode: plot mode, nTabs_1Col, nTabs_SameCols, nTabs_SimCols

    return:
      PD_comp : new PlotData list that compares the input list PD
    
    """
    # --- Helper function
    def getError(y,yref,method):
        if len(y)!=len(yref):
            raise NotImplementedError('Cannot compare signals of different lengths')
        if sComp=='Relative':
            if np.mean(np.abs(yref))<1e-7:
                Error=(y-yRef)/(yRef+1)*100
            else:
                Error=(y-yRef)/yRef*100
        elif sComp=='|Relative|':
            if np.mean(np.abs(yref))<1e-7:
                Error=abs((y-yRef)/(yRef+1))*100
            else:
                Error=abs((y-yRef)/yRef)*100
        elif sComp=='Ratio':
            if np.mean(np.abs(yref))<1e-7:
                Error=(y+1)/(yRef+1)
            else:
                Error=y/yRef
        elif sComp=='Absolute':
            Error=y-yRef
        else:
            raise Exception('Something wrong '+sComp)
        return Error

    def getErrorLabel(ylab=''):
        if len(ylab)>0:
            ylab=no_unit(ylab)
            ylab='in '+ylab+' '
        if sComp=='Relative':
            return 'Relative error '+ylab+'[%]';
        elif sComp=='|Relative|':
            return 'Abs. relative error '+ylab+'[%]';
        if sComp=='Ratio':
            return 'Ratio '+ylab.replace('in','of')+'[-]';
        elif sComp=='Absolute':
            usy   = unique([pd.sy for pd in PD])
            yunits= unique([unit(sy) for sy in usy])
            if len(yunits)==1 and len(yunits[0])>0:
                return 'Absolute error '+ylab+'['+yunits[0]+']'
            else:
                return 'Absolute error '+ylab;
        elif sComp=='Y-Y':
            return PD[0].sy

    xlabelAll=PD[0].sx

    
    if any([pd.yIsString for pd in PD]):
        raise Exception('Warn: Cannot compare strings')
    if any([pd.yIsDate for pd in PD]):
        raise Exception('Warn: Cannot compare dates with other values')

    if mode=='nTabs_1Col':
        ylabelAll=getErrorLabel(PD[1].sy)
        usy   = unique([pd.sy for pd in PD])
        #print('Compare - different tabs - 1 col')
        st  = [pd.st for pd in PD]
        if len(usy)==1:
           SS=usy[0] + ', '+ ' wrt. '.join(st[::-1])
           if sComp=='Y-Y':
               xlabelAll=PD[0].st+', '+PD[0].sy
               ylabelAll=PD[1].st+', '+PD[1].sy
        else:
            SS=' wrt. '.join(usy[::-1])
            if sComp=='Y-Y':
                xlabelAll=PD[0].sy
                ylabelAll=PD[1].sy

        xRef = PD[0].x
        yRef = PD[0].y
        PD[1].syl=SS
        y=np.interp(xRef,PD[1].x,PD[1].y)
        if sComp=='Y-Y':
            PD[1].x=yRef
            PD[1].y=y
        else:
            Error = getError(y,yRef,sComp)
            PD[1].x=xRef
            PD[1].y=Error
        PD[1].sx=xlabelAll
        PD[1].sy=ylabelAll
        PD_comp=[PD[1]] # return

    elif mode=='1Tab_nCols':
        # --- Compare one table - different columns
        #print('One Tab, different columns')
        ylabelAll=getErrorLabel()
        xRef = PD[0].x
        yRef = PD[0].y
        pdRef=PD[0]
        for pd in PD[1:]:
            if sComp=='Y-Y':
                pd.syl = no_unit(pd.sy)+' wrt. '+no_unit(pdRef.sy)
                pd.x   = yRef
                pd.sx  = PD[0].sy
            else:
                pd.syl = no_unit(pd.sy)+' wrt. '+no_unit(pdRef.sy)
                pd.sx  = xlabelAll
                pd.sy  = ylabelAll
                Error  = getError(pd.y,yRef,sComp)
                pd.x=xRef
                pd.y=Error
        PD_comp=PD[1:]
    elif mode =='nTabs_SameCols':
        # --- Compare different tables, same column
        #print('Several Tabs, same columns')
        uiy=unique([pd.iy for pd in PD])
        uit=unique([pd.it for pd in PD])
        PD_comp=[]
        for iy in uiy:
            PD_SameCol=[pd for pd in PD if pd.iy==iy]
            xRef = PD_SameCol[0].x
            yRef = PD_SameCol[0].y
            ylabelAll=getErrorLabel(PD_SameCol[0].sy)
            for pd in PD_SameCol[1:]:
                if pd.xIsString:
                    if len(xRef)==len(pd.x):
                        pass # fine able to interpolate
                    else:
                        raise Exception('X values have different length and are strings, cannot interpolate string. Use `Index` for x instead.')
                else:
                    pd.y=np.interp(xRef,pd.x,pd.y)
                if sComp=='Y-Y':
                    pd.x=yRef
                    pd.sx=PD_SameCol[0].st+', '+PD_SameCol[0].sy
                    if len(PD_SameCol)==1:
                        pd.sy =pd.st+', '+pd.sy
                    else:
                        pd.syl= pd.st
                else:
                    if len(uit)<=2:
                        pd.syl = pd.st+' wrt. '+PD_SameCol[0].st+', '+pd.sy
                    else:
                        pd.syl = pd.st+'|'+pd.sy
                    pd.sx  = xlabelAll
                    pd.sy  = ylabelAll
                    Error = getError(pd.y,yRef,sComp)
                    pd.x=xRef
                    pd.y=Error
                PD_comp.append(pd)
    elif mode =='nTabs_SimCols':
        # --- Compare different tables, similar columns
        print('Several Tabs, similar columns, TODO')
        PD_comp=[]

    return PD_comp

