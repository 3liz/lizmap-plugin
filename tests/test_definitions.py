from lizmap.definitions.definitions import LwcVersions, ReleaseStatus

from .compat import TestCase


class TestDefinitions(TestCase):
    def test_lwc_version_string(self):
        """Test to retrieve LWC version from a string."""
        self.assertEqual(LwcVersions.find("3.5.0"), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find("3.5.2-pre"), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find("3.5.2-pre.5204"), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find("3.1.0"), LwcVersions.Lizmap_3_1)
        self.assertEqual(LwcVersions.find("3.10.0"), LwcVersions.Lizmap_3_10)

        # Check a non-existing release in Python source code
        # The release string can be provided the online JSON file
        # So in production, if the exception is raised, developer need to update the Python plugin
        assert LwcVersions.find("1.0.0") is None

    def test_version_info(self):
        """Test version as a list."""
        assert LwcVersions.Lizmap_3_10.version_info == (3, 10)

    def test_version_comparison(self):
        """Test we can test the version comparaison."""
        self.assertTrue(LwcVersions.Lizmap_3_6 == LwcVersions.Lizmap_3_6)
        self.assertTrue(LwcVersions.Lizmap_3_6 != LwcVersions.Lizmap_3_5)

        self.assertTrue(LwcVersions.Lizmap_3_4 < LwcVersions.Lizmap_3_5)
        self.assertTrue(LwcVersions.Lizmap_3_6 > LwcVersions.Lizmap_3_5)
        self.assertTrue(LwcVersions.Lizmap_3_6 >= LwcVersions.Lizmap_3_6)
        self.assertTrue(LwcVersions.Lizmap_3_5 <= LwcVersions.Lizmap_3_5)

        self.assertEqual(LwcVersions.Lizmap_3_11, LwcVersions.latest())

        # Do not confuse LWC 3.1 and 3.10
        self.assertTrue(LwcVersions.Lizmap_3_10 > LwcVersions.Lizmap_3_9)
        self.assertTrue(LwcVersions.Lizmap_3_9 < LwcVersions.Lizmap_3_10)
        self.assertTrue(LwcVersions.Lizmap_3_10 >= LwcVersions.Lizmap_3_10)
        self.assertTrue(LwcVersions.Lizmap_3_10 <= LwcVersions.Lizmap_3_10)

    def test_release_status(self):
        """Test to retrieve release status."""
        self.assertEqual(ReleaseStatus.SecurityBugfixOnly, ReleaseStatus.find("security_bugfix_only"))
        self.assertEqual(ReleaseStatus.ReleaseCandidate, ReleaseStatus.find("feature_freeze"))
        self.assertEqual(ReleaseStatus.Stable, ReleaseStatus.find("stable"))
        self.assertEqual(ReleaseStatus.Unknown, ReleaseStatus.find("i_dont_know"))
