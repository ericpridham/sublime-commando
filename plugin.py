import sublime, sublime_plugin
import os
from . import core

class Commando:
  context = None
  callback = None
  input = None
  cmd_args = None

  def _get_context(self):
    if self.context:
      return self.context
    return {"window_id": self._get_window_id(), "view_id": self._get_view_id()}

  def _get_window_id(self):
    if sublime.active_window():
      return sublime.active_window().id()
    return None

  def _get_view_id(self):
    if sublime.active_window() and sublime.active_window().active_view():
      return sublime.active_window().active_view().id()
    return None

  def _do_var_subs(self, items):
    if isinstance(items, list):
      for i, val in enumerate(items):
        items[i] = self._var_sub(val)
    elif isinstance(items, list):
      for k, val in items.iteritems():
        items[k] = self._var_sub(val)
    return items

  def _var_sub(self, val):
    if val == '$file':
      if self.get_view() and self.get_view().file_name():
        return self.get_view().file_name()
    if val == '$input':
      return self.input
    return val

  def commando(self, commands, input=None):
    core.commando(self._get_context(), commands, input=input)

  def run(self, context=None, callback=None, input=None, cmd_args=None):
    self.context = context
    self.callback = callback

    if cmd_args is None:
      self.cmd_args = {}
    else:
      self.cmd_args = self._do_var_subs(cmd_args)

    if 'input' in self.cmd_args:
      self.input = self.cmd_args['input']
    else:
      self.input = input

    self.input = self.cmd(self.input, self.cmd_args)
    if self.input != False and self.callback:
        self.commando(self.callback, input=self.input)

  def cmd(self, input, args=None):
    return input

  def get_window(self):
    return core.get_window_by_context(self._get_context())

  def get_view(self):
    return core.get_view_by_context(self._get_context())

  # Note: This goes here instead of in the inherited classes because we're
  # basing the working dir off of the context (which comes from the initial command)
  # not off the type of the current command.
  def get_working_dir(self):
    context = self._get_context()
    if context:
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

  def get_filename(self):
    view = core.get_view_by_context(self._get_context())
    return self.get_path(view.file_name())

  def get_path(self, filename=None):
    working_dir = self.get_working_dir()
    if working_dir:
      return working_dir + ('/' + filename if filename else '')

    return None

  def panel(self, content):
    if content:
      core.panel(self._get_context(), content)

  def quick_panel(self, items, on_done):
    core.quick_panel(self._get_context(), items, on_done)

  def input_panel(self, caption, initial_text, on_done, on_change, on_cancel):
    core.input_panel(self._get_context(), caption, initial_text, on_done, on_change, on_cancel)

  def new_file(self, content, name=None, scratch=None, ro=None, syntax=None):
    if content and content.rstrip() != '':
      core.new_file(self._get_context(), content.rstrip(), name=name, scratch=scratch, ro=ro, syntax=syntax)

  def open_file(self, filename):
    core.open_file(self._get_context(), filename)


class ApplicationCommando(Commando, sublime_plugin.ApplicationCommand):
  pass

class WindowCommando(Commando, sublime_plugin.WindowCommand):
  def _get_window_id(self):
    return self.window.id()

class TextCommando(Commando, sublime_plugin.TextCommand):
  def run(self, edit, context=None, callback=None, input=None, cmd_args=None):
    if cmd_args is None:
      cmd_args = {}
    cmd_args['edit'] = edit
    return Commando.run(self, context=context, callback=callback, input=input, cmd_args=cmd_args)

  def _get_window_id(self):
    return self.view.window().id()

  def _get_view_id(self):
    return self.view.id()

