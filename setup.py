from setuptools import setup, find_packages

from vdm import __version__

setup(
    name = 'vdm',
    version = __version__,
    packages = find_packages(),
    install_requires = [ 'SQLObject >= 0.7' ],
    scripts = [],

    # metadata for upload to PyPI
    author = "Rufus Pollock (Open Knowledge Foundation)",
    author_email = "rufus@rufuspollock.org",
    description = \
"A versioned domain model framework.",
    long_description = \
"""
The vdm package allows you to 'version' your domain model objects in the same
way that source code version control systems such as subversion help you
version your code. At present the package is built as a simple extension on top
of SQLObject so that those already familiar with SQLObject for creating domain
 models will find it easy to use the versioning facilities provided by this
 library.
""",
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
