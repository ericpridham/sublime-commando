"""Simplifies integrating with command-line tools.

The 'exec' command is too specific to builds to be used to call generic command
line commands. This plugin creates a new command, 'commando_exec' for just that
purpose. It accepts commands similar to 'exec', but instead of outputting to
a panel, it calls a provided callback with the output. This allows greater
control over what to do with the output, as well as allows chaining multiple
exec calls to create a more complicated process flow.

Then it goes a step further and creates an abstract class to wrap around a
specific binary (say, git) to make it easier to integrate with specific apps.
Finally, it provides subclasses for WindowCommand and TextCommand to make
writing specific Sublime Text commands that integrate with the command wrapper
easier.

Note: This code started as a copy of Default/exec.py, and was modified from
there. Some of the clarifying comments were kept from the original.
"""

import sublime, sublime_plugin
import os, sys
import threading
import subprocess
import functools
import time

import collections
import pipes
import string

from Default.exec import ProcessListener, AsyncProcess

class CommandoKillCommand(sublime_plugin.WindowCommand):
  def run(self):
    sublime.run_command("commando_exec", {"kill": True})
#
# Module functions
#

def class_to_command(cls):
  clsname = cls.__name__
  name = clsname[0].lower()
  last_upper = False
  for c in clsname[1:]:
      if c.isupper() and not last_upper:
          name += '_'
          name += c.lower()
      else:
          name += c
      last_upper = c.isupper()
  if name.endswith("_command"):
      name = name[0:-8]
  return name

def get_command_type(command):
  for c in sublime_plugin.application_command_classes:
    if class_to_command(c) == command:
      return 'app'
  for c in sublime_plugin.window_command_classes:
    if class_to_command(c) == command:
      return 'window'
  for c in sublime_plugin.text_command_classes:
    if class_to_command(c) == command:
      return 'text'
  return None

def get_window_by_id(id):
  for window in sublime.windows():
    if window.id() == id:
      return window
  return None

def get_window_by_context(context):
  if context and context['window_id']:
    return get_window_by_id(context['window_id'])
  return sublime.active_window();

def get_view_by_context(context):
  if context and context['window_id'] and context['view_id']:
    return get_view_by_id(context['window_id'], context['view_id'])
  elif sublime.active_window():
    return sublime.active_window().active_view();
  return None

def get_view_by_id(window_id, view_id):
  window = get_window_by_id(window_id)
  if window:
    for view in window.views():
      if view.id() == view_id:
        return view
  return None

def panel(content, context, name="commando"):
  if content and content.rstrip() != '':
    window = get_window_by_context(context)
    p = window.create_output_panel(name)
    p.run_command("simple_insert", {"contents": content})
    window.run_command("show_panel", {"panel":"output."+name})

def select(items, command, context, flags=sublime.MONOSPACE_FONT):
  def on_done(i):
    if i != -1:
      commando(command, context, input=items[i])

  get_window_by_context(context).show_quick_panel(items, on_done, flags)

def new_file(content, context, name=None, scratch=None, ro=None, syntax=None):
  new_view = get_window_by_context(context).new_file()
  if name:
    new_view.set_name(name)
  if scratch:
    new_view.set_scratch(True)
  if syntax:
    new_view.set_syntax_file("Packages/"+syntax+"/"+syntax+".tmLanguage")
  new_view.run_command("simple_insert", {"contents": content})
  if ro:
    new_view.set_read_only(True)

def open_file(filename, context):
  if os.path.exists(filename):
    get_window_by_context(context).open_file(filename)
  else:
    sublime.error_message('File not found:' + filename)

def exec_command(cmd, working_dir=None, env=None, context=None, callback=None):
  # by default display the output in a panel
  if callback is None:
    callback = "app.commando_show_panel"

  sublime.run_command("commando_exec",
                      {"cmd": cmd, "working_dir": working_dir, "env": env,
                       "context": context, "callback": callback })

