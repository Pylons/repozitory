
from setuptools import setup, find_packages
import os

version = '1.1'

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

setup(
    name='repozitory',
    version=version,
    description="Simple document versioning for web apps, "
        "especially Pyramid apps.",
    long_description=README + '\n\nChanges\n=======\n\n' + CHANGES,
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[],
    keywords='pyramid pylons document version versioning sql sqlalchemy',
    author='Shane Hathaway',
    author_email='shane@hathawaymix.org',
    url='https://github.com/Pylons/repozitory',
    license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'psycopg2',
        'simplejson',
        'SQLAlchemy>=0.7.1',
        'zope.interface',
        'zope.schema',
        'zope.sqlalchemy',
    ],
    tests_require=['unittest2'],
    extras_require={'test': ['unittest2']},
    entry_points="""
    # -*- Entry points: -*-
    """,
)
