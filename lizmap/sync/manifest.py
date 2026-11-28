"""Parser of the JSON manifest listing a directory on the server.

The format is described by ``manifest.schema.json``, next to this file. The validation is done
manually, the "jsonschema" package is not available in all QGIS installations.
"""

from __future__ import annotations

import json
import re

from dataclasses import dataclass
from typing import Any

from lizmap.sync.model import RemoteEntry
from lizmap.sync.paths import InvalidPathError, normalize_relative_path, parent_directories

# Major version of the manifest format supported by this client
SUPPORTED_MAJOR_VERSION = 1
SUPPORTED_CHECKSUM_ALGORITHMS = ("sha256",)

_VERSION = re.compile(r"^(\d+)\.(\d+)$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """The manifest sent by the server is not valid."""


@dataclass(frozen=True)
class RemoteManifest:
    """Recursive listing of a directory on the server.

    :param version: Version of the format, "MAJOR.MINOR".
    :param root: Listed directory, relative to the WebDAV root, with a trailing slash.
    :param generated_at: Generation time, in seconds since the epoch.
    :param checksum_algorithm: Algorithm of the checksums.
    :param checksum_max_size: Files bigger than this size don't have a checksum, None if no limit.
    :param dirs: All sub-directories, including the parents of the files.
    :param files: Files, by normalised relative path.
    """

    version: str
    root: str
    generated_at: int
    checksum_algorithm: str
    checksum_max_size: int | None
    dirs: frozenset[str]
    files: dict[str, RemoteEntry]


def _is_positive_int(value: Any) -> bool:
    """Check if a JSON value is a positive integer, booleans excluded.

    :param value: The value to check.
    :return: True if the value is a positive integer.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _positive_int(data: dict, key: str, context: str) -> int:
    """Read a mandatory positive integer.

    :param data: The JSON object.
    :param key: The key to read.
    :param context: Description of the object, for the error message.
    :return: The integer.
    :raises ManifestError: If the value is missing or not a positive integer.
    """
    value: Any = data.get(key)
    if not _is_positive_int(value):
        raise ManifestError(f"'{key}' must be a positive integer in {context}.")
    return int(value)


def _path(value: Any, context: str) -> str:
    """Read and normalise a relative path.

    :param value: The JSON value.
    :param context: Description of the object, for the error message.
    :return: The normalised path.
    :raises ManifestError: If the path is not valid.
    """
    try:
        return normalize_relative_path(value)
    except InvalidPathError as e:
        raise ManifestError(f"Invalid path in {context} : {e}") from e


def _parse_file(item: Any, index: int) -> RemoteEntry:
    """Parse a file of the manifest.

    :param item: The JSON object of the file.
    :param index: Index of the file in the list, for the error messages.
    :return: The remote entry.
    :raises ManifestError: If the file is not valid.
    """
    context = f"files[{index}]"
    if not isinstance(item, dict):
        raise ManifestError(f"{context} must be an object.")

    path = _path(item.get("path"), context)
    size = _positive_int(item, "size", context)
    mtime = _positive_int(item, "mtime", context)

    etag = item.get("etag")
    if not isinstance(etag, str) or not etag:
        raise ManifestError(f"'etag' must be a non-empty string in {context}.")

    # The checksum is optional for big files, but the key is mandatory
    if "checksum" not in item:
        raise ManifestError(f"'checksum' is missing in {context}.")
    checksum = item["checksum"]
    if checksum is not None:
        if not isinstance(checksum, str) or not _SHA256.match(checksum.lower()):
            raise ManifestError(f"'checksum' must be a SHA-256 hexadecimal string or null in {context}.")
        checksum = checksum.lower()

    return RemoteEntry(path=path, size=size, mtime=mtime, etag=etag, checksum=checksum)


def parse_manifest(data: Any) -> RemoteManifest:
    """Validate and parse a manifest, already decoded from JSON.

    Unknown properties are ignored, for the compatibility with next minor versions.
    Parent directories of the files are added to the directories, even if the server omitted them.

    :param data: The decoded JSON document.
    :return: The parsed manifest.
    :raises ManifestError: If the manifest is not valid or if the major version is not supported.
    """
    if not isinstance(data, dict):
        raise ManifestError("The manifest must be a JSON object.")

    # Version, checked first, the rest of the format may change with another major version
    version = data.get("version")
    if not isinstance(version, str):
        raise ManifestError("'version' must be a string like 'MAJOR.MINOR'.")
    match = _VERSION.match(version)
    if not match:
        raise ManifestError("'version' must be a string like 'MAJOR.MINOR'.")
    if int(match.group(1)) != SUPPORTED_MAJOR_VERSION:
        raise ManifestError(f"The manifest version '{version}' is not supported.")

    # Listed directory
    root = data.get("root")
    if not isinstance(root, str):
        raise ManifestError("'root' must be a string.")
    if root:
        if not root.endswith("/"):
            raise ManifestError("'root' must end with a '/'.")
        root = _path(root, "'root'") + "/"

    generated_at = _positive_int(data, "generated_at", "the manifest")

    # Checksums
    algorithm = data.get("checksum_algorithm")
    if algorithm not in SUPPORTED_CHECKSUM_ALGORITHMS:
        raise ManifestError(f"The checksum algorithm '{algorithm}' is not supported.")
    if "checksum_max_size" not in data:
        raise ManifestError("'checksum_max_size' is missing.")
    max_size = data["checksum_max_size"]
    if max_size is not None and not _is_positive_int(max_size):
        raise ManifestError("'checksum_max_size' must be a positive integer or null.")

    # Directories
    raw_dirs = data.get("dirs")
    if not isinstance(raw_dirs, list):
        raise ManifestError("'dirs' must be a list.")
    dirs = {_path(item, f"dirs[{i}]") for i, item in enumerate(raw_dirs)}

    # Files
    raw_files = data.get("files")
    if not isinstance(raw_files, list):
        raise ManifestError("'files' must be a list.")
    files: dict[str, RemoteEntry] = {}
    for index, item in enumerate(raw_files):
        entry = _parse_file(item, index)
        if entry.path in files:
            raise ManifestError(f"The file '{entry.path}' is listed twice.")
        files[entry.path] = entry
        # Be tolerant if the server didn't list a parent directory
        dirs.update(parent_directories(entry.path))

    # A path can't be both a file and a directory
    both = dirs.intersection(files)
    if both:
        raise ManifestError(f"'{sorted(both)[0]}' is listed as a file and as a directory.")

    return RemoteManifest(
        version=version,
        root=root,
        generated_at=generated_at,
        checksum_algorithm=algorithm,
        checksum_max_size=max_size,
        dirs=frozenset(dirs),
        files=files,
    )


def parse_manifest_json(content: str | bytes) -> RemoteManifest:
    """Decode and parse a JSON manifest.

    :param content: The body of the HTTP response.
    :return: The parsed manifest.
    :raises ManifestError: If the content is not valid JSON or not a valid manifest.
    """
    try:
        data = json.loads(content)
    except ValueError as e:
        raise ManifestError(f"The manifest is not valid JSON : {e}") from e
    return parse_manifest(data)
