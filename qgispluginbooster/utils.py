import re
import os


def replace_in_file(file_path: str, pattern: str, new: str, encoding = "utf8"):
    with open(file_path, 'r', encoding=encoding) as f:
        content = f.read()
    content = re.sub(pattern, new, content, flags=re.M)
    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)


def touch_file(path, update_time: bool = False, create_dir: bool = True):
    basedir = os.path.dirname(path)
    if create_dir and not os.path.exists(basedir):
        os.makedirs(basedir)
    with open(path, 'a'):
        if update_time:
            os.utime(path, None)
        else:
            pass

