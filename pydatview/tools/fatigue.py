# --------------------------------------------------------------------------------}
# --- Info 
# --------------------------------------------------------------------------------{
# Tools for fatigue analysis
#
# Taken from:
#    repository:  wetb
#    package:     wetb.fatigue_tools,
#    institution: DTU wind energy, Denmark 
#    main author: mmpe
'''
Created on 04/03/2013
@author: mmpe


'eq_load' calculate equivalent loads using one of the two rain flow counting methods
'cycle_matrix' calculates a matrix of cycles (binned on amplitude and mean value)
'eq_load_and_cycles' is used to calculate eq_loads of multiple time series (e.g. life time equivalent load)

The methods uses the rainflow counting routines (See documentation in top of methods):
- 'rainflow_windap': (Described in "Recommended Practices for Wind Turbine Testing - 3. Fatigue Loads",
                      2. edition 1990, Appendix A)
or
- 'rainflow_astm' (based on the c-implementation by Adam Nieslony found at the MATLAB Central File Exchange
                   http://www.mathworks.com/matlabcentral/fileexchange/3026)
'''
import warnings
import numpy as np


__all__  = ['rainflow_astm', 'rainflow_windap','eq_load','eq_load_and_cycles','cycle_matrix','cycle_matrix2']


def equivalent_load(signal, m=3, Teq=1, nBins=46, method='rainflow_windap'):
    """Equivalent load calculation

    Calculate the equivalent loads for a list of Wohler exponent

    Parameters
    ----------
    signals : array-like, the signal
    m :    Wohler exponent (default is 3)
    Teq : The equivalent number of load cycles (default is 1, but normally the time duration in seconds is used)
    nBins : Number of bins in rainflow count histogram
    method: 'rainflow_windap, rainflow_astm, fatpack

    Returns
    -------
    Leq : the equivalent load for given m and Tea
    """
    signal = np.asarray(signal)

    rainflow_func_dict = {'rainflow_windap':rainflow_windap, 'rainflow_astm':rainflow_astm}
    if method in rainflow_func_dict.keys():
        # Call wetb function for one m
        Leq = eq_load(signal, m=[m], neq=Teq, no_bins=nBins, rainflow_func=rainflow_func_dict[method])[0][0]

    elif method=='fatpack':
        import fatpack
        # find rainflow ranges
        try:
            ranges = fatpack.find_rainflow_ranges(signal)
        except IndexError:
            # Typically fails for constant signal
            return np.nan
        # find range count and bin
        Nrf, Srf = fatpack.find_range_count(ranges, nBins)
        # get DEL
        DELs = Srf**m * Nrf / Teq
        Leq = DELs.sum() ** (1/m)

    else:
        raise NotImplementedError(method)

    return Leq

 


def check_signal(signal):
    # check input data validity
    if not type(signal).__name__ == 'ndarray':
        raise TypeError('signal must be ndarray, not: ' + type(signal).__name__)

    elif len(signal.shape) not in (1, 2):
        raise TypeError('signal must be 1D or 2D, not: ' + str(len(signal.shape)))

    if len(signal.shape) == 2:
        if signal.shape[1] > 1:
            raise TypeError('signal must have one column only, not: ' + str(signal.shape[1]))
    if np.min(signal) == np.max(signal):
        raise TypeError("Signal contains no variation")


