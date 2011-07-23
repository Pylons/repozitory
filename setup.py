
from setuptools import setup, find_packages

version = '0.1dev'

setup(
    name='repozitory',
    version=version,
    description="SQLAlchemy repository for Python objects",
    long_description="",
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[],
    keywords='repoze sql sqlalchemy',
    author='Shane Hathaway',
    author_email='shane@hathawaymix.org',
    url='http://pypi.python.org/pypi/repozitory',
    license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'psycopg2',
        'simplejson',
        'SQLAlchemy>=0.7.1',
        'zope.sqlalchemy',
    ],
    tests_require=['unittest2', 'transaction'],
    extras_require={'test': ['unittest2']},
    entry_points="""
    # -*- Entry points: -*-
    """,
)
