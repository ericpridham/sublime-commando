"""Commando - Sublime command builder commands.

"""
import sublime, sublime_plugin
import os, sys
import threading
import subprocess
import functools
from . import plugin, core

class CommandoCommand(plugin.CommandoRun):
  pass

class CommandoExecCommand(plugin.CommandoCmd):
  """Simplified version of ExecCommand from Default/exec.py that supports chaining."""
  proc     = None
  encoding = None
  killed   = False
  output   = ""
  loop     = 0
  longrun  = False

  def cmd(self, context, input, args):
    # override default behavior with params if provided
    if self.proc and 'kill' not in args:
      # ignore overlapping commando_exec calls
      return False

    # kill running proc (if exists)
    if 'kill' in args:
      if self.proc:
        self.proc.kill()
        self.proc = None
        self.killed = True
      return False

    if not 'cmd' in args:
      return False

    if 'encoding' in args:
      encoding = args['encoding']
    else:
      encoding = 'utf-8'

    self.proc = None

    if 'working_dir' in args:
      working_dir = args['working_dir']
    else:
      working_dir = core.get_working_dir(context)

    # Change to the working dir, rather than spawning the process with it,
    # so that emitted working dir relative path names make sense
    if working_dir is not None:
      os.chdir(working_dir)

    if 'env' in args:
      env = args['env']
    else:
      env = {}

    try:
      self._do_var_subs(context, args['cmd'])
      self.proc_cmd = args['cmd']
      self.proc = CommandoProcess(args['cmd'], functools.partial(self.finish, context),
        input=input, env=env, encoding=encoding)
      self.proc.start()

      self.longrun = False
      sublime.set_timeout(self.watch_proc, 500)

    except Exception as e:
      self.finish(context, 1, None, str(e))

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

  def finish(self, context, exitcode, stdout, stderr):
    self.proc = None
    if exitcode:
      sublime.error_message("Error (" + str(exitcode) + "): " + stderr)
    elif context['commands']:
      context['input'] = stdout+stderr
      core.next_commando(context)

class CommandoKillCommand(plugin.CommandoRun):
  def commands(self):
    return [
      ["commando_exec", {"kill": True}]
    ]

class CommandoShowPanelCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    if input:
      core.panel(context, input)

class CommandoNewFileCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):#name=None, scratch=None, ro=None, syntax=None):
    if input and input.rstrip() != '':
      name = scratch = readonly = syntax = None
      if 'name' in args:
        name = args['name']
      if 'scratch' in args:
        scratch = args['scratch']
      if 'readonly' in args:
        readonly = args['readonly']
      if 'syntax' in args:
        syntax = args['syntax']
      view = core.new_file(context, input.rstrip(), name=name, scratch=scratch, readonly=readonly, syntax=syntax)
      view.settings().set('context', context)

    return False

class CommandoOpenFileCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    if os.path.exists(input.strip()):
      view = core.open_file(context, input.strip())
      if view:
        view.settings().set('context', context)
    return False

class CommandoQuickPanelCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):#on_done=None):
    if 'on_done' in args:
      on_done = args['on_done']
    else:
      on_done = context['commands']

    if input:
      core.quick_panel(context, input, on_done)

    return False

class CommandoInputPanelCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):#on_done=None, on_change=None, on_cancel=None):
    if not 'caption' in args:
      return False

    on_done = context['commands'] # by default, on_done is the remaining commands stack
    context['commands'] = []

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

    core.input_panel(context, args['caption'], initial_text, on_done, on_change, on_cancel)
    return False

class CommandoOkCancelDialogCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    if 'msg' in args:
      msg = args['msg']
    else:
      msg = 'Are you sure?'

    if not sublime.ok_cancel_dialog(msg):
      return False

    # pass the input through
    context['input'] = input

class CommandoSwitchCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    input = input.strip()
    if input in args:
      context['commands'] = args[input] + context['commands']
    elif 'default' in args:
      context['commands'] = args['default'] + context['commands']

class CommandoArgCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    if 'name' in args:
      context['args'] = args # passthrough previous args
      commands = ['commando_add_arg']+context['commands']
      core.input_panel(context, args['name'], "", commands)
    return False

class CommandoAddArgCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    context['args'] = args
    context['args'][args['name']] = input

class CommandoSplitCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    if 'sep' in args:
      sep = args['sep']
    else:
      sep = "\n"

    if 'limit' in args:
      limit = args['limit']
    else:
      limit = -1

    context['input'] = input.split(sep, limit)


class SimpleInsertCommand(sublime_plugin.TextCommand):
  def run(self, edit, contents):
    self.view.insert(edit, 0, contents)
    self.view.run_command("goto_line", {"line":1})

class CommandoProcess(threading.Thread):
  def __init__(self, cmd, on_done, input=None, env=None, path=None, encoding="utf-8"):
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

class CommandoNewFileWatcher(sublime_plugin.EventListener):
  def on_pre_close(self, view):
    context = view.settings().get('context')
    if context:
      context['input'] = view.substr(sublime.Region(0, view.size()))
      core.next_commando(context)
