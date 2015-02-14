"""

"""

import sublime, sublime_plugin
import os, sys
import threading
import subprocess

def devlog(message):
  print("DEVLOG: " + str(message))

class CommandoProcess(threading.Thread):

  def __init__(self, cmd, on_done, input="", env=None, path="", encoding="utf-8"):
    super(CommandoProcess, self).__init__()
    self.proc = None
    self.killed = False
    self.cmd = cmd
    self.on_done = on_done
    if input is None:
      input = ""
    self.input = input.encode(encoding)
    self.env = env
    self.path = path
    self.encoding = encoding

  def run(self):
    # Hide the console window on Windows
    startupinfo = None
    if os.name == "nt":
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Set temporary PATH to locate executable in cmd
    if self.path:
      old_path = os.environ["PATH"]
      # The user decides in the build system whether he wants to append $PATH
      # or tuck it at the front: "$PATH;C:\\new\\path", "C:\\new\\path;$PATH"
      os.environ["PATH"] = os.path.expandvars(self.path)

    proc_env = os.environ.copy()
    if self.env:
      proc_env.update(self.env)
    for k, v in proc_env.items():
      proc_env[k] = os.path.expandvars(v)

    self.proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 startupinfo=startupinfo, env=proc_env)

    (stdout, stderr) = self.proc.communicate(input=self.input)

    try:
      stdout = stdout.decode(self.encoding)
    except Exception:
      print("[Decode error - stdout not " + self.encoding + "]\n")

    try:
      stderr = stderr.decode(self.encoding)
    except Exception:
      print("[Decode error - stderr not " + self.encoding + "]\n")

    exitcode = self.exit_code()

    sublime.set_timeout(lambda: self.on_done(exitcode, stdout, stderr), 0)

    if self.path:
      os.environ["PATH"] = old_path

  def kill(self):
    if not self.killed:
      self.killed = True
      if sys.platform == "win32":
        # terminate would not kill process opened by the shell cmd.exe, it will
        # only kill cmd.exe leaving the child running
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen("taskkill /PID " + str(self.proc.pid), startupinfo=startupinfo)
      else:
        self.proc.terminate()

  def poll(self):
    return self.proc.poll() == None

  def exit_code(self):
    return self.proc.poll()

###
###
###

class CommandoKillCommand(sublime_plugin.WindowCommand):
  def run(self):
    sublime.run_command("commando_exec", {"cmd_args": {"kill": True}})

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

def get_window_by_id(window_id):
  for window in sublime.windows():
    if window.id() == window_id:
      return window
  return None

def get_window_by_context(context):
  if context and context['window_id']:
    return get_window_by_id(context['window_id'])
  return sublime.active_window()

def get_view_by_context(context):
  if context and context['window_id'] and context['view_id']:
    return get_view_by_id(context['window_id'], context['view_id'])
  elif sublime.active_window():
    return sublime.active_window().active_view()
  return None

def get_view_by_id(window_id, view_id):
  window = get_window_by_id(window_id)
  if window:
    for view in window.views():
      if view.id() == view_id:
        return view
  return None

def panel(context, content, name="commando"):
  if content and content.rstrip() != '':
    window = get_window_by_context(context)
    p = window.create_output_panel(name)
    p.run_command("simple_insert", {"contents": content})
    window.run_command("show_panel", {"panel":"output."+name})

def quick_panel(context, items, on_done_cmd, flags=sublime.MONOSPACE_FONT, selected_idx=-1, on_highlighted_cmd=None):
  def on_done(i):
    if on_done_cmd and i != -1:
      commando(context, on_done_cmd, input=items[i])
  def on_highlighted(i):
    if on_highlighted_cmd and i != -1:
      commando(context, on_highlighted_cmd, input=items[i])

  get_window_by_context(context).show_quick_panel(items, on_done, flags, selected_idx, on_highlighted)

def input_panel(context, caption, initial_text, on_done_cmd, on_change_cmd=None, on_cancel_cmd=None):
  def on_done(str):
    if on_done_cmd and str:
      commando(context, on_done_cmd, input=str)
  def on_change(str):
    if on_change_cmd and str:
      commando(context, on_change_cmd, input=str)
  def on_cancel():
    if on_cancel_cmd:
      commando(context, on_cancel_cmd)

  get_window_by_context(context).show_input_panel(caption, initial_text, on_done, on_change, on_cancel)

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
  return new_view

def focus_view(context, view):
  if view.is_loading():
    sublime.set_timeout(lambda: focus_view(context, view), 100)
  else:
    window = get_window_by_context(context)
    window.focus_view(view)
    # stolen from http://www.sublimetext.com/forum/viewtopic.php?f=5&t=10997&p=48890&hilit=fuzzyfilenav#p48890
    window.run_command("show_panel", {"panel": "console"})
    window.run_command("hide_panel", {"cancel": True})

def open_file(filename, context):
  if os.path.exists(filename):
    view = get_window_by_context(context).open_file(filename)
    if view is not None:
      sublime.set_timeout(lambda: focus_view(context, view), 100)
    return view
  else:
    sublime.error_message('File not found:' + filename)
    return None

