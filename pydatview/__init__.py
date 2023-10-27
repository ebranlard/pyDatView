__all__ = ['show', 'show_sys_args']

# defining main function here, to avoid import of pydatview and wx of some unittests
def show(*args,**kwargs):
    from pydatview.main import showApp
    showApp(*args,**kwargs)

def show_sys_args():
    import sys
    if len(sys.argv)>1:
        show(filenames=sys.argv[1:])
    else:
        show()

