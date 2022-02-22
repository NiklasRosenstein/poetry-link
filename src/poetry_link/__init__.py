
""" A Poetry plugin to add a "link" command. """

from __future__ import annotations

__version__ = '0.1.6'

from poetry.console.application import Application
from poetry.plugins.application_plugin import ApplicationPlugin
from slam.ext.application.link import LinkCommandPlugin
from slam.util.cleo import add_style


class LinkCommand(LinkCommandPlugin):

  @staticmethod
  def factory() -> LinkCommand:
    from slam.application import Application
    app = Application()
    app.load_projects()
    command = LinkCommand()
    command.app = app
    return command

  def handle(self) -> int:
    add_style(self.io, 'u', options=['underline'])
    add_style(self.io, 'opt', foreground='cyan', options=['italic'])
    return super().handle()


class LinkCommandPlugin(ApplicationPlugin):

  def activate(self, application: Application):
    application.command_loader.register_factory("link", LinkCommand.factory)
