
from setuptools import setup, find_packages

version = '0.1'

setup(
    name='repozitory',
    version=version,
    description="A library for archiving documents using SQLAlchemy",
    long_description="See the documentation at "
        "http://packages.python.org/repozitory",
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[],
    keywords='repoze zodb sql sqlalchemy',
    author='Shane Hathaway',
    author_email='shane@hathawaymix.org',
    url='http://packages.python.org/repozitory',
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
