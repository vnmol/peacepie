from setuptools import setup, find_packages

setup(
    name='simple_script_commander',
    version='0.0.1',
    packages=find_packages(),
    install_requires=[
        'asyncssh',
    ],
)