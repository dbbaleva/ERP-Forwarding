import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
    'alembic',
    'FormEncode',
    'WebHelpers2',
    'passlib',
    'reportlab',
    'xhtml2pdf',
    'WebTest'
    ]

setup(name='ERP',
      version='0.0',
      description='ERP',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='erp',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = erp:main
      [console_scripts]
      initialize_ERP_db = erp.scripts.initializedb:main
      """,
      )
