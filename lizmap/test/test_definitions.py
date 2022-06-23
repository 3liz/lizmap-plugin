import unittest

from lizmap.definitions.definitions import LwcVersions


class TestDefinitions(unittest.TestCase):

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
