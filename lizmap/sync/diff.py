"""Comparison engine of the synchronisation.

The comparison is a three-way comparison between the local files, the files on the server and
the state of the last synchronisation (the "base"):

* checksums, when available on both sides, tell if two files have the same content,
* the base tells which side changed since the last synchronisation, and if a file only on one side
  is new on this side or has been deleted on the other one.

Without checksum, the size, the local modification time and the ETag on the server are used to
detect changes. The modification time on the server can't be compared with the local one: it's the
upload time, not the modification time of the original file.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lizmap.sync.filters import ExclusionReason, match_rule
from lizmap.sync.model import (
    Direction,
    FileDiff,
    FileStatus,
    Preference,
    SyncAction,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from lizmap.sync.filters import ExcludeRules
    from lizmap.sync.model import BaseEntry, LocalEntry, RemoteEntry

# Default preference for each status, files are never deleted by default
DEFAULT_PREFERENCES: dict[FileStatus, Preference] = {
    FileStatus.NewLocal: Preference.Local,
    FileStatus.NewRemote: Preference.Remote,
    FileStatus.LocalModified: Preference.Local,
    FileStatus.RemoteModified: Preference.Remote,
    FileStatus.Different: Preference.Nothing,
    FileStatus.Unverified: Preference.Nothing,
    FileStatus.Conflict: Preference.Nothing,
    FileStatus.DeletedLocal: Preference.Nothing,
    FileStatus.DeletedRemote: Preference.Nothing,
}

# Statuses for which no action is possible
_FROZEN_STATUSES = (FileStatus.Identical, FileStatus.Excluded, FileStatus.CaseConflict)


@dataclass
class Comparison:
    """Result of a comparison.

    :param diffs: One result per file, sorted by path.
    :param stale_paths: Paths only in the base, deleted on both sides, to remove from the state.
    """

    diffs: list[FileDiff] = field(default_factory=list)
    stale_paths: list[str] = field(default_factory=list)

    def to_run(self) -> list[FileDiff]:
        """Files with an action to run.

        :return: The files having an action other than "Nothing".
        """
        return [diff for diff in self.diffs if diff.action != SyncAction.Nothing]

    def summary(self) -> dict[SyncAction, tuple[int, int]]:
        """Count the files and the bytes to transfer, by action.

        :return: For each action to run, the number of files and the number of bytes.
        """
        counts: dict[SyncAction, list[int]] = defaultdict(lambda: [0, 0])
        for diff in self.to_run():
            counts[diff.action][0] += 1
            counts[diff.action][1] += diff.transfer_size
        return {action: (values[0], values[1]) for action, values in counts.items()}

    def apply_preference(self, preference: Preference, statuses: tuple[FileStatus, ...] | None = None):
        """Choose the action of several files from a preference, for the bulk buttons.

        :param preference: The side which wins.
        :param statuses: Only change files having one of these statuses, all files if None.
        """
        for diff in self.diffs:
            if statuses is None or diff.status in statuses:
                diff.choose(resolve_action(diff, preference))

    def reset(self):
        """Restore the default action of all files."""
        for diff in self.diffs:
            diff.reset()


def _same_content(local: LocalEntry, remote: RemoteEntry) -> bool | None:
    """Tell if a local file and a remote file have the same content.

    :param local: The local entry.
    :param remote: The remote entry.
    :return: True or False if it can be decided, None if both have the same size without checksum.
    """
    if local.size != remote.size:
        return False
    if local.checksum and remote.checksum:
        return local.checksum == remote.checksum
    return None


def _local_changed(local: LocalEntry, base: BaseEntry) -> bool:
    """Tell if the local file changed since the last synchronisation.

    The checksum is preferred, so a file only "touched" is not considered as changed.

    :param local: The local entry.
    :param base: The entry of the last synchronisation.
    :return: True if the local file changed.
    """
    if local.size != base.local_size:
        return True
    if local.checksum and base.local_checksum:
        return local.checksum != base.local_checksum
    return local.mtime_ns != base.local_mtime_ns


def _remote_changed(remote: RemoteEntry, base: BaseEntry) -> bool:
    """Tell if the remote file changed since the last synchronisation.

    :param remote: The remote entry.
    :param base: The entry of the last synchronisation.
    :return: True if the remote file changed.
    """
    if remote.size != base.remote_size:
        return True
    if remote.checksum and base.remote_checksum:
        return remote.checksum != base.remote_checksum
    return remote.etag != base.remote_etag


def classify(local: LocalEntry | None, remote: RemoteEntry | None, base: BaseEntry | None) -> FileStatus:
    """Compute the status of a file, without taking care of the filters.

    :param local: The local entry, if the file exists locally.
    :param remote: The remote entry, if the file exists on the server.
    :param base: The entry of the last synchronisation, if any.
    :return: The status of the file.
    :raises ValueError: If the file exists neither locally nor on the server.
    """
    # On both sides
    if local and remote:
        same = _same_content(local, remote)
        if same:
            return FileStatus.Identical
        if base is None:
            return FileStatus.Different if same is False else FileStatus.Unverified

        local_changed = _local_changed(local, base)
        remote_changed = _remote_changed(remote, base)
        if local_changed and remote_changed:
            return FileStatus.Conflict
        if local_changed:
            return FileStatus.LocalModified
        if remote_changed:
            return FileStatus.RemoteModified
        # Unchanged on both sides since a synchronisation, unless checksums say otherwise
        return FileStatus.Identical if same is None else FileStatus.Different

    # Only locally
    if local:
        if base is None:
            return FileStatus.NewLocal
        # Modified locally but deleted on the server
        if _local_changed(local, base):
            return FileStatus.Conflict
        return FileStatus.DeletedRemote

    # Only on the server
    if remote:
        if base is None:
            return FileStatus.NewRemote
        # Modified on the server but deleted locally
        if _remote_changed(remote, base):
            return FileStatus.Conflict
        return FileStatus.DeletedLocal

    raise ValueError("The file must exist at least on one side.")


# Actions forbidden by a direction
_FORBIDDEN_ACTIONS = {
    Direction.TwoWay: (),
    Direction.PullOnly: (SyncAction.Upload, SyncAction.DeleteRemote),
    Direction.PushOnly: (SyncAction.Download, SyncAction.DeleteLocal),
}


def allowed_actions(
    status: FileStatus,
    local: LocalEntry | None,
    remote: RemoteEntry | None,
    direction: Direction = Direction.TwoWay,
) -> tuple[SyncAction, ...]:
    """List the actions which can be chosen for a file.

    :param status: Status of the file.
    :param local: The local entry, if the file exists locally.
    :param remote: The remote entry, if the file exists on the server.
    :param direction: Allowed direction of the transfers.
    :return: The allowed actions, "Nothing" first.
    """
    if status in _FROZEN_STATUSES:
        return (SyncAction.Nothing,)
    if local and remote:
        actions: tuple[SyncAction, ...] = (SyncAction.Nothing, SyncAction.Upload, SyncAction.Download)
    elif local:
        actions = (SyncAction.Nothing, SyncAction.Upload, SyncAction.DeleteLocal)
    else:
        actions = (SyncAction.Nothing, SyncAction.Download, SyncAction.DeleteRemote)
    return tuple(action for action in actions if action not in _FORBIDDEN_ACTIONS[direction])


def resolve_action(diff: FileDiff, preference: Preference) -> SyncAction:
    """Translate a preference into an action for a file.

    :param diff: The file.
    :param preference: The side which wins.
    :return: The action, "Nothing" if the preference can't be applied to this file.
    """
    action = SyncAction.Nothing

    if preference == Preference.Local:
        # The local side wins, including a local deletion
        action = SyncAction.Upload if diff.local else SyncAction.DeleteRemote
    elif preference == Preference.Remote:
        # The server wins, including a deletion on the server
        action = SyncAction.Download if diff.remote else SyncAction.DeleteLocal
    elif preference == Preference.Newest and diff.local and diff.remote:
        # Only possible when both sides exist, the time of a deletion is unknown
        remote_mtime_ns = diff.remote.mtime * 1_000_000_000
        if diff.local.mtime_ns > remote_mtime_ns:
            action = SyncAction.Upload
        elif diff.local.mtime_ns < remote_mtime_ns:
            action = SyncAction.Download

    if action not in diff.allowed_actions:
        return SyncAction.Nothing

    # A file produced by the server is deleted or overwritten only by an explicit choice
    if diff.protected and (
        action == SyncAction.DeleteRemote or (action == SyncAction.Upload and diff.remote)
    ):
        return SyncAction.Nothing
    return action


def _case_conflicts(paths: set[str]) -> set[str]:
    """Find paths differing only by the case.

    :param paths: All the paths.
    :return: Paths having at least one other path with the same lowercase form.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        groups[path.casefold()].append(path)
    return {path for group in groups.values() if len(group) > 1 for path in group}


