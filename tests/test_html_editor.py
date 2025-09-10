"""Test HTML editor dialog.

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""

import pytest

from lizmap.widgets.html_editor import (
    QGIS_EXPRESSION_TEXT,
    HtmlEditorWidget,
    expression_from_html_to_qgis,
    expression_from_qgis_to_html,
)

from .compat import TestCase


class TestHtmlEditorWidget(TestCase):

    # It seems I can't get trumbowyg loading if it's not show in a UI ?
    @pytest.mark.xfail()
    def test_html_editor_dialog(self):
        """ Test to open, save some HTML. """
        # NOTE: Fail with error
        # "TypeError: HtmlEditorWidget.__init__() missing 1 required positional argument: 'parent'"
        html_editor = HtmlEditorWidget()
        html = "<p>Lizmap is <strong>cool</strong></p>"
        html_editor.set_html_content(html)
        self.assertEqual(html, html_editor.html_content())

    def test_regex_from_qgis_to_html(self):
        """ Test the regex about QGIS expression from QGIS to HTML. """
        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_qgis_to_html,
                '<p>Hi [% "name" %] ! You have edited [% count %] features.</p>'
            ),
            '<p>Hi [% &quot;name&quot; %] ! You have edited [% count %] features.</p>'
        )

        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_qgis_to_html,
                '<p>Hi John</p>'
            ),
            '<p>Hi John</p>'
        )

        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_qgis_to_html,
                """<p style="color:[% if("POPULATION" > 5000, 'red', 'black') %]">[% POPULATION %]</p>"""
            ),
            (
                '<p style="color:[% if(&quot;POPULATION&quot; &gt; 5000, &#x27;red&#x27;, &#x27;black&#x27;) %]">'
                '[% POPULATION %]</p>'
            )
        )

    def test_regex_from_html_to_qgis(self):
        """ Test the regex about QGIS expression from HTML to QGIS. """
        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_html_to_qgis,
                '<p>Hi [% &quot;name&quot; %] ! You have edited [% count %] features.</p>'
            ),
            '<p>Hi [% "name" %] ! You have edited [% count %] features.</p>'
        )

        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_html_to_qgis,
                '<p>Hi John</p>'
            ),
            '<p>Hi John</p>'
        )

        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_html_to_qgis,
                (
                    '<p style="color:[% if(&quot;POPULATION&quot; &gt; 5000, &#x27;red&#x27;, &#x27;black&#x27;) %]">'
                    '[% POPULATION %]</p>'
                )
            ),
            """<p style="color:[% if("POPULATION" > 5000, 'red', 'black') %]">[% POPULATION %]</p>"""
        )

    def test_regex_from_qgis_to_html_lizmap_template(self):
        """ Test the regex about QGIS expression from QGIS to HTML with Lizmap template. """
        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_qgis_to_html,
                '<p>Hi [% "name" %] ! Trace {$y1}.</p>'
            ),
            '<p>Hi [% &quot;name&quot; %] ! Trace {$y1}.</p>'
        )

    def test_regex_from_html_to_qgis_lizmap_template(self):
        """ Test the regex about QGIS expression from HTML to QGIS with Lizmap template. """
        self.assertEqual(
            QGIS_EXPRESSION_TEXT.sub(
                expression_from_html_to_qgis,
                '<p>Hi [% &quot;name&quot; %] ! Trace {$y1}.</p>'
            ),
            '<p>Hi [% "name" %] ! Trace {$y1}.</p>'
        )
