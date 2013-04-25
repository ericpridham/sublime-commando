import sublime, sublime_plugin
import Commando.Core as CC
import re

class RedpomoCommand(CC.Command, sublime_plugin.WindowCommand):
  priority_descs = {'A':'Immediate','B':'Urgent','C':'High'}
  actions = [
    {'action': 'open',  'desc': 'Open'},
    {'action': 'start', 'desc': 'Start'},
    {'action': 'close', 'desc': 'Close'}]

  def redpomo(self, params, callback = None):
    s = sublime.load_settings("Redpomo.sublime-settings")
    cmd = s.get('redpomo_command')
    if cmd:
      self.exec_command(cmd, params, callback)

  def todo(self, params, callback = None):
    s = sublime.load_settings("Redpomo.sublime-settings")
    cmd = s.get('todo_command')
    if cmd:
      self.exec_command(cmd, params, callback)

class RedpomoListCommand(RedpomoCommand):
  def run(self):
    self.todo(['-p', 'list'], self.list_done)

  def list_done(self, output):
    self.tasks = []
    for line in output.splitlines():
      m = re.search('^[0-9]+ (\((?P<pri>.)\) )?(?P<sub>.*) (?P<iss>#\w+) \+(?P<proj>[\w-]+) (?P<trk>@\w+)$', line)
      if m:
        self.tasks.append({
          'priority': m.group('pri') if m.group('pri') else '',
          'priority_desc': self.priority_descs[m.group('pri')] if m.group('pri') else '',
          'subject':  m.group('sub'),
          'issue': m.group('iss'),
          'project': m.group('proj'),
          'tracker': m.group('trk')})

    s = sublime.load_settings("Redpomo.sublime-settings")
    if s.get('compact_list'):
      task_list = ["{priority:<2} {issue:>4} {project:<9} {subject}".format(**t) for t in self.tasks]
    else:
      task_list = [["{issue} {subject}".format(**t), "{priority_desc} {project}".format(**t)] for t in self.tasks]
      pass
    self.select(task_list, self.ticket_selected, sublime.MONOSPACE_FONT)

  def ticket_selected(self, selected):
    if 0 <= selected < len(self.tasks):
      self.panel("{issue} {subject}".format(**self.tasks[selected]))

class RedpomoPullCommand(RedpomoCommand):
  def run(self):
    self.redpomo(['pull'], self.pull_done)

  def pull_done(self, output):
    self.window.run_command('redpomo_list')