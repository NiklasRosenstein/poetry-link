# poetry-lock

Poetry natively does not support editable installs (as of writing this on Jan 22, 2022). This
command makes use of the Flit backend to leverage its excellent symlink support. Relevant parts of
the Poetry configuration will by adpated such that no Flit related configuration needs to be added
to pyproject.toml.

## Example usage:

    $ poetry link
    Discovered modules in /projects/poetry-link/src: my_package
    Extras to install for deps 'all': {'.none'}
    Symlinking src/my_package -> .venv/lib/python3.10/site-packages/my_package

## How it works

First, the Poetry configuration in pyproject.toml will be updated temporarily to contain the
relevant parts in the format that Flit understands. The changes to the configuration include

* copy tool.poetry.plugins -> tool.flit.entrypoints
* copy tool.poetry.scripts -> tool.flit.scripts
* add tool.flit.metadata
  * the module is derived automatically using setuptools.find_namespace_packages() on the
    src/ directory, if it exists, or otherwise on the current directory. Note that Flit
    only supports installing one package at a time, so it will be an error if setuptools
    discovers more than one package.

Then, while the configuration is in an updated state, $ flit install -s --python python is
invoked. This will symlink your package into your currently active Python environment. (Note that right
now, the plugin does not support auto-detecting the virtual environment automatically created for you by
Poetry and the environment in which you want to symlink the package to needs to be active).

Finally, the configuration is reverted to its original state.
