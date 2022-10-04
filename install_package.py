import pip
from sys import argv

def install(package):
    if hasattr(pip, 'main'):
        pip.main(['install', package])
    else:
        pip._internal.main(['install', package])

if __name__ == '__main__':
    package = argv[1]
    # package = argv[1]
    install(package)