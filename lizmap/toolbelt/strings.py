__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import random
import string
import unicodedata

from pathlib import Path


def unaccent(a_string: str) -> str:
    """ Return the unaccentuated string. """
    return ''.join(
        c for c in unicodedata.normalize('NFD', a_string) if unicodedata.category(c) != 'Mn')


def human_size(byte_size, units=None):
    """ Returns a human-readable string representation of bytes """
    byte_size = int(byte_size)
    if not units:
        units = [' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    return str(byte_size) + " " + units[0] if byte_size < 1024 else human_size(byte_size >> 10, units[1:])


def random_string(length: int = 5) -> str:
    """ Generate a random string with the given length. """
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def path_to_url(file_path: Path) -> str:
    """ Transform a file path to a URL. """
    # TODO Use urllib.request.pathname2url
    # Quick hack
    return str(file_path).replace('\\', '/')


def format_version_integer(version_string: str) -> str:
    """Transform version string to integers to allow comparing versions.

    Transform "0.1.2" into "000102"
    Transform "10.9.12" into "100912"
    """
    if version_string in ('master', 'dev'):
        return '000000'

    version_string = version_string.strip()

    output = ""

    for a in version_string.split("."):
        if '-' in a:
            a = a.split('-')[0]
        output += str(a.zfill(2))

    return output


def merge_strings(string_1: str, string_2: str) -> str:
    """ Merge two strings by removing the common part in between.

    'I like chocolate' and 'chocolate and banana' → 'I like chocolate and banana'
    """
    k = 0
    for i in range(1, len(string_2)):
        if string_1.endswith(string_2[:i]):
            k = i

    return string_1 + (string_2 if k is None else string_2[k:])
