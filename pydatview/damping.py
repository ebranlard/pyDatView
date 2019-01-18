import numpy as np


def indexes(y, thres=0.3, min_dist=1, thres_abs=False):
    """Peak detection routine.

    Finds the numeric index of the peaks in *y* by taking its first order difference. By using
    *thres* and *min_dist* parameters, it is possible to reduce the number of
    detected peaks. *y* must be signed.

    Parameters
    ----------
    y : ndarray (signed)
        1D amplitude data to search for peaks.
    thres : float between [0., 1.]
        Normalized threshold. Only the peaks with amplitude higher than the
        threshold will be detected.
    min_dist : int
        Minimum distance between each detected peak. The peak with the highest
        amplitude is preferred to satisfy this constraint.
    thres_abs: boolean
        If True, the thres value will be interpreted as an absolute value, instead of
        a normalized threshold.

    Returns
    -------
    ndarray
        Array containing the numeric indexes of the peaks that were detected
    """
    if isinstance(y, np.ndarray) and np.issubdtype(y.dtype, np.unsignedinteger):
        raise ValueError("y must be signed")

    if not thres_abs:
        thres = thres * (np.max(y) - np.min(y)) + np.min(y)
        
    min_dist = int(min_dist)

    # compute first order difference
    dy = np.diff(y)

    # propagate left and right values successively to fill all plateau pixels (0-value)
    zeros,=np.where(dy == 0)
    
    # check if the signal is totally flat
    if len(zeros) == len(y) - 1:
        return np.array([])

    if len(zeros):
        # compute first order difference of zero indexes
        zeros_diff = np.diff(zeros)
        # check when zeros are not chained together
        zeros_diff_not_one, = np.add(np.where(zeros_diff != 1), 1)
        # make an array of the chained zero indexes
        zero_plateaus = np.split(zeros, zeros_diff_not_one)

        # fix if leftmost value in dy is zero
        if zero_plateaus[0][0] == 0:
            dy[zero_plateaus[0]] = dy[zero_plateaus[0][-1] + 1]
            zero_plateaus.pop(0)

        # fix if rightmost value of dy is zero
        if len(zero_plateaus) and zero_plateaus[-1][-1] == len(dy) - 1:
            dy[zero_plateaus[-1]] = dy[zero_plateaus[-1][0] - 1]
            zero_plateaus.pop(-1)

        # for each chain of zero indexes
        for plateau in zero_plateaus:
            median = np.median(plateau)
            # set leftmost values to leftmost non zero values
            dy[plateau[plateau < median]] = dy[plateau[0] - 1]
            # set rightmost and middle values to rightmost non zero values
            dy[plateau[plateau >= median]] = dy[plateau[-1] + 1]

    # find the peaks by using the first order difference
    peaks = np.where((np.hstack([dy, 0.]) < 0.)
                     & (np.hstack([0., dy]) > 0.)
                     & (np.greater(y, thres)))[0]

    # handle multiple peaks, respecting the minimum distance
    if peaks.size > 1 and min_dist > 1:
        highest = peaks[np.argsort(y[peaks])][::-1]
        rem = np.ones(y.size, dtype=bool)
        rem[peaks] = False

        for peak in highest:
            if not rem[peak]:
                sl = slice(max(0, peak - min_dist), peak + min_dist + 1)
                rem[sl] = True
                rem[peak] = False

        peaks = np.arange(y.size)[~rem]

    return peaks


