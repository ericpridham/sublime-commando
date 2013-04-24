import sublime, sublime_plugin
import Commando.Core as CC
import os.path
import time

PLUGIN_PATH = None
def plugin_loaded():
  global PLUGIN_PATH
  PLUGIN_PATH = os.path.dirname(__file__)

class GitCommand(CC.Command):
  def git_root(self, in_file):
    cur_path = in_file if os.path.isdir(in_file) else os.path.dirname(in_file)
    cur_path = os.path.normpath(cur_path)
    while cur_path:
      if os.path.exists(os.path.join(cur_path,'.git')):
        return cur_path
      parent = os.path.normpath(os.path.join(cur_path,'..'))
      cur_path = parent if parent != cur_path else False
    return False

  def git(self, params, callback = None):
    self.exec_command("git", params, callback)

  def is_enabled(self):
    return True if self.get_working_dir() is not None else False

  def is_visible(self):
    return self.is_enabled()

class GitRepoCommand(GitCommand, sublime_plugin.WindowCommand):
  def get_working_dir(self):
    for folder in self.window.folders():
      git_root = self.git_root(folder)
      if git_root:
        return git_root
    return None

class GitFileCommand(GitCommand, sublime_plugin.TextCommand):
  def get_working_dir(self):
    if self.view.file_name() is not None:
      git_root = self.git_root(self.view.file_name())
      if git_root:
        return git_root
    return None

#
# Meta
#
class CommandoRepoCommand(GitCommand, sublime_plugin.WindowCommand):
  def get_working_dir(self):
    if os.path.isdir(PLUGIN_PATH):
      return PLUGIN_PATH
    return None

#
# Events
#
class GitCommitMessageListener(sublime_plugin.EventListener):
  def on_close(self, view):
    if view.name() == 'COMMIT_EDITMSG':
      full_region = sublime.Region(0, view.size())
      contents = view.substr(full_region)
      sublime.active_window().run_command("git_commit_complete", {"contents": contents})

class GitStatusListener(sublime_plugin.EventListener):
  def on_load(self, view):
    view.run_command("git_show_version")

#
# Commands
#

class GitShowVersionCommand(GitFileCommand):
  def run(self, edit):
    self.git(['branch', '--no-color'], self.branch_done)
  
  def branch_done(self, results):
    self.cur_branch = None
    for i in results.rstrip().split("\n"):
      if '*' in i:
        self.cur_branch = i.replace('*', '').strip()
    
    if self.cur_branch == None:
      return
    
    self.git(['for-each-ref', 'refs/tags', '--sort=-taggerdate', '--format=%(refname)', '--count=1'], self.tag_latest_done)

  def tag_latest_done(self, results):
    if results.rstrip():
      self.cur_tag = results.rstrip().replace('refs/tags/', '')
      self.active_view().set_status('git_status',
        'git: v%s [%s]' % (self.cur_tag, self.cur_branch))

class GitStatusCommand(GitRepoCommand):
  def description(self):
    return "Git: Status"

  def run(self):
    self.git(['status', '--porcelain'], self.status_done)

  def status_done(self, output):
    if output.rstrip() != '':
      self.statuses = output.rstrip().split("\n")
      self.select(self.statuses, self.status_selected, sublime.MONOSPACE_FONT)

  def status_selected(self, selected):
    if selected != -1:
      self.open_file(self.statuses[selected][3:])

class GitDiffCommand(GitFileCommand):
  def run(self, edit):
    self.git(['diff', self.view.file_name()], self.diff_done)

  def diff_done(self, output):
    if output.rstrip() == '':
      self.panel("No output.")
    else:
      self.scratch(output, "Git Diff", "Diff", ro=True)

class GitDiffAllCommand(GitRepoCommand):
  def run(self):
    self.git(['diff'], self.diff_done)

  def diff_done(self, output):
    if output.rstrip() == '':
      self.panel("No output.")
    else:
      self.scratch(output, "Git Diff", "Diff", ro=True)

class GitAddCommand(GitFileCommand):
  def run(self, edit):
    self.git(['add', self.view.file_name()])
    sublime.status_message("Added " + self.view.file_name())

class GitResetCommand(GitFileCommand):
  def run(self, edit):
    self.git(['reset', '-q', 'HEAD', self.view.file_name()])
    sublime.status_message("Reset " + self.view.file_name())

class GitCommitCommand(GitRepoCommand):
  def run(self):
    self.git(['status'], self.status_done)

  def status_done(self, output):
    no_changes = 'no changes added to commit (use "git add" and/or "git commit -a")'
    if no_changes in output:
      self.panel(no_changes)
    else:
      s = self.scratch(output, "COMMIT_EDITMSG")
      s.run_command('simple_insert', {"contents":"\n"})
      # self.prompt('Commit Message', '', 
      #   lambda str: self.commit_change,
      #   lambda str:,
      #   lambda: )
      # self.panel("Commit Message Here")

class GitCommitCompleteCommand(GitRepoCommand):
  def run(self, contents):
    lines = filter(lambda x: x.strip() and x.strip()[0] != "#", contents.split("\n"))
    message = '\n'.join(lines)
    if message:
      self.git(['commit', '-m', message])
    else:
      self.panel("Aborting commit due to empty commit message.")

class GitPushCommand(GitRepoCommand):
  def run(self):
    self.git(['push', '--tags'], self.tags_done)

  def tags_done(self, output):
    if output.rstrip() == 'Everything up-to-date':
      output = ''
    self.tag_output = output
    self.git(['push'], self.push_done)
  
  def push_done(self, output):
    if output.rstrip() == 'Everything up-to-date':
      output = ''

    if output == '' and self.tag_output == '':
      message = 'Everything up-to-date'
    else:
      message = self.tag_output + '\n' + output;
    self.panel(message)

class GitPullCommand(GitRepoCommand):
  def run(self):
    self.git(['fetch', '--tags'], self.fetch_tags_done)

  def fetch_tags_done(self, output):
    self.tag_output = output.rstrip()
    self.git(['pull'], self.pull_done)

  def pull_done(self, output):
    if self.tag_output == "":
      message = output
    else:
      message = self.tag_output
      if output != 'Already up-to-date.':
        message += '\n' + output
    self.panel(message)

class GitLogCommand(GitRepoCommand):
  def run(self):
    self.git(['log', '--format=%s\aby %an on %ad (%ar)\a%H', '--date=local'], self.log_done)

  def log_done(self, output):
    logs = [x.split('\a', 2) for x in output.rstrip().split('\n')]
    self.select(logs, self.log_selected)

  def log_selected(self, selection):
    pass

#
# Meta
#
class GitPluginUpdateCommand(CommandoRepoCommand):
  def run(self):
    self.git(['fetch'], self.fetch_done)

  def fetch_done(self, results):
    self.git(['tag', '-l'], self.tags_list_done)

  def tags_list_done(self, results):
    if results.rstrip():
      tags = results.rstrip().split("\n")
      tags.reverse()
      latest_tag = tags[0]
      self.git(['checkout', 'tags/'+latest_tag], self.update_done)
  
  def update_done(self, results):
    self.git(['describe', '--abbrev=0', '--always'], self.current_version_done)

  def current_version_done(self, version):
    self.panel('Commando version: ' + version.rstrip())
