#!/usr/bin/python3

import git
import tarfile
import zipfile
from tempfile import mkstemp
from glob import glob

from qgispluginci.parameters import Parameters
from qgispluginci.translation import Translation
from qgispluginci.utils import replace_in_file


def release(parameters: Parameters,
            release_version: str,
            transifex_token: str = None):

    # set version in metadata
    replace_in_file('{}/metadata.txt'.format(parameters.src_dir),
                    r'^version=.*\$',
                    'version=${}'.format(release_version))

    # replace any DEBUG=False in the plugin main file
    replace_in_file('{d}/{f}'.format(d=parameters.src_dir, f=parameters.plugin_main_file),
                    r'^DEBUG\s*=\s*True',
                    'DEBUG = False')

    if transifex_token is not None:
        tr = Translation(parameters, create_project=False, transifex_token=transifex_token)
        tr.pull()
        tr.compile_strings()

    output = '{project_slug}-{release_version}.zip'.format(project_slug=parameters.project_slug,
                                                           release_version=release_version)
    create_archive(parameters, output=output, add_translations=transifex_token is not None)


def create_archive(parameters: Parameters,
                   output: str,
                   add_translations: bool = False):
    top_tar_handle, top_tar_file = mkstemp(suffix='.tar')

    repo = git.Repo()
    try:
        stash = repo.git.stash('create')
    except git.exc.GitCommandError:
        stash = 'HEAD'
    # create TAR archive
    repo.git.archive(stash, '--prefix', '{}/'.format(parameters.src_dir), '-o', top_tar_file, parameters.src_dir)
    with tarfile.open(top_tar_file, mode="a") as tt:
        # adding submodules
        for submodule in repo.submodules:
            _, sub_tar_file = mkstemp(suffix='.tar')
            if submodule.path.split('/')[0] != parameters.src_dir:
                print('skipping submodule not in plugin source directory ({})'.format(submodule.name))
                continue
            submodule.update(init=True)
            sub_repo = submodule.module()
            print(sub_repo)
            sub_repo.git.archive('HEAD', '--prefix', '{}/'.format(submodule.path), '-o', sub_tar_file)
            with tarfile.open(sub_tar_file, mode="r:") as st:
                for m in st.getmembers():
                    tt.addfile(m)
        print('files in TAR archive:')
        print(tt.list())

        # add translation files
        if add_translations:
            for file in glob('i18n/*.qm'):
                tt.addfile(tarfile.TarInfo('{s}/i18n/{f}'.format(s=parameters.src_dir, f=file)), file)

    # converting to ZIP
    # why using TAR before? because it provides the prefix and makes things easier
    with zipfile.ZipFile(file=output, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        # adding the content of TAR archive
        with tarfile.open(top_tar_file, mode='r:') as tt:
            for m in tt.getmembers():
                if m.type == tarfile.DIRTYPE:
                    continue
                f = tt.extractfile(m)
                fl = f.read()
                fn = m.name
                zf.writestr(fn, fl)







"""


# Extract to a temporary location and add translations
TEMPDIR=/tmp/build-${PLUGIN_REPO_NAME}
mkdir -p ${TEMPDIR}/${PLUGIN_REPO_NAME}/${PLUGIN_REPO_NAME}/i18n
tar -xf ${CURDIR}/${PLUGIN_REPO_NAME}-${RELEASE_VERSION}.tar -C ${TEMPDIR}
if [[ "${PLUGIN_SRC_DIR}" != "${PLUGIN_REPO_NAME}" ]]; then
  mv ${TEMPDIR}/${PLUGIN_REPO_NAME}/${PLUGIN_SRC_DIR}/* ${TEMPDIR}/${PLUGIN_REPO_NAME}/${PLUGIN_REPO_NAME}
  rmdir ${TEMPDIR}/${PLUGIN_REPO_NAME}/${PLUGIN_SRC_DIR}
fi
if [[ -d i18n ]]; then
  mv i18n/*.qm ${TEMPDIR}/${PLUGIN_REPO_NAME}/${PLUGIN_REPO_NAME}/i18n
else
  if [[ -d .tx ]]; then
    echo -e "\033[0;33mNo i18n folder is present, even though pytransifex is. Something seems to be going wrong.\033[0m"
  fi
fi

pushd ${TEMPDIR}/${PLUGIN_REPO_NAME}
zip -r ${CURDIR}/${ZIPFILENAME} ${PLUGIN_REPO_NAME}
popd

echo "## Detailed changelog" > /tmp/changelog
git log HEAD^...$(git describe --abbrev=0 --tags HEAD^) --pretty=format:"### %s%n%n%b" >> /tmp/changelog

CHANGELOG_OPTION=""
if [[ "$APPEND_CHANGELOG" = "true" ]]; then
  CHANGELOG_OPTION="-c /tmp/changelog"
fi


${DIR}/create_release.py -f ${CURDIR}/${ZIPFILENAME} ${APPEND_CHANGELOG:+-c /tmp/changelog} -o /tmp/release_notes
cat /tmp/release_notes
if [[ ${PUSH_TO} =~ ^github$ ]]; then
  ${DIR}/publish_plugin_github.sh
else
  ${DIR}/publish_plugin_osgeo.py -u "${OSGEO_USERNAME}" -w "${OSGEO_PASSWORD}" -r "${TRAVIS_TAG}" ${ZIPFILENAME} -c /tmp/release_notes
fi
"""