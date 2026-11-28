"""Interface of a transport between the plugin and the server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from qgis.core import QgsFeedback

    from lizmap.sync.manifest import RemoteManifest

# HTTP status of a failed precondition, the file changed on the server in the meantime
HTTP_PRECONDITION_FAILED = 412


class BackendError(Exception):
    """A request to the server failed.

    :param message: Human readable message, from the server if possible.
    :param http_status: HTTP status, None for a network error.
    """

    def __init__(self, message: str, http_status: int | None = None):
        super().__init__(message)
        self.http_status = http_status

    @property
    def is_conflict(self) -> bool:
        """Tell if the file changed on the server since the manifest.

        :return: True for a failed "If-Match" or "If-None-Match" precondition.
        """
        return self.http_status == HTTP_PRECONDITION_FAILED


class BackendCanceled(BackendError):
    """The request has been canceled by the user."""

    def __init__(self):
        super().__init__("Canceled by the user")


class RemoteBackend(Protocol):
    """A directory on the server, such as a Lizmap repository.

    All paths are normalised relative paths, from the root of this directory.
    """

    def fetch_manifest(self, feedback: QgsFeedback | None = None) -> RemoteManifest:
        """Fetch the recursive listing of the directory.

        :param feedback: To cancel the request.
        :return: The manifest.
        :raises BackendError: If the request failed or the manifest is not valid.
        """
        ...

    def make_directory(self, path: str, feedback: QgsFeedback | None = None):
        """Create a directory, its parent must exist. An existing directory is not an error.

        :param path: Relative path of the directory, empty for the root directory itself.
        :param feedback: To cancel the request.
        :raises BackendError: If the directory can't be created.
        """
        ...

    def upload(
        self, local_file: Path, path: str, etag: str | None, feedback: QgsFeedback | None = None
    ) -> str | None:
        """Send a file, its parent directory must exist.

        :param local_file: The local file to send.
        :param path: Relative path on the server.
        :param etag: ETag of the file to replace, None if the file must not exist yet.
        :param feedback: To cancel the request and follow the progress.
        :return: The ETag of the new file, if given by the server.
        :raises BackendError: If the upload failed, ``is_conflict`` if the file changed in the meantime.
        """
        ...

    def download(
        self,
        path: str,
        local_file: Path,
        etag: str | None = None,
        checksum: str | None = None,
        feedback: QgsFeedback | None = None,
    ) -> str | None:
        """Fetch a file. The local file is replaced only once the download is complete and verified.

        The local file must be replaced by renaming a temporary file, never rewritten in place,
        so a hard link to the previous file, as in the local trash, keeps the previous content.

        :param path: Relative path on the server.
        :param local_file: The local file to write, its parent directory is created if needed.
        :param etag: Expected ETag, the download fails with a conflict if the file changed. None for any version.
        :param checksum: Expected SHA-256 of the content, verified before replacing the local file, if given.
        :param feedback: To cancel the request and follow the progress.
        :return: The ETag of the downloaded file, if given by the server.
        :raises BackendError: If the download failed, ``is_conflict`` if the file changed on the server.
        """
        ...

    def delete(self, path: str, etag: str | None, feedback: QgsFeedback | None = None):
        """Delete a file. A file already deleted is not an error.

        :param path: Relative path on the server.
        :param etag: Expected ETag of the file, None to delete it whatever its content.
        :param feedback: To cancel the request.
        :raises BackendError: If the deletion failed, ``is_conflict`` if the file changed in the meantime.
        """
        ...

    def delete_empty_directory(self, path: str, feedback: QgsFeedback | None = None):
        """Delete a directory, only if it's empty. A directory already deleted is not an error.

        :param path: Relative path of the directory.
        :param feedback: To cancel the request.
        :raises BackendError: If the directory is not empty or can't be deleted.
        """
        ...
