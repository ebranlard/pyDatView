import os
import numpy as np
from pydatview.common import no_unit, unit, inverse_unit, has_chinese_char
from pydatview.common import isString, isDate, getDt
from pydatview.common import unique, pretty_num, pretty_time, pretty_date
import matplotlib.dates as mdates

# --------------------------------------------------------------------------------}
# --- PlotDataList functions
# --------------------------------------------------------------------------------{
def PDL_xlabel(PDL):
    #PD[axes[-1].iPD[0]].sx, **font_options)
    return PDL[-1].sx

# --------------------------------------------------------------------------------}
# --- PlotData 
# --------------------------------------------------------------------------------{
class PlotData():
    """ 
    Class for plot data

    For now, relies on some "indices" related to Tables/Columns/ and maybe Selection panel
    Not really elegant. These dependencies should be removed in the future
    """
    def __init__(PD, x=None, y=None, sx='', sy=''):
        """ Dummy init for now """
        PD.id=-1
        PD.it=-1 # table index
        PD.ix=-1 # column index
        PD.iy=-1 # column index
        PD.sx='' # x label
        PD.sy='' # y label
        PD.st='' # table label
        PD.syl='' # y label for legend
        PD.filename = ''
        PD.tabname = ''
        PD.tabID   = -1
        PD.x        =[]     # x data
        PD.y        =[]     # y data
        PD.xIsString=False  # true if strings
        PD.xIsDate  =False  # true if dates
        PD.yIsString=False  # true if strings
        PD.yIsDate  =False  # true if dates
        # Misc data
        PD._xMin = None
        PD._xMax = None
        PD._yMin = None
        PD._yMax = None
        PD._xAtYMin = None
        PD._xAtYMax = None
        # Backup data
        PD._x0Min = None
        PD._x0Max = None
        PD._y0Min = None
        PD._y0Max = None
        PD._x0AtYMin = None
        PD._x0AtYMax = None
        PD._y0Std  = None
        PD._y0Mean = None
        PD._n0     = None
        PD.x0 = None
        PD.y0 = None
        # Store xyMeas input values so we don't need to recompute xyMeas in case they didn't change
        PD.xyMeasInput1 = (None, None)
        PD.xyMeasInput2 = (None, None)
        PD.xyMeas      = [(None,None)]*2 # 2 measures for now

        if x is not None and y is not None:
            PD.fromXY(x,y,sx,sy)

    def fromIDs(PD, tabs, i, idx, SameCol, pipeline=None):
        """ Nasty initialization of plot data from "IDs" """
        PD.id = i
        PD.it = idx[0] # table index
        PD.ix = idx[1] # x index
        PD.iy = idx[2] # y index
        PD.sx = idx[3].replace('_',' ') # x label
        PD.sy = idx[4].replace('_',' ') # y label
        PD.syl = ''    # y label for legend
        PD.st = idx[5] # table label
        PD.filename = tabs[PD.it].filename
        PD.tabname  = tabs[PD.it].active_name
        PD.tabID   = -1 # TODO
        PD.SameCol  = SameCol
        PD.x, PD.xIsString, PD.xIsDate,_ = tabs[PD.it].getColumn(PD.ix)  # actual x data, with info
        PD.y, PD.yIsString, PD.yIsDate,c = tabs[PD.it].getColumn(PD.iy)  # actual y data, with info
        PD.c =c  # raw values, used by PDF

        PD._post_init(pipeline=pipeline)

    def fromXY(PD, x, y, sx='', sy=''):
        PD.x  = x
        PD.y  = y
        PD.c  = y
        PD.sx = sx.replace('_',' ')
        PD.sy = sy.replace('_',' ')
        PD.xIsString = isString(x)
        PD.yIsString = isString(y)
        PD.xIsDate   = isDate  (x)
        PD.yIsDate   = isDate  (y)

        PD._post_init()


    def _post_init(PD, pipeline=None):

        # --- Apply filters from pipeline on the fly
        #if pipeline is not None:
        #    print('[PDat]', pipeline.__reprFilters__())
        if pipeline is not None:
            PD.x, PD.y = pipeline.applyOnPlotData(PD.x, PD.y, PD.tabID) # TODO pass the tabID


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
        PD._x0AtYMin = PD._xAtYMin
        PD._x0AtYMax = PD._xAtYMax
        PD._y0Std  = PD.yStd()
        PD._y0Mean = PD.yMean()
        PD._n0     = (n,'{:d}'.format(n))
        PD.x0 =PD.x
        PD.y0 =PD.y

    def __repr__(s):
        s1='id:{}, it:{}, ix:{}, iy:{}, sx:"{}", sy:"{}", st:{}, syl:{}'.format(s.id,s.it,s.ix,s.iy,s.sx,s.sy,s.st,s.syl)
        #s1='id:{}, it:{}, sx:"{}", xyMeas:{}\n'.format(s.id,s.it,s.sx,s.xyMeas)
        return s1


    def toXY_date2num(self):
        """ return a XY array, converting dates to num if necessary"""
        if self.xIsDate :
            X = mdates.date2num(self.x)
        else:
            X = self.x
        if self.yIsDate :
            Y = mdates.date2num(self.y)
        else:
            Y = self.y
        XY = np.array([X, Y]).transpose()
        return XY

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


    def toFFT(PD, yType='Amplitude', xType='1/x', avgMethod='Welch', avgWindow='Hamming', bDetrend=True, nExp=8, nPerDecade=10):
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
        PD.x, PD.y, Info = fft_wrap(PD.x, PD.y, dt=dt, output_type=yType,averaging=avgMethod, averaging_window=avgWindow,detrend=bDetrend,nExp=nExp, nPerDecade=nPerDecade)
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
        PD._xAtYMin  = PD._xAtYMinCalc(PD._yMin[0])
        PD._xAtYMax  = PD._xAtYMaxCalc(PD._yMax[0])

    # --------------------------------------------------------------------------------}
    # --- Stats functions that should only becalled once, could maybe use @attributes..
    # --------------------------------------------------------------------------------{
    def _yMinCalc(PD):
        if PD.yIsString:
            return PD.y[0],PD.y[0].strip()
        elif PD.yIsDate:
            return PD.y[0],'{}'.format(PD.y[0])
        else:
            try:
                v=np.nanmin(PD.y)
                s=pretty_num(v)
            except:
                return np.nan, 'NA'
        return (v,s)

    def _yMaxCalc(PD):
        if PD.yIsString:
            return PD.y[-1],PD.y[-1].strip()
        elif PD.yIsDate:
            return PD.y[-1],'{}'.format(PD.y[-1])
        else:
            try:
                v=np.nanmax(PD.y)
                s=pretty_num(v)
            except:
                return np.nan, 'NA'
        return (v,s)

    def _xAtYMinCalc(PD, yMin):
        if PD.xIsString:
            return PD.x[0],PD.x[0].strip()
        elif PD.xIsDate:
            return PD.x[0],'{}'.format(PD.x[0])
        else:
            try:
                v = PD.x[np.where(PD.y == yMin)[0][0]]   # Might fail if all nan
            except:
                v = PD.x[0]
            s=pretty_num(v)
        return (v,s)

    def _xAtYMaxCalc(PD, yMax):
        if PD.xIsString:
            return PD.x[-1],PD.x[-1].strip()
        elif PD.xIsDate:
            return PD.x[-1],'{}'.format(PD.x[-1])
        else:
            try:
                v = PD.x[np.where(PD.y == yMax)[0][0]] # Might fail if all nan
            except:
                v = PD.x[0]
            s=pretty_num(v)
        return (v,s)

    def _xMinCalc(PD):
        if PD.xIsString:
            return PD.x[0],PD.x[0].strip()
        elif PD.xIsDate:
            return PD.x[0],'{}'.format(PD.x[0])
        else:
            try:
                v=np.nanmin(PD.x)
                s=pretty_num(v)
            except:
                return np.nan, 'NA'
        return (v,s)

    def _xMaxCalc(PD):
        if PD.xIsString:
            return PD.x[-1],PD.x[-1].strip()
        elif PD.xIsDate:
            return PD.x[-1],'{}'.format(PD.x[-1])
        else:
            try:
                v=np.nanmax(PD.x)
                s=pretty_num(v)
            except:
                return np.nan, 'NA'
        return (v,s)

    def xMin(PD):
        return PD._xMin

    def xMax(PD):
        return PD._xMax

    def xAtYMin(PD):
        return PD._xAtYMin

    def xAtYMax(PD):
        return PD._xAtYMax

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
            try:
                v=np.nanmean(PD.y)
                s=pretty_num(v)
            except:
                return np.nan, 'NA'
        return (v,s)

    def yMedian(PD):
        if PD.yIsString or  PD.yIsDate:
            return None,'NA'
        else:
            try:
                v=np.nanmedian(PD.y)
                s=pretty_num(v)
            except:
                return np.nan, 'NA'
        return (v,s)

    def yStd(PD):
        if PD.yIsString or  PD.yIsDate:
            return None,'NA'
        else:
            try:
                v=np.nanstd(PD.y)
                s=pretty_num(v)
            except:
                return np.nan, 'NA'
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
        if PD._y0Mean[0]==0:
            return np.nan,'NA'
        try:
            v=PD._y0Std[0]/PD._y0Mean[0]
            s=pretty_num(v)
            return v,s
        except:
            return np.nan,'NA'


    def yRange(PD):
        if PD.yIsString:
            return 'NA','NA'
        elif PD.yIsDate:
            dtAll=getDt([PD.x[0],PD.x[-1]])
            return np.nan,pretty_time(dtAll)
        else:
            try:
                v=np.nanmax(PD.y)-np.nanmin(PD.y)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan,'NA'

    def yAbsMax(PD):
        if PD.yIsString or PD.yIsDate:
            return 'NA','NA'
        else:
            try:
                v=max(np.abs(PD._y0Min[0]),np.abs(PD._y0Max[0]))
                s=pretty_num(v)
                return v,s
            except:
                return np.nan,'NA'

    def xRange(PD):
        if PD.xIsString:
            return 'NA','NA'
        elif PD.xIsDate:
            dtAll=getDt([PD.x[0],PD.x[-1]])
            return np.nan,pretty_time(dtAll)
        else:
            try:
                v=np.nanmax(PD.x)-np.nanmin(PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'


    def inty(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            try:
                v=np.trapz(y=PD.y,x=PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'

    def intyintdx(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            try:
                v=np.trapz(y=PD.y,x=PD.x)/np.trapz(y=PD.x*0+1,x=PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'

    def intyx1(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            try:
                v=np.trapz(y=PD.y*PD.x,x=PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'
                

    def intyx1_scaled(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            try:
                v=np.trapz(y=PD.y*PD.x,x=PD.x)
                v=v/np.trapz(y=PD.y,x=PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'

    def intyx2(PD):
        if PD.yIsString or PD.yIsDate or PD.xIsString or PD.xIsDate:
            return None,'NA'
        else:
            try:
                v=np.trapz(y=PD.y*PD.x**2,x=PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'


    # --------------------------------------------------------------------------------}
    # --- Measure - TODO: cleanup
    # --------------------------------------------------------------------------------{
    def ymeas1(PD):
        # NOTE: calculation happens in GUIMeasure..
        if PD.xyMeas[0][0] is not None:
            yv = PD.xyMeas[0][1]
            if PD.yIsString:
                return yv, yb
            elif PD.yIsDate:
                return yv, pretty_date(yv)
            else:
                return yv, pretty_num(yv)
        else:
            return np.nan, 'NA'

    def ymeas2(PD):
        # NOTE: calculation happens in GUIMeasure..
        if PD.xyMeas[1][0] is not None:
            yv = PD.xyMeas[1][1]
            if PD.yIsString:
                return yv, yb
            elif PD.yIsDate:
                return yv, pretty_date(yv)
            else:
                return yv, pretty_num(yv)
        else:
            return np.nan, 'NA'

    def yMeanMeas(PD):
        return PD._measCalc('mean')

    def yMinMeas(PD):
        return PD._measCalc('min')

    def yMaxMeas(PD):
        return PD._measCalc('max')

    def xAtYMinMeas(PD):
        return PD._measCalc('xmin')

    def xAtYMaxMeas(PD):
        return PD._measCalc('xmax')

    def _measCalc(PD, mode):
        # TODO clean up
        if PD.xyMeas[0][0] is None or PD.xyMeas[1][0] is None:
            return np.nan, 'NA'
        if np.isnan(PD.xyMeas[0][0]) or np.isnan(PD.xyMeas[1][0]):
            return np.nan, 'NA'
        # We only support the case where y values are numeric
        if PD.yIsDate or PD.yIsString:
            return np.nan, 'NA'

        try:
            v = np.nan
            left_index  = np.argmin(np.abs(PD.x - PD.xyMeas[0][0]))
            right_index = np.argmin(np.abs(PD.x - PD.xyMeas[1][0]))
            if left_index == right_index:
                return np.nan, 'Empty'
            if left_index > right_index:
                left_index, right_index = right_index, left_index
        except (IndexError, TypeError):
            return np.nan, 'NA'

        try:
            yValues = PD.y[left_index:right_index]
            if mode == 'mean':
                v = np.nanmean(yValues)
                s = pretty_num(v)
            elif mode == 'min':
                v = np.nanmin(yValues)
                s = pretty_num(v)
            elif mode == 'max':
                v = np.nanmax(yValues)
                s = pretty_num(v)
            elif mode == 'xmin':
                v = PD.x[left_index + np.where(yValues == np.nanmin(yValues))[0][0]]
                if PD.xIsDate:
                    s = pretty_date(v)
            elif mode == 'xmax':
                v = PD.x[left_index + np.where(yValues == np.nanmax(yValues))[0][0]]
                if PD.xIsDate:
                    s = pretty_date(v)
            else:
                raise NotImplementedError('Error: Mode ' + mode + ' not implemented')
        except (IndexError, TypeError):
            return np.nan, 'NA'

        return v, s

    # --------------------------------------------------------------------------------}
    # --- Other Stats functions
    # --------------------------------------------------------------------------------{
    def dx(PD):
        if len(PD.x)<=1:
            return 'NA','NA'
        if PD.xIsString:
            return None,'NA'
        elif  PD.xIsDate:
            dt=getDt(PD.x)
            return dt,pretty_time(dt)
        else:
            try:
                v=PD.x[1]-PD.x[0]
                s=pretty_num(v)
                return v,s
            except:
                print('plotdata: computing dx failed for {}'.format(PD))
                return np.nan, 'NA'

    def xMax(PD):
        if PD.xIsString:
            return PD.x[-1],PD.x[-1]
        elif  PD.xIsDate:
            return PD.x[-1],'{}'.format(PD.x[-1])
        else:
            try:
                v=np.nanmax(PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'
    def xMin(PD):
        if PD.xIsString:
            return PD.x[0],PD.x[0]
        elif  PD.xIsDate:
            return PD.x[0],'{}'.format(PD.x[0])
        else:
            try:
                v=np.nanmin(PD.x)
                s=pretty_num(v)
                return v,s
            except:
                return np.nan, 'NA'

    def leq(PD, m, method=None):
        from pydatview.tools.fatigue import equivalent_load
        if PD.yIsString or  PD.yIsDate:
            return 'NA','NA'
        else:
            if method is None:
                try:
                    import fatpack
                    method='fatpack'
                except ModuleNotFoundError:
                    print('[INFO] module fatpack not installed, default to windap method for equivalent load')
                    method='rainflow_windap'
            try:
                v = equivalent_load(PD.x, PD.y, m=m, Teq=1, bins=100, method=method)
            except:
                v = np.nan
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

    @staticmethod
    def createDummy(n=30):
        x = np.linspace(0,4*np.pi,n)
        y = np.sin(x)
        return PlotData(x=x, y=y, sx='time [s]', sy='Signal [m]')


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

