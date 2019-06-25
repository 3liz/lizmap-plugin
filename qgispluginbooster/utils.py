import re
import os
from tempfile import mkstemp
from shutil import move
import html

def replace_in_file(file_path: str, pattern: str, new: str, encoding = "utf8"):
    with open(file_path, 'r', encoding=encoding) as f:
        content = f.read()
    content = re.sub(pattern, new, content, flags=re.M)
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)


def fix_pylupdate_encoding(file_path: str):
    fh, abs_path = mkstemp()
    with os.fdopen(fh, 'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(html.unescape(line).encode('latin-1').decode('utf-8'))
    # Remove original file
    os.remove(file_path)
    # Move new file
    move(abs_path, file_path)


def touch_file(path, update_time: bool = False, create_dir: bool = True):
    basedir = os.path.dirname(path)
    if create_dir and not os.path.exists(basedir):
        os.makedirs(basedir)
    with open(path, 'a'):
        if update_time:
            os.utime(path, None)
        else:
            pass

