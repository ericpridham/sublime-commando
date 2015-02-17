"""Commando - Plugin helpers.

"""
import sublime, sublime_plugin
import os
from . import core

class Commando:
  def init_context(self):
    return {
      "window_id": self._get_window_id(),
      "view_id": self._get_view_id(),
      "args": {},
      "input": None,
      "commands": [],
    }

  def _get_window_id(self):
    return core.get_active_window_id()

  def _get_view_id(self):
    return core.get_active_view_id()

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

  def run(self, context=None):
    if context is None:
      context = self.init_context()

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
      core.devlog("FFF:"+str(context))
      self.commando(context)

  def commando(self, context, commands=None):
    core.commando(context, commands)

  def cmd(self, context):
    pass

  def get_window(self, context=None):
    if context is None:
      context = self.init_context()
    return core.get_window_by_context(context)

  def get_view(self, context=None):
    if context is None:
      context = self.init_context()
    return core.get_view_by_context(context)

  # Note: This goes here instead of in the inherited classes because we're
  # basing the working dir off of the context (which comes from the initial command)
  # not off the type of the current command.
  def get_working_dir(self, context=None):
    if context is None:
      context = self.init_context()
    window = core.get_window_by_context(context)
    view = core.get_view_by_context(context)
    if window and window.folders():
      # find the folder that is a subset of the full file path
      if view and view.file_name():
        for folder in window.folders():
          if view.file_name().find(folder) == 0:
            return folder
      # otherwise, just use the first folder
      return window.folders()[0]
    if view and view.file_name():
      return os.path.dirname(view.file_name())
    return None

  def get_filename(self, context):
    view = core.get_view_by_context(context)
    return self.get_path(context, view.file_name())

  def get_path(self, context, filename=None):
    working_dir = self.get_working_dir(context)
    if working_dir:
      return working_dir + ('/' + filename if filename else '')

    return None

  def panel(self, context, content):
    if content:
      core.panel(context, content)

  def quick_panel(self, context, items, on_done):
    core.quick_panel(context, items, on_done)

  def input_panel(self, context, caption, initial_text, on_done, on_change=None, on_cancel=None):
    core.input_panel(context, caption, initial_text, on_done, on_change, on_cancel)

  def new_file(self, context, content, name=None, scratch=None, readonly=None, syntax=None):
    if content and content.rstrip() != '':
      return core.new_file(context, content.rstrip(), name=name, scratch=scratch, readonly=readonly, syntax=syntax)
    return None

  def open_file(self, context, filename):
    return core.open_file(context, filename)


class ApplicationCommando(Commando, sublime_plugin.ApplicationCommand):
  pass

class WindowCommando(Commando, sublime_plugin.WindowCommand):
  def _get_window_id(self):
    return self.window.id()

class TextCommando(Commando, sublime_plugin.TextCommand):
  def run(self, edit, context=None):
    if context is None:
      context = self.init_context()
    if context['args'] is None:
      context['args'] = {}
    context['args']['edit'] = edit
    return Commando.run(self, context=context)

  def _get_window_id(self):
    return self.view.window().id()

  def _get_view_id(self):
    return self.view.id()

