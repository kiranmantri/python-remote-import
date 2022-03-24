"""Import modules (or packages) from a Remote Location.

This module reimplement the meta_path search to allow loading python code
from a remote location (currently only http)

References:
[1] PEP 302 -- New Import Hooks; https://www.python.org/dev/peps/pep-0302/
[2] PEP 451 -- A ModuleSpec Type for the Import System; https://www.python.org/dev/peps/pep-0451

Usage:

>> from remote_import import RemoteImporter
>> RemoteImporter.add_namespaces(['test_package'], 'http://0.0.0.0:8000/packages/')

>> from test_package.d.aclass import SomeUselessClass
>> obj = SomeUselessClass()

"""
import os
import re
import sys
import types
import importlib
import traceback
import fsspec
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from importlib.util import LazyLoader
from typing import List, AnyStr
import logging

logger = logging.getLogger("remote_import")


def validate_variable_string(variable_string):
    return re.sub(r"\W|^(?=\d)", "_", variable_string)


def sanitize_url(url):
    return re.sub(r"([^:]/)(/)+", r"\1", url)


class RemoteImporter(MetaPathFinder, LazyLoader):
    """Find and load models in remote locations (HTTP).

    Once added to the sys.meta_path, the subsystem looks for 3 methods in this importer
    1. find_spec(...) --> return a spec
    2. create_module(spec) --> return a (new) module
    3. exec_module(module) --> return the module
    """

    def __init__(self, namespace: str, base_url: str, headers: dict = {}, extra_args: dict = {}):
        self.namespace = namespace
        self.base_url = base_url
        self.namespace_url = self.url(self.namespace)
        self.headers = headers
        self.extra_args = extra_args

    @property
    def package_name(self):
        return self.namespace

    @property
    def package_hash(self):
        return self.headers.get('X-hash') or self.headers.get('x-hash')

    @property
    def fs(self):
        _fs, _ = fsspec.core.url_to_fs(self.namespace_url, **self.extra_args)
        return _fs

    @property
    def package_files(self):
        url = self.namespace_url
        fs = self.fs
        # We need to use "fs.find()" to have a recursive list of files
        # But I am having issues with fs.find(), because it was not listing the current dir,
        # only the children dirs. Workaround: find() + ls() covers everything
        package_files = set(fs.find(url) + fs.ls(url, detail=False))
        return package_files

    def url(self, full_name):
        module_path = full_name.replace('.', '/')
        url = f"{self.base_url}/{os.path.normpath(module_path)}"
        url = sanitize_url(url)
        return url

    def add_header(self, key: str, value: str) -> dict:
        self.__headers[key] = value
        return self.__headers

    def _get_raw_source_code(self, url):
        try:
            response = self.fs.cat(url).decode()
        except Exception as e:
            # any other error is a fail to import
            # the import subsystem will handle 'ModuleNotFoundError'
            error_msg = f"File request failed. URL: {url}. Error: {e}, "
            error_msg += f"stack: {traceback.format_tb(e.__traceback__)}"
            logger.critical(error_msg)
            raise ModuleNotFoundError(error_msg)
        else:
            # If no suffix, means folder and no __init__.py neither __main__.
            # which means source_code is empty for this module
            # raw_source_code = "" if suffix == "" else response
            raw_source_code = response
            return raw_source_code

    def find_spec(self, full_name, path, target):
        logger.debug(f"Searching module full_name={full_name}, path={path}, target={target}")
        # When 'find_spec' returns None, it is signaling to the subsystem that the
        # requested path (or full_name) is not fullfilled by this package.
        # Then, the import subsystem will act accordingly. In this case it will
        # keep searching (with the remaining finders in sys.meta_path) until some finder claims
        # ownership of that full_name, or until the subsystem returns ModuleNotFound

        package_name, *_ = full_name.split('.')
        if package_name != self.namespace:
            logger.debug(
                f"{self.package_name} not found in {self.namespace} namespace ({self.url(full_name)}). "
                "Moving on to next finder."
            )
            return None

        # The packages (i.e. folders) have precedence over files (.py):
        # 1. search for __init__.py,
        # 2. search for <module base name>.py
        # e.g.: import example.a.b.c
        #   - search for <base_url>/example/a/b/c/__init__.py
        #   - search for <base_url>/example/a/b/c.py
        # So, if there exists:
        #    .
        #    ├── a
        #    │   └── __init__.py
        #    ├── a.py
        #    ├── b.py
        #
        # /a/__init__.py --> will be loaded first, and
        # /a.py          --> will be ignored
        # If you have this situation, rename either the folder or the .py file to avoid name clashing
        # https://docs.python.org/3.10/tutorial/modules.html#packages
        # https://stackoverflow.com/questions/16245106/python-import-class-with-same-name-as-directory

        this_module_url = self.url(full_name)
        url_init = sanitize_url(f"{this_module_url}/__init__.py")
        url_py = sanitize_url(f"{this_module_url}.py")
        if url_init in self.package_files:
            url = url_init
            logger.info(f"Loading module {full_name} {url}")
            raw_source_code = self._get_raw_source_code(url=url)
        elif url_py in self.package_files:
            url = url_py
            logger.info(f"Loading module {full_name} {url}")
            raw_source_code = self._get_raw_source_code(url=url)
        else:
            url = this_module_url
            logger.debug(f"Folder without a __init__.py? {full_name} {url}")
            raw_source_code = ''

        logger.info(f"Lodule loaded {full_name} {url}")
        self._full_url = url
        self._raw_source_code = raw_source_code
        return ModuleSpec(full_name, self)

    def create_module(self, spec):
        module = types.ModuleType(spec.name)
        module.__package__ = spec.name
        module.__path__ = self.base_url
        module.__url__ = self.url(spec.name)
        module.__file__ = self.url(spec.name)
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module):
        module.__source__ = self._raw_source_code
        self.compiled_source = compile(source=self._raw_source_code, filename=self.base_url, mode='exec')
        exec(self.compiled_source, module.__dict__)
        return module

    @classmethod
    def add_remote(
        cls,
        namespaces: List[AnyStr],
        base_url: AnyStr,
        reload: bool = False,
        headers: dict = {},
        extra_args: dict = {},
        test_connection: bool = False,
    ):
        for namespace in namespaces:
            if test_connection:
                url = sanitize_url(f"{base_url}/{namespace}")
                fs, _ = fsspec.core.url_to_fs(url, **extra_args)
                if fs.exists(url):
                    logger.info(f"Package at {url} is OK")
                else:
                    msg = f"Module '{namespace}' not found in '{url}'.\n"
                    msg += "Check network and module name"
                    logger.critical(msg)
                    raise ModuleNotFoundError(msg)

            for importer in [i for i in sys.meta_path if isinstance(i, RemoteImporter)]:
                if namespace == importer.namespace:
                    if reload:
                        importer.__headers = headers
                        importer.__base_url = base_url
                        for module in [m for m in sys.modules if namespace in m]:
                            logger.debug(f"Updating importer - headers: {headers}, base_url: {base_url}")
                            importlib.reload(sys.modules[module])
                    else:
                        logger.warning(
                            f"Namespace {namespace} already imported."
                            "Use reload=True if you want to force reload."
                        )
                    return importer
            # IMPORTANT: must be added to the first item
            # because some finder along the lines mess up with "lib" keyword.
            importer = cls(namespace, base_url, headers=headers, extra_args=extra_args)
            sys.meta_path.insert(0, importer)
        return importer
