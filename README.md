# incusdev: Container dev tools with incus

This is a python library for interacting with incus containers in order to do containerised development.

This repo is to reduce code duplication because it is so useful to me.

This could be modified to work with any container system (or remote server)  that can use SSH, SCP and/or file sharing.

## Installation and use

- Install this library with

```bash
host $ venv activate <your-python-env>
host $ pip3 install --editable <this-directory> #  so source code changes will be used
```


## Todo

- add tests
- can we interact with incusdev using command line options / entry points?
- demonstrate/implement how to make this work with non-incus machines, such as remote machines and virtual machines that work with an ssh interface