#!/bin/sh

setup_git() {
  git config --global user.email "etrimaille@3liz.com"
  git config --global user.name "3Liz bot"
}

commit_i18n_files() {
  git checkout -b master
  git add lizmap/i18n/*.qm
  git commit --message "Update translations to version : $TRAVIS_TAG" --message "[skip travis]"
}

upload_files() {
  git remote add origin-push https://"${GH_TOKEN}"@github.com/"${TRAVIS_REPO_SLUG}".git > /dev/null 2>&1
  git push --quiet --set-upstream origin-push master
}

setup_git
commit_i18n_files
upload_files