def exec_command(cmd, input=None, working_dir=None, env=None, context=None, callback=None):
  # by default display the output in a panel
  if callback is None:
    callback = "app.commando_show_panel"

  sublime.run_command("commando_exec", {"cmd": cmd, "input":input, "working_dir": working_dir,
                                        "env": env, "context": context, "callback": callback})

def commando(context, commands, input=None):
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
    runner.run_command(next_command, {"context": context, "callback": commands,
                                      "input": input, "cmd_args": cmd_args})

#
# Helper commands
#

class Commando:
  """The core for commando commands."""
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
    commando(self._get_context(), commands, input=input)

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
    return get_window_by_context(self._get_context())

  def get_view(self):
    return get_view_by_context(self._get_context())

  # Note: This goes here instead of in the inherited classes because we're
  # basing the working dir off of the context (which comes from the initial command)
  # not off the type of the current command.
  def get_working_dir(self):
    context = self._get_context()
    if context:
      window = get_window_by_context(context)
      view = get_view_by_context(context)
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
    view = get_view_by_context(self._get_context())
    return self.get_path(view.file_name())

  def get_path(self, filename=None):
    working_dir = self.get_working_dir()
    if working_dir:
      return working_dir + ('/' + filename if filename else '')

    return None

  def panel(self, content):
    if content:
      panel(self._get_context(), content)

  def quick_panel(self, items, on_done):
    quick_panel(self._get_context(), items, on_done)

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
    if cmd_args is None:
      cmd_args = {}
    cmd_args['edit'] = edit
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
  proc = None
  encoding = None
  killed = False

  output = ""
  loop = 0
  longrun = False

  def cmd(self, input, args):
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
      devlog(self.proc)
      if self.proc:
        self.proc.kill()
        self.proc = None
        self.killed = True
      return

    if not 'cmd' in args:
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
      sublime.status_message('running[' + ' '.join(self.proc_cmd) + ']' +
                             '.' * self.loop + ' ' * (3 - self.loop))
      sublime.set_timeout(lambda: self.watch_proc(), 200)

    elif self.longrun:
      msg = ' '.join(self.proc_cmd) + ':'
      if self.killed:
        msg += ' Killed!'
      else:
        msg += ' Done!'
      sublime.status_message(msg)
      sublime.set_timeout(lambda: sublime.status_message(''), 3000)

  def finish(self, exitcode, stdout, stderr):
    self.proc = None
    if exitcode:
      sublime.error_message("Error (" + str(exitcode) + "): " + stderr)
    elif self.callback:
      self.commando(self.callback, input=stdout+stderr)

class SimpleInsertCommand(sublime_plugin.TextCommand):
  def run(self, edit, contents):
    self.view.insert(edit, 0, contents)
    self.view.run_command("goto_line", {"line":1})

class CommandoShowPanelCommand(ApplicationCommando):
  def cmd(self, input, args):
    if input:
      panel(self._get_context(), input)

class CommandoNewFileWatcher(sublime_plugin.EventListener):
  def on_pre_close(self, view):
    callback = view.settings().get('callback')
    context = view.settings().get('context')
    if context and callback:
      content = view.substr(sublime.Region(0, view.size()))
      commando(context, callback, input=content)
    pass

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
      view = new_file(input.rstrip(), self._get_context(), name=name, scratch=scratch, ro=ro, syntax=syntax)
      view.settings().set('callback', self.callback)
      view.settings().set('context', self.context)

    return False # cancel callback chain

class CommandoOpenFileCommand(ApplicationCommando):
  def cmd(self, input, args):
    if os.path.exists(input):
      view = open_file(input, self._get_context())
      view.settings().set('callback', self.callback)
      view.settings().set('context', self.context)

    return False # need to handle our own callback here

class CommandoQuickPanelCommand(ApplicationCommando):
  def cmd(self, input, args):#on_done=None):
    if 'on_done' in args:
      on_done = args['on_done']
    else:
      on_done = self.callback

    if input:
      quick_panel(self._get_context(), input, on_done)
    else:
      quick_panel(self.get_context(), [['Nothing to select.']], on_done)
    return False

class CommandoInputPanelCommand(ApplicationCommando):
  def cmd(self, input, args):#on_done=None, on_change=None, on_cancel=None):
    if not 'caption' in args:
      return False

    on_done = self.callback # by default, on_done is the remaining callback stack

    initial_text = ""
    on_change = on_cancel = None

    if 'initial_text' in args:
      initial_text = args['initial_text']
    if 'on_done' in args:
      if on_done:
        print('Warning: on_done provided but command stack is not empty. Skipping ' + str(on_done))
      on_done = args['on_done']
    if 'on_change' in args:
      on_change = args['on_change']
    if 'on_cancel' in args:
      on_cancel = args['on_cancel']

    input_panel(self._get_context(), args['caption'], initial_text, on_done, on_change, on_cancel)
    return False

class CommandoOkCancelDialogCommand(ApplicationCommando):
  def cmd(self, input, args):
    if 'string' in args:
      string = args['string']
    else:
      string = 'Are you sure?'

    if sublime.ok_cancel_dialog(string):
      return input # pass the input through to the next command

    return False

class CommandoSwitchCommand(ApplicationCommando):
  def cmd(self, input, args):
    if input in args:
      self.callback = args[input] + self.callback
