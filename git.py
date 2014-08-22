#
# Commando git plugin (including git-flow support)
#
import sublime, sublime_plugin
import Commando.core as CC
import os.path
import time
import re

PLUGIN_PATH = None
def plugin_loaded():
  global PLUGIN_PATH
  PLUGIN_PATH = os.path.dirname(__file__)
  sublime.active_window().run_command('git_window_show_version')

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
    s = sublime.load_settings("git.sublime-settings")
    cmd = s.get('git_binary', 'git')
    self.exec_command(cmd, params, callback)

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
    if view.name() == 'COMMIT_EDITMSG' or view.name() == 'COMMIT_ALL_EDITMSG':
      full_region = sublime.Region(0, view.size())
      contents = view.substr(full_region)
      if view.name() == 'COMMIT_ALL_EDITMSG':
        commit_all = True
      else:
        commit_all = False
      sublime.active_window().run_command("git_commit_complete", {"contents": contents, "commit_all": commit_all})

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
    for i in results.splitlines():
      if '*' in i:
        self.cur_branch = i.replace('*', '').strip()
    
    if self.cur_branch == None:
      return
    
    self.git(['for-each-ref', 'refs/tags', '--sort=-taggerdate', '--format=%(refname)', '--count=1'], self.tag_latest_done)

  def tag_latest_done(self, results):
    if results.rstrip():
      self.cur_tag = results.rstrip().replace('refs/tags/', '')
      self.status('git_status',
        'git: v%s [%s]' % (self.cur_tag, self.cur_branch))

class GitWindowShowVersionCommand(GitRepoCommand):
  def run(self):
    for view in self.get_window().views():
      view.run_command('git_show_version')

class GitStatusCommand(GitRepoCommand):
  def run(self):
    self.git(['status', '--porcelain'], self.status_done)

  def status_done(self, output):
    if output.rstrip() != '':
      self.statuses = output.splitlines()
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

class GitCheckoutCommand(GitFileCommand):
  def run(self, edit):
    self.git(['checkout', self.view.file_name()])
    sublime.status_message("Checked out " + self.view.file_name())

class GitStashCommand(GitRepoCommand):
  def run(self):
    self.git(['stash'])

class GitStashPopCommand(GitRepoCommand):
  def run(self):
    self.git(['stash', 'pop'])

class GitCommitCommand(GitRepoCommand):
  def run(self):
    self.git(['status'], self.status_done)

  def status_done(self, output):
    no_changes = 'no changes added to commit (use "git add" and/or "git commit -a")'
    clean_wd = "nothing to commit, working directory clean"
    if no_changes in output or clean_wd in output:
      self.panel(no_changes)
    else:
      lines = map(lambda l: "#"+l if not l or l[0] != "#" else l, output.split("\n"))
      s = self.scratch("\n".join(lines), "COMMIT_EDITMSG")
      s.run_command('simple_insert', {"contents":"\n"})
      # self.prompt('Commit Message', '', 
      #   lambda str: self.commit_change,
      #   lambda str:,
      #   lambda: )
      # self.panel("Commit Message Here")

class GitCommitCompleteCommand(GitRepoCommand):
  def run(self, contents, commit_all=False):
    lines = filter(lambda x: x.strip() and x.strip()[0] != "#", contents.split("\n"))
    message = '\n'.join(lines)
    if message:
      if commit_all:
        self.git(['commit', '-a', '-m', message])
      else:
        self.git(['commit', '-m', message])
    else:
      self.panel("Aborting commit due to empty commit message.")

class GitCommitAllCommand(GitRepoCommand):
  def run(self):
    self.git(['status'], self.status_done)

  def status_done(self, output):
    no_changes = 'no changes added to commit (use "git add" and/or "git commit -a")'
    clean_wd = "nothing to commit, working directory clean"
    output = output.replace(no_changes,'')
    if clean_wd in output:
      self.panel(no_changes)
    else:
      s = self.scratch(output, "COMMIT_ALL_EDITMSG")
      s.run_command('simple_insert', {"contents":"\n"})

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
    self.window.run_command('git_window_show_version')

