import sublime, sublime_plugin
import os, sys
import threading
import subprocess
from . import plugin

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
# Helper commands
#

class CommandoCommand(plugin.ApplicationCommando):
  def cmd(self, input, args):
    self.commando(args['commands'])

class CommandoExecCommand(plugin.ApplicationCommando):
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

class CommandoShowPanelCommand(plugin.ApplicationCommando):
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

class CommandoNewFileCommand(plugin.ApplicationCommando):
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
      view = self.new_file(input.rstrip(), name=name, scratch=scratch, ro=ro, syntax=syntax)
      view.settings().set('callback', self.callback)
      view.settings().set('context', self.context)

    return False # cancel callback chain

class CommandoOpenFileCommand(ApplicationCommando):
  def cmd(self, input, args):
    if os.path.exists(input):
      view = self.open_file(input)
      view.settings().set('callback', self.callback)
      view.settings().set('context', self.context)

    return False # need to handle our own callback here

class CommandoQuickPanelCommand(plugin.ApplicationCommando):
  def cmd(self, input, args):#on_done=None):
    if 'on_done' in args:
      on_done = args['on_done']
    else:
      on_done = self.callback

    if input:
      self.quick_panel(input, on_done)
    else:
      self.quick_panel([['Nothing to select.']], on_done)

    return False

class CommandoInputPanelCommand(plugin.ApplicationCommando):
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

    self.input_panel(args['caption'], initial_text, on_done, on_change, on_cancel)
    return False

class CommandoOkCancelDialogCommand(plugin.ApplicationCommando):
  def cmd(self, input, args):
    if 'string' in args:
      string = args['string']
    else:
      string = 'Are you sure?'

    if sublime.ok_cancel_dialog(string):
      return input # pass the input through to the next command

    return False

class CommandoSwitchCommand(plugin.ApplicationCommando):
  def cmd(self, input, args):
    if input in args:
      self.callback = args[input] + self.callback
