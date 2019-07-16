#! /usr/bin/env python

import os
import unittest
import yaml
import filecmp
import urllib.request
from tempfile import mkstemp
from github import Github, GithubException

from qgispluginci.parameters import Parameters
from qgispluginci.release import release
from qgispluginci.translation import Translation
from qgispluginci.exceptions import GithubReleaseNotFound


# if change, also update on .travis.yml
RELEASE_VERSION_TEST = '0.1.2'


class TestRelease(unittest.TestCase):

    def setUp(self):
        arg_dict = yaml.safe_load(open(".qgis-plugin-ci"))
        self.parameters = Parameters(arg_dict)
        self.transifex_token = os.getenv('transifex_token')
        self.github_token = os.getenv('github_token')
        self.repo = None
        if self.github_token:
            print('init Github')
            self.repo = Github(self.github_token).get_repo('opengisch/qgis-plugin-ci')

    def tearDown(self):
        if self.repo:
            rel = None
            try:
                rel = self.repo.get_release(id=RELEASE_VERSION_TEST)
            except GithubException as e:
                raise GithubReleaseNotFound('Release {} not found'.format(RELEASE_VERSION_TEST))
            if rel:
                print('deleting release assets')
                for asset in rel.get_assets():
                    print('  delete {}'.format(asset.name))
                    asset.delete_asset()

    def test_release(self):
        release(self.parameters, RELEASE_VERSION_TEST)

    def test_release_with_transifex(self):
        assert self.transifex_token is not None
        t = Translation(self.parameters, transifex_token=self.transifex_token)
        release(self.parameters, RELEASE_VERSION_TEST, transifex_token=self.transifex_token)

    def test_release_upload_github(self):
        release(self.parameters, RELEASE_VERSION_TEST, github_token=self.github_token, upload_plugin_repo_github=True)

        # check the custom plugin repo
        _, xml_repo = mkstemp(suffix='.xml')
        url = 'https://github.com/opengisch/qgis-plugin-ci/releases/download/{}/plugins.xml'.format(RELEASE_VERSION_TEST)
        # TODO uncomment when new release
        #urllib.request.urlretrieve(url, xml_repo)
        #self.assertTrue(filecmp('test/plugins.xml.expected', xml_repo))

        # compare archive file size
        gh_release = self.repo.get_release(id=RELEASE_VERSION_TEST)
        archive_name = 'qgis-plugin-ci-{}.zip'.format(RELEASE_VERSION_TEST)
        fs = os.path.getsize(archive_name)
        print('size: ', fs)
        self.assertGreater(fs, 0, 'archive file size must be > 0')
        for a in gh_release.get_assets():
            if a.name == archive_name:
                self.assertEqual(fs, a.size, 'asset size doesn\'t march archive size.')
                break
            self.assertTrue(False, 'asset not found')



if __name__ == '__main__':
    unittest.main()