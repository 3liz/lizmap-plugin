#! /usr/bin/env python

import unittest
import yaml
import os

from qgispluginbooster.parameters import Parameters
from qgispluginbooster.translation import Translation
from pytransifex.exceptions import PyTransifexException

class TestTranslation(unittest.TestCase):

    def setUp(self):
        arg_dict = yaml.safe_load(open(".qgis-plugin-booster"))
        self.parameters = Parameters(arg_dict)
        self.parameters.transifex_token = os.getenv('transifex_token')
        assert self.parameters.transifex_token is not None
        self.t = Translation(self.parameters, transifex_token=self.parameters.transifex_token)

    def tearDown(self):
        try:
            self.t._t.delete_project(self.parameters.project_slug)
        except PyTransifexException:
            pass

    def test_creation(self):
        self.t = Translation(self.parameters, transifex_token=self.parameters.transifex_token)
        self.tearDown()
        self.t = Translation(self.parameters, transifex_token=self.parameters.transifex_token)

    def test_pull(self):
        self.t.pull()
        self.t.compile_strings()


if __name__ == '__main__':
    unittest.main()
