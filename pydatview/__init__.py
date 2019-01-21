from __future__ import absolute_import

__all__ = ['show']

# defining main function here, to avoid import of pydatview and wx of some unittests
def show(*args,**kwargs):
    from pydatview.pydatview import showApp
    showApp(*args,**kwargs)