def rainflow_windap(signal, levels=255., thresshold=(255 / 50)):
    """Windap equivalent rainflow counting


    Calculate the amplitude and mean values of half cycles in signal

    This algorithms used by this routine is implemented directly as described in
    "Recommended Practices for Wind Turbine Testing - 3. Fatigue Loads", 2. edition 1990, Appendix A

    Parameters
    ----------
    Signal : array-like
        The raw signal

    levels : int, optional
        The signal is discretize into this number of levels.
        255 is equivalent to the implementation in Windap

    thresshold : int, optional
        Cycles smaller than this thresshold are ignored
        255/50 is equivalent to the implementation in Windap

    Returns
    -------
    ampl : array-like
        Peak to peak amplitudes of the half cycles

    mean : array-like
        Mean values of the half cycles


    Examples
    --------
    >>> signal = np.array([-2.0, 0.0, 1.0, 0.0, -3.0, 0.0, 5.0, 0.0, -1.0, 0.0, 3.0, 0.0, -4.0, 0.0, 4.0, 0.0, -2.0])
    >>> ampl, mean = rainflow_windap(signal)
    """
    check_signal(signal)
    #type <double> is required by <find_extreme> and <rainflow>
    signal = signal.astype(np.double)
    if np.all(np.isnan(signal)):
        return None
    offset = np.nanmin(signal)
    signal -= offset
    if np.nanmax(signal) > 0:
        gain = np.nanmax(signal) / levels
        signal = signal / gain
        signal = np.round(signal).astype(int)


        # If possible the module is compiled using cython otherwise the python implementation is used


        #Convert to list of local minima/maxima where difference > thresshold
        sig_ext = peak_trough(signal, thresshold)


        #rainflow count
        ampl_mean = pair_range_amplitude_mean(sig_ext)

        ampl_mean = np.array(ampl_mean)
        ampl_mean = np.round(ampl_mean / thresshold) * gain * thresshold
        ampl_mean[:, 1] += offset
        return ampl_mean.T



def rainflow_astm(signal):
    """Matlab equivalent rainflow counting

    Calculate the amplitude and mean values of half cycles in signal

    This implemementation is based on the c-implementation by Adam Nieslony found at
    the MATLAB Central File Exchange http://www.mathworks.com/matlabcentral/fileexchange/3026

    Parameters
    ----------
    Signal : array-like
        The raw signal

    Returns
    -------
    ampl : array-like
        peak to peak amplitudes of the half cycles (note that the matlab implementation
        uses peak amplitude instead of peak to peak)

    mean : array-like
        Mean values of the half cycles


    Examples
    --------
    >>> signal = np.array([-2.0, 0.0, 1.0, 0.0, -3.0, 0.0, 5.0, 0.0, -1.0, 0.0, 3.0, 0.0, -4.0, 0.0, 4.0, 0.0, -2.0])
    >>> ampl, mean = rainflow_astm(signal)
    """
    check_signal(signal)

    # type <double> is reuqired by <find_extreme> and <rainflow>
    signal = signal.astype(np.double)

    # Import find extremes and rainflow.
    # If possible the module is compiled using cython otherwise the python implementation is used

    # Remove points which is not local minimum/maximum
    sig_ext = find_extremes(signal)

    # rainflow count
    ampl_mean = np.array(rainflowcount(sig_ext))

    return np.array(ampl_mean).T


def eq_load(signals, no_bins=46, m=[3, 4, 6, 8, 10, 12], neq=1, rainflow_func=rainflow_windap):
    """Equivalent load calculation

    Calculate the equivalent loads for a list of Wohler exponent and number of equivalent loads

    Parameters
    ----------
    signals : list of tuples or array_like
        - if list of tuples: list must have format [(sig1_weight, sig1),(sig2_weight, sig1),...] where\n
            - sigx_weight is the weight of signal x\n
            - sigx is signal x\n
        - if array_like: The signal
    no_bins : int, optional
        Number of bins in rainflow count histogram
    m : int, float or array-like, optional
        Wohler exponent (default is [3, 4, 6, 8, 10, 12])
    neq : int, float or array-like, optional
        The equivalent number of load cycles (default is 1, but normally the time duration in seconds is used)
    rainflow_func : {rainflow_windap, rainflow_astm}, optional
        The rainflow counting function to use (default is rainflow_windap)

    Returns
    -------
    eq_loads : array-like
        List of lists of equivalent loads for the corresponding equivalent number(s) and Wohler exponents

    Examples
    --------
    >>> signal = np.array([-2.0, 0.0, 1.0, 0.0, -3.0, 0.0, 5.0, 0.0, -1.0, 0.0, 3.0, 0.0, -4.0, 0.0, 4.0, 0.0, -2.0])
    >>> eq_load(signal, no_bins=50, neq=[1, 17], m=[3, 4, 6], rainflow_func=rainflow_windap)
    [[10.311095426959747, 9.5942535021382174, 9.0789213365013932], # neq = 1, m=[3,4,6]
    [4.010099657859783, 4.7249689509841746, 5.6618639965313005]], # neq = 17, m=[3,4,6]

    eq_load([(.4, signal), (.6, signal)], no_bins=50, neq=[1, 17], m=[3, 4, 6], rainflow_func=rainflow_windap)
    [[10.311095426959747, 9.5942535021382174, 9.0789213365013932], # neq = 1, m=[3,4,6]
    [4.010099657859783, 4.7249689509841746, 5.6618639965313005]], # neq = 17, m=[3,4,6]
    """
    try:
        return eq_load_and_cycles(signals, no_bins, m, neq, rainflow_func)[0]
    except TypeError:
        return [[np.nan] * len(np.atleast_1d(m))] * len(np.atleast_1d(neq))