def _exclusion_text(rules: ExcludeRules, path: str, size: int) -> str | None:
    """Describe why a file is excluded.

    :param rules: The exclusion rules.
    :param path: Normalised relative path.
    :param size: Size in bytes.
    :return: A short description, or None if the file is not excluded.
    """
    exclusion = rules.file_exclusion(path, size)
    if exclusion is None:
        return None
    if exclusion.reason == ExclusionReason.Size:
        return f"size > {exclusion.detail}"
    return f"{exclusion.reason.value} : {exclusion.detail}"


def compare(
    local: Mapping[str, LocalEntry],
    remote: Mapping[str, RemoteEntry],
    base: Mapping[str, BaseEntry],
    rules: ExcludeRules | None = None,
    preferences: Mapping[FileStatus, Preference] | None = None,
    direction: Direction = Direction.TwoWay,
    protected_patterns: tuple[str, ...] = (),
    download_threshold: int | None = None,
) -> Comparison:
    """Compare the local files with the files on the server.

    :param local: Local files, by normalised relative path.
    :param remote: Files on the server, by normalised relative path.
    :param base: Entries of the last synchronisation, by normalised relative path.
    :param rules: Exclusion rules, nothing is excluded if None.
    :param preferences: Default preference by status, ``DEFAULT_PREFERENCES`` is used for missing ones.
    :param direction: Allowed direction of the transfers.
    :param protected_patterns: Rules of the files produced by the server, see ``FileDiff.protected``
        and the syntax in ``filters``.
    :param download_threshold: Files missing locally and bigger than this size, in bytes, are not
        downloaded by default. None for no limit.
    :return: The comparison, with the default action chosen for each file.
    """
    preferences = {**DEFAULT_PREFERENCES, **(preferences or {})}
    paths = set(local) | set(remote)
    case_conflicts = _case_conflicts(paths)

    comparison = Comparison()
    comparison.stale_paths = sorted(set(base) - paths)

    for path in sorted(paths):
        local_entry = local.get(path)
        remote_entry = remote.get(path)
        base_entry = base.get(path)

        # Filters first, an excluded file is never transferred whatever its status
        size = local_entry.size if local_entry else remote_entry.size if remote_entry else 0
        exclusion = _exclusion_text(rules, path, size) if rules else None
        if exclusion:
            status = FileStatus.Excluded
        elif path in case_conflicts:
            status = FileStatus.CaseConflict
        else:
            status = classify(local_entry, remote_entry, base_entry)

        diff = FileDiff(
            path=path,
            status=status,
            local=local_entry,
            remote=remote_entry,
            base=base_entry,
            allowed_actions=allowed_actions(status, local_entry, remote_entry, direction),
            exclusion=exclusion,
            protected=any(match_rule(path, pattern) for pattern in protected_patterns),
        )

        # The default action depends on the allowed actions, so it's set once the diff is built
        preference = preferences.get(status, Preference.Nothing)
        too_big = (
            status == FileStatus.NewRemote
            and download_threshold is not None
            and remote_entry is not None
            and remote_entry.size > download_threshold
        )
        diff.default_action = SyncAction.Nothing if too_big else resolve_action(diff, preference)
        diff.reset()
        comparison.diffs.append(diff)

    return comparison
