import sublime, sublime_plugin
import Commando.core as CC
import re
import webbrowser
import time

class RedpomoCommand(CC.Command, sublime_plugin.WindowCommand):
  priority_descs = {'A':'Immediate','B':'Urgent','C':'High'}
  actions = ['open', 'start', 'close']
  action_descs = ['Open', 'Start', 'Close']

  def redpomo(self, params, callback = None):
    s = sublime.load_settings("redpomo.sublime-settings")
    cmd = s.get('redpomo_command')
    if cmd:
      self.exec_command(cmd, params, callback)

  def todo(self, params, callback = None):
    s = sublime.load_settings("redpomo.sublime-settings")
    cmd = s.get('todo_command')
    if cmd:
      self.exec_command(cmd, params, callback)

  #Issue created, see it at http://projects.replicocorp.com/issues/#
  def open_issue_url(self, output):
    p = output.find("http://")
    if p != -1:
      webbrowser.open(output[p:].strip()+'/edit', 2)
    else:
      self.generic_done(output)

class RedpomoPullCommand(RedpomoCommand):
  def run(self):
    self.redpomo(['pull'], self.pull_done)

  def pull_done(self, output):
    self.window.run_command('redpomo_list')

class RedpomoAddCommand(RedpomoCommand):
  def run(self):
    self.prompt("redpomo add", "", self.on_input, None, None)

  def on_input(self, new_task):
    if not '@' in new_task:
      s = sublime.load_settings("redpomo.sublime-settings")
      default_tracker = s.get('default_tracker')
      if default_tracker:
        new_task += " @"+default_tracker
    self.redpomo(['add', new_task], self.open_issue_url)

class RedpomoListCommand(RedpomoCommand):
  def run(self):
    self.todo(['-p', 'list'], self.list_done)

  def list_done(self, output):
    self.tasks = []
    for line in output.splitlines():
      m = re.search('^(?P<id>[0-9]+) (\((?P<pri>.)\) )?(?P<sub>.*) #(?P<iss>\w+) \+(?P<proj>[\w-]+) (?P<trk>@\w+)$', line)
      if m:
        self.tasks.append({
          'id': m.group('id'),
          'priority': m.group('pri') if m.group('pri') else '',
          'priority_desc': self.priority_descs[m.group('pri')] if m.group('pri') else '',
          'subject':  m.group('sub'),
          'issue': m.group('iss'),
          'project': m.group('proj'),
          'tracker': m.group('trk')})

    s = sublime.load_settings("redpomo.sublime-settings")
    if s.get('compact_list'):
      task_list = ["{priority:<2} #{issue:>3} {project:<10} {subject}".format(**t) for t in self.tasks]
    else:
      task_list = [["{issue} {subject}".format(**t), "{priority_desc} {project}".format(**t)] for t in self.tasks]
      pass
    self.select(task_list, self.get_task_num, sublime.MONOSPACE_FONT)

  def get_task_num(self, selected):
    if 0 <= selected < len(self.tasks):
      self.do_task_action(self.tasks[selected]['id'])

  def do_redpomo_action(self, action, task_num):
    if action == 'open':
      self.redpomo(['open', task_num])
    elif action == 'start':
      self.redpomo(['open', task_num])
      time.sleep(1)
      self.redpomo(['start', task_num])
    elif action == 'close':
      self.task_num_selected = task_num
      self.prompt("redpomo close", "", self.on_redpomo_close_input, None, None)

  def on_redpomo_close_input(self, message):
    if message.strip():
      self.redpomo(['close', '-m', message.strip(), self.task_num_selected], self.open_issue_url)

  #
  # Override from here down
  #
  def do_task_action(self, task_num):
    self.task_num_selected = task_num
    self.select(self.action_descs, self.get_command)

  def get_command(self, selected):
    if 0 <= selected < len(self.actions):
      self.do_redpomo_action(self.actions[selected], self.task_num_selected)


class RedpomoOpenCommand(RedpomoListCommand):
  def do_task_action(self, task_num):
    self.do_redpomo_action('open', task_num)

class RedpomoStartCommand(RedpomoListCommand):
  def do_task_action(self, task_num):
    self.do_redpomo_action('start', task_num)

class RedpomoCloseCommand(RedpomoListCommand):
  def do_task_action(self, task_num):
    self.do_redpomo_action('close', task_num)