class GitLog:
  def file_name(self):
    try:
      return self.view.file_name()
    except AttributeError:
      return ''

  def run(self, edit = None):
    self.git(['log', '--format=%s\aby %an on %ad (%ar)\a%H', '--date=local', '--', self.file_name()], self.log_done)

  def log_done(self, output):
    self.logs = [x.split('\a', 2) for x in output.splitlines()]
    display_logs = [x[:2] for x in self.logs]
    self.select(display_logs, self.log_selected)

  def log_selected(self, selected):
    if 0 <= selected < len(self.logs):
      self.git(['log', '-p', '-1', self.logs[selected][2], '--', self.file_name()], self.display_log)

  def display_log(self, output):
    self.scratch(output, 'Git Log Details', 'Diff')

class GitLogCommand(GitLog, GitFileCommand):
  pass

class GitLogAllCommand(GitLog, GitRepoCommand):
  pass

class GitBranchCommand(GitRepoCommand):
  def run(self):
    self.git(['branch', '--no-color'], self.branch_done)

  def branch_done(self, output):
    self.branches = [ b.strip() for b in output.splitlines() ]
    self.select(self.branches, self.branch_selected, sublime.MONOSPACE_FONT)

  def branch_selected(self, selected):
    if 0 <= selected < len(self.branches):
      selected_branch = self.branches[selected]
      if not selected_branch.startswith("*"):
        self.git(['checkout', selected_branch], self.checkout_done)
  
  def checkout_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

#    
# Flow
#

class GitFlowInitCommand(GitRepoCommand):
  def run(self):
    self.git(['flow', 'init'], self.init_done)
  
  def init_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

class GitFlowHotfixStartCommand(GitRepoCommand):
  def run(self):
    self.git(['status', '--porcelain'], self.status_done)

  def status_done(self, output):
    uncommitted = [x for x in output.splitlines() if x and x[0] != '?']
    if uncommitted:
      self.panel("Working tree contains unstaged or uncommitted changes. Aborting.")
    else:
      self.prompt("git flow hotfix start", "", self.hotfix_entered)

  def hotfix_entered(self, user_input):
    hotfix = str(user_input)
    if re.search('^[0-9.]+$', hotfix):
      self.git(['flow', 'hotfix', 'start', hotfix], self.hotfix_start_done)
    else:
      self.panel("Invalid hotfix name")
  
  def hotfix_start_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

class GitFlowHotfixFinish(GitRepoCommand):
  def run(self):
    self.git(['flow', 'hotfix', 'list'], self.hotfix_list_done)

  def hotfix_list_done(self, output):
    if 'No hotfix branches exist.' in output:
      self.panel(output)
    else:
      self.hotfixes = [x.replace('*','').strip() for x in output.splitlines()]
      self.select(self.hotfixes, self.hotfix_selected, sublime.MONOSPACE_FONT)

  def hotfix_selected(self, selected):
    if 0 <= selected < len(self.hotfixes):
      selected_hotfix = self.hotfixes[selected]
      self.git(['flow', 'hotfix', 'finish',
        '-m', 'Hotfix ' + selected_hotfix, selected_hotfix], self.hotfix_finish_done)
  
  def hotfix_finish_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

class GitFlowHotfixPublishCommand(GitRepoCommand):
  def run(self):
    self.git(['flow', 'hotfix', 'list'], self.hotfix_list_done)

  def hotfix_list_done(self, output):
    if 'No hotfix branches exist.' in output:
      self.panel(output)
    else:
      self.hotfixes = [x.replace('*','').strip() for x in output.splitlines()]
      self.select(self.hotfixes, self.hotfix_selected, sublime.MONOSPACE_FONT)

  def hotfix_selected(self, selected):
    if 0 <= selected < len(self.hotfixes):
      self.git(['flow', 'hotfix', 'publish', self.hotfixes[selected]], self.hotfix_publish_done)
  
  def hotfix_publish_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

