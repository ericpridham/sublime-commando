import sublime, sublime_plugin
import os
import Commando.core as CC

class TerminalCommand(CC.Command):
  def term(self, cwd):
    self.exec_command('bash', [os.path.join(os.path.dirname(__file__),'iTerm.sh'), cwd])

class TerminalHereCommand(TerminalCommand, sublime_plugin.WindowCommand):
  def run(self):
    v = self.window.active_view()
    if v is not None and v.file_name() is not None:
      self.term(os.path.dirname(v.file_name()))
    else:
      f = self.window.folders()
      if len(f):
        self.term(f[0])
      else:
        print ("You ain't nowhere.")
