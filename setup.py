# https://godatadriven.com/blog/a-practical-guide-to-using-setup-py/

from setuptools import setup, find_packages

setup(
    name='incusdev',
    version='0.0.1',
    packages=find_packages(include=['incusdev']),
	install_requires=[
        "loguru",
		"paramiko"
    ],
	 entry_points = {
        'console_scripts': ['incusdev=incusdev.standalone_cli:main'],
    }
)
