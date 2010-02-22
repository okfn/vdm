from setuptools import setup, find_packages

from vdm import __version__
from vdm import __description__
from vdm import __doc__ as __long_description__

setup(
    name = 'vdm',
    version = __version__,
    packages = find_packages(),
    install_requires = [ ],

    # metadata for upload to PyPI
    author = "Rufus Pollock (Open Knowledge Foundation)",
    author_email = "info@okfn.org",
    description = __description__,
    long_description = __long_description__,
    license = "MIT",
    keywords = "versioning sqlobject sqlalchemy orm",
    url = "http://www.okfn.org/vdm/", 
    download_url = "http://knowledgeforge.net/ckan/vdm",
    zip_safe = False,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'],
)
