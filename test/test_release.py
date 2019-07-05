#! /usr/bin/env python

import os
import unittest
import yaml
from github import Github
import git

from qgispluginci.parameters import Parameters
from qgispluginci.release import release
from qgispluginci.translation import Translation
from qgispluginci.exceptions import GithubReleaseNotFound
from github import GithubException

# if change, also update on .travis.yml
RELEASE_VERSION_TEST = '9.8.7'


class TestRelease(unittest.TestCase):

    def setUp(self):
        arg_dict = yaml.safe_load(open(".qgis-plugin-ci"))
        self.parameters = Parameters(arg_dict)
        self.transifex_token = os.getenv('transifex_token')
        self.github_token = os.getenv('github_token')
        self.repo = None
        if self.github_token:
            print('creating fake release on Github ({})'.format(RELEASE_VERSION_TEST))
            self.repo = Github(self.github_token).get_repo('opengisch/qgis-plugin-ci')
            self.repo.create_git_release(RELEASE_VERSION_TEST, 'some fake release for testing', '', draft=False, prerelease=False)

    def tearDown(self):
        if self.repo:
            rel = None
            try:
                rel = self.repo.get_release(id=RELEASE_VERSION_TEST)
            except GithubException as e:
                raise GithubReleaseNotFound('Release {} not found'.format(RELEASE_VERSION_TEST))
            if rel:
                print('cleaning release')
                rel.delete_release()
                git_repo = git.repo.Repo()
                git_repo.remotes.origin.fetch()
                for t in git_repo.tags:
                    if t.name == RELEASE_VERSION_TEST:
                        print('cleaning tag {}'.format(t.name))
                        git_repo.delete_tag(t)
                        git_repo.remotes.origin.push(':{}'.format(t.path))

    def test_release(self):
        release(self.parameters, RELEASE_VERSION_TEST)

    def test_release_with_transifex(self):
        assert self.transifex_token is not None
        t = Translation(self.parameters, transifex_token=self.transifex_token)
        release(self.parameters, RELEASE_VERSION_TEST, transifex_token=self.transifex_token)

    def test_release_upload_github(self):
        release(self.parameters, RELEASE_VERSION_TEST, github_token=self.github_token)

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