def eq_load_and_cycles(signals, no_bins=46, m=[3, 4, 6, 8, 10, 12], neq=[10 ** 6, 10 ** 7, 10 ** 8], rainflow_func=rainflow_windap):
    """Calculate combined fatigue equivalent load

    Parameters
    ----------
    signals : list of tuples or array_like
        - if list of tuples: list must have format [(sig1_weight, sig1),(sig2_weight, sig1),...] where\n
            - sigx_weight is the weight of signal x\n
            - sigx is signal x\n
        - if array_like: The signal
    no_bins : int, optional
        Number of bins for rainflow counting
    m : int, float or array-like, optional
        Wohler exponent (default is [3, 4, 6, 8, 10, 12])
    neq : int or array-like, optional
        Equivalent number, default is [10^6, 10^7, 10^8]
    rainflow_func : {rainflow_windap, rainflow_astm}, optional
        The rainflow counting function to use (default is rainflow_windap)

    Returns
    -------
    eq_loads : array-like
        List of lists of equivalent loads for the corresponding equivalent number(s) and Wohler exponents
    cycles : array_like
        2d array with shape = (no_ampl_bins, 1)
    ampl_bin_mean : array_like
        mean amplitude of the bins
    ampl_bin_edges
        Edges of the amplitude bins
    """
    cycles, ampl_bin_mean, ampl_bin_edges, _, _ = cycle_matrix(signals, no_bins, 1, rainflow_func)
    if 0:  #to be similar to windap
        ampl_bin_mean = (ampl_bin_edges[:-1] + ampl_bin_edges[1:]) / 2
    cycles, ampl_bin_mean = cycles.flatten(), ampl_bin_mean.flatten()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        eq_loads = [[((np.nansum(cycles * ampl_bin_mean ** _m) / _neq) ** (1. / _m)) for _m in np.atleast_1d(m)]  for _neq in np.atleast_1d(neq)]
    return eq_loads, cycles, ampl_bin_mean, ampl_bin_edges


def cycle_matrix(signals, ampl_bins=10, mean_bins=10, rainflow_func=rainflow_windap):
    """Markow load cycle matrix

    Calculate the Markow load cycle matrix

    Parameters
    ----------
    Signals : array-like or list of tuples
        - if array-like, the raw signal\n
        - if list of tuples, list of (weight, signal), e.g. [(0.1,sig1), (0.8,sig2), (.1,sig3)]\n
    ampl_bins : int or array-like, optional
        if int, Number of amplitude value bins (default is 10)
        if array-like, the bin edges for amplitude
    mean_bins : int or array-like, optional
        if int, Number of mean value bins (default is 10)
        if array-like, the bin edges for mea
    rainflow_func : {rainflow_windap, rainflow_astm}, optional
        The rainflow counting function to use (default is rainflow_windap)

    Returns
    -------
    cycles : ndarray, shape(ampl_bins, mean_bins)
        A bi-dimensional histogram of load cycles(full cycles). Amplitudes are\
        histogrammed along the first dimension and mean values are histogrammed along the second dimension.
    ampl_bin_mean : ndarray, shape(ampl_bins,)
        The average cycle amplitude of the bins
    ampl_edges : ndarray, shape(ampl_bins+1,)
        The amplitude bin edges
    mean_bin_mean : ndarray, shape(ampl_bins,)
        The average cycle mean of the bins
    mean_edges : ndarray, shape(mean_bins+1,)
        The mean bin edges

    Examples
    --------
    >>> signal = np.array([-2.0, 0.0, 1.0, 0.0, -3.0, 0.0, 5.0, 0.0, -1.0, 0.0, 3.0, 0.0, -4.0, 0.0, 4.0, 0.0, -2.0])
    >>> cycles, ampl_bin_mean, ampl_edges, mean_bin_mean, mean_edges = cycle_matrix(signal)
    >>> cycles, ampl_bin_mean, ampl_edges, mean_bin_mean, mean_edges = cycle_matrix([(.4, signal), (.6,signal)])
    """

    if isinstance(signals[0], tuple):
        weights, ampls, means = np.array([(np.zeros_like(ampl)+weight,ampl,mean) for weight, signal in signals for ampl,mean in rainflow_func(signal[:]).T], dtype=np.float64).T
    else:
        ampls, means = rainflow_func(signals[:])
        weights = np.ones_like(ampls)
    if isinstance(ampl_bins, int):
        ampl_bins = np.linspace(0, 1, num=ampl_bins + 1) * ampls[weights>0].max()
    cycles, ampl_edges, mean_edges = np.histogram2d(ampls, means, [ampl_bins, mean_bins], weights=weights)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ampl_bin_sum = np.histogram2d(ampls, means, [ampl_bins, mean_bins], weights=weights * ampls)[0]
        ampl_bin_mean = np.nanmean(ampl_bin_sum / np.where(cycles,cycles,np.nan),1)
        mean_bin_sum = np.histogram2d(ampls, means, [ampl_bins, mean_bins], weights=weights * means)[0]
        mean_bin_mean = np.nanmean(mean_bin_sum / np.where(cycles, cycles, np.nan), 1)
    cycles = cycles / 2  # to get full cycles
    return cycles, ampl_bin_mean, ampl_edges, mean_bin_mean, mean_edges


