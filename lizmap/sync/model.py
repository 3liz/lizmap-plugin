"""Data model of the synchronisation: entries, statuses and actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FileStatus(Enum):
    """Status of a file after the comparison between the local directory and the server."""

    # Same content on both sides
    Identical = "identical"
    # Only local, never synchronised: missing on the server
    NewLocal = "new_local"
    # Only on the server, never synchronised: missing locally
    NewRemote = "new_remote"
    # Modified locally since the last synchronisation, unchanged on the server
    LocalModified = "local_modified"
    # Modified on the server since the last synchronisation, unchanged locally
    RemoteModified = "remote_modified"
    # On both sides, never synchronised, the content is different
    Different = "different"
    # On both sides, never synchronised, same size but the content cannot be verified
    Unverified = "unverified"
    # Modified on both sides, or modified on one side and deleted on the other one
    Conflict = "conflict"
    # Deleted locally since the last synchronisation, unchanged on the server
    DeletedLocal = "deleted_local"
    # Deleted on the server since the last synchronisation, unchanged locally
    DeletedRemote = "deleted_remote"
    # Excluded by the filters
    Excluded = "excluded"
    # Several paths differing only by the case, they can't live on a case-insensitive file system
    CaseConflict = "case_conflict"


class SyncAction(Enum):
    """Action to run on a file."""

    Nothing = "nothing"
    Upload = "upload"
    Download = "download"
    DeleteRemote = "delete_remote"
    DeleteLocal = "delete_local"


class Preference(Enum):
    """Which side wins, used for the default actions and the bulk buttons."""

    # No action
    Nothing = "nothing"
    # The local side wins: upload, or delete on the server if the file is missing locally
    Local = "local"
    # The server wins: download, or delete locally if the file is missing on the server
    Remote = "remote"
    # The most recent file wins, only when the file exists on both sides
    Newest = "newest"


@dataclass(frozen=True)
class LocalEntry:
    """A file in the local directory.

    :param path: Normalised relative path.
    :param size: Size in bytes.
    :param mtime_ns: Last modification time, in nanoseconds since the epoch.
    :param checksum: SHA-256 of the content in lowercase hexadecimal, if computed.
    """

    path: str
    size: int
    mtime_ns: int
    checksum: str | None = None

    @property
    def mtime(self) -> float:
        """Last modification time.

        :return: Seconds since the epoch.
        """
        return self.mtime_ns / 1_000_000_000


@dataclass(frozen=True)
class RemoteEntry:
    """A file on the server.

    :param path: Normalised relative path.
    :param size: Size in bytes.
    :param mtime: Last modification time on the server, in seconds since the epoch.
        It's the upload time, not the modification time of the original file.
    :param etag: Value of the HTTP ETag header, quotes included, usable with "If-Match".
    :param checksum: SHA-256 of the content in lowercase hexadecimal, if provided by the server.
    """

    path: str
    size: int
    mtime: int
    etag: str
    checksum: str | None = None


@dataclass(frozen=True)
class BaseEntry:
    """State of a file just after its last synchronisation, on both sides.

    :param local_size: Local size in bytes.
    :param local_mtime_ns: Local modification time, in nanoseconds.
    :param local_checksum: Local SHA-256, if computed.
    :param remote_size: Size on the server in bytes.
    :param remote_mtime: Modification time on the server, in seconds.
    :param remote_etag: ETag on the server.
    :param remote_checksum: SHA-256 on the server, if provided.
    :param synced_at: Time of the synchronisation, in seconds since the epoch.
    """

    local_size: int
    local_mtime_ns: int
    local_checksum: str | None
    remote_size: int
    remote_mtime: int
    remote_etag: str
    remote_checksum: str | None
    synced_at: int


@dataclass
class FileDiff:
    """Result of the comparison for a single file.

    :param path: Normalised relative path.
    :param status: Status of the file.
    :param local: Local entry, if the file exists locally.
    :param remote: Remote entry, if the file exists on the server.
    :param base: Entry from the last synchronisation, if any.
    :param allowed_actions: Actions which can be chosen for this file.
    :param default_action: Action given by the preferences.
    :param exclusion: Human readable reason of the exclusion, for the "Excluded" status.
    """

    path: str
    status: FileStatus
    local: LocalEntry | None
    remote: RemoteEntry | None
    base: BaseEntry | None
    allowed_actions: tuple[SyncAction, ...]
    default_action: SyncAction = SyncAction.Nothing
    exclusion: str | None = None
    # The action chosen by the user, initialised with the default action
    action: SyncAction = field(init=False)

    def __post_init__(self):
        """Initialise the chosen action with the default action."""
        self.action = self.default_action

    def choose(self, action: SyncAction):
        """Choose the action to run.

        :param action: The new action.
        :raises ValueError: If the action is not allowed for this file.
        """
        if action not in self.allowed_actions:
            raise ValueError(f"The action '{action.value}' is not allowed for '{self.path}'.")
        self.action = action

    def reset(self):
        """Restore the default action."""
        self.action = self.default_action

    @property
    def transfer_size(self) -> int:
        """Number of bytes to transfer for the chosen action.

        :return: The local size for an upload, the remote size for a download, 0 otherwise.
        """
        if self.action == SyncAction.Upload and self.local:
            return self.local.size
        if self.action == SyncAction.Download and self.remote:
            return self.remote.size
        return 0
