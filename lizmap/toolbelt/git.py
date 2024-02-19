__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import os
import subprocess


def current_git_hash() -> str:
    """ Retrieve the current git hash number of the git repo (first 6 digit). """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git rev-parse --short=6 HEAD',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    try:
        hash_number = git_show.communicate()[0].partition('\n')[0]
    except IndexError:
        # Reported on redmine
        # Was-it due to Python 3.7.0 ?
        # IndexError: list index out of range
        hash_number = ''

    if hash_number == '':
        hash_number = 'unknown'
    return hash_number


def has_git() -> bool:
    """ Using Git command, trying to know if we are in a git directory. """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git rev-parse --git-dir',
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    try:
        output = git_show.communicate()[0].partition('\n')[0]
    except IndexError:
        # Reported on redmine
        # Was-it due to Python 3.7.0 ?
        # IndexError: list index out of range
        output = ''

    return output != ''


def next_git_tag():
    """ Using Git command, trying to guess the next tag. """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    git_show = subprocess.Popen(
        'git describe --tags $(git rev-list --tags --max-count=1)',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=repo_dir,
        universal_newlines=True,
        encoding='utf8'
    )
    try:
        tag = git_show.communicate()[0].partition('\n')[0]
    except IndexError:
        # Reported on redmine
        # Was-it due to Python 3.7.0 ?
        # IndexError: list index out of range
        tag = ''

    if not tag:
        return 'next'
    versions = tag.split('.')
    try:
        text = '{}.{}.{}-alpha'.format(versions[0], versions[1], int(versions[2]) + 1)
        return text
    except ValueError:
        # 4.0.0-beta.1 can not be cast to int
        return 'next'
