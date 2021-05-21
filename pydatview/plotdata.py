from __future__ import absolute_import
import os
import numpy as np
from .common import no_unit, unit, inverse_unit, has_chinese_char
from .common import isString, isDate, getDt
from .common import unique, pretty_num, pretty_time
from .GUIMeasure import find_closest # Should not depend on wx 

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

    def fromIDs(PD, tabs, i, idx, SameCol, Options={}):
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

        PD._post_init(Options=Options)

    def fromXY(PD, x, y, sx='', sy=''):
        PD.x  = x
        PD.y  = y
        PD.c  = y
        PD.sx = sx
        PD.sy = sy
        PD.xIsString = isString(x)
        PD.yIsString = isString(y)
        PD.xIsDate   = isDate  (x)
        PD.yIsDate   = isDate  (y)

        PD._post_init()


    def _post_init(PD, Options={}):
        # --- Perform data manipulation on the fly
        #print(Options)
        keys=Options.keys()
        if 'RemoveOutliers' in keys:
            if Options['RemoveOutliers']:
                from pydatview.tools.signal import reject_outliers
                try:
                    PD.x, PD.y = reject_outliers(PD.y, PD.x, m=Options['OutliersMedianDeviation'])
                except:
                    raise Exception('Warn: Outlier removal failed. Desactivate it or use a different signal. ')
        if 'Filter' in keys:
            if Options['Filter']:
                from pydatview.tools.signal import applyFilter
                PD.y = applyFilter(PD.x, PD.y, Options['Filter'])

        if 'Sampler' in keys:
            if Options['Sampler']:
                from pydatview.tools.signal import applySampler
                PD.x, PD.y = applySampler(PD.x, PD.y, Options['Sampler'])

        # --- Store stats
        n=len(PD.y)
        if n>1000:
            if (PD.xIsString):
                raise Exception('Error: x values contain more than 1000 string. This is not suitable for plotting.\n\nPlease select another column for table: {}\nProblematic column: {}\n'.format(PD.st,PD.sx))
            if (PD.yIsString):
                raise Exception('Error: y values contain more than 1000 string. This is not suitable for plotting.\n\nPlease select another column for table: {}\nProblematic column: {}\n'.format(PD.st,PD.sy))

        PD.needChineseFont = has_chinese_char(PD.sy) or has_chinese_char(PD.sx)
        # Stats of the raw data (computed once and for all, since it can be expensive for large dataset
        PD.computeRange()
        # Store the values of the original data (labelled "0"), since the data might be modified later by PDF or MinMax etc.
        PD._y0Min = PD._yMin
        PD._y0Max = PD._yMax
        PD._x0Min = PD._xMin
        PD._x0Max = PD._xMax
        PD._y0Std  = PD.yStd()
        PD._y0Mean = PD.yMean()
        PD._n0     = (n,'{:d}'.format(n))
        PD.x0 =PD.x
        PD.y0 =PD.y

    def __repr__(s):
        s1='id:{}, it:{}, ix:{}, iy:{}, sx:"{}", sy:"{}", st:{}, syl:{}\n'.format(s.id,s.it,s.ix,s.iy,s.sx,s.sy,s.st,s.syl)
        return s1

    def toPDF(PD, nBins=30, smooth=False):
        """ Convert y-data to Probability density function (PDF) as function of x 
        Uses "stats" library  (from welib/pybra)
        NOTE: inPlace
        """
        from pydatview.tools.stats import pdf_gaussian_kde, pdf_histogram

        n=len(PD.y)
        if PD.yIsString:
            if n>100:
                raise Exception('Warn: Dataset has string format and is too large to display')
            vc = PD.c.value_counts().sort_index()
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
                try:
                    PD.x, PD.y = pdf_gaussian_kde(PD.y, nOut=nBins)
                except np.linalg.LinAlgError as e:
                    PD.x, PD.y = pdf_histogram(PD.y, nBins=nBins, norm=True, count=False)
            else:
                PD.x, PD.y = pdf_histogram(PD.y, nBins=nBins, norm=True, count=False)
            PD.xIsString=False
            PD.yIsString=False

        PD.sx = PD.sy;
        PD.sy = 'PDF('+no_unit(PD.sy)+')'
        iu = inverse_unit(PD.sy)
        if len(iu)>0:
            PD.sy += ' ['+ iu +']'

        # Compute min max once and for all
        PD.computeRange()

        return nBins


    def toMinMax(PD, xScale=False, yScale=True):
        """ Convert plot data to MinMax data based on GUI options
        NOTE: inPlace
        """
        if yScale:
            if PD.yIsString:
                raise Exception('Warn: Cannot compute min-max for strings')
            mi = PD._y0Min[0] #mi= np.nanmin(PD.y)
            mx = PD._y0Max[0] #mx= np.nanmax(PD.y)
            if mi == mx:
                PD.y=PD.y*0
            else:
                PD.y = (PD.y-mi)/(mx-mi)
            PD._yMin=0,'0'
            PD._yMax=1,'1'
        if xScale:
            if PD.xIsString:
                raise Exception('Warn: Cannot compute min-max for strings')
            mi= PD._x0Min[0]
            mx= PD._x0Max[0]
            if mi == mx:
                PD.x=PD.x*0
            else:
                PD.x = (PD.x-mi)/(mx-mi)
            PD._xMin=0,'0'
            PD._xMax=1,'1'

        # Compute min max once and for all
        #PD.computeRange()

        return None


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
        from pydatview.tools.spectral import fft_wrap

        # --- TODO, make this independent of GUI
        if PD.yIsString or PD.yIsDate:
            raise Exception('Warn: Cannot plot FFT of dates or strings')
        elif PD.xIsString:
            raise Exception('Warn: Cannot plot FFT if x axis is string')

        dt=None
        if PD.xIsDate:
            dt = getDt(PD.x)
        # --- Computing fft - x is freq, y is Amplitude
        PD.x, PD.y, Info = fft_wrap(PD.x, PD.y, dt=dt, output_type=yType,averaging=avgMethod, averaging_window=avgWindow,detrend=bDetrend,nExp=nExp)
        # --- Setting plot options
        PD._Info=Info
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

        PD.computeRange()
        return Info

    def computeRange(PD):
        """  Compute min max of data once and for all and store 
        From the performance tests, this ends up having a non negligible cost for large dataset,
        so we store it to reuse these as much as possible. 
        If possible, should be used for the plotting as well, so that matplotlib don't
        have to compute them again
        NOTE: each variable is a tuple (v,s), with a float and its string representation
        """
        PD._xMin  = PD._xMinCalc() 
        PD._xMax  = PD._xMaxCalc()
        PD._yMin  = PD._yMinCalc() 
        PD._yMax  = PD._yMaxCalc()


    # --------------------------------------------------------------------------------}
    # --- Stats functions that should only becalled once, could maybe use @attributes..
    # --------------------------------------------------------------------------------{
    def _yMinCalc(PD):
        if PD.yIsString:
            return PD.y[0],PD.y[0].strip()
        elif PD.yIsDate:
            return PD.y[0],'{}'.format(PD.y[0])
        else:
            v=np.nanmin(PD.y)
            s=pretty_num(v)
        return (v,s)

    def _yMaxCalc(PD):
        if PD.yIsString:
            return PD.y[-1],PD.y[-1].strip()
        elif PD.yIsDate:
            return PD.y[-1],'{}'.format(PD.y[-1])
        else:
            v=np.nanmax(PD.y)
            s=pretty_num(v)
        return (v,s)

    def _xMinCalc(PD):
        if PD.xIsString:
            return PD.x[0],PD.x[0].strip()
        elif PD.xIsDate:
            return PD.x[0],'{}'.format(PD.x[0])
        else:
            v=np.nanmin(PD.x)
            s=pretty_num(v)
        return (v,s)

    def _xMaxCalc(PD):
        if PD.xIsString:
            return PD.x[-1],PD.x[-1].strip()
        elif PD.xIsDate:
            return PD.x[-1],'{}'.format(PD.x[-1])
        else:
            v=np.nanmax(PD.x)
            s=pretty_num(v)
        return (v,s)

    def xMin(PD):
        return PD._xMin

    def xMax(PD):
        return PD._xMax

    def yMin(PD):
        return PD._yMin

    def yMax(PD):
        return PD._yMax

    def y0Min(PD):
        return PD._y0Min

    def y0Max(PD):
        return PD._y0Max

    def y0Mean(PD):
        return PD._y0Mean

    def y0Std(PD):
        return PD._y0Std

    def n0(PD):
        return PD._n0

    # --------------------------------------------------------------------------------}
    # --- Stats functions
    # --------------------------------------------------------------------------------{
    def yMean(PD):
        if PD.yIsString or  PD.yIsDate:
            return None,'NA'
        else:
            v=np.nanmean(PD.y)
            s=pretty_num(v)
        return (v,s)

    def yMedian(PD):
        if PD.yIsString or  PD.yIsDate:
            return None,'NA'
        else:
            v=np.nanmedian(PD.y)
            s=pretty_num(v)
        return (v,s)

    def yStd(PD):
        if PD.yIsString or  PD.yIsDate:
            return None,'NA'
        else:
            v=np.nanstd(PD.y)
            s=pretty_num(v)
        return (v,s)

    def yName(PD):
        return PD.sy, PD.sy

    def fileName(PD):
        return os.path.basename(PD.filename), os.path.basename(PD.filename)

    def baseDir(PD):
        return os.path.dirname(PD.filename),os.path.join(os.path.dirname(PD.filename),'')

    def tabName(PD):
        return PD.tabname, PD.tabname

    def ylen(PD):
        v=len(PD.y)
        s='{:d}'.format(v)
        return v,s


    def y0Var(PD):
        if PD._y0Std[0] is not None: 
            v=PD._y0Std[0]**2
            s=pretty_num(v)
        else:
            v=None
            s='NA'
        return v,s

    def y0TI(PD):
        v=PD._y0Std[0]/PD._y0Mean[0]
        s=pretty_num(v)
        return v,s


    def yRange(PD):
        if PD.yIsString:
            return 'NA','NA'
        elif PD.yIsDate:
            dtAll=getDt([PD.x[-1]-PD.x[0]])
            return '',pretty_time(dtAll)
        else:
            v=np.nanmax(PD.y)-np.nanmin(PD.y)
            s=pretty_num(v)
        return v,s

    def yAbsMax(PD):
        if PD.yIsString or PD.yIsDate:
            return 'NA','NA'
        else:
            v=max(np.abs(PD._y0Min[0]),np.abs(PD._y0Max[0]))
            s=pretty_num(v)
        return v,s


    def xRange(PD):
        if PD.xIsString:
            return 'NA','NA'
        elif PD.xIsDate:
            dtAll=getDt([PD.x[-1]-PD.x[0]])
            return '',pretty_time(dtAll)
        else:
            v=np.nanmax(PD.x)-np.nanmin(PD.x)
            s=pretty_num(v)
        return v,s


    def inty(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            v=np.trapz(y=PD.y,x=PD.x)
            s=pretty_num(v)
        return v,s

    def intyintdx(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            v=np.trapz(y=PD.y,x=PD.x)/np.trapz(y=PD.x*0+1,x=PD.x)
            s=pretty_num(v)
        return v,s

    def intyx1(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            v=np.trapz(y=PD.y*PD.x,x=PD.x)
            s=pretty_num(v)
        return v,s

    def intyx1_scaled(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            v=np.trapz(y=PD.y*PD.x,x=PD.x)
            v=v/np.trapz(y=PD.y,x=PD.x)
            s=pretty_num(v)
        return v,s

    def intyx2(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            v=np.trapz(y=PD.y*PD.x**2,x=PD.x)
            s=pretty_num(v)
        return v,s

    def meas(PD, xymeas):
        try:
            v='NA'
            xy = np.array([PD.x, PD.y]).transpose()
            points = find_closest(xy, [xymeas[0], xymeas[1]], False)
            if points.ndim == 1:
                v = points[1]
                s=pretty_num(v)
            else:
                v = points[0, 1]
                s = ' / '.join([str(p) for p in points[:, 1]])
        except (IndexError, TypeError):
            v='NA'
            s='NA'
        return v,s

    def yMeanMeas(PD, xymeas1, xymeas2):
        try:
            xy = np.array([PD.x, PD.y]).transpose()
            points_left = find_closest(xy, [xymeas1[0], xymeas1[1]], True)
            points_right = find_closest(xy, [xymeas2[0], xymeas2[1]], True)
            v = 'NA'
            left_index = np.where(PD.x == points_left[0])[0][0]
            right_index = np.where(PD.x == points_right[0])[0][0]
            mean_y = np.mean(PD.y[left_index:right_index])
            v = mean_y
            s = pretty_num(v)
        except (IndexError, TypeError):
            v = 'NA'
            s = 'NA'
        return v, s

    def dx(PD):
        if len(PD.x)<=1:
            return 'NA','NA'
        if PD.xIsString:
            return None,'NA'
        elif  PD.xIsDate:
            dt=getDt(PD.x)
            return dt,pretty_time(dt)
        else:
            v=PD.x[1]-PD.x[0]
            s=pretty_num(v)
            return v,s

    def xMax(PD):
        if PD.xIsString:
            return PD.x[-1],PD.x[-1]
        elif  PD.xIsDate:
            return PD.x[-1],'{}'.format(PD.x[-1])
        else:
            v=np.nanmax(PD.x)
            s=pretty_num(v)
            return v,s
    def xMin(PD):
        if PD.xIsString:
            return PD.x[0],PD.x[0]
        elif  PD.xIsDate:
            return PD.x[0],'{}'.format(PD.x[0])
        else:
            v=np.nanmin(PD.x)
            s=pretty_num(v)
            return v,s

    def leq(PD,m):
        from pydatview.tools.fatigue import eq_load
        if PD.yIsString or  PD.yIsDate:
            return 'NA','NA'
        else:
            T,_=PD.xRange()
            v=eq_load(PD.y, m=m, neq=T)[0][0]
            return v,pretty_num(v)

    def Info(PD,var):
        if var=='LSeg':
            return '','{:d}'.format(PD._Info.LSeg)
        elif var=='LWin':
            return '','{:d}'.format(PD._Info.LWin)
        elif var=='LOvlp':
            return '','{:d}'.format(PD._Info.LOvlp)
        elif var=='nFFT':
            return '','{:d}'.format(PD._Info.nFFT)


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

