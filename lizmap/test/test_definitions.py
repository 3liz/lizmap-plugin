import unittest

from lizmap.definitions.definitions import LwcVersions


class TestDefinitions(unittest.TestCase):

    def test_lwc_version_string(self):
        """ Test to retrieve LWC version from a string. """
        self.assertEqual(LwcVersions.find('3.5.0'), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find('3.5.2-pre'), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find('3.5.2-pre.5204'), LwcVersions.Lizmap_3_5)

        # Check a non-existing release in Python source code
        # The release string can be provided the online JSON file
        # So in production, if the exception is raised, developer need to update the Python plugin
        # No exception is raised in production for non developers.
        with self.assertRaises(Exception):
            LwcVersions.find('1.0.0', True)
        self.assertIsInstance(LwcVersions.find('1.0.0'), LwcVersions)

    def test_version_comparaison(self):
        """ Test we can test the version comparaison. """
        self.assertTrue(LwcVersions.Lizmap_3_6 == LwcVersions.Lizmap_3_6)
        self.assertTrue(LwcVersions.Lizmap_3_6 != LwcVersions.Lizmap_3_5)

        self.assertFalse(LwcVersions.Lizmap_3_4 > LwcVersions.Lizmap_3_5)
        self.assertTrue(LwcVersions.Lizmap_3_6 >= LwcVersions.Lizmap_3_6)
        self.assertTrue(LwcVersions.Lizmap_3_6 > LwcVersions.Lizmap_3_5)

        self.assertTrue(LwcVersions.Lizmap_3_5 < LwcVersions.Lizmap_3_6)
        self.assertTrue(LwcVersions.Lizmap_3_5 <= LwcVersions.Lizmap_3_5)
        self.assertFalse(LwcVersions.Lizmap_3_5 < LwcVersions.Lizmap_3_4)
