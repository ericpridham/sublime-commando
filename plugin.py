"""Commando - Plugin helpers.

"""
import sublime, sublime_plugin
import os
from . import core

class CommandoRun(sublime_plugin.ApplicationCommand):
  def run(self, commands=None, context=None):
    if commands is None:
      commands = self.commands()

    if commands:
      core.run_commando(commands, context=context)

  def commands(self):
    """Overwrite in child class."""
    return None

  def get_window(self):
    return core.get_window_by_context(core.init_active_context())

  def get_view(self):
    return core.get_view_by_context(core.init_active_context())

  def get_path(self):
    """Grab the path to the current context."""
    context = core.init_active_context()
    return core.get_working_dir(context)

class CommandoCmd(sublime_plugin.ApplicationCommand):
  def run(self, context=None):
    # context needs to be a kwarg, otherwise it won't be useable as a Sublime command.
    if context is None:
      return

    # process the arg vars
    self._do_var_subs(context, context['args'])

    # allow the user to override input through command args
    if 'input' in context['args']:
      context['input'] = context['args']['input']
      context['args']['input'] = None

    # pop input and args
    cmd_input = context['input']
    cmd_args = context['args']
    context['input'] = None
    context['args'] = {}

    # note: cmd can manipulate context any way it wants
    ret = self.cmd(context, cmd_input, cmd_args)

    # continue the chain
    if ret != False:
      core.next_commando(context)

  def cmd(self, context):
    """Override on child."""
    pass

  def get_window(self, context):
    return core.get_window_by_context(context)

  def get_view(self, context):
    return core.get_view_by_context(context)

  def get_filename(self, context):
    view = core.get_view_by_context(context)
    return self.get_path(context, view.file_name())

  def get_path(self, context, filename=None):
    working_dir = core.get_working_dir(context)
    if working_dir:
      return working_dir + ('/' + filename if filename else '')
    return None

  def _do_var_subs(self, context, items):
    if isinstance(items, list):
      for i, val in enumerate(items):
        items[i] = self._var_sub(context, val)
    elif isinstance(items, list):
      for k, val in items.iteritems():
        items[k] = self._var_sub(context, val)

  def _var_sub(self, context, val):
    if val == '$file':
      if self.get_view(context) and self.get_view(context).file_name():
        return self.get_view(context).file_name()
    if val == '$input':
      return context['input']
    return val
