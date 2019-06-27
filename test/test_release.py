#! /usr/bin/env python

import unittest
import yaml

from qgispluginci.parameters import Parameters
from qgispluginci.release import release
from qgispluginci.translation import Translation


class TestRelease(unittest.TestCase):

    def setUp(self):
        arg_dict = yaml.safe_load(open(".qgis-plugin-ci"))
        self.parameters = Parameters(arg_dict)

    def tearDown(self):
        pass

    def test_release(self):
        release(self.parameters, '1.2.3')

    def test_release_with_transifex(self):
        Translation(self.parameters, transifex_token=self.parameters.transifex_token)
        release(self.parameters, '1.2.3', transifex_token=self.parameters.transifex_token)


if __name__ == '__main__':
    unittest.main()