from setuptools import setup, find_packages

setup(
    name='peacepie',
    version='0.0.7',
    description='A simple actor system',
    long_description='This is a simple actor system.',
    license='MIT',
    author='Vladimir Molodtsov',
    author_email='vmol@mail.ru',
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
