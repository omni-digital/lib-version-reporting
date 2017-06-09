"""
Gather environment data
"""

from __future__ import unicode_literals

import subprocess
import socket
import getpass


class StatsGather(object):
    """
    Get application environment data
    """
    username = None
    server_address = None
    os_release = None
    django_version = None
    python_dependencies = None
    python_versions = None
    postgres_version = None

    newline = '\n'

    def __init__(self):
        """
        Class initializer
        """
        self.username = self.get_username()
        self.server_address = self.get_server_address()
        self.django_version = self.get_django_version()
        self.hostname = self.get_hostname()
        self.os_release = self.get_os_version()
        self.python_dependencies = self.get_python_dependencies()
        self.python_versions = self.get_python_versions()
        self.postgres_version = self.get_postgres_version()

    @staticmethod
    def run(command):
        """
        Run the shell command and return standard output and error
        :param command: command
        :return: (stdin, stderr)
        """
        try:
            output = subprocess.getoutput(command)
            return output, ''
        except AttributeError:
            output = subprocess.Popen(command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            return output.communicate()


    def get_username(self):
        """

        :return:
        """
        return getpass.getuser()

    def get_os_version(self):
        """
        Get OS version
        :return: string
        """
        # If ubuntu
        try:
            mark = 'Description:'
            for line in self.run('lsb_release -a')[0].split(self.newline):
                if line.startswith(mark):
                    return line.replace(mark, '').strip()
        except OSError:
            pass

        # If centos

        try:
            return self.run('cat /etc/centos-release')[0]
        except OSError:
            pass

        return None

    def get_python_dependencies(self):
        """
        Get the list of installed python requirements
        :return: ((library name, library version), )
        """
        try:
            data = self.run('pip freeze')[0]
        except OSError:
            return None

        items = []
        for item in data.split(self.newline):
            parts = item.split('==')
            if len(parts) > 1:
                items.append((parts[0].strip().lower(), parts[1]))

        return items

    def get_django_version(self):
        """
        Get django version
        :return: string
        """
        dependencies = self.get_python_dependencies()
        if not dependencies:
            return None

        for item in dependencies:
            if item[0] == 'django':
                return item[1]

        return None

    def get_python_versions(self):
        """
        Get the installed python versions
        """
        response = {
            'python2': None,
            'python3': None
        }

        try:
            stderr = self.run('python --version')[1]
            response['python2'] = stderr.split(self.newline)[0].strip()
        except OSError:
            pass

        try:
            stdout = self.run('python3 --version')[0]
            response['python3'] = stdout.split(self.newline)[0].strip()
        except OSError:
            pass

        return response

    def get_postgres_version(self):
        """
        Get postgres version
        :return: string
        """
        try:
            lines = self.run('psql --version')[0].split(self.newline)
            return lines[0].split(' ')[2]
        except OSError:
            return None

    @staticmethod
    def get_hostname():
        """
        Get machine hostname
        :return: string
        """
        return socket.gethostname()

    @staticmethod
    def get_server_address():
        """
        Get machine IP address
        :return: IP
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


if __name__ == '__main__':
    stats = StatsGather()
    print(stats.os_release)
    print(stats.python_dependencies)
    print(stats.python_versions)
    print(stats.postgres_version)