def cycle_matrix2(signal, nrb_amp, nrb_mean, rainflow_func=rainflow_windap):
    """
    Same as wetb.fatigue.cycle_matrix but bin from min_amp to
    max_amp instead of 0 to max_amp.

    Parameters
    ----------

    Signal : ndarray(n)
        1D Raw signal array

    nrb_amp : int
        Number of bins for the amplitudes

    nrb_mean : int
        Number of bins for the means

    rainflow_func : {rainflow_windap, rainflow_astm}, optional
        The rainflow counting function to use (default is rainflow_windap)

    Returns
    -------

    cycles : ndarray, shape(ampl_bins, mean_bins)
        A bi-dimensional histogram of load cycles(full cycles). Amplitudes are\
        histogrammed along the first dimension and mean values are histogrammed
        along the second dimension.

    ampl_edges : ndarray, shape(no_bins+1,n)
        The amplitude bin edges

    mean_edges : ndarray, shape(no_bins+1,n)
        The mean bin edges

    """
    bins = [nrb_amp, nrb_mean]
    ampls, means = rainflow_func(signal)
    weights = np.ones_like(ampls)
    cycles, ampl_edges, mean_edges = np.histogram2d(ampls, means, bins,
                                                    weights=weights)
    cycles = cycles / 2  # to get full cycles

    return cycles, ampl_edges, mean_edges

# --------------------------------------------------------------------------------}
# --- Rainflowcount_astm.py
# --------------------------------------------------------------------------------{
'''
Created on 27/02/2013

@author: mmpe

How to use:

import_cython("cy_rainflowcount",'cy_rainflowcount.py','')
from cy_rainflowcount import find_extremes,rainflow

ext = find_extremes(np.array([-2,0,1,0,-3,0,5,0,-1,0,3,0,-4,0,4,0,-2]).astype(np.double))
print rainflow(ext)
'''
def find_extremes(signal):  #cpdef find_extremes(np.ndarray[double,ndim=1] signal):
    """return indexes of local minima and maxima plus first and last element of signal"""

    #cdef int pi, i
    # sign of gradient
    sign_grad = np.int8(np.sign(np.diff(signal)))

    # remove plateaus(sign_grad==0) by sign_grad[plateau_index]=sign_grad[plateau_index-1]
    plateau_indexes, = np.where(sign_grad == 0)
    if len(plateau_indexes) > 0 and plateau_indexes[0] == 0:
        # first element is a plateau
        if len(plateau_indexes) == len(sign_grad):
                # All values are equal to crossing level!
                return np.array([0])

        # set first element = first element which is not a plateau and delete plateau index
        i = 0
        while sign_grad[i] == 0:
            i += 1
        sign_grad[0] = sign_grad[i]

        plateau_indexes = np.delete(plateau_indexes, 0)

    for pi in plateau_indexes.tolist():
        sign_grad[pi] = sign_grad[pi - 1]

    extremes, = np.where(np.r_[1, (sign_grad[1:] * sign_grad[:-1] < 0), 1])

    return signal[extremes]


