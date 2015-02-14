import sublime, sublime_plugin
import os

#
# Module functions
#

def devlog(message):
  print("DEVLOG: " + str(message))

def class_to_command(cls):
  clsname = cls.__name__
  name = clsname[0].lower()
  last_upper = False
  for c in clsname[1:]:
    if c.isupper() and not last_upper:
      name += '_'
      name += c.lower()
    else:
      name += c
    last_upper = c.isupper()
  if name.endswith("_command"):
    name = name[0:-8]
  return name

def get_command_type(command):
  for c in sublime_plugin.application_command_classes:
    if class_to_command(c) == command:
      return 'app'
  for c in sublime_plugin.window_command_classes:
    if class_to_command(c) == command:
      return 'window'
  for c in sublime_plugin.text_command_classes:
    if class_to_command(c) == command:
      return 'text'
  return None

def get_active_window_id():
  if sublime.active_window():
    return sublime.active_window().id()
  return None

def get_active_view_id():
  if sublime.active_window() and sublime.active_window().active_view():
    return sublime.active_window().active_view().id()
  return None

def get_active_context():
  return {"window_id": get_active_window_id(), "view_id": get_active_view_id()}

def get_window_by_id(window_id):
  for window in sublime.windows():
    if window.id() == window_id:
      return window
  return None

def get_window_by_context(context):
  if context and context['window_id']:
    return get_window_by_id(context['window_id'])
  return sublime.active_window()

def get_view_by_context(context):
  if context and context['window_id'] and context['view_id']:
    return get_view_by_id(context['window_id'], context['view_id'])
  elif sublime.active_window():
    return sublime.active_window().active_view()
  return None

def get_view_by_id(window_id, view_id):
  window = get_window_by_id(window_id)
  if window:
    for view in window.views():
      if view.id() == view_id:
        return view
  return None

def panel(context, content, name="commando"):
  if content and content.rstrip() != '':
    window = get_window_by_context(context)
    p = window.create_output_panel(name)
    p.run_command("simple_insert", {"contents": content})
    window.run_command("show_panel", {"panel":"output."+name})

def quick_panel(context, items, on_done_cmd, flags=sublime.MONOSPACE_FONT, selected_idx=-1, on_highlighted_cmd=None):
  def on_done(i):
    if on_done_cmd and i != -1:
      commando(context, on_done_cmd, input=items[i])
  def on_highlighted(i):
    if on_highlighted_cmd and i != -1:
      commando(context, on_highlighted_cmd, input=items[i])

  get_window_by_context(context).show_quick_panel(items, on_done, flags, selected_idx, on_highlighted)

def input_panel(context, caption, initial_text, on_done_cmd, on_change_cmd=None, on_cancel_cmd=None):
  def on_done(str):
    if on_done_cmd and str:
      commando(context, on_done_cmd, input=str)
  def on_change(str):
    if on_change_cmd and str:
      commando(context, on_change_cmd, input=str)
  def on_cancel():
    if on_cancel_cmd:
      commando(context, on_cancel_cmd)

  get_window_by_context(context).show_input_panel(caption, initial_text, on_done, on_change, on_cancel)

def new_file(context, content, name=None, scratch=None, ro=None, syntax=None):
  new_view = get_window_by_context(context).new_file()
  if name:
    new_view.set_name(name)
  if scratch:
    new_view.set_scratch(True)
  if syntax:
    new_view.set_syntax_file("Packages/"+syntax+"/"+syntax+".tmLanguage")
  new_view.run_command("simple_insert", {"contents": content})
  if ro:
    new_view.set_read_only(True)
  return new_view

def focus_view(context, view):
  if view.is_loading():
    sublime.set_timeout(lambda: focus_view(context, view), 100)
  else:
    window = get_window_by_context(context)
    window.focus_view(view)
    # stolen from http://www.sublimetext.com/forum/viewtopic.php?f=5&t=10997&p=48890&hilit=fuzzyfilenav#p48890
    window.run_command("show_panel", {"panel": "console"})
    window.run_command("hide_panel", {"cancel": True})

def open_file(context, filename):
  if os.path.exists(filename):
    view = get_window_by_context(context).open_file(filename)
    if view is not None:
      sublime.set_timeout(lambda: focus_view(context, view), 100)
    return view
  else:
    sublime.error_message('File not found:' + filename)
    return None

def exec_command(cmd, input=None, working_dir=None, env=None, context=None, callback=None):
  # by default display the output in a panel
  if callback is None:
    callback = "app.commando_show_panel"

  sublime.run_command("commando_exec", {"cmd": cmd, "input":input, "working_dir": working_dir,
                                        "env": env, "context": context, "callback": callback})

def commando(context, commands, input=None):
  if isinstance(commands, str):
    commands = [commands]
  elif not isinstance(commands, list):
    commands = []

  next_command = commands.pop(0)

  if isinstance(next_command, list):
    cmd_args = next_command[1]
    next_command = next_command[0]
  else:
    cmd_args = {}

  command_type = get_command_type(next_command)

  if not command_type:
    print('Command not found: ' + next_command)
    return

  runner = None

  if command_type == 'app':
    runner = sublime

  elif command_type == 'window':
    if not context['window_id']:
      print('Context error (window)')
    else:
      window = get_window_by_id(context['window_id'])
      if not window:
        print('Could not find window')
      else:
        runner = window

  elif command_type == 'text':
    if not context['window_id'] or not context['view_id']:
      print('Context error (view)')
    else:
      view = get_view_by_id(context['window_id'], context['view_id'])
      if not view:
        print('Could not find view')
      else:
        runner = view
  else:
    print('Unsupported command context')

  if runner:
    runner.run_command(next_command, {"context": context, "callback": commands,
                                      "input": input, "cmd_args": cmd_args})

