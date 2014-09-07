import sublime, sublime_plugin
import Commando.core as CC
import os.path

class JavaFileCommand(CC.Command, sublime_plugin.TextCommand):
  def get_conf_env(self):
    s = sublime.load_settings("java.sublime-settings")
    classpath = s.get('classpath')
    env = {"CLASSPATH": str(classpath)}
    return env

  def java(self, params, callback = None):
    self.exec_command('java', params, callback, self.get_conf_env())

  def javac(self, params, callback = None):
    self.exec_command('javac', params, callback, self.get_conf_env())

  def environ(self, params, callback = None):
    self.exec_command('env', params, callback, self.get_conf_env())

  def get_working_dir(self):
    if self.view.file_name() is not None:
      java_root = os.path.dirname(self.view.file_name())
      if java_root:
        return java_root
    return None

  def is_enabled(self):
    if os.path.splitext(self.get_view().file_name())[1] == '.java':
      return True
    return False

class JavaCompileCommand(JavaFileCommand):
  def run(self, edit):
    self.javac(['-verbose', self.view.file_name()])
    # self.environ([])

class JavaRunCommand(JavaFileCommand):
  def run(self, edit):
    self.pname = os.path.basename(os.path.splitext(self.view.file_name())[0])
    self.prompt("java " + self.pname, "", self.params_entered)

  def params_entered(self, params_string):
    params = params_string.split(' ')
    self.java([self.pname] + params)
