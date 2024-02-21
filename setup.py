# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='wcmatch',
    version='9.0',
    description='Wildcard/glob file name matcher.',
    author_email='Isaac Muse <Isaac.Muse@gmail.com>',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Typing :: Typed',
    ],
    install_requires=[
        'bracex>=2.1.1',
    ],
    packages=[
        'wcmatch',
    ],
)
