from setuptools import setup
from setuptools.command.install import install
import subprocess

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        subprocess.call(['python', 'patch_treetaggerwrapper.py'])

setup(
    name='myrepository',
    version='1.0',
    packages=['Scripts'],
    install_requires=[
        'pandas',
        'nltk',
        'beautifulsoup4',
        'treetaggerwrapper',
        'scikit-learn',
        'streamlit',
        'openpyxl',
    ],
    cmdclass={
        'install': PostInstallCommand,
    },
)