def commando(commands, context, input=None):
  if isinstance(commands, str):
    commands = [commands]
  elif not isinstance(commands, list):
    commands = []

  next_command = commands.pop(0)

  if isinstance(next_command, list):
    cmd_args = next_command[1]
    next_command = next_command[0]
  else:
    cmd_args = {}

  command_type = get_command_type(next_command)

  if not command_type:
    print('Command not found: ' + next_command)
    return

  runner = None

  if command_type == 'app':
    runner = sublime

  elif command_type == 'window':
    if not context['window_id']:
      print('Context error (window)')
    else:
      window = get_window_by_id(context['window_id'])
      if not window:
        print('Could not find window')
      else:
        runner = window

  elif command_type == 'text':
    if not context['window_id'] or not context['view_id']:
      print('Context error (view)')
    else:
      view = get_view_by_id(context['window_id'], context['view_id'])
      if not view:
        print('Could not find view')
      else:
        runner = view
  else:
    print('Unsupported command context')

  if runner:
    runner.run_command(next_command, {
      "context": context,
      "callback": commands,
      "input": input,
      "cmd_args": cmd_args
    })

#
# Helper commands
#

class Commando:
  """The core for commando commands.

  """
  context = None
  callback = None

  def get_context(self):
    if self.context:
      return self.context

    return {"window_id": self.get_window_id(), "view_id": self.get_view_id()}

  def get_window_id(self):
    if sublime.active_window():
      return sublime.active_window().id()
    return None

  def get_view_id(self):
    if sublime.active_window() and sublime.active_window().active_view():
      return sublime.active_window().active_view().id()
    return None

  def get_window(self):
    return get_window_by_context(self.get_context())

  def get_view(self):
    return get_view_by_context(self.get_context())

  def commando(self, commands, input=None):
    commando(commands, self.get_context(), input=input)

  def run(self, context=None, callback=None, input=None, cmd_args=None):
    self.context = context
    self.callback = callback
    if cmd_args is None:
      cmd_args = {}

    input = self.cmd(input, cmd_args)
    if input != False and callback:
        commando(callback, context, input=input)

  def cmd(self, input, args=None):
    return input

  # Note: This goes here instead of in the inherited classes because we're
  # basing the working dir off of the context (which comes from the initial command)
  # not off the type of the current command.
  def get_working_dir(self):
    context = self.get_context()
    if context:
      if context['window_id'] and context['view_id']:
        view = get_view_by_id(context['window_id'], context['view_id'])
        if view.file_name():
          return os.path.dirname(view.file_name())

      elif context['window_id']:
        window = get_window_by_id(context['window_id'])
        if window.folders():
          return window.folders()[0]

  def get_filename(self):
    view = get_view_by_context(self.get_context())
    return self.get_path(view.file_name())

  def get_path(self, filename=None):
    context = self.get_context()
    if context and context['window_id']:
      window = get_window_by_id(context['window_id'])
      if window.folders():
        return window.folders()[0] + ('/' + filename if filename else '')


    return None

  def panel(self, content):
    if content:
      panel(content, context=self.get_context())

  def select(self, items, on_done):
    select(items, on_done, self.get_context())

  def new_file(self, content, name=None, scratch=None, ro=None, syntax=None):
    if content and content.rstrip() != '':
      new_file(content.rstrip(), self.get_context(), name=name, scratch=scratch, ro=ro, syntax=syntax)

  def open_file(self, filename):
    open_file(filename, self.get_context())


class ApplicationCommando(Commando, sublime_plugin.ApplicationCommand):
  pass

class WindowCommando(Commando, sublime_plugin.WindowCommand):
  def get_window_id(self):
    return self.window.id()

class TextCommando(Commando, sublime_plugin.TextCommand):
  def run(self, edit, context=None, callback=None, input=None, cmd_args=None):
    return Commando.run(self, context=context, callback=callback, input=input, cmd_args=cmd_args)

  def get_window_id(self):
    return self.view.window().id()

  def get_view_id(self):
    return self.view.id()

class CommandoCommand(ApplicationCommando):
  def cmd(self):
    pass

