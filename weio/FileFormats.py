
class FileFormat():
    def __init__(self,fileclass):
        self.constructor = fileclass
        self.extensions  = fileclass.defaultExtensions()
        self.name        = fileclass.formatName()
        self.isValid     = fileclass.isRightFormat

    def __repr__(self):
        return 'Format: {} ({})'.format(self.name,self.extensions[0])

