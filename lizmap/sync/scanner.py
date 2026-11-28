"""Scan of the local directory."""

from __future__ import annotations

import hashlib
import os
import unicodedata

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from lizmap.sync.filters import INTERNAL_PREFIX
from lizmap.sync.model import LocalEntry
from lizmap.sync.paths import InvalidPathError, normalize_relative_path

if TYPE_CHECKING:
    from collections.abc import Mapping

    from lizmap.sync.filters import ExcludeRules
    from lizmap.sync.model import BaseEntry

HASH_CHUNK_SIZE = 1024 * 1024


class Cancelable(Protocol):
    """Anything telling if the user canceled the task, such as a QgsFeedback."""

    def isCanceled(self) -> bool: ...


class ScanCanceled(Exception):
    """The scan has been canceled by the user."""


@dataclass
class LocalScan:
    """Result of the scan of the local directory.

    :param files: Files, by normalised relative path. Excluded files are listed, without checksum.
    :param dirs: Directories which are not excluded.
    :param errors: Files which couldn't be read, with the error message.
    """

    files: dict[str, LocalEntry] = field(default_factory=dict)
    dirs: set[str] = field(default_factory=set)
    errors: dict[str, str] = field(default_factory=dict)


def file_checksum(file_path: Path, feedback: Cancelable | None = None) -> str:
    """Compute the SHA-256 of a file.

    :param file_path: The file to read.
    :param feedback: To stop the computation if the user cancels.
    :return: The checksum in lowercase hexadecimal.
    :raises ScanCanceled: If the user canceled.
    """
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(HASH_CHUNK_SIZE):
            if feedback and feedback.isCanceled():
                raise ScanCanceled()
            digest.update(chunk)
    return digest.hexdigest()


def _cached_checksum(size: int, mtime_ns: int, base: BaseEntry | None) -> str | None:
    """Reuse the checksum of the last synchronisation if the file didn't change since.

    :param size: Current size.
    :param mtime_ns: Current modification time, in nanoseconds.
    :param base: Entry of the last synchronisation.
    :return: The previous checksum, or None if it must be computed again.
    """
    if base and base.local_size == size and base.local_mtime_ns == mtime_ns:
        return base.local_checksum
    return None


def stat_local(
    root: Path,
    path: str,
    checksum_max_size: int | None = None,
    previous: LocalEntry | None = None,
) -> LocalEntry | None:
    """Read the current state of a single local file.

    :param root: The local directory.
    :param path: Normalised relative path of the file.
    :param checksum_max_size: Files bigger than this size don't get a checksum, None for no limit.
    :param previous: A previous entry, its checksum is reused if the file didn't change.
    :return: The entry, None if the file doesn't exist.
    """
    file_path = root.joinpath(path)
    try:
        stat = file_path.stat()
    except FileNotFoundError:
        return None

    checksum = None
    if checksum_max_size is None or stat.st_size <= checksum_max_size:
        if previous and previous.size == stat.st_size and previous.mtime_ns == stat.st_mtime_ns:
            checksum = previous.checksum
        if checksum is None:
            checksum = file_checksum(file_path)

    return LocalEntry(path=path, size=stat.st_size, mtime_ns=stat.st_mtime_ns, checksum=checksum)


def scan_local(
    root: Path,
    rules: ExcludeRules,
    base: Mapping[str, BaseEntry] | None = None,
    checksum_max_size: int | None = None,
    feedback: Cancelable | None = None,
) -> LocalScan:
    """Scan recursively the local directory.

    Excluded directories are not visited. Symbolic links to directories are not followed,
    to avoid loops. A checksum is computed for files which are not excluded, not bigger than
    ``checksum_max_size``, and changed since the last synchronisation.

    :param root: The local directory to synchronise.
    :param rules: The exclusion rules.
    :param base: Entries of the last synchronisation, to reuse checksums of unchanged files.
    :param checksum_max_size: Files bigger than this size don't get a checksum, None for no limit.
    :param feedback: To stop the scan if the user cancels.
    :return: The scan result.
    :raises ScanCanceled: If the user canceled.
    """
    base = base or {}
    result = LocalScan()

    # Iterative walk, with a stack of directories, relative path "" being the root
    stack = [""]
    while stack:
        relative_dir = stack.pop()
        directory = root.joinpath(relative_dir) if relative_dir else root
        try:
            with os.scandir(directory) as iterator:
                items = list(iterator)
        except OSError as e:
            result.errors[relative_dir or "."] = str(e)
            continue

        for item in items:
            if feedback and feedback.isCanceled():
                raise ScanCanceled()

            # Files of the synchronisation itself, such as the trash, are never listed
            if item.name.startswith(INTERNAL_PREFIX):
                continue

            # Build the normalised relative path
            name = unicodedata.normalize("NFC", item.name)
            raw_path = f"{relative_dir}/{name}" if relative_dir else name
            try:
                path = normalize_relative_path(raw_path)
            except InvalidPathError as e:
                result.errors[raw_path] = str(e)
                continue

            try:
                if item.is_dir(follow_symlinks=False):
                    if rules.directory_exclusion(path) is None:
                        result.dirs.add(path)
                        stack.append(path)
                    continue

                if not item.is_file():
                    # Socket, broken link…
                    continue

                stat = item.stat()
                checksum = None
                excluded = rules.file_exclusion(path, stat.st_size) is not None
                too_big = checksum_max_size is not None and stat.st_size > checksum_max_size
                if not excluded and not too_big:
                    checksum = _cached_checksum(stat.st_size, stat.st_mtime_ns, base.get(path))
                    if checksum is None:
                        checksum = file_checksum(Path(item.path), feedback)

                result.files[path] = LocalEntry(
                    path=path, size=stat.st_size, mtime_ns=stat.st_mtime_ns, checksum=checksum
                )
            except OSError as e:
                result.errors[path] = str(e)

    return result
