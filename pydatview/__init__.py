__all__ = ['show']

# defining main function here, to avoid import of pydatview and wx of some unittests
def show(*args,**kwargs):
    from pydatview.main import showApp
    showApp(*args,**kwargs)


