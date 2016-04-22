# This file is part of Adblock Plus <https://adblockplus.org/>,
# Copyright (C) 2006-2016 Eyeo GmbH
#
# Adblock Plus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# Adblock Plus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adblock Plus.  If not, see <http://www.gnu.org/licenses/>.

"""Helper classes that handle IO for parsing and rendering."""

import codecs
from os import path

try:
    from urllib2 import urlopen, HTTPError
except ImportError:  # The module was renamed in Python 3.
    from urllib.request import urlopen
    from urllib.error import HTTPError

__all__ = ['FSSource', 'TopSource', 'WebSource', 'NotFound']


class NotFound(Exception):
    """Requested file doesn't exist in this source.

    The file with requested name doesn't exist. If this results from an
    include, the including list probably contains an error.
    """


class FSSource(object):
    """Directory on the filesystem.

    :param root_path: The path to the directory.
    :param encoding: Encoding to use for reading the files (default: utf-8).
    """

    is_inheritable = True

    def __init__(self, root_path, encoding='utf-8'):
        root_path = path.abspath(root_path)
        self.root_path = root_path
        self.encoding = encoding

    def resolve_path(self, path_in_source):
        parts = path_in_source.split('/')
        full_path = path.abspath(path.join(self.root_path, *parts))
        if not full_path.startswith(self.root_path):
            raise ValueError('Invalid path: \'{}\''.format(path_in_source))
        return full_path

    def get(self, path_in_source):
        full_path = self.resolve_path(path_in_source)
        try:
            with codecs.open(full_path, encoding=self.encoding) as open_file:
                for line in open_file:
                    yield line.rstrip()
        except IOError as exc:
            if exc.errno == 2:  # No such file or directory.
                raise NotFound('File not found: \'{}\''.format(full_path))
            else:
                raise exc


class TopSource(FSSource):
    """Current directory without path conversion.

    Also supports absolute paths. This source is used for the top fragment.

    :param encoding: Encoding to use for reading the files (default: utf-8).
    """

    is_inheritable = False

    def __init__(self, encoding='utf-8'):
        super(TopSource, self).__init__('.', encoding)

    def resolve_path(self, path_in_source):
        return path_in_source


class WebSource(object):
    """Handler for http or https.

    :param protocol: "http" or "https".
    :param default_encoding: Encoding to use when the server doesn't specify
        it (default: utf-8).
    """

    is_inheritable = False

    def __init__(self, protocol, default_encoding='utf-8'):
        self.protocol = protocol
        self.default_encoding = default_encoding

    def get(self, path_in_source):
        url = '{}:{}'.format(self.protocol, path_in_source)
        try:
            response = urlopen(url)
            info = response.info()
            # info.getparam became info.get_param in Python 3 so we'll
            # try both.
            get_param = (getattr(info, 'get_param', None) or
                         getattr(info, 'getparam', None))
            encoding = get_param('charset') or self.default_encoding
            for line in response:
                yield line.decode(encoding).rstrip()
        except HTTPError as err:
            if err.code == 404:
                raise NotFound('HTTP 404 Not found: \'{}:{}\''
                               .format(self.protocol, path_in_source))
            else:
                raise err