
from weio import userFileClasses

UserClasses, UserPaths, UserModules, UserModuleNames, errors = userFileClasses()
UserClassNames = [cls.__name__ for cls in UserClasses]

for mod_name, mod, cls, cls_name in zip(UserModuleNames, UserModules, UserClasses, UserClassNames): 
    globals()[cls_name] = cls
