
import logging
import textwrap
import typing as t
from pathlib  import Path

from cleo.io.outputs.output import Verbosity
from flit.install import Installer
from nr.util.fs import atomic_swap
from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin
from setuptools import find_namespace_packages

if t.TYPE_CHECKING:
  from tomlkit.toml_document import TOMLDocument


class PoetryLinkCommand(Command):
  """
  Poetry natively does not support editable installs (as of writing this on Jan 22, 2022). This
  command makes use of the <fg=green>Flit</fg> backend to leverage its excellent symlink support. Relevant parts of
  the Poetry configuration will by adpated such that no Flit related configuration needs to be added
  to <fg=cyan>pyproject.toml</fg>.

  <b>Example usage:</b>

    <fg=cyan>$ poetry link</fg>
    Discovered modules in /projects/poetry-link/src: my_package
    Extras to install for deps 'all': {{'.none'}}
    Symlinking src/my_package -> .venv/lib/python3.10/site-packages/my_package

  <b>How it works</b>

    First, the Poetry configuration in <fg=cyan>pyproject.toml</fg> will be updated temporarily to contain the
    relevant parts in the format that Flit understands. The changes to the configuration include

      • copy <fg=cyan>tool.poetry.plugins</fg> -> <b>tool.flit.entrypoints</b>
      • copy <fg=cyan>tool.poetry.scripts</fg> -> <b>tool.flit.scripts</b>
      • add <b>tool.flit.metadata</b>
        • the <b>module</b> is derived automatically using <fg=cyan>setuptools.find_namespace_packages()</fg> on the
          <b>src/</b> directory, if it exists, or otherwise on the current directory. Note that Flit
          only supports installing one package at a time, so it will be an error if setuptools
          discovers more than one package.

    Then, while the configuration is in an updated state, <fg=cyan>$ flit install -s --python python</fg> is
    invoked. This will symlink your package into your currently active Python environment. (Note that right
    now, the plugin does not support auto-detecting the virtual environment automatically created for you by
    Poetry and the environment in which you want to symlink the package to needs to be active).

    Finally, the configuration is reverted to its original state.

  <info>This command is available because you have the <b>poetry-link</b> package installed.</info>
  """

  name = "link"
  description = "Install your package in development mode using Flit."
  help = textwrap.dedent(__doc__)

  def handle(self) -> int:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    self.setup_flit_config(self.poetry.pyproject.data)
    pyproject_file = Path('pyproject.toml')
    with atomic_swap(pyproject_file, 'w', always_revert=True) as fp:
      fp.close()
      self.poetry.pyproject.save()
      installer = Installer.from_ini_path(pyproject_file, python='python', symlink=True)
      installer.install()

  def setup_flit_config(self, data: 'TOMLDocument') -> None:
    """ Copies and transforms some of the Poetry tool configuration to Flit tool configuration in the PyProject
    configuration. """

    from tomlkit import table

    poetry = data['tool'].get('poetry', {})
    plugins = poetry.get('plugins', table()).value
    scripts = poetry.get('scripts', table()).value

    flit = table()
    data['tool'].add('flit', flit)

    if plugins:
      flit.add('entrypoints', plugins)
    if scripts:
      flit.add('scripts', scripts)

    # TODO (@NiklasRosenstein): Do we need to support gui-scripts as well?

    directory = Path.cwd()
    if (src_dir := directory / 'src').is_dir():
      directory = src_dir

    modules = find_namespace_packages(directory)
    self.line(f'Discovered modules in <fg=cyan>{directory}</fg>: {", ".join(modules)}', None, Verbosity.VERBOSE)

    flit.add('metadata', {
      'module': modules[0],
      'author': poetry['authors'][0]
    })


class PoetryLinkPlugin(ApplicationPlugin):

  def activate(self, application: Application):
    application.command_loader.register_factory("link", PoetryLinkCommand)
