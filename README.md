# python-remote-import

Enable the Python import subsystem to load libraries from remote (e.g. HTTP, S3,
SSH).

# Install from pip

```
pip install -U remote_import
```

# Usage

## HTTP

Optionally, start a webserver, to test HTTP Remote Import:

```bash
git clone git@github.com:kiranmantri/python-remote-import
cd python-remote-import
python -m http.server 7777
```

```Python
from remote_import import RemoteImporter

RemoteImporter.add_remote(
    namespaces=['test_package'],
    base_url='http://0.0.0.0:7777/examples'
    )

from test_package.a import main
print(main())

from test_package.b import value
value
```

## Github

```Python
from remote_import import RemoteImporter

RemoteImporter.add_remote(
    namespaces=["test_package"],
    base_url ='github://kiranmantri:python-remote-import@/examples'
    )
```

## S3

```Python
from remote_import import RemoteImporter

RemoteImporter.add_remote(
    namespaces=["test_package"],
    base_url ='s3://bucket/folder'
    )
```

# Install from source

```
git clone git@github.com:kiranmantri/python-remote-import.git
cd python-remote-import
python install .
```

# Build

```
git clone git@github.com:kiranmantri/python-remote-import.git
cd python-remote-import
python setup.py bdist_wheel
```

```
```