class CommandoExecCommand(ApplicationCommando, ProcessListener):
  """Simplified version of ExecCommand from Default/exec.py that supports chaining."""
  cmd = None
  proc = None
  encoding = None

  output = ""
  loop = 0
  longrun = False

  def cmd(self, input, args):

    if not 'cmd' in args:
      return

    # override default behavior with params if provided
    if 'context' in args:
      self.context = args['context']
    if 'callback' in args:
      self.callback = args['callback']

    if self.proc and not kill:
      # ignore overlapping commando calls
      return

    # kill running proc (if exists)
    if 'kill' in args:
      if self.proc:
        self.proc.kill()
        self.proc = None
      return

    if 'encoding' in args:
      self.encoding = args['encoding']
    else:
      self.encoding = 'utf-8'

    self.proc = None

    if 'working_dir' in args:
      working_dir = args['working_dir']
    else:
      working_dir = self.get_working_dir()

    # Change to the working dir, rather than spawning the process with it,
    # so that emitted working dir relative path names make sense
    if working_dir is not None:
      os.chdir(working_dir)

    if 'env' in args:
      env = args['env']
    else:
      env = {}

    try:
      self.proc_cmd = args['cmd']
      self.proc = AsyncProcess(args['cmd'], None, env, self)
      self.longrun = False
      sublime.set_timeout(self.watch_proc, 500)

    except Exception as e:
      self.append_output(str(e) + "\n")

    # we're handling our own callback, so cancel the bubble
    return False

  def is_enabled(self, kill=False):
    if kill:
      return (self.proc != None) and self.proc.poll()
    else:
      return True

  def watch_proc(self):
    self.loop = (self.loop+1) % 4

    if self.proc is not None and self.proc.poll():
      # we don't want to flash the status bar with commands that run quickly,
      # so we only show status bar after the first watch_proc call
      self.longrun = True
      sublime.status_message(' '.join(self.proc_cmd) + ': Running' +
                             '.' * self.loop + ' ' * (3 - self.loop))
      sublime.set_timeout(lambda: self.watch_proc(), 200)

    elif self.longrun:
      sublime.status_message(' '.join(self.proc_cmd) + ': Done!')
      sublime.set_timeout(lambda: sublime.status_message(''), 3000)

  def append_output(self, string):
    self.output += string

  def finish(self, proc):
    exit_code = proc.exit_code()

    if proc != self.proc:
      return

    if self.callback:
      commando(self.callback, self.context, input=self.output)

    self.proc = None
    self.output = ""

  def on_data(self, proc, data):
    if proc != self.proc:
      return

    try:
      string = data.decode(self.encoding)

    except Exception:
      print("[Decode error - output not " + self.encoding + "]\n")
      string = ""
      proc = None

    # Normalize newlines, Sublime Text always uses a single \n separator
    # in memory.
    string = string.replace('\r\n', '\n').replace('\r', '\n')

    self.append_output(string)

  def on_finished(self, proc):
    if proc != self.proc:
      return

    sublime.set_timeout(lambda: self.finish(proc), 0)

class SimpleInsertCommand(sublime_plugin.TextCommand):
  def run(self, edit, contents):
    self.view.insert(edit, 0, contents)
    self.view.run_command("goto_line", {"line":1})

class CommandoShowPanelCommand(ApplicationCommando):
  def cmd(self, input):
    if input:
      panel(input, context=self.get_context())

class CommandoNewFileCommand(ApplicationCommando):
  def cmd(self, input, args):#name=None, scratch=None, ro=None, syntax=None):
    if input and input.rstrip() != '':
      name = scratch = ro = syntax = None
      if 'name' in args:
        name = args['name']
      if 'scratch' in args:
        scratch = args['scratch']
      if 'ro' in args:
        ro = args['ro']
      if 'syntax' in args:
        syntax = args['syntax']
      new_file(content.rstrip(), self.get_context(), name=name, scratch=scratch, ro=ro, syntax=syntax)

class CommandoOpenFileCommand(ApplicationCommando):
  def cmd(self, input):
    if os.path.exists(input):
      new_file(content.rstrip(), self.get_context(), name=name, scratch=scratch, ro=ro, syntax=syntax)

class CommandoSelectCommand(ApplicationCommando):
  def cmd(self, input, args):#on_done=None):
    if 'on_done' in args:
      on_done = args['on_done']
    else:
      on_done = None

    if input:
      select(input, on_done, self.get_context())
    else:
      select([['Nothing to select.']], on_done, self.get_context())