def rainflowcount(sig):  #cpdef rainflowcount(np.ndarray[double,ndim=1] sig):
    """Cython compilable rain ampl_mean count without time analysis


    This implemementation is based on the c-implementation by Adam Nieslony found at
    the MATLAB Central File Exchange http://www.mathworks.com/matlabcentral/fileexchange/3026

    References
    ----------
    Adam Nieslony, "Determination of fragments of multiaxial service loading
    strongly influencing the fatigue of machine components,"
    Mechanical Systems and Signal Processing 23, no. 8 (2009): 2712-2721.

    and is based on the following standard:
    ASTM E 1049-85 (Reapproved 1997), Standard practices for cycle counting in
    fatigue analysis, in: Annual Book of ASTM Standards, vol. 03.01, ASTM,
    Philadelphia, 1999, pp. 710-718.

    Copyright (c) 1999-2002 by Adam Nieslony

    Ported to Cython compilable Python by Mads M Pedersen
    In addition peak amplitude is changed to peak to peak amplitude


    """

    #cdef int sig_ptr, index
    #cdef double ampl
    a = []
    sig_ptr = 0
    ampl_mean = []
    for _ in range(len(sig)):
        a.append(sig[sig_ptr])
        sig_ptr += 1
        while len(a) > 2 and abs(a[-3] - a[-2]) <= abs(a[-2] - a[-1]):
            ampl = abs(a[-3] - a[-2])
            mean = (a[-3] + a[-2]) / 2;
            if len(a) == 3:
                del a[0]
                if ampl > 0:
                    ampl_mean.append((ampl, mean))
            elif len(a) > 3:
                del a[-3:-1]
                if ampl > 0:
                    ampl_mean.append((ampl, mean))
                    ampl_mean.append((ampl, mean))
    for index in range(len(a) - 1):
        ampl = abs(a[index] - a[index + 1])
        mean = (a[index] + a[index + 1]) / 2;
        if ampl > 0:
            ampl_mean.append((ampl, mean))
    return ampl_mean

# --------------------------------------------------------------------------------}
# --- Peak_trough.py
# --------------------------------------------------------------------------------{
# @cython.locals(BEGIN=cython.int, MINZO=cython.int, MAXZO=cython.int, ENDZO=cython.int, \
#                R=cython.int, L=cython.int, i=cython.int, p=cython.int, f=cython.int)
def peak_trough(x, R):  #cpdef np.ndarray[long,ndim=1] peak_trough(np.ndarray[long,ndim=1] x, int R):
    """
    Returns list of local maxima/minima.

    x: 1-dimensional numpy array containing signal
    R: Thresshold (minimum difference between succeeding min and max

    This routine is implemented directly as described in
    "Recommended Practices for Wind Turbine Testing - 3. Fatigue Loads", 2. edition 1990, Appendix A
    """

    BEGIN = 0
    MINZO = 1
    MAXZO = 2
    ENDZO = 3
    S = np.zeros(x.shape[0] + 1, dtype=int)

    L = x.shape[0]
    goto = BEGIN

    while 1:
        if goto == BEGIN:
            trough = x[0]
            peak = x[0]

            i = 0
            p = 1
            f = 0
            while goto == BEGIN:
                i += 1
                if i == L:
                    goto = ENDZO
                    continue
                else:
                    if x[i] > peak:
                        peak = x[i]
                        if peak - trough >= R:
                            S[p] = trough
                            goto = MAXZO
                            continue
                    elif x[i] < trough:
                        trough = x[i]
                        if peak - trough >= R:
                            S[p] = peak
                            goto = MINZO
                            continue

        elif goto == MINZO:
            f = -1

            while goto == MINZO:
                i += 1
                if i == L:
                    goto = ENDZO
                    continue
                else:
                    if x[i] < trough:
                        trough = x[i]
                    else:
                        if x[i] - trough >= R:
                            p += 1
                            S[p] = trough
                            peak = x[i]
                            goto = MAXZO
                            continue
        elif goto == MAXZO:
            f = 1
            while goto == MAXZO:
                i += 1
                if i == L:
                    goto = ENDZO
                    continue
                else:
                    if x[i] > peak:
                        peak = x[i]
                    else:
                        if peak - x[i] >= R:
                            p += 1
                            S[p] = peak
                            trough = x[i]
                            goto = MINZO
                            continue
        elif goto == ENDZO:

            n = p + 1
            if abs(f) == 1:
                if f == 1:
                    S[n] = peak
                else:
                    S[n] = trough
            else:
                S[n] = (trough + peak) / 2
            S = S[1:n + 1]
            return S


