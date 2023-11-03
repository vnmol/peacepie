from setuptools import setup, find_packages

setup(
    name='simple_kafka_downloader',
    version='0.0.1',
    packages=find_packages(),
    install_requires=[
        'aiokafka==0.8.0',
    ],
)