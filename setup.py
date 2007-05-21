from setuptools import setup, find_packages

from vdm import __version__
from vdm import __description__
from vdm import __long_description__

setup(
    name = 'vdm',
    version = __version__,
    packages = find_packages(),
    install_requires = [ 'SQLObject >= 0.7' ],
    scripts = [],

    # metadata for upload to PyPI
    author = "Rufus Pollock (Open Knowledge Foundation)",
    author_email = "rufus@rufuspollock.org",
    description = __description__,
    long_description = __long_description__,
    license = "MIT",
    keywords = "versioning subversion python sqlobject",
    url = "http://p.knowledgeforge.net/ckan/svn/vdm/", 
    download_url = "http://p.knowledgeforge.net/ckan/svn/vdm/trunk",
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'],
)
