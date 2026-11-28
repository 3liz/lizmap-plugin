"""Options of the synchronisation: excluded files, files produced by the server, sizes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsSettings
from qgis.gui import QgsSpinBox
from qgis.PyQt.QtGui import QFontDatabase
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lizmap.definitions.qgis_settings import Settings
from lizmap.sync.filters import DEFAULT_EXCLUDE_PATTERNS, parse_rules
from lizmap.sync.options import SyncOptions
from lizmap.sync.pair import PairKind
from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from collections.abc import Mapping

MEGABYTE = 1024 * 1024

# Keys of the personal options, in the QGIS settings
_EXCLUDE_HIDDEN = "sync/exclude_hidden"
_MAX_SIZE = "sync/max_size_mb"
_DOWNLOAD_THRESHOLD = "sync/download_threshold_mb"
_PROTECTED = "sync/protected"


def _megabytes(value: int | None) -> int:
    """Size for a spin box.

    :param value: Size in bytes, None for no limit.
    :return: Size in megabytes, 0 for no limit.
    """
    return 0 if value is None else max(1, round(value / MEGABYTE))


def _bytes(value: int) -> int | None:
    """Size from a spin box.

    :param value: Size in megabytes, 0 for no limit.
    :return: Size in bytes, None for no limit.
    """
    return value * MEGABYTE if value > 0 else None


def load_options() -> SyncOptions:
    """Read the personal options from the QGIS settings.

    :return: The options, the default ones for the missing settings.
    """
    settings = QgsSettings()
    defaults = SyncOptions()

    def protected(kind: PairKind) -> tuple[str, ...]:
        """Read the rules of the files produced by the server.

        :param kind: The kind of pair.
        :return: The rules.
        """
        text = settings.value(Settings.key(f"{_PROTECTED}/{kind.value}"), None)
        if text is None:
            return defaults.protected(kind)
        return parse_rules(str(text))[0]

    return SyncOptions(
        exclude_hidden=settings.value(Settings.key(_EXCLUDE_HIDDEN), defaults.exclude_hidden, bool),
        max_size=_bytes(settings.value(Settings.key(_MAX_SIZE), _megabytes(defaults.max_size), int)),
        download_threshold=_bytes(
            settings.value(Settings.key(_DOWNLOAD_THRESHOLD), _megabytes(defaults.download_threshold), int)
        ),
        protected_repository=protected(PairKind.Repository),
        protected_shared_media=protected(PairKind.SharedMedia),
    )


def save_options(options: SyncOptions):
    """Write the personal options in the QGIS settings.

    :param options: The options.
    """
    settings = QgsSettings()
    settings.setValue(Settings.key(_EXCLUDE_HIDDEN), options.exclude_hidden)
    settings.setValue(Settings.key(_MAX_SIZE), _megabytes(options.max_size))
    settings.setValue(Settings.key(_DOWNLOAD_THRESHOLD), _megabytes(options.download_threshold))
    for kind in PairKind:
        settings.setValue(Settings.key(f"{_PROTECTED}/{kind.value}"), "\n".join(options.protected(kind)))


def default_rules_text() -> str:
    """Default content of the excluded files, with comments explaining the syntax.

    :return: The text.
    """
    comments = [
        tr("Files and directories which are not synchronised, one rule per line."),
        tr("The lines starting with # are comments. Examples:"),
        "  *.bak          " + tr('files ending with ".bak", in all directories'),
        "  drafts         " + tr('files or directories named "drafts", in all directories'),
        "  drafts/        " + tr('only the directories named "drafts"'),
        "  /exports/      " + tr('only the "exports" directory at the root'),
        "  data/*.csv     " + tr('the CSV files of the "data" directory at the root'),
        "  **/old/*.tif   " + tr('the TIF files of all directories named "old"'),
    ]
    lines = [f"# {comment}" for comment in comments]
    return "\n".join([*lines, "", *DEFAULT_EXCLUDE_PATTERNS]) + "\n"


def _text_editor(text: str) -> QPlainTextEdit:
    """Build an editor of rules, with a fixed width font.

    :param text: The initial text.
    :return: The editor.
    """
    editor = QPlainTextEdit()
    editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    editor.setPlainText(text)
    return editor


class SyncOptionsDialog(QDialog):
    """Edit the options of the synchronisation.

    :param parent: Parent widget.
    :param options: The current personal options.
    :param rules: For each synchronised directory: its label and the text of its excluded files,
        None for the default rules.
    """

    def __init__(
        self,
        parent: QWidget | None,
        options: SyncOptions,
        rules: Mapping[PairKind, tuple[str, str | None]],
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("Options of the synchronisation"))
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)

        # Excluded files, one editor by directory
        group = QGroupBox(tr("Excluded files"))
        group_layout = QVBoxLayout(group)
        help_label = QLabel(
            tr(
                "These files are never synchronised. The rules of a directory are shared with the other "
                "users synchronising the same directory."
            )
        )
        help_label.setWordWrap(True)
        group_layout.addWidget(help_label)
        self.rules_tabs = QTabWidget()
        self.rules_editors: dict[PairKind, QPlainTextEdit] = {}
        self.original_rules: dict[PairKind, str] = {}
        for kind, (label, text) in rules.items():
            original = text if text is not None else default_rules_text()
            self.original_rules[kind] = original
            editor = _text_editor(original)
            editor.setMinimumHeight(220)
            editor.textChanged.connect(self._validate)
            self.rules_editors[kind] = editor
            self.rules_tabs.addTab(editor, label)
        group_layout.addWidget(self.rules_tabs)
        self.invalid_label = QLabel()
        self.invalid_label.setWordWrap(True)
        self.invalid_label.setStyleSheet("color: #c62828")
        group_layout.addWidget(self.invalid_label)

        form = QFormLayout()
        self.exclude_hidden = QCheckBox(tr('Exclude the hidden files and directories, starting with a "."'))
        form.addRow(self.exclude_hidden)
        self.max_size = QgsSpinBox()
        self.max_size.setRange(0, 1_000_000)
        self.max_size.setSuffix(" " + tr("MB"))
        self.max_size.setSpecialValueText(tr("No limit"))
        self.max_size.setClearValue(0)
        form.addRow(tr("Exclude the files bigger than"), self.max_size)
        group_layout.addLayout(form)
        # The excluded files take most of the height
        layout.addWidget(group, 1)

        # Files produced by the server
        group = QGroupBox(tr("Files produced by the server"))
        group_layout = QVBoxLayout(group)
        help_label = QLabel(
            tr(
                "Files such as the files sent with the web forms, with the same rules as above. "
                "They are never deleted nor overwritten on the server by the default choices and by the "
                "buttons acting on all files, only by a choice made file by file."
            )
        )
        help_label.setWordWrap(True)
        group_layout.addWidget(help_label)
        self.protected_tabs = QTabWidget()
        self.protected_editors: dict[PairKind, QPlainTextEdit] = {}
        for kind, (label, _text) in rules.items():
            editor = _text_editor("")
            editor.setMaximumHeight(80)
            editor.textChanged.connect(self._validate)
            self.protected_editors[kind] = editor
            self.protected_tabs.addTab(editor, label)
        self.protected_tabs.setMaximumHeight(120)
        group_layout.addWidget(self.protected_tabs)
        layout.addWidget(group)

        # Downloads
        form = QFormLayout()
        self.download_threshold = QgsSpinBox()
        self.download_threshold.setRange(0, 1_000_000)
        self.download_threshold.setSuffix(" " + tr("MB"))
        self.download_threshold.setSpecialValueText(tr("No limit"))
        self.download_threshold.setClearValue(0)
        form.addRow(tr("By default, do not download the files bigger than"), self.download_threshold)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(buttons)

        self.set_options(options)

    def set_options(self, options: SyncOptions):
        """Display personal options.

        :param options: The options.
        """
        self.exclude_hidden.setChecked(options.exclude_hidden)
        self.max_size.setValue(_megabytes(options.max_size))
        self.download_threshold.setValue(_megabytes(options.download_threshold))
        for kind, editor in self.protected_editors.items():
            editor.setPlainText("\n".join(options.protected(kind)))
        self._validate()

    def restore_defaults(self):
        """Display the default options and the default excluded files."""
        self.set_options(SyncOptions())
        for editor in self.rules_editors.values():
            editor.setPlainText(default_rules_text())

    def _validate(self):
        """Display the lines which are not supported."""
        invalid = []
        for editor in (*self.rules_editors.values(), *self.protected_editors.values()):
            invalid.extend(parse_rules(editor.toPlainText())[1])
        if invalid:
            self.invalid_label.setText(
                tr("These lines are not supported and ignored: {}").format(", ".join(invalid))
            )
        else:
            self.invalid_label.setText("")

    def options(self) -> SyncOptions:
        """Personal options chosen by the user.

        :return: The options.
        """
        protected = {
            kind: parse_rules(editor.toPlainText())[0] for kind, editor in self.protected_editors.items()
        }
        defaults = SyncOptions()
        return SyncOptions(
            exclude_hidden=self.exclude_hidden.isChecked(),
            max_size=_bytes(self.max_size.value()),
            download_threshold=_bytes(self.download_threshold.value()),
            protected_repository=protected.get(PairKind.Repository, defaults.protected_repository),
            protected_shared_media=protected.get(PairKind.SharedMedia, defaults.protected_shared_media),
        )

    def changed_rules(self) -> dict[PairKind, str]:
        """Excluded files changed by the user.

        :return: The new text, by kind of pair, only for the changed ones.
        """
        return {
            kind: editor.toPlainText()
            for kind, editor in self.rules_editors.items()
            if editor.toPlainText() != self.original_rules[kind]
        }
