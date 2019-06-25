#! /usr/bin/env python

import unittest
import yaml

from qgispluginbooster.parameters import Parameters
from qgispluginbooster.release import release


class TestTranslation(unittest.TestCase):

    def setUp(self):
        arg_dict = yaml.safe_load(open(".qgis-plugin-booster"))
        self.parameters = Parameters(arg_dict)

    def tearDown(self):
        pass

    def test_release(self):
        release(self.parameters, '1.2.3', translation=False)


if __name__ == '__main__':
    unittest.main()