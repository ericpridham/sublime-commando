"""Commando - Bundle handler.

"""
import sublime, sublime_plugin
from . import plugin, core
import json
import os
import fnmatch

class CommandoLoadBundleCommand(plugin.CommandoRun):
  def commands(self):
    return [
      'commando_get_bundles',
      'commando_quick_panel'
    ]

class CommandoGetBundlesCommand(plugin.CommandoCmd):
  def cmd(self, context, input, args):
    context['input'] = []
    for root, dirnames, filenames in os.walk(sublime.packages_path()):
      for filename in fnmatch.filter(filenames, '*.commando'):
        context['input'].append(os.path.join(root, filename))
        # matches.append(os.path.join(root, filename))
