"""Test the parser of the synchronisation manifest."""

import json

from pathlib import Path

import pytest

from lizmap.sync.manifest import ManifestError, parse_manifest, parse_manifest_json
from lizmap.sync.model import RemoteEntry
from lizmap.sync.paths import InvalidPathError, normalize_relative_path, parent_directories

SCHEMA = Path(__file__).parent.parent.joinpath("lizmap", "sync", "manifest.schema.json")
SHA = "0123456789abcdef" * 4


def manifest(**overrides) -> dict:
    """Build a valid manifest.

    :param overrides: Keys to replace.
    :return: The manifest.
    """
    data = {
        "version": "1.0",
        "root": "urbanism/",
        "generated_at": 1795772400,
        "checksum_algorithm": "sha256",
        "checksum_max_size": 1000,
        "dirs": ["data"],
        "files": [
            {"path": "plu.qgs", "size": 10, "mtime": 1, "etag": '"a"', "checksum": SHA.upper()},
            {"path": "data/sub/big.tif", "size": 5000, "mtime": 2, "etag": '"b"', "checksum": None},
        ],
    }
    data.update(overrides)
    return data


def test_parse_valid():
    """Test a valid manifest."""
    result = parse_manifest(manifest())
    assert result.root == "urbanism/"
    assert result.checksum_max_size == 1000
    # Parent directories are added, even if the server forgot them
    assert result.dirs == frozenset({"data", "data/sub"})
    assert result.files == {
        "plu.qgs": RemoteEntry("plu.qgs", 10, 1, '"a"', SHA),
        "data/sub/big.tif": RemoteEntry("data/sub/big.tif", 5000, 2, '"b"', None),
    }


def test_parse_root_and_minor_version():
    """Test the root directory and an unknown minor version with extra keys."""
    result = parse_manifest_json(json.dumps(manifest(version="1.7", root="", extra={"foo": 1})))
    assert result.root == ""
    assert result.version == "1.7"


def test_schema_examples():
    """Test that the examples of the JSON schema are accepted by the parser."""
    schema = json.loads(SCHEMA.read_text(encoding="utf8"))
    assert schema["examples"]
    for example in schema["examples"]:
        parse_manifest(example)


@pytest.mark.parametrize(
    "overrides",
    [
        {"version": "2.0"},
        {"version": 1},
        {"root": "urbanism"},
        {"root": "/urbanism/"},
        {"generated_at": -1},
        {"generated_at": True},
        {"checksum_algorithm": "md5"},
        {"checksum_max_size": "big"},
        {"dirs": "data"},
        {"dirs": ["../data"]},
        {"files": {}},
        {"files": [{"path": "a", "size": 1, "mtime": 1, "etag": '"a"'}]},
        {"files": [{"path": "a", "size": 1, "mtime": 1, "etag": "", "checksum": None}]},
        {"files": [{"path": "a", "size": 1.5, "mtime": 1, "etag": '"a"', "checksum": None}]},
        {"files": [{"path": "a", "size": 1, "mtime": 1, "etag": '"a"', "checksum": "abc"}]},
        {"files": [{"path": "../a", "size": 1, "mtime": 1, "etag": '"a"', "checksum": None}]},
        {"files": [{"path": "a", "size": 1, "mtime": 1, "etag": '"a"', "checksum": None}] * 2},
        {"dirs": ["a"], "files": [{"path": "a", "size": 1, "mtime": 1, "etag": '"a"', "checksum": None}]},
    ],
)
def test_parse_invalid(overrides):
    """Test invalid manifests."""
    with pytest.raises(ManifestError):
        parse_manifest(manifest(**overrides))


def test_parse_invalid_json():
    """Test a content which is not JSON."""
    with pytest.raises(ManifestError):
        parse_manifest_json("<html>Error 500</html>")
    with pytest.raises(ManifestError):
        parse_manifest_json("[]")


def test_normalize_relative_path():
    """Test the normalisation of relative paths."""
    # NFD, as on macOS, to NFC
    assert normalize_relative_path("me\u0301dia/e\u0301te\u0301.png") == "m\u00e9dia/\u00e9t\u00e9.png"
    assert normalize_relative_path("media/") == "media"
    for path in ("", "/a", "a//b", "a/./b", "../a", "a/..", "a\\b", "C:/a", "a\x00b"):
        with pytest.raises(InvalidPathError):
            normalize_relative_path(path)


def test_parent_directories():
    """Test the list of parent directories."""
    assert parent_directories("a/b/c.txt") == ["a", "a/b"]
    assert parent_directories("c.txt") == []