# --------------------------------------------------------------------------------}
# --- pair_range.py
# --------------------------------------------------------------------------------{
# @cython.locals(p=cython.int, q=cython.int, f=cython.int, flow=list, k=cython.int, n=cython.int, ptr=cython.int)
def pair_range_amplitude(x):  # cpdef pair_range(np.ndarray[long,ndim=1]  x):
    """
    Returns a list of half-cycle-amplitudes
    x: Peak-Trough sequence (integer list of local minima and maxima)

    This routine is implemented according to
    "Recommended Practices for Wind Turbine Testing - 3. Fatigue Loads", 2. edition 1990, Appendix A
    except that a list of half-cycle-amplitudes are returned instead of a from_level-to_level-matrix
    """

    x = x - np.min(x)
    k = np.max(x)
    n = x.shape[0]
    S = np.zeros(n + 1)

    #A = np.zeros(k+1)
    flow = []
    S[1] = x[0]
    ptr = 1
    p = 1
    q = 1
    f = 0
    # phase 1
    while True:
        p += 1
        q += 1

        # read
        S[p] = x[ptr]
        ptr += 1

        if q == n:
            f = 1
        while p >= 4:
            if (S[p - 2] > S[p - 3] and S[p - 1] >= S[p - 3] and S[p] >= S[p - 2]) \
                or\
                    (S[p - 2] < S[p - 3] and S[p - 1] <= S[p - 3] and S[p] <= S[p - 2]):
                ampl = abs(S[p - 2] - S[p - 1])
                # A[ampl]+=2 #Two half cycles
                flow.append(ampl)
                flow.append(ampl)
                S[p - 2] = S[p]

                p -= 2
            else:
                break

        if f == 0:
            pass
        else:
            break
    # phase 2
    q = 0
    while True:
        q += 1
        if p == q:
            break
        else:
            ampl = abs(S[q + 1] - S[q])
            # A[ampl]+=1
            flow.append(ampl)
    return flow





# @cython.locals(p=cython.int, q=cython.int, f=cython.int, flow=list, k=cython.int, n=cython.int, ptr=cython.int)
def pair_range_from_to(x):  # cpdef pair_range(np.ndarray[long,ndim=1]  x):
    """
    Returns a list of half-cycle-amplitudes
    x: Peak-Trough sequence (integer list of local minima and maxima)

    This routine is implemented according to
    "Recommended Practices for Wind Turbine Testing - 3. Fatigue Loads", 2. edition 1990, Appendix A
    except that a list of half-cycle-amplitudes are returned instead of a from_level-to_level-matrix
    """

    x = x - np.min(x)
    k = np.max(x)
    n = x.shape[0]
    S = np.zeros(n + 1)

    A = np.zeros((k + 1, k + 1))
    S[1] = x[0]
    ptr = 1
    p = 1
    q = 1
    f = 0
    # phase 1
    while True:
        p += 1
        q += 1

        # read
        S[p] = x[ptr]
        ptr += 1

        if q == n:
            f = 1
        while p >= 4:
            #print S[p - 3:p + 1]
            #print S[p - 2], ">", S[p - 3], ", ", S[p - 1], ">=", S[p - 3], ", ", S[p], ">=", S[p - 2], (S[p - 2] > S[p - 3] and S[p - 1] >= S[p - 3] and S[p] >= S[p - 2])
            #print S[p - 2], "<", S[p - 3], ", ", S[p - 1], "<=", S[p - 3], ", ", S[p], "<=", S[p - 2], (S[p - 2] < S[p - 3] and S[p - 1] <= S[p - 3] and S[p] <= S[p - 2])
            #print (S[p - 2] > S[p - 3] and S[p - 1] >= S[p - 3] and S[p] >= S[p - 2]) or (S[p - 2] < S[p - 3] and S[p - 1] <= S[p - 3] and S[p] <= S[p - 2])
            if (S[p - 2] > S[p - 3] and S[p - 1] >= S[p - 3] and S[p] >= S[p - 2]) or \
               (S[p - 2] < S[p - 3] and S[p - 1] <= S[p - 3] and S[p] <= S[p - 2]):
                A[S[p - 2], S[p - 1]] += 1
                A[S[p - 1], S[p - 2]] += 1
                S[p - 2] = S[p]
                p -= 2
            else:
                break

        if f == 1:
            break  # q==n
    # phase 2
    q = 0
    while True:
        q += 1
        if p == q:
            break
        else:
            #print S[q], "to", S[q + 1]
            A[S[q], S[q + 1]] += 1
    return A

