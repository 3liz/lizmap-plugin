
import glob
import subprocess
from pytransifex import Transifex
from qgispluginci.parameters import Parameters
from qgispluginci.exceptions import TranslationFailed, TransifexNoResource, TransifexManyResources
from qgispluginci.utils import touch_file


class Translation():
    def __init__(self, parameters: Parameters,
                 transifex_token: str,
                 create_project: bool = True):
        """
        Parameters
        ----------
        parameters:

        transifex_token:
            Transifex API token

        create_project:
            if True, it will create the project, resource and language on Transifex

        """
        self.parameters = parameters
        self._t = Transifex(transifex_token, parameters.transifex_organization, i18n_type='QT')
        assert self._t.ping()
        self.ts_file = '{dir}/i18n/{res}_{lan}.ts'.format(dir=self.parameters.plugin_path,
                                                          res=self.parameters.project_slug,
                                                          lan=self.parameters.translation_source_language)

        if self._t.project_exists(parameters.project_slug):
            print('Project {o}/{p} exists on Transifex'.format(o=self.parameters.transifex_organization,
                                                               p=self.parameters.project_slug))
        elif create_project:
            print('project does not exists on Transifex, creating one as {o}/{p}'.format(o=self.parameters.transifex_organization,
                                                                                         p=self.parameters.project_slug))
            self._t.create_project(slug=parameters.project_slug,
                                repository_url=self.parameters.repository_url,
                                source_language_code=parameters.translation_source_language)
            self.update_strings()
            print('creating resource in {o}/{p} with {f}'.format(o=self.parameters.transifex_organization,
                                                                 p=self.parameters.project_slug,
                                                                 f=self.ts_file))
            self._t.create_resource(project_slug=self.parameters.project_slug,
                                 path_to_file=self.ts_file,
                                 resource_slug=self.parameters.project_slug)
            print('OK')
        else:
            raise TranslationFailed('Project {o}/{p} does notexists on Transifex'.format(
                o=self.parameters.transifex_organization, p=self.parameters.project_slug))

    def update_strings(self):
        """
        Update TS files from plugin source strings
        """
        cmd = [self.parameters.pylupdate5_path, '-noobsolete']
        for ext in ('py', 'ui'):
            for file in glob.glob('{dir}/**/*.{ext}'.format(dir=self.parameters.plugin_path, ext=ext), recursive=True):
                cmd.append(file)
        touch_file(self.ts_file)
        cmd.append('-ts')
        cmd.append(self.ts_file)
        output = subprocess.run(cmd, capture_output=True, text=True)
        if output.returncode != 0:
            raise TranslationFailed(output.stderr)
        else:
            print('Successfuly run pylupdate5: {}'.format(output.stdout))

    def compile_strings(self):
        """
        Compile TS file into QM files
        """
        cmd = [self.parameters.lrelease_path]
        for file in glob.glob('{dir}/i18n/*.ts'.format(dir=self.parameters.plugin_path)):
            cmd.append(file)
        output = subprocess.run(cmd, capture_output=True, text=True)
        if output.returncode != 0:
            raise TranslationFailed(output.stderr)
        else:
            print('Successfuly run lrelease: {}'.format(output.stdout))

    def pull(self):
        """
        Pull TS files from Transifex
        """
        resource = self.__get_resource()
        existing_langs = self._t.list_languages(
            project_slug=self.parameters.project_slug, resource_slug=resource['slug']
        )
        existing_langs.remove(self.parameters.translation_source_language)
        print('{c} languages found for resource ''{s}'' ({langs})'.format(
            s=resource['slug'], c=len(existing_langs), langs=existing_langs)
        )
        for lang in self.parameters.translation_languages:
            if lang not in existing_langs:
                print('creating missing language: {}'.format(lang))
                self._t.create_language(self.parameters.project_slug, lang, [self.parameters.transifex_coordinator])
                existing_langs.append(lang)
        for lang in existing_langs:
            ts_file = '{dir}/i18n/{res}_{lan}.ts'.format(dir=self.parameters.plugin_path,
                                                         res=self.parameters.project_slug,
                                                         lan=lang)
            print('downloading translation file: {}'.format(ts_file))
            self._t.get_translation(self.parameters.project_slug, resource['slug'], lang, ts_file)

    def push(self):
        resource = self.__get_resource()
        print('pushing resource: {} with file {}'.format(resource['slug'], self.ts_file))
        result = self._t.update_source_translation(
            project_slug=self.parameters.project_slug,
            resource_slug=resource['slug'],
            path_to_file=self.ts_file)
        print('done: {}'.format(result))

    def __get_resource(self) -> dict:
        resources = self._t.list_resources(self.parameters.project_slug)
        if len(resources) == 0:
            raise TransifexNoResource("project '{}' has no resource on Transifex".format(self.parameters.project_slug))
        if len(resources) > 1:
            for resource in resources:
                if resource['name'] == self.parameters.transifex_resource:
                    return resource
            raise TransifexManyResources("project '{p}' has several resources on Transifex "
                                         "and none is named as the project slug."
                                         "Specify one in the parameters with transifex_resource"
                                         .format(p=self.parameters.project_slug))
        return resources[0]
