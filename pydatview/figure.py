import matplotlib.pyplot as plt
from matplotlib.figure import Figure

class SwappyFigure(Figure):
    """ 
    Override the "Figure" class such that "add_subplot" adds instances of SwappyAxes
    instead of plt.axes.Axes
    """
    def add_subplot(self, *args, projection='swappy', swap=False, **kwargs):
        # See matplotlib.figure.py  :  _process_projection_requirements
        # See matplotlib.projections/__init__.py    projection_registry.register
        kwargs.update({'projection':projection})
        ax =  super().add_subplot(*args, **kwargs)
        ax.setSwap(swap)
        return ax

class SwappyAxes(plt.Axes):
    """ 
    Override the "Axes" class such that when plotting the x and y axes can be swapped dynamically.
    """
    name = 'swappy'
    def __init__(self, *args, **kwargs):
        # See matplotlib.axes._base.py
        self.swap=False
        super().__init__(*args, **kwargs)

    def setSwap(self, swap):
        self.swap=swap

    def plot(self, *args, **kwargs):
        args = list(args)
        if self.swap:
            args[0], args[1] = args[1], args[0]
        return super().plot(*args, **kwargs)

    def annotate(self, text, xy, *args, **kwargs):
        if self.swap:
            xy = (xy[1], xy[0])
            if 'xytext' in  kwargs.keys():
                kwargs['xytext'] = (kwargs['xytext'][1], kwargs['xytext'][0])
        return super().annotate(text, xy, *args, **kwargs)

    
    # --------------------------------------------------------------------------------}
    # --- Methods that need a new name to avoid breaking the parent classe
    # --------------------------------------------------------------------------------{
    # NOTE: we add an underscore to these routines. Otherwise zooming/panning will fails
    def set_xlim_(self, *args, **kwargs):
        if self.swap:
            super().set_ylim(*args,**kwargs)
        else:
            super().set_xlim(*args,**kwargs)

    def set_ylim_(self, *args, **kwargs):
        if self.swap:
            super().set_xlim(*args,**kwargs)
        else:
            super().set_ylim(*args,**kwargs)

    def get_xlim_(self, *args, **kwargs):
        if self.swap:
            return super().get_ylim(*args,**kwargs)
        else:
            return super().get_xlim(*args,**kwargs)

    def get_ylim_(self, *args, **kwargs):
        if self.swap:
            return super().get_xlim(*args,**kwargs)
        else:
            return super().get_ylim(*args,**kwargs)

    def axvline_(self, x, *args, **kwargs):
        if self.swap:
            y=x
            return super().axhline(y, *args, **kwargs)
        else:
            return super().axvline(x, *args, **kwargs)

    # --------------------------------------------------------------------------------}
    # --- Simple override 
    # --------------------------------------------------------------------------------{
    def set_xlabel(self, *args, **kwargs):
        if self.swap:
            super().set_ylabel(*args,**kwargs)
        else:
            super().set_xlabel(*args,**kwargs)

    def set_ylabel(self, *args, **kwargs):
        if self.swap:
            super().set_xlabel(*args,**kwargs)
        else:
            super().set_ylabel(*args,**kwargs)

    def set_xscale(self, *args, **kwargs):
        if self.swap:
            super().set_yscale(*args,**kwargs)
        else:
            super().set_xscale(*args,**kwargs)

    def set_yscale(self, *args, **kwargs):
        if self.swap:
            super().set_xscale(*args,**kwargs)
        else:
            super().set_yscale(*args,**kwargs)

    def autoscale(self, *args, **kwargs):
        if self.swap:
            if 'axis' in kwargs.keys():
                if kwargs['axis']=='x':
                    kwargs['axis'] = 'y'
                elif kwargs['axis']=='y':
                    kwargs['axis'] = 'x'
            return super().autoscale(*args,**kwargs)
        else:
            return super().autoscale(*args,**kwargs)

# --- Register
import matplotlib.projections as proj
proj.register_projection(SwappyAxes)

if __name__ == '__main__':
    # fig = plt.figure()
    fig = SwappyFigure()
    ax = fig.add_subplot(1, 1, 1, swap=True)
    # Example data
    x_data = [1, 2, 3, 4, 5]
    y_data = [10, 8, 6, 4, 2]
    ax.plot(y_data, x_data, label='Swapped Axes')
    ax.legend()
    plt.show() # NOTE: doesn't work...