#indexes =indexes(x, thres=0.02/max(x), min_dist=1, thres_abs=true)
def logDecFromThreshold(x,threshold=None,bothSides=False):
    """ Detect maxima in a signal, computes the log deg based on it """
    if bothSides:
        ldPos,iTPos,stdPos,IPos = logDecFromThreshold( x, threshold=threshold)
        ldNeg,iTNeg,stdNeg,INeg = logDecFromThreshold(-x, threshold=threshold)
        return (ldPos+ldNeg)/2, (iTPos+iTNeg)/2, (stdPos+stdNeg)/2, (IPos,INeg)

    if threshold is None:
        threshold = np.mean(abs(x-np.mean(x)))/3;
    I =indexes(x, thres=threshold, min_dist=1, thres_abs=True)
    # Estimating "index" period
    iT = round(np.median(np.diff(I)));
    vn=np.arange(0,len(I)-1)+1
    # Quick And Dirty Way using one as ref and assuming all periods were found
    vDamping   = 1/vn*np.log( x[I[0]]/x[I[1:]] ) # Damping Ratios
    vLogDec    = 1/np.sqrt(1+ (2*np.pi/vDamping)**2 )
    logdec     = np.mean(vLogDec);
    std_logdec = np.std(vLogDec) ;
    return logdec,iT,std_logdec,I


def logDecFromDecay(x,t,threshold=None):
    m = np.mean(x)
    if threshold is None:
        threshold = np.mean(abs(x-m))/3;
    
    dt = t[1]-t[0] # todo signal with dt not uniform

    # Computing log decs from positive and negative side and taking the mean
    logdec,iT,std,(IPos,INeg) = logDecFromThreshold( x-m, threshold=threshold, bothSides=True)
    DampingRatio=2*np.pi*logdec/np.sqrt(1-logdec**2) # damping ratio


    # Going to time space
    T = iT*dt # Period of damped oscillations. Badly estimated due to dt resolution
#     % Better estimate of period
#     [T,~,iCross]=fGetPeriodFromZeroCrossing(x(1:IPos(end)),dt);
    fd = 1/T           
    fn = fd/np.sqrt(1-logdec**2)
    # --- Model
    # Estimating signal params 
    delta   = DampingRatio
    alpha   = delta/T    
    omega   = 2*np.pi*fd  
    # Values at a peak half way through
    i1      = IPos[int(len(IPos)/2)]   
    A1      = x[i1]                                     ;
    t1      = dt*i1                                     ;
    XX=x[i1:]-m
    ineg=i1+np.where(XX<0)[0][0]
    ipos=ineg-1
    xcross=[x[ipos],x[ineg]]-m
    icross=[ipos,ineg]
    i0 = np.interp(0,xcross,icross)
    # For phase determination, we use a precise 0-up-crossing - 
    t0=dt*i0
    phi0    = np.mod(2*np.pi- omega*t0+np.pi/2,2*np.pi)                  ;
    A = (A1-m)/(np.exp(-alpha*t1)*np.cos(omega*t1+phi0));
    x_model = A*np.exp(-alpha*t)*np.cos(omega*t+phi0)+m;
    epos   =  A*np.exp(-alpha*t)+m                   ;
    eneg   = -A*np.exp(-alpha*t)+m                  ;

    return logdec,DampingRatio,T,fn,fd,IPos,INeg,epos,eneg



if __name__ == '__main__':
    import matplotlib.pyplot as plt
    T=10;
    logdec=0.1; # log decrements (<1)
    delta=2*np.pi*logdec/np.sqrt(1-logdec**2); # damping ratio; logdec  = 1./sqrt(1+ (2*pi./delta).^2 )  ;
    alpha=delta/T
    print('logdec in:  ',logdec)
    print('alpha in :  ',alpha)
    t=np.linspace(0,30*T,1000)
    x=np.cos(2*np.pi/T*t)*np.exp(-alpha*t)+10;
    logdec,DampingRatio,T,fn,fd,IPos,INeg,epos,eneg=logDecFromDecay(x,t)
    print('logdec out: ',logdec)
    print('alpha out : ',DampingRatio/T)
    plt.plot(t,x)
    plt.plot(t[IPos],x[IPos],'o')
    plt.plot(t[INeg],x[INeg],'o')
    plt.plot(t,epos,'k--')
    plt.plot(t,eneg,'k--')
    plt.show()
