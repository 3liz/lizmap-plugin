#/usr/bin/python3

 
import codecs
import requests
import json
import os
from pytransifex.exceptions import PyTransifexException


class Transifex(object):
    def __init__(self, api_token: str, organization: str, i18n_type: str = 'PO'):
        """
        Initializes Transifex 

        Parameters
        ----------
        api_token
            the API token to the service
        organization
            the name of the organization
        i18n_type
            the type of translation (PO, QT, …)
            defaults to: PO
        """
        self.auth = ('api', api_token)
        self.organization = organization
        self.i18n_type = i18n_type

    def new_project(self,
                    slug,
                    name: str = None,
                    source_language_code: str = 'en-gb',
                    outsource_project_name: str = None,
                    private: bool = False,
                    repository_url: str = None):
        """
        Create a new project on Transifex
        
        Parameters
        ----------
        slug
            the project slug
        name
            the project name, defaults to the project slug
        source_language_code
            the source language code, defaults to 'en-gb'
        outsource_project_name
            the name of the project to outsource translation team management to
        private
            controls if this is created as a closed source or open-source
            project, defaults to `False`
        repository_url
            The url for the repository. This is required if private is set to
            False

        Raises
        ------
        `PyTransifexException`
           if project was not created properly
        """
        if name is None:
            name = slug

        url = 'https://www.transifex.com/api/2/projects/'
        data = {
            'name': name,
            'slug': slug,
            'organization': self.organization,
            'source_language_code': source_language_code,
            'description': name,
            'private': private,
            'repository_url': repository_url
        }
        if outsource_project_name is not None:
            data['outsource'] = outsource_project_name

        response = requests.post(url,
                                 data=json.dumps(data),
                                 auth=self.auth,
                                 headers={'content-type': 'application/json'})

        if response.status_code != requests.codes['CREATED']:
            print('Could not create project with data: {}'.format(data))
            raise PyTransifexException(response)

    def delete_projet(self, project_slug: str):
        url = 'https://www.transifex.com/api/2/project/{}'.format(project_slug)
        response = requests.delete(
            url, auth=self.auth, headers={'content-type': 'application/json'},
        )

    def list_resources(self, project_slug) -> list:
        """
        List all resources in a project

        Parameters
        ----------
        project_slug
            the project slug

        Returns
        -------
        list of dictionaries with resources info
            each dictionary may contain
                category
                i18n_type
                source_language_code
                slug
                name

        Raises
        ------
        `PyTransifexException`
        """
        url = 'https://api.transifex.com/organizations/{o}/projects/{p}/resources/'.format(
            o=self.organization, p=project_slug
        )
        response = requests.get(url, auth=self.auth)

        if response.status_code != requests.codes['OK']:
            raise PyTransifexException(response)

        return json.loads(codecs.decode(response.content, 'utf-8'))

    def new_resource(self,
                     project_slug,
                     path_to_file,
                     resource_slug=None,
                     resource_name=None):
        """
        Creates a new resource with the specified slug from the given file.

        Parameters
        ----------
        project_slug
            the project slug
        path_to_file
            the path to the file which will be uploaded
        resource_slug
            the resource slug, defaults to a sluggified version of the filename
        resource_name
            the resource name, defaults to the resource name

        Raises
        ------
        `PyTransifexException`
        `IOError`
        """
        url = 'https://www.transifex.com/api/2/project/{p}/resources/'.format(p=project_slug)
        data = {
            'name': resource_name or resource_slug,
            'slug': resource_slug,
            'i18n_type': self.i18n_type,
            'content': open(path_to_file, 'r').read()
        }
        response = requests.post(url,
                                 data=json.dumps(data),
                                 auth=self.auth,
                                 headers={'content-type': 'application/json'})

        if response.status_code != requests.codes['CREATED']:
            raise PyTransifexException(response)

    def update_source_translation(self, project_slug, resource_slug,
                                  path_to_pofile):
        """
        Update the source translation for a give resource

        Parameters
        ----------
        project_slug
            the project slug
        resource_slug
            the resource slug
        path_to_pofile
            the path to the pofile which will be uploaded

        Returns
        -------
        dictionary with info
            Info may include keys
                strings_added
                strings_updated
                redirect

        Raises
        ------
        `PyTransifexException`
        `IOError`
        """
        url = '{u}/project/{s}/resource/{r}/content'.format(u=self._base_api_url, s=project_slug, r=resource_slug)
        content = open(path_to_pofile, 'r').read()
        data = {'content': content}
        response = requests.put(
             url, data=json.dumps(data), auth=self.auth, headers={'content-type': 'application/json'},
        )

        if response.status_code != requests.codes['OK']:
            raise PyTransifexException(response)
        else:
            return json.loads(codecs.decode(response.content, 'utf-8'))

    def delete_resource(self, project_slug, resource_slug):
        """
        Deletes the given resource

        Parameters
        ----------
        project_slug
            the project slug
        resource_slug
            the resource slug

        Raises
        ------
        `PyTransifexException`
        """
        url = '{u}/project/{s}/resource/{r}'.format(u=self._base_api_url, s=project_slug, r=resource_slug)
        response = requests.delete(url, auth=self.auth)
        if response.status_code != requests.codes['NO_CONTENT']:
            raise PyTransifexException(response)

    def new_translation(self, project_slug, resource_slug, language_code,
                        path_to_file):
        """
        Creates or updates the translation for the specified language

        Parameters
        ----------
        project_slug
            the project slug
        resource_slug
            the resource slug
        language_code
            the language_code of the file
        path_to_file
            the path to the file which will be uploaded

        Returns
        -------
        dictionary with info
            Info may include keys
                strings_added
                strings_updated
                redirect

        Raises
        ------
        `PyTransifexException`
        `IOError`
        """
        url = '{u}/project/{s}/resource/{r}/translation/{l}'.format(u=self._base_api_url,
                                                                     s=project_slug,
                                                                     r=resource_slug,
                                                                     l=language_code)
        content = open(path_to_file, 'r').read()
        data = {'content': content}
        response = requests.put(
             url, data=json.dumps(data), auth=self.auth, headers={'content-type': 'application/json'},
        )

        if response.status_code != requests.codes['OK']:
            raise PyTransifexException(response)
        else:
            return json.loads(codecs.decode(response.content, 'utf-8'))

    def get_translation(self,
                        project_slug: str,
                        resource_slug: str,
                        language_code: str,
                        path_to_file: str):
        """
        Returns the requested translation, if it exists. The translation is
        returned as a serialized string, unless the GET parameter file is
        specified.

        Parameters
        ----------
        project_slug
            The project slug
        resource_slug
            The resource slug
        language_code
            The language_code of the file.
            This should be the *Transifex* language code
        path_to_file
            The path to the translation file which will be saved

        Raises
        ------
        `PyTransifexException`
        `IOError`
        """
        url = 'https://www.transifex.com/api/2/project/{s}/resource/{r}/translation/{l}'.format(
            s=project_slug, r=resource_slug, l=language_code)
        query = {'file': ''}
        response = requests.get(url, auth=self.auth, params=query)
        if response.status_code != requests.codes['OK']:
            raise PyTransifexException(response)
        else:
            with open(path_to_file, 'wb') as f:
                for line in response.iter_content():
                    f.write(line)

    def list_languages(self, project_slug, resource_slug):
        """
        List all the languages available for a given resource in a project

        Parameters
        ----------
        project_slug
            The project slug
        resource_slug
            The resource slug

        Returns
        -------
        list
            The language codes which this resource has translations

        Raises
        ------
        `PyTransifexException`
        """
        url = 'https://www.transifex.com/api/2/project/{s}/resource/{r}'.format(s=project_slug, r=resource_slug)
        response = requests.get(url, auth=self.auth, params={'details': ''})

        if response.status_code != requests.codes['OK']:
            raise PyTransifexException(response)

        content = json.loads(codecs.decode(response.content, 'utf-8'))
        languages = [language['code'] for language in content['available_languages']]
        return languages

    def new_language(self, project_slug: str, language_code: str, coordinators: list):
        """
        Parameters
        ----------
        project_slug:
        language_code:
        coordinators:
            list of coordinators
        """
        url = 'https://www.transifex.com/api/2/project/{s}/languages'.format(s=project_slug)
        data = {'language_code': language_code, 'coordinators': coordinators}
        response = requests.post(url,
                                 headers={'content-type': 'application/json'},
                                 auth=self.auth,
                                 data=json.dumps(data))
        if response.status_code != requests.codes['CREATED']:
            raise PyTransifexException(response)

    def coordinator(self, project_slug: str, language_code: str = 'en'):
        """
        Parameters
        ----------
        project_slug:
        language_code:
        """
        url = 'https://www.transifex.com/api/2/project/{s}/language/{l}/coordinators'.format(s=project_slug, l=language_code)
        response = requests.get(url, auth=self.auth)
        if response.status_code != requests.codes['OK']:
            raise PyTransifexException(response)
        content = json.loads(codecs.decode(response.content, 'utf-8'))
        return content['coordinators']


    def project_exists(self, project_slug):
        """
        Check if there is a project with the given slug registered with
        Transifex

        project_slug
            The project slug

        @return Boolean
           True is project exists
           False if not
        """
        url = 'https://api.transifex.com/organizations/{o}/projects/{s}'.format(o=self.organization, s=project_slug)
        response = requests.get(url, auth=self.auth)
        if response.status_code == requests.codes['OK']:
            return True
        elif response.status_code == requests.codes['NOT_FOUND']:
            return False
        else:
            raise PyTransifexException(response)

    def ping(self) -> bool:
        """
        Check the connection to the server and the auth credentials
        """
        url = 'https://api.transifex.com/organizations/{}/projects/'.format(self.organization)
        response = requests.get(url, auth=self.auth)
        success = response.status_code == requests.codes['OK']
        if not success:
            raise PyTransifexException(response)
        return success
