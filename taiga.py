#!/usr/bin/env python
from __future__ import unicode_literals

import datetime
import requests
import json
from jinja2 import Template


class TaigaWiki(object):
    """
    Taiga wiki API wrapper
    """
    slug_base = 'droplet-library-versions-{0}'

    def __init__(self, api_base, username, password, project_slug):
        """
        Class initialization logic

        :param api_base: server address
        :param username: api username
        :param password: api password
        :param project_slug: project slug (taken from url)
        """
        self.api_base = api_base
        self.username = username
        self.password = password
        self.project_slug = project_slug

        self.auth_header = self._get_auth_header()
        self.project_id = self._get_object_id_by_slug('projects', project_slug)
        self.link_base = '{0}/project/{1}/wiki/'.format(self.api_base, project_slug)
        self.now = datetime.datetime.utcnow()

    def _get_auth_header(self):
        """
        Get auth header in order to make authenticated requests
        :return: header dict
        """
        response = requests.post(
            '{0}/api/v1/auth'.format(self.api_base),
            data={
                "password": self.password,
                "type": "normal",
                "username": self.username
            })

        return {
            'Authorization': 'Bearer {0}'.format(response.json()['auth_token'])
        }

    def _get_settings(self):
        """
        Read the settings page contents
        :return: encoded JSON
        """
        url = '{0}/api/v1/wiki/by_slug?slug={1}&project={2}'.format(
            self.api_base, self._make_slug('configuration'), self.project_id
        )
        response = requests.get(url, headers=self.auth_header)
        return json.loads(response.json()['content'].replace('```', ''))

    def _get_object_id_by_slug(self, object_type, slug):
        """

        :param object_type:
        :param slug:
        :return:
        """
        if object_type == 'projects':
            url = '{0}/api/v1/{1}/by_slug?slug={2}'.format(self.api_base, object_type, slug)
        else:
            url = '{0}/api/v1/{1}/by_slug?slug={2}&project={3}'.format(self.api_base, object_type, slug,
                                                                       self.project_id)

        response = requests.get(url, headers=self.auth_header)
        return response.json()['id']

    def _submit_page(self, template_path, context, slug):
        """
        Try to create a new wiki page, if such page already exists, removes the previous and create again.

        :param template_path: template location in filesystem
        :param context: template context data
        :param slug: wiki page slug
        """
        template = Template(open(template_path, 'r').read())
        body = template.render(context)

        payload = {
            'project': self.project_id,
            'content': body,
            'slug': slug
        }
        response = requests.post('{0}/api/v1/wiki'.format(self.api_base, self.project_id),
                                 headers=self.auth_header,
                                 data=payload)

        data = response.json()
        error_key = '__all__'
        if error_key in data and 'exists' in data[error_key][0].lower():
            requests.delete(
                '{0}/api/v1/wiki/{1}'.format(self.api_base, self._get_object_id_by_slug('wiki', slug)),
                headers=self.auth_header)

            self._submit_page(template_path, context, slug)

    def _make_slug(self, part):
        """
        Make full page slug from the last part
        :param part: slug part
        :return: slug - string
        """
        return self.slug_base.format(part)

    def _sync_index_page(self):
        """
        Update index page from the existing API pages
        """
        config_slug = self._make_slug('configuration')
        index_slug = self._make_slug('index')
        settings = self._get_settings()

        response = requests.get(
            '{0}/api/v1/wiki?project={1}'.format(self.api_base, self.project_id),
            headers=self.auth_header)

        wiki_pages = response.json()

        # Getting all library version pages excluding configuration and index page
        pages = [i['slug'] for i in wiki_pages if i['slug'].startswith(self.slug_base[:-3])]
        pages = [i for i in pages if not i.endswith(index_slug)]
        pages = [i for i in pages if not i.endswith(config_slug)]
        pages = [(i, '{0}@{1}'.format(i.split('--')[1], i.split('--')[2].replace('_', '.'))) for i in pages]
        pages = [(i[0], settings.get(i[1], i[1])) for i in pages]

        self._submit_page('templates/index.html', {
            'config_slug': config_slug,
            'link_base': self.link_base,
            'now': self.now,
            'pages': pages,
        }, index_slug)

    def make_profile_page(self, data):
        """
        Create service profile wiki page
        :param data: StatsGather instance
        """
        print({
            'link_base': self.link_base,
            'username': data.username,
            'hostname': data.hostname,
            'server_address': data.server_address,
            'now': self.now,
            'os_release': data.os_release,
            'python_dependencies': data.python_dependencies,
            'django_version': data.django_version,
            'python_versions': data.python_versions,
            'postgres_version': data.postgres_version,
        })

        slug_part = '-{0}--{1}'.format(data.username, data.server_address.replace('.', '_'))
        self._submit_page('templates/profile.html', {
            'link_base': self.link_base,
            'username': data.username,
            'hostname': data.hostname,
            'server_address': data.server_address,
            'now': self.now,
            'os_release': data.os_release,
            'python_dependencies': data.python_dependencies,
            'django_version': data.django_version,
            'python_versions': data.python_versions,
            'postgres_version': data.postgres_version,
        }, self._make_slug(slug_part))

        # Need to synchronize index page too
        self._sync_index_page()


if __name__ == '__main__':
    import argparse  # noqa
    from stats import StatsGather  # noqa

    parser = argparse.ArgumentParser(description='Omni taiga server wiki api wrapper')
    parser.add_argument('--api_base', default=None, help='API server URL')
    parser.add_argument('--username', default=None, help='API username')
    parser.add_argument('--password', default=None, help='API password')
    parser.add_argument('--project_slug', default=None, help='Project slug (taken from taiga project URL)')

    opts = parser.parse_args()

    if not opts.username or not opts.password:
        raise Exception('Username and/or password must be set')

    if not opts.project_slug:
        raise Exception('Taiga project slug must be set')

    if not opts.api_base:
        raise Exception('API server url must be set')

    api = TaigaWiki(opts.api_base, opts.username, opts.password, opts.project_slug)
    api.make_profile_page(StatsGather())
