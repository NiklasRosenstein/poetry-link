
""" A Poetry plugin to add a "link" command. """

__version__ = '0.1.5'

from poetry.console.application import Application
from poetry.plugins.application_plugin import ApplicationPlugin

from shut.commands.link import LinkCommand as _LinkCommand
from shut.util.cleo import add_style


class LinkCommand(_LinkCommand):

  def handle(self) -> int:
    add_style(self.io, 'u', options=['underline'])
    add_style(self.io, 'opt', foreground='cyan', options=['italic'])
    return super().handle()


class LinkCommandPlugin(ApplicationPlugin):

  def activate(self, application: Application):
    application.command_loader.register_factory("link", LinkCommand)
