# Python 2 and 3: easiest option
# see http://python-future.org/compatible_idioms.html
from future.standard_library import install_aliases  # isort:skip to keep 'install_aliases()'
install_aliases()

import codecs
import json
import logging
import os.path
import sys
from urllib.parse import quote, unquote, urljoin

import requests
from bs4 import BeautifulSoup

logging.basicConfig()
log = logging.getLogger(sys.argv[0] if __name__ == "__main__" else __name__)
logging.captureWarnings(True)  # see https://urllib3.readthedocs.org/en/latest/security.html#disabling-warnings


class DownloadError(Exception):
    """content could not be downloaded as requested."""
    pass


def url_to_filename(url):
    """
    Convert URL to a valid, unambigous filename.

    >>> url_to_filename('http://openqa.opensuse.org/tests/foo/3')
    'http%3A::openqa.opensuse.org:tests:foo:3'
    """
    return quote(url).replace('/', ':')


def filename_to_url(name):
    """
    Convert filename generated by 'url_to_filename' back to valid URL.

    >>> str(filename_to_url('http%3A::openqa.opensuse.org:tests:foo:3'))
    'http://openqa.opensuse.org/tests/foo/3'
    """
    return unquote(name.replace(':', '/'))


class Browser(object):

    """download relative or absolute url and return soup."""

    def __init__(self, args, root_url):
        """Construct a browser object with options."""
        self.save = args.save if hasattr(args, 'save') else False
        self.load = args.load if hasattr(args, 'load') else False
        self.load_dir = args.load_dir if hasattr(args, 'load_dir') else '.'
        self.save_dir = args.save_dir if hasattr(args, 'save_dir') else '.'
        self.root_url = root_url
        self.cache = {}

    def get_soup(self, url):
        """Return content from URL as 'BeautifulSoup' output."""
        assert url, "url can not be None"
        return BeautifulSoup(self.get_page(url), "html.parser")

    def get_json(self, url):
        """Wrapper method for get_page retrieving json API output."""
        return self.get_page(url, as_json=True)

    def get_page(self, url, as_json=False):
        """Return content from URL as string.

        If object parameter 'load' was specified, the URL content is loaded
        from a file.
        """
        if url in self.cache:
            log.info("Loading content instead of URL %s from in-memory cache" % url)
            return json.loads(self.cache[url]) if as_json else self.cache[url]
        filename = url_to_filename(url)
        if self.load:
            log.info("Loading content instead of URL %s from filename %s" % (url, filename))
            raw = open(os.path.join(self.load_dir, filename)).read()
            content = json.loads(raw) if as_json else raw
        else:  # pragma: no cover
            absolute_url = url if not url.startswith('/') else urljoin(self.root_url, str(url))
            r = requests.get(absolute_url)
            if r.status_code != 200:
                msg = "Request to %s was not successful, status code: %s" % (absolute_url, r.status_code)
                log.info(msg)
                raise DownloadError(msg)
            content = r.json() if as_json else r.content.decode('utf8')
        raw = json.dumps(content) if as_json else content
        if self.save:
            log.info("Saving content instead from URL %s from filename %s" % (url, filename))
            codecs.open(os.path.join(self.save_dir, filename), 'w', 'utf-8').write(raw)
        self.cache[url] = raw
        return content


def add_load_save_args(parser):
    load_save = parser.add_mutually_exclusive_group()
    load_save.add_argument('--save', action='store_true',
                           help="""Save downloaded webpages and test data to local
                           folder. Name is autogenerated. This could be useful
                           for test investigation, loading same results for
                           another run of report generation with "--load" or
                           debugging""")
    load_save.add_argument('--load', action='store_true',
                           help="""Use previously downloaded webpages and data.
                           See '--save'.""")
    parser.add_argument('--load-dir', default='.',
                        help="""The directory to read cache files from when
                        using '--load'.""")
    parser.add_argument('--save-dir', default='.',
                        help="""The directory to write cache files to when
                        using '--save'.""")
