from .file import WrongFormatError

def isRightFormat(fileformat, filename, **kwargs):
    """ Tries to open a file, return true and the file if it succeeds """
    #raise NotImplementedError("Method must be implemented in the subclass")
    try:
        F=fileformat.constructor(filename=filename, **kwargs)
        return True,F
    except MemoryError:
        raise
    except WrongFormatError:
        return False,None
    except:
        raise

class FileFormat():
    def __init__(self,fileclass=None):
        self.constructor = fileclass
        if fileclass is None:
            self.extensions = []
            self.name = ''
        else:
            self.extensions  = fileclass.defaultExtensions()
            self.name        = fileclass.formatName()


    def __repr__(self):
        return 'FileFormat object: {} ({})'.format(self.name,self.extensions[0])