# @cython.locals(p=cython.int, q=cython.int, f=cython.int, flow=list, k=cython.int, n=cython.int, ptr=cython.int)
def pair_range_amplitude_mean(x):  # cpdef pair_range(np.ndarray[long,ndim=1]  x):
    """
    Returns a list of half-cycle-amplitudes
    x: Peak-Trough sequence (integer list of local minima and maxima)

    This routine is implemented according to
    "Recommended Practices for Wind Turbine Testing - 3. Fatigue Loads", 2. edition 1990, Appendix A
    except that a list of half-cycle-amplitudes are returned instead of a from_level-to_level-matrix
    """

    x = x - np.min(x)
    k = np.max(x)
    n = x.shape[0]
    S = np.zeros(n + 1)
    ampl_mean = []
    A = np.zeros((k + 1, k + 1))
    S[1] = x[0]
    ptr = 1
    p = 1
    q = 1
    f = 0
    # phase 1
    while True:
        p += 1
        q += 1

                # read
        S[p] = x[ptr]
        ptr += 1

        if q == n:
            f = 1
        while p >= 4:
            if (S[p - 2] > S[p - 3] and S[p - 1] >= S[p - 3] and S[p] >= S[p - 2]) \
                or\
                    (S[p - 2] < S[p - 3] and S[p - 1] <= S[p - 3] and S[p] <= S[p - 2]):
                # Extract two intermediate half cycles
                ampl = abs(S[p - 2] - S[p - 1])
                mean = (S[p - 2] + S[p - 1]) / 2
                ampl_mean.append((ampl, mean))
                ampl_mean.append((ampl, mean))

                S[p - 2] = S[p]

                p -= 2
            else:
                break

        if f == 0:
            pass
        else:
            break
    # phase 2
    q = 0
    while True:
        q += 1
        if p == q:
            break
        else:
            ampl = abs(S[q + 1] - S[q])
            mean = (S[q + 1] + S[q]) / 2
            ampl_mean.append((ampl, mean))
    return ampl_mean




# --------------------------------------------------------------------------------}
# --- Unittests
# --------------------------------------------------------------------------------{
import unittest

