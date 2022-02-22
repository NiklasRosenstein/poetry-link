# poetry-link

Poetry natively does not support editable installs (as of writing this on Jan 22, 2022). This
command makes use of the Flit backend to leverage its excellent symlink support. Relevant parts of
the Poetry configuration will by adpated such that no Flit related configuration needs to be added
to `pyproject.toml`.

This package depends on [Slam](https://pypi.org/project/slam-cli/) for the `slam link` command and
exposes it as plugin in Poetry.

### Example usage

    $ poetry link
    Discovered modules in /projects/my-package/src: my_package
    Extras to install for deps 'all': {'.none'}
    Symlinking src/my_package -> .venv/lib/python3.10/site-packages/my_package
