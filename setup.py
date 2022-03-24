"""Create the distribution file (pypi)."""
import importlib
import setuptools
from pathlib import Path

this_package_name = 'remote_import'
version_file = Path(__file__).absolute().parent / this_package_name / "__version__.py"


setuptools.setup(
    name=this_package_name,
    url="https://github.com/kiranmantri/python-remote_import",
    author="Kiran Mantripragada (and Lydia.ai team)",
    author_email="kiran.mantri@gmail.com",
    description="Enable the Python import subsystem to load libraries from remote (e.g. HTTP, S3, SSH).",
    version=importlib.import_module("remote_import.version", "__version__").__version__,
    long_description=open("README.rst").read(),
    packages=[this_package_name],
    python_requires=">=3.7",
    install_requires=[
        line for line in open("requirements.txt").read().split("\n") if not line.startswith("#")
    ],
    include_package_data=True,
    setup_requires=["wheel"],
)