class TestFatigue(unittest.TestCase):

    def test_leq_1hz(self):
        """Simple test of wetb.fatigue.eq_load using a sine
        signal.
        """
        amplitude = 1
        m = 1
        point_per_deg = 100

        for amplitude in [1,2,3]:
            peak2peak = amplitude * 2
            # sine signal with 10 periods (20 peaks)
            nr_periods = 10
            time = np.linspace(0, nr_periods*2*np.pi, point_per_deg*180)
            neq = time[-1]
            # mean value of the signal shouldn't matter
            signal = amplitude * np.sin(time) + 5
            r_eq_1hz = eq_load(signal, no_bins=1, m=m, neq=neq)[0]
            r_eq_1hz_expected = ((2*nr_periods*amplitude**m)/neq)**(1/m)
            np.testing.assert_allclose(r_eq_1hz, r_eq_1hz_expected)

            # sine signal with 20 periods (40 peaks)
            nr_periods = 20
            time = np.linspace(0, nr_periods*2*np.pi, point_per_deg*180)
            neq = time[-1]
            # mean value of the signal shouldn't matter
            signal = amplitude * np.sin(time) + 9
            r_eq_1hz2 = eq_load(signal, no_bins=1, m=m, neq=neq)[0]
            r_eq_1hz_expected2 = ((2*nr_periods*amplitude**m)/neq)**(1/m)
            np.testing.assert_allclose(r_eq_1hz2, r_eq_1hz_expected2)

            # 1hz equivalent should be independent of the length of the signal
            np.testing.assert_allclose(r_eq_1hz, r_eq_1hz2)

    def test_rainflow_combi(self):
        # Signal with two frequencies and amplitudes
        amplitude = 1
        # peak2peak = amplitude * 2
        m = 1
        point_per_deg = 100

        nr_periods = 10
        time = np.linspace(0, nr_periods*2*np.pi, point_per_deg*180)

        signal = (amplitude*np.sin(time)) + 5 + (amplitude*0.2*np.cos(5*time))
        cycles, ampl_bin_mean, ampl_edges, mean_bin_mean, mean_edges = \
            cycle_matrix(signal, ampl_bins=10, mean_bins=5)

        cycles.sum()



    def test_astm1(self):

        signal = np.array([-2.0, 0.0, 1.0, 0.0, -3.0, 0.0, 5.0, 0.0, -1.0, 0.0, 3.0, 0.0, -4.0, 0.0, 4.0, 0.0, -2.0])

        ampl, mean = rainflow_astm(signal)
        np.testing.assert_array_equal(np.histogram2d(ampl, mean, [6, 4])[0], np.array([[ 0., 1., 0., 0.],
                                                                                                           [ 1., 0., 0., 2.],
                                                                                                           [ 0., 0., 0., 0.],
                                                                                                           [ 0., 0., 0., 1.],
                                                                                                           [ 0., 0., 0., 0.],
                                                                                                           [ 0., 0., 1., 2.]]))

    def test_windap1(self):
        signal = np.array([-2.0, 0.0, 1.0, 0.0, -3.0, 0.0, 5.0, 0.0, -1.0, 0.0, 3.0, 0.0, -4.0, 0.0, 4.0, 0.0, -2.0])
        ampl, mean = rainflow_windap(signal, 18, 2)
        np.testing.assert_array_equal(np.histogram2d(ampl, mean, [6, 4])[0], np.array([[ 0., 0., 1., 0.],
                                                                                       [ 1., 0., 0., 2.],
                                                                                       [ 0., 0., 0., 0.],
                                                                                       [ 0., 0., 0., 1.],
                                                                                       [ 0., 0., 0., 0.],
                                                                                       [ 0., 0., 2., 1.]]))

    def test_eq_load_basic(self):
        import numpy.testing
        signal1 = np.array([-2.0, 0.0, 1.0, 0.0, -3.0, 0.0, 5.0, 0.0, -1.0, 0.0, 3.0, 0.0, -4.0, 0.0, 4.0, 0.0, -2.0])
        try:
            M1=eq_load(signal1, no_bins=50, neq=[1, 17], m=[3, 4, 6], rainflow_func=rainflow_windap)
            doTest=True
        except FloatingPointError as e:
            doTest=False
            print('>>> Floating point error')
        M1_ref=np.array([[10.348414123746581, 9.635653414943068, 9.122399471334054], [4.024613313976801, 4.745357541147315, 5.68897815218057]])
        #M1_ref=np.array([[10.311095426959747, 9.5942535021382174, 9.0789213365013932],[4.010099657859783, 4.7249689509841746, 5.6618639965313005]])
        numpy.testing.assert_almost_equal(M1,M1_ref,decimal=5)
        #signal2 = signal1 * 1.1
        #         print (eq_load(signal1, no_bins=50, neq=17, rainflow_func=rainflow_windap))
        #         print (eq_load(signal1, no_bins=50, neq=17, rainflow_func=rainflow_astm))
        #         # equivalent load for default wohler slopes
        #         # Cycle matrix with 4 amplitude bins and 4 mean value bins
        #         print (cycle_matrix(signal1, 4, 4, rainflow_func=rainflow_windap))
        #         print (cycle_matrix(signal1, 4, 4, rainflow_func=rainflow_astm))
        #         # Cycle matrix where signal1 and signal2 contributes with 50% each
        #         print (cycle_matrix([(.5, signal1), (.5, signal2)], 4, 8, rainflow_func=rainflow_astm))





if __name__ == '__main__':
    unittest.main()

