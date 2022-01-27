# https://godatadriven.com/blog/a-practical-guide-to-using-setup-py/

from setuptools import setup, find_packages

setup(
    name='lxdev',
    version='0.0.1',
    packages=find_packages(include=['lxdev']),
	install_requires=[
        "loguru",
		"paramiko"
    ],
	 entry_points = {
        'console_scripts': ['lxdev=lxdev.standalone_cli:main'],
    }
)