class GitFlowHotfixTrackCommand(GitRepoCommand):
  def run(self):
    self.git(['branch', '-r', '--no-color'], self.branch_done)

  def branch_done(self, output):
    self.hotfixes = [i.replace('origin/hotfix/', 'Hotfix ').strip()
      for i in output.splitlines() if i.find('origin/hotfix/') != -1]
    if self.hotfixes:
      self.select(self.hotfixes, self.hotfix_selected, sublime.MONOSPACE_FONT)
    else:
      self.panel('No remote hotfixes exist.')

  def hotfix_selected(self, selected):
    if 0 <= selected < len(self.hotfixes):
      selected_hotfix = self.hotfixes[picked].replace('Hotfix ', '')
      self.git(['flow', 'hotfix', 'track', selected_hotfix], self.hotfix_track_done)
  
  def hotfix_track_done(self, output):
    self.panel(results)
    self.window.run_command('git_window_show_version')

class GitFlowReleaseStartCommand(GitRepoCommand):
  def run(self):
    self.git(['status', '--porcelain'], self.status_done)

  def status_done(self, output):
    uncommitted = [x for x in output.splitlines() if x and x[0] != '?']
    if uncommitted:
      self.panel("Working tree contains unstaged or uncommitted changes. Aborting.")
    else:
      self.prompt("git flow release start", "", self.release_entered)

  def release_entered(self, user_input):
    release = str(user_input)
    if re.search('^[0-9.]+$', release):
      self.git(['flow', 'release', 'start', release], self.release_start_done)
    else:
      self.panel("Invalid release name")
  
  def release_start_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

class GitFlowReleaseFinish(GitRepoCommand):
  def run(self):
    self.git(['flow', 'release', 'list'], self.release_list_done)

  def release_list_done(self, output):
    if 'No release branches exist.' in output:
      self.panel(output)
    else:
      self.releases = [x.replace('*','').strip() for x in output.splitlines()]
      self.select(self.releases, self.release_selected, sublime.MONOSPACE_FONT)

  def release_selected(self, selected):
    if 0 <= selected < len(self.releases):
      selected_release = self.releases[selected]
      self.git(['flow', 'release', 'finish',
        '-m', 'Release ' + selected_release, selected_release], self.release_finish_done)
  
  def release_finish_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

class GitFlowReleasePublishCommand(GitRepoCommand):
  def run(self):
    self.git(['flow', 'release', 'list'], self.release_list_done)

  def release_list_done(self, output):
    if 'No release branches exist.' in output:
      self.panel(output)
    else:
      self.releases = [x.replace('*','').strip() for x in output.splitlines()]
      self.select(self.releases, self.release_selected, sublime.MONOSPACE_FONT)

  def release_selected(self, selected):
    if 0 <= selected < len(self.releases):
      self.git(['flow', 'release', 'publish', self.releases[selected]], self.release_publish_done)
  
  def release_publish_done(self, output):
    self.panel(output)
    self.window.run_command('git_window_show_version')

class GitFlowReleaseTrackCommand(GitRepoCommand):
  def run(self):
    self.git(['branch', '-r', '--no-color'], self.branch_done)

  def branch_done(self, output):
    self.releases = [i.replace('origin/release/', 'Release ').strip()
      for i in output.splitlines() if i.find('origin/release/') != -1]
    if self.releases:
      self.select(self.releases, self.release_selected, sublime.MONOSPACE_FONT)
    else:
      self.panel('No remote releases exist.')

  def release_selected(self, selected):
    if 0 <= selected < len(self.releases):
      selected_release = self.releases[picked].replace('Release ', '')
      self.git(['flow', 'release', 'track', selected_release], self.release_track_done)
  
  def release_track_done(self, output):
    self.panel(results)
    self.window.run_command('git_window_show_version')

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
      tags = results.splitlines()
      tags.reverse()
      latest_tag = tags[0]
      self.git(['checkout', 'tags/'+latest_tag], self.update_done)
  
  def update_done(self, results):
    self.git(['describe', '--abbrev=0', '--always'], self.current_version_done)

  def current_version_done(self, version):
    self.panel('Commando version: ' + version.rstrip())
