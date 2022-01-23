
import logging
import shutil
import textwrap
import typing as t
from pathlib  import Path

from cleo.helpers import option
from flit.install import Installer
from nr.util.algorithm import longest_common_substring
from nr.util.fs import atomic_swap
from poetry.console.application import Application
from poetry.console.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin
from setuptools import find_namespace_packages

if t.TYPE_CHECKING:
  from tomlkit.toml_document import TOMLDocument


def pick_modules_with_init_py(directory: Path, modules: list[str]) -> list[str]:
  def _filter(module: str) -> bool:
    return (directory / module.replace('.', '/') / '__init__.py').is_file()
  return list(filter(_filter, modules))


def identify_flit_module(directory: Path) -> str:
  """ Identifies the name of the module that is contained in *directory*. This uses #find_namespace_packages()
  and then tries to identify the one main module name that should be passed to the `tool.flit.metadata.module`
  option. """

  modules = find_namespace_packages(directory)
  if not modules:
    raise ValueError(f'no modules discovered in {directory}')

  if len(modules) > 1:
    modules = pick_modules_with_init_py(directory, modules)

  if len(modules) > 1:
    # If we stil have multiple modules, we try to find the longest common path.
    common = longest_common_substring(*(x.split('.') for x in modules), start_only=True)
    if not common:
      raise ValueError(f'no common root package modules: {modules}')
    return '.'.join(common)

  return modules[0]


class LinkCommand(Command):
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
      • add <b>project</b>
        • the <b>module</b> is derived automatically using <fg=cyan>setuptools.find_namespace_packages()</fg> on the
          <b>src/</b> directory, if it exists, or otherwise on the current directory. Note that Flit
          only supports installing one package at a time, so it will be an error if setuptools
          discovers more than one package.

    Then, while the configuration is in an updated state, <fg=cyan>$ flit install -s --python `which python`</fg> is
    invoked. This will symlink your package into your currently active Python environment. (Note that right
    now, the plugin does not support auto-detecting the virtual environment automatically created for you by
    Poetry and the environment in which you want to symlink the package to needs to be active).

    Finally, the configuration is reverted to its original state.

  <info>This command is available because you have the <b>poetry-link</b> package installed.</info>
  """

  name = "link"
  description = "Install your package in development mode using Flit."
  help = textwrap.dedent(__doc__)
  options = [
    option(
      "python",
      description="The Python executable to link the package to.",
      flag=False,
      default="python",
    ),
    option(
      "dump-pyproject",
      description="Dump the updated pyproject.toml and do not actually do the linking.",
    )
  ]

  def handle(self) -> int:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    if not self.setup_flit_config(self.poetry.pyproject.data):
      return 1
    pyproject_file = Path('pyproject.toml')
    if self.option('dump-pyproject'):
      from tomlkit import dumps
      print(dumps(self.poetry.pyproject.data))
      return

    with atomic_swap(pyproject_file, 'w', always_revert=True) as fp:
      fp.close()
      self.poetry.pyproject.save()
      installer = Installer.from_ini_path(pyproject_file, python=shutil.which(self.option("python")), symlink=True)
      installer.install()

  def setup_flit_config(self, data: 'TOMLDocument') -> bool:
    """ Copies and transforms some of the Poetry tool configuration to Flit tool configuration in the PyProject
    configuration. """

    from tomlkit import table

    poetry = data['tool'].get('poetry', {})
    plugins = poetry.get('plugins', table()).value
    scripts = poetry.get('scripts', table()).value

    if 'project' in data:
      project = data['project']
    else:
      project = table()
      data.add('project', project)

    if plugins:
      project.add('entry-points', plugins)
    if scripts:
      project.add('scripts', scripts)

    # TODO (@NiklasRosenstein): Do we need to support gui-scripts as well?

    module = identify_flit_module(self.get_source_directory())
    project.add('name', module)
    project.add('version', poetry['version'])
    project.add('description', '')

    return True

  def get_source_directory(self) -> Path:
    directory = Path.cwd()
    if (src_dir := directory / 'src').is_dir():
      directory = src_dir
    return directory


class LinkPlugin(ApplicationPlugin):

  def activate(self, application: Application):
    application.command_loader.register_factory("link", LinkCommand)
