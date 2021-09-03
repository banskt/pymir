import sys
import atexit
import setuptools
from setuptools.command.bdist_egg import bdist_egg

sys.path.append('src')
from version import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

class bdist_egg_disabled(bdist_egg):
    """Disabled version of bdist_egg
    Prevents setup.py install performing setuptools' default easy_install,
    which it should never ever do.
    """
    def run(self):
        sys.exit("ERROR: aborting implicit building of eggs. Use \"pip install .\" to install from source.")

cmdclass = {'bdist_egg': bdist_egg if 'bdist_egg' in sys.argv else bdist_egg_disabled}

setuptools.setup(
    name             = "pymir", # Replace with your own username
    version          = __version__,
    author           = "Saikat Banerjee",
    author_email     = "bnrj.saikat@gmail.com",
    description      = "Personal Python tools for analysis and plotting",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    license          = "MIT",
    url              = "https://github.com/banskt/pymir",
    project_urls     = {
        "Bug Tracker": "https://github.com/banskt/pymir/issues",
    },
    classifiers      = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir      = {"": "src"},
    packages         = ["pymir"],
    python_requires  = ">=3.7",
    install_requires = [
        "numpy>=1.19.4",
        "matplotlib>=3.3.4",
    ],
    cmdclass         = cmdclass,
)
