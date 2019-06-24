import os

_version_path = os.path.join(os.path.dirname(__file__), 'version.txt')

VERSION = open(_version_path).read().rstrip() #rstrip() removes newlines


try:
    import semver
except ImportError:
    pass
else:
    VERSION_INFO = semver.parse(VERSION)

