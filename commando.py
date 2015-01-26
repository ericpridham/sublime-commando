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

from Default.exec import ProcessListener, AsyncProcess

#
# Sublime commands

class CommandoKillCommand(sublime_plugin.WindowCommand):
  def run(self):
    sublime.run_command("commando_exec", {"kill": True})

class CommandoExecCommand(sublime_plugin.ApplicationCommand, ProcessListener):
  """Simplified version of ExecCommand from Default/exec.py"""
  cmd = None
  proc = None
  context = None
  callback = None
  encoding = None

  output = ""
  loop = 0
  longrun = False

  def run(self, cmd=None, working_dir=None, context=None, callback=None,
          env=None, kill=False, encoding="utf-8"):

    if self.proc and not kill:
      # ignore overlapping commando calls
      return

    self.context = context
    if isinstance(callback, str):
      callback = [callback]
    elif not isinstance(callback, list):
      callback = []
    self.callback = callback

    # kill running proc (if exists)
    if kill:
      if self.proc:
        self.proc.kill()
        self.proc = None
      return

    self.encoding = encoding
    self.proc = None

    # Change to the working dir, rather than spawning the process with it,
    # so that emitted working dir relative path names make sense
    if working_dir is not None:
      os.chdir(working_dir)

    if env is None:
      env = {}

    try:
      self.cmd = cmd
      self.proc = AsyncProcess(cmd, None, env, self)
      self.longrun = False
      sublime.set_timeout(self.watch_proc, 500)

    except Exception as e:
      self.append_output(str(e) + "\n")

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
      sublime.status_message(' '.join(self.cmd) + ': Running' +
                             '.' * self.loop + ' ' * (3 - self.loop))
      sublime.set_timeout(lambda: self.watch_proc(), 200)

    elif self.longrun:
      sublime.status_message(' '.join(self.cmd) + ': Done!')
      sublime.set_timeout(lambda: sublime.status_message(''), 3000)

  def append_output(self, string):
    self.output += string

  def finish(self, proc):
    exit_code = proc.exit_code()

    if proc != self.proc:
      return

    results = {"code": exit_code, "content": self.output}

    if self.callback:
      run_commands(self.callback, self.context, input=results)

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


#
# Module functions
#

def get_window_by_id(id):
  for window in sublime.windows():
    if window.id() == id:
      return window
  return None

def get_window_by_context(context):
  if context and context['window_id']:
    return get_window_by_id(context['window_id'])
  else:
    return sublime.active_window();

def get_view_by_id(window_id, view_id):
  window = get_window_by_id(window_id)
  if (window):
    for view in window.views():
      if view.id() == view_id:
        return view
  return None

def panel(content, name="commando", context=None):
  if content and content.rstrip() != '':
    window = get_window_by_context(context)
    p = window.create_output_panel(name)
    p.run_command("simple_insert", {"contents": content})
    window.run_command("show_panel", {"panel":"output."+name})


def exec_command(cmd, working_dir=None, env=None, context=None, callback=None):
  # by default, just display the output in a panel
  if callback is None:
    callback = "app.commando_show_panel"

  sublime.run_command("commando_exec",
                      {"cmd": cmd, "working_dir": working_dir, "env": env,
                       "context": context, "callback": callback })

def run_commands(commands, context, input=None):
  next_command = commands.pop(0)

  if isinstance(next_command, list):
    extra_args = next_command[1]
    next_command = next_command[0]
  else:
    extra_args = {}

  command_parts = next_command.split('.')

  if len(command_parts) != 2:
    print('Error or whatever.')
    return

  runner = None
  if command_parts[0] == 'app' or command_parts[0] == 'application':
    runner = sublime

  elif command_parts[0] == 'window':
    if not context['window_id']:
      print('Context error (window)')
    else:
      window = get_window_by_id(context['window_id'])
      if not window:
        print('Could not find window')
      else:
        runner = window

  elif command_parts[0] == 'view' or command_parts[0] == 'text':
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
    args = {"context": context, "callback": commands, "input": input}
    args.update(extra_args)
    runner.run_command(command_parts[1], args)

#
# Helper commands
#

class Commando:
  context = None

  def run(self, context=None, callback=None, input=None):
    self.context = context

    if input:
      input = self.process_input(input)

    if input and input['code']:
      run_commands(['app.commando_show_panel'], self.context, input=input)
    else:
      cmd = self.get_exec_command(input)
      if cmd:
        exec_command(cmd, context=self.context, callback=callback, working_dir=self.get_working_dir(context))
      else:
        self.do_command(input)
        if callback:
          run_commands(callback, context, input=input)

  def get_exec_command(self, input=None):
    return None

  def do_command(self, input=None):
    pass

  def process_input(self, input):
    return input

  def run_commands(self, commands):
    run_commands(commands, self.get_context())

  def get_context(self):
    return {"window_id": self.get_window_id(), "view_id": self.get_view_id()}

  def get_window_id(self):
    return None

  def get_view_id(self):
    return None

  # Default working dir is:
  #   ApplicationCommand - None
  #   WindowCommand - First folder in project
  #   TextCommand - Path to filename
  #
  # Note: This goes here instead of in the inherited classes because we're
  # basing the working dir off of the context (which comes from the initial command)
  # not off the type of the current command.
  def get_working_dir(self, context):
    if context['view_id']:
      view = get_view_by_id(context['window_id'], context['view_id'])
      print(view.file_name())
      if view.file_name():
        return os.path.dirname(view.file_name())

    elif context['window_id']:
      window = get_window_by_id(context['window_id'])
      if window.folders():
        return window.folders()[0]

    return None

  def panel(self, content, context=None):
    if content:
      panel(input['conten'])

class ApplicationCommando(Commando, sublime_plugin.ApplicationCommand):
  pass

class WindowCommando(Commando, sublime_plugin.WindowCommand):
  def get_window_id(self):
    return self.window.id()

class TextCommando(Commando, sublime_plugin.TextCommand):
  def run(self, edit, context=None, callback=None, input=None):
    return Commando.run(self, context=context, callback=callback, input=input)

  def get_window_id(self):
    return self.view.window().id()

  def get_view_id(self):
    return self.view.id()


class CommandoShowPanelCommand(ApplicationCommando):
  def run(self, context=None, callback=None, input=None):
    if input:
      panel(input['content'], context=context)

class CommandoNewFileCommand(ApplicationCommando):
  def run(self, context=None, callback=None, input=None, name=None, scratch=None, ro=None):
    if input and input['content'] and input['content'].rstrip() != '':
      window = get_window_by_context(context)
      new_view = window.new_file()
      if name:
        new_view.set_name(name)
      if scratch:
        new_view.set_scratch(True)
      new_view.run_command("simple_insert", {"contents": input['content']})
      if ro:
        new_view.set_read_only(True)

class CommandoNewFileCommand(ApplicationCommando):
  def run(self, context=None, callback=None, input=None, name=None, scratch=None, ro=None):
    if input and input['content'] and input['content'].rstrip() != '':
      window = get_window_by_context(context)
      new_view = window.new_file()
      if name:
        new_view.set_name(name)
      if scratch:
        new_view.set_scratch(True)
      new_view.run_command("simple_insert", {"contents": input['content']})
      if ro:
        new_view.set_read_only(True)

class CommandoOpenFileCommand(ApplicationCommando):
  pass

class CommandoSelect(ApplicationCommando):
  def on_command(self, input=None):
    
