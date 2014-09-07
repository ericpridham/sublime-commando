import sublime, sublime_plugin
import Commando.core as CC
import os.path


class AndroidTools(CC.Command):
  def android(self, params, callback = None):
    s = sublime.load_settings("Android.sublime-settings")
    path = s.get('android_tools_path')
    if path:
      cmd = os.path.join(path, 'android')
      self.exec_command(cmd, params, callback)

class AndroidCommand(AndroidTools, sublime_plugin.WindowCommand):
  pass

class AndroidCreateProjectCommand(AndroidCommand):
  step_input = []
  step_defaults = []
  proj_settings = {}
  sc = None

  def run(self, target_id = None):
    self.proj_settings = {
      "target": target_id,
      "name": "",
      "path": "",
      "activity": "",
      "package": ""
    }
    # sublime.set_timeout(self.insert_current_command, 10)
    self.cur_step = 0
    self.run_step()

  def prompt_step(self, caption, initial_text = ""):
    self.prompt(caption, initial_text, self.on_step_done, None, self.on_step_cancel)

  def select_step(self, items, display_items = None):
    if display_items is None:
      display_items = items
    self.select_items = items
    self.select(display_items, self.select_step_done)

  def select_step_done(self, selected):
    if 0 <= selected < len(self.select_items):
      self.on_step_done(self.select_items[selected])

  def run_step(self):
    print(self.cur_step)
    if self.cur_step == -1:
      if self.sc.is_valid():
        self.sc.close()
    if self.cur_step == 0:
      self.android(['list', 'targets'], self.list_targets_done)
    elif self.cur_step == 1:
      self.prompt_step("App Name:", self.proj_settings["name"])
    elif self.cur_step == 2:
      if not self.proj_settings['path']:
      self.prompt_step("Path:", self.step_defaults[self.cur_step])

  def on_step_done(self, input):
    self.step_input[self.cur_step] = input
    if self.cur_step == 0:
      self.proj_settings['target'] = input
    elif self.cur_step == 1:
      self.proj_settings['name'] = input
      s = sublime.load_settings("Android.sublime-settings")
      path = s.get('workspace_path')
      self.proj_settings['path'] = os.path.join(path, self.proj_settings['name'])

    self.insert_current_command()
    self.cur_step += 1
    self.run_step()

  def on_step_cancel(self):
    self.cur_step -= 1
    self.run_step()

  def insert_current_command(self):
    # command = "android create project\n\t--target <target-id>\n\t--name MyFirstApp\n\t--path <path-to-workspace>/MyFirstApp\n\t--activity MainActivity\n\t--package com.example.myfirstapp"
    args = ["--{0} {1}".format(k, v) for k, v in self.proj_settings.items() if v]
    command = "android create project\n\t" + "\n\t".join(args)

    if self.sc is None or not self.sc.is_valid():
      self.sc = self.scratch("")

    settings = ["{0}: {1}".format(k, v) for k, v in self.proj_settings.items() if v]
    contents = "# settings\n"+"\n\t".join(settings)+"\n\n# command preview\n"+command
    self.sc.run_command("replace_all", {"contents": contents})

  def list_targets_done(self, output):
    # self.panel(output.split('----------\n'))
    targets = []
    for target in output.split('----------\n'):
      if target.startswith('id:'):
        new_target = {}
        for target_details in target.splitlines():
          field = target_details.split(':', 1)
          if len(field) == 2:
            new_target[field[0].strip()] = field[1].strip()
        targets.append(new_target)

    target_ids = [t['id'] for t in targets]
    display_targets = [[t['id'], '{Name} ({Type})'.format(**t)] for t in targets]
    self.select_step(target_ids, display_targets)
