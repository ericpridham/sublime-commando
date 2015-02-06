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

def devlog(message):
  print("DEVLOG MESSAGE: " + str(message))

# Encapsulates subprocess.Popen, forwarding stdout to a supplied
# ProcessListener (on a separate thread)
class CommandoProcess(threading.Thread):
  def __init__(self, cmd, on_done, input="", env=None, path="", encoding="utf-8"):
    super().__init__()
    self.killed = False

    # Hide the console window on Windows
    startupinfo = None
    if os.name == "nt":
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Set temporary PATH to locate executable in cmd
    if path:
      old_path = os.environ["PATH"]
      # The user decides in the build system whether he wants to append $PATH
      # or tuck it at the front: "$PATH;C:\\new\\path", "C:\\new\\path;$PATH"
      os.environ["PATH"] = os.path.expandvars(path)

    proc_env = os.environ.copy()
    if env:
      proc_env.update(env)
    for k, v in proc_env.items():
      proc_env[k] = os.path.expandvars(v)

    self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
      stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env)

    if input is None:
      input = ""

    (stdout, stderr) = self.proc.communicate(input=input.encode(encoding))

    try:
      stdout = stdout.decode(encoding)
    except Exception:
      print("[Decode error - stdout not " + encoding + "]\n")

    try:
      stderr = stderr.decode(encoding)
    except Exception:
      print("[Decode error - stderr not " + encoding + "]\n")

    exitcode = self.exit_code()

    sublime.set_timeout(lambda: on_done(exitcode, stdout, stderr), 0)

    if path:
      os.environ["PATH"] = old_path

  def kill(self):
    if not self.killed:
      self.killed = True
      if sys.platform == "win32":
        # terminate would not kill process opened by the shell cmd.exe, it will only kill
        # cmd.exe leaving the child running
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen("taskkill /PID " + str(self.proc.pid), startupinfo=startupinfo)
      else:
        self.proc.terminate()
      self.listener = None

  def poll(self):
    return self.proc.poll() == None

  def exit_code(self):
    return self.proc.poll()

###
###
###

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

def exec_command(cmd, input=input, working_dir=None, env=None, context=None, callback=None):
  # by default display the output in a panel
  if callback is None:
    callback = "app.commando_show_panel"

  sublime.run_command("commando_exec",
                      {"cmd": cmd, "input":input, "working_dir": working_dir, "env": env,
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
    return val

  def commando(self, commands, input=None):
    commando(commands, self._get_context(), input=input)

  def run(self, context=None, callback=None, input=None, cmd_args=None):
    self.context = context
    self.callback = callback
    if cmd_args is None:
      cmd_args = {}
    else:
      cmd_args = self._do_var_subs(cmd_args)

    input = self.cmd(input, cmd_args)
    if input != False and callback:
        commando(callback, context, input=input)

  def cmd(self, input, args=None):
    return input

  def get_window(self):
    return get_window_by_context(self._get_context())

  def get_view(self):
    return get_view_by_context(self._get_context())

  # Note: This goes here instead of in the inherited classes because we're
  # basing the working dir off of the context (which comes from the initial command)
  # not off the type of the current command.
  def get_working_dir(self):
    context = self._get_context()
    if context:
      if isinstance(self, sublime_plugin.TextCommand):
        view = get_view_by_id(context['window_id'], context['view_id'])
        if view.file_name():
          return os.path.dirname(view.file_name())
      else:
        window = get_window_by_id(context['window_id'])
        if window.folders():
          return window.folders()[0]
    return None

  def get_filename(self):
    view = get_view_by_context(self._get_context())
    return self.get_path(view.file_name())

  def get_path(self, filename=None):
    context = self._get_context()
    if context and context['window_id']:
      window = get_window_by_id(context['window_id'])
      if window.folders():
        return window.folders()[0] + ('/' + filename if filename else '')

    return None

  def panel(self, content):
    if content:
      panel(content, context=self._get_context())

  def select(self, items, on_done):
    select(items, on_done, self._get_context())

  def new_file(self, content, name=None, scratch=None, ro=None, syntax=None):
    if content and content.rstrip() != '':
      new_file(content.rstrip(), self._get_context(), name=name, scratch=scratch, ro=ro, syntax=syntax)

  def open_file(self, filename):
    open_file(filename, self._get_context())


class ApplicationCommando(Commando, sublime_plugin.ApplicationCommand):
  pass

class WindowCommando(Commando, sublime_plugin.WindowCommand):
  def _get_window_id(self):
    return self.window.id()

class TextCommando(Commando, sublime_plugin.TextCommand):
  def run(self, edit, context=None, callback=None, input=None, cmd_args=None):
    return Commando.run(self, context=context, callback=callback, input=input, cmd_args=cmd_args)

  def _get_window_id(self):
    return self.view.window().id()

  def _get_view_id(self):
    return self.view.id()

class CommandoCommand(ApplicationCommando):
  def cmd(self, input, args):
    self.commando(args['commands'])

class CommandoExecCommand(ApplicationCommando):
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

    if self.proc and 'kill' not in args:
      # ignore overlapping commando calls
      return

    # kill running proc (if exists)
    if 'kill' in args:
      if self.proc:
        self.proc.kill()
        self.proc = None
      return

    if 'encoding' in args:
      encoding = args['encoding']
    else:
      encoding = 'utf-8'

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
      self.proc_cmd = self._do_var_subs(args['cmd'])
      self.proc = CommandoProcess(args['cmd'], self.finish, input=input, env=env, encoding=encoding)
      self.proc.start()

      self.longrun = False
      sublime.set_timeout(self.watch_proc, 500)

    except Exception as e:
      self.finish(1, None, str(e))

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

  def finish(self, exitcode, stdout, stderr):
    self.proc = None
    devlog(exitcode)
    devlog(stdout)
    devlog(stderr)
    if exitcode:
      sublime.error_message("Error (" + str(exitcode) + "): " + stderr)
    elif self.callback:
      commando(self.callback, self.context, input=stdout+stderr)

class SimpleInsertCommand(sublime_plugin.TextCommand):
  def run(self, edit, contents):
    self.view.insert(edit, 0, contents)
    self.view.run_command("goto_line", {"line":1})

class CommandoShowPanelCommand(ApplicationCommando):
  def cmd(self, input, args):
    if input:
      panel(input, context=self._get_context())

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
      new_file(input.rstrip(), self._get_context(), name=name, scratch=scratch, ro=ro, syntax=syntax)

class CommandoOpenFileCommand(ApplicationCommando):
  def cmd(self, input, args):
    if os.path.exists(input):
      open_file(input, self._get_context())

class CommandoSelectCommand(ApplicationCommando):
  def cmd(self, input, args):#on_done=None):
    if 'on_done' in args:
      on_done = args['on_done']
    else:
      on_done = None

    if input:
      select(input, on_done, self._get_context())
    else:
      select([['Nothing to select.']], on_done, self._get_context())
