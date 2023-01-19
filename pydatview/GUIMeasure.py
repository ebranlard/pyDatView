import numpy as np


class GUIMeasure:
    def __init__(self, index, color):
        # Main data
        self.index = index
        self.color = color
        self.x_target = None # x closest in data where click was done
        self.y_target = None # y closest in data where click was done
        # Plot data
        self.points = []    # Intersection points
        self.lines  = []    # vertical lines (per ax)
        self.annotations = []

    def clear(self):
        self.x_target=None
        self.y_target=None
        self.clearPlot()

    def clearPlot(self):
        """ Remove points, vertical lines and annotation from plot"""
        self.clearPointLines()
        self.clearAnnotations()

    def clearAnnotations(self):
        try:
            [a.remove() for a in self.annotations]
        except (ValueError,TypeError,AttributeError):
            pass
        self.annotations = []

    def clearPointLines(self):
        """ Remove points, vertical lines"""
        try:
            [p.remove() for p in self.points]
        except (ValueError,TypeError,AttributeError):
            pass
        try:
            [l.remove() for l in self.lines]
        except (ValueError,TypeError,AttributeError):
            pass
        self.points= []
        self.lines= []

    def get_xydata(self):
        if self.x_target is None or self.y_target is None:
            return None, None
        else:
            return (self.x_target, self.y_target)

    def set(self, axes, ax, x, y, PD):
        """ 
        - x,y : point where the user clicked (will likely be slightly off plotdata)
        """
        self.clearPlot()
        # Point closest to user click location
        x_closest, y_closest, pd_closest = self.find_closest_point(x, y, ax)
        self.x_target = x_closest
        self.y_target = y_closest
        self.pd_closest = pd_closest

        # Plot measure where the user clicked (only for the axis that the user chose)
        # - plot intersection point, vertical line, and annotation
        self.plot(axes, PD)

    def compute(self, PD):
        for ipd, pd in enumerate(PD):
            if pd !=self.pd_closest:
                XY = np.array([pd.x, pd.y]).transpose()
                try:
                    xc, yc = find_closestX(XY, self.x_target)
                    pd.xyMeas[self.index-1] = (xc, yc)
                except:
                    print('[FAIL] GUIMeasure: failed to compute closest point')
                    xc, yc = np.nan, np.nan
            else:
                # Already computed
                xc, yc = self.x_target, self.y_target
                pd.xyMeas[self.index-1] = (xc, yc)

    def plotAnnotation(self, ax, xc, yc):
        #self.clearAnnotation()
        sAnnotation = '{0}: ({1}, {2})'.format(self.index, formatValue(xc), formatValue(yc))
        bbox_args = dict(boxstyle='round', fc='0.9', alpha=0.75)
        annotation = ax.annotate(sAnnotation, (xc, yc), xytext=(5, -2), textcoords='offset points', color=self.color, bbox=bbox_args)
        self.annotations.append(annotation)

    def plotPoint(self, ax, xc, yc, ms=3):
        """ plot point at intersection"""
        Mark = ['o','d','^','s']
        #i = np.random.randint(0,4)
        i=0
        point = ax.plot(xc, yc, color=self.color, marker=Mark[i], markersize=ms)[0]
        self.points.append(point)

    def plotLine(self, ax):
        """ plot vertical line across axis"""
        line = ax.axvline(x=self.x_target, color=self.color, linewidth=0.5)
        self.lines.append(line)

    def plot(self, axes, PD):
        """ 
        Given an axis, 
         - find intersection point  
              - closest to our "target" x when matchY is False
              - or closest to "target" (x,y) point when matchY is True
         - plot intersection point, vertical line
        """
        if self.x_target is None:
            return
        if PD is not None:
            self.compute(PD)
        # Clear data
        self.clearAnnotations() # Adapt if not wanted
        self.clearPointLines()

        # Find interesction points and plot points
        for iax, ax in enumerate(axes):
            for pd in ax.PD:
                if pd !=self.pd_closest:
                    xc, yc = pd.xyMeas[self.index-1]
                    self.plotPoint(ax, xc, yc, ms=3)
                    self.plotAnnotation(ax, xc, yc) # NOTE Comment if unwanted
                else:
                    #xc, yc = pd.xyMeas[self.index-1]
                    xc, yc = self.x_target, self.y_target
                    self.plotPoint(ax, xc, yc, ms=6)
                    self.plotAnnotation(ax, xc, yc)

        # Plot lines
        for iax, ax in enumerate(axes):
            self.plotLine(ax)

        # Store as target if there is only one plot and one ax (important for "dx dy")
        if PD is not None:
            if len(axes)==1 and len(PD)==1:
                self.x_target = xc
                self.y_target = yc
                # self.plotAnnotation(axes[0], xc, yc)


    def find_closest_point(self, xt, yt, ax):
        """ 
        Find closest point to target across all plotdata in a given ax
        """
        # Compute axis diagonal
        try:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            rdist_min = np.sqrt((xlim[1]-xlim[0])**2 + (ylim[1]-ylim[0])**2)
        except:
            print('[FAIL] GUIMeasure: Computing axis diagonal failed')
            rdist_min = 1e9

        # --- Find closest intersection point
        x_closest = xt
        y_closest = yt
        pd_closest= None
        for pd in ax.PD:
            XY = np.array([pd.x, pd.y]).transpose()
            try:
                x, y = find_closest(XY, [xt, yt], xlim, ylim)
                rdist = abs(x - xt) + abs(y - yt)
                if rdist < rdist_min:
                    rdist_min = rdist
                    x_closest = x
                    y_closest = y
                    pd_closest = pd
            except (TypeError,ValueError):
                # Fails when x/y data are dates or strings 
                print('[FAIL] GUIMeasure: find_closest failed on some data')
        return x_closest, y_closest, pd_closest


    def sDeltaX(self, meas2):
        try:
            dx = self.x_target - meas2.x_target
            return 'dx = ' + formatValue(dx)
        except:
            return ''

    def sDeltaY(self, meas2):
        try:
            dy = self.y_target - meas2.y_target
            return 'dy = ' + formatValue(dy)
        except:
            return ''




