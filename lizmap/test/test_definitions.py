import unittest

from lizmap.definitions.definitions import LwcVersions


class TestDefinitions(unittest.TestCase):

    def test_lwc_version_string(self):
        """ Test to retrieve LWC version from a string. """
        self.assertEqual(LwcVersions.find('3.5.0'), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find('3.5.2-pre'), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find('3.5.2-pre.5204'), LwcVersions.Lizmap_3_5)
        self.assertEqual(LwcVersions.find('3.7.2-pre.5204'), LwcVersions.Lizmap_3_7)

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
