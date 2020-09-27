import numpy as np


class GUIMeasure:
    def __init__(self, index, color):
        self.index = index
        self.color = color
        self.point = None
        self.line = None
        self.annotation = None
        self.clear()

    def clear(self):
        self.axis_idx = -1
        self.x = np.NaN
        self.y = np.NaN
        if self.point is not None:
            self.point.remove()
        self.point = None
        if self.line is not None:
            self.line.remove()
        self.line = None
        if self.annotation is not None:
            self.annotation.remove()
        self.annotation = None

    def set(self, axis_idx, x, y):
        self.axis_idx = axis_idx
        self.x = x
        self.y = y

    def plot(self, ax, ax_idx):
        if self.axis_idx == -1 or self.axis_idx != ax_idx:
            return
        try:
            self.point.remove()
            self.line.remove()
            self.annotation.remove()
        except AttributeError:
            pass

        # Hook annotation to closest on signal
        x_closest = self.x
        y_closest = self.y
        rdist_min = 1e9
        for line in ax.get_lines():
            # TODO: check if 'if'can be avoided by using len(PD):
            if str(line).startswith('Line2D(_line') is False:
                xy = np.array([line.get_xdata(), line.get_ydata()]).transpose()
                for (x, y) in xy:
                    rdist = abs(x - self.x) + abs(y - self.y)
                    if rdist < rdist_min:
                        rdist_min = rdist
                        x_closest = x
                        y_closest = y
        self.x = x_closest
        self.y = y_closest

        annotation = '{0}: ({1}, {2})'.format(self.index,
                                              formatValue(self.x),
                                              formatValue(self.y))
        bbox_args = dict(boxstyle='round', fc='0.9', alpha=0.75)
        self.point = ax.plot(self.x, self.y, color=self.color, marker='o',
                             markersize=1)[0]
        self.line = ax.axvline(x=self.x, color=self.color, linewidth=0.5)
        self.annotation = ax.annotate(annotation,
                                      (self.x, self.y),
                                      xytext=(5, -2),
                                      textcoords='offset points',
                                      color=self.color,
                                      bbox=bbox_args)


def formatValue(value):
    try:
        if abs(value) < 1000 and abs(value) > 1e-4:
            s = '{:.4f}'.format(value)
        else:
            s = '{:.3e}'.format(value)
    except TypeError:
        s = ''
    return s


def find_closest(matrix, vector):
    indx = np.array([np.linalg.norm(x+y) for (x, y) in matrix-vector]).argmin()
    return matrix[indx]
