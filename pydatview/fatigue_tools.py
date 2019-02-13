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
#
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()

# import cython # TODO
import numpy as np

__all__  = ['find_extremes', 'rainflowcount', 'peak_trough','pair_range_amplitude','pair_range_from_to','pair_range_amplitude_mean']

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
    S = np.zeros(x.shape[0] + 1, dtype=np.int)

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