def formatValue(value):
    try:
        if abs(value) < 1000 and abs(value) > 1e-4:
            s = '{:.4f}'.format(value)
        else:
            s = '{:.3e}'.format(value)
    except TypeError:
        s = ''
    return s


def find_closestX(XY, x_target):
    """ return x,y values closest to a given x value """
    i = np.argmin(np.abs(XY[:,0]-x_target))
    return XY[i,:]

def find_closest(XY, point, xlim=None, ylim=None):
    """Return closest point(s), using norm2 distance 
    if xlim and ylim is provided, these are used to make the data non dimensional.
    """
    # NOTE: this will fail for datetime
    if xlim is not None:
        x_scale = (xlim[1]-xlim[0])**2
        y_scale = (ylim[1]-ylim[0])**2
    else:
        x_scale = 1
        y_scale = 1

    norm2 = ((XY[:,0]-point[0])**2)/x_scale + ((XY[:,1]-point[1])**2)/y_scale
    ind = np.argmin(norm2, axis=0)
    return XY[ind,:]

    # --- Old method
    ## By default return closest single point.
    ## Set single=False to find up to two y-values on
    ## one x-position, where index needs to have
    ## min. discontinuity of 1% of number of samples
    ## and y-values need to differ at least by 5% of FS.
    ##ind = np.argsort(np.abs(XY - point), axis=0) # TODO use norm instead of abs
    #ind = np.argsort(norm2, axis=0)
    #closest = XY[ind[0, 0]]

    #N = 5
    #closest_Nind = ind[0:N-1]
    #diff = np.diff(closest_Nind[:, 0])
    #discont_ind = [i for i, x in enumerate(diff) if abs(x) > (len(XY) / 100)]
    #for di in discont_ind:
    #    y = XY[closest_Nind[di+1, 0]][1]
    #    if abs(closest[1] - y) > (max(XY[:, 1]) / 20):
    #        closest = np.vstack([closest, XY[closest_Nind[di+1, 0]]])
    #        break
    #if closest.ndim == 2:
    #    # For multiple y-candidates find closest on y-direction:
    #    ind_y = np.argsort(abs(closest[:, 1] - point[1]))
    #    closest = closest[ind_y, :]
    #if closest.ndim == 1 or single is False:
    #    return closest
    #else:
    #    return closest[0, :]
