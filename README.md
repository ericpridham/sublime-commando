# What is this?

Commando wraps around built-in Sublime commands and allows them to be chained together to build more complex commands.

## Huh?

OK, check this out:

```json
{ "keys": ["ctrl+shift+x"], "command": "commando", "args": {
 "cmd_args": {
   "commands": [
     ["commando_exec", {"cmd": ["ls", "-l"]}],
     "commando_show_panel"
   ]
 }
}}
```

This open the output of `ls -l` in a panel.

## ... and?

Fine, how about this:

```json
{ "keys": ["ctrl+shift+d"], "command": "commando", "args": {
 "cmd_args": {
   "commands": [
     ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
     ["commando_new_file", {"syntax": "Diff", "scratch": true, "ro": true, "name": "Git Diff"}]
   ]
 }
}}
```

Runs a git diff on the current file and puts the output in a new scratch view with syntax highlighting.

## That's a little more useful.

I hope so!  How it works is, the list of commands is run in order using the "output" from the previous command as the "input" to the next.

There are currently wrappers for `exec`, `new_file`, `open_file`, `show_panel`, `quick_panel`, `input_panel`, `ok_cancel_dialog`.  Each command tries to act the Right Way.  The "input" becomes the content of `new_file`, is the file name for `open_file`, is "stdin" for `exec`, etc.  A lot of the defaults can also be overridden.

## Neat.

But wait, there's more!  Creating your own commands through keybindings is just the beginning.  The functionality is also available for plugin developers through custom Application/Window/TextCommand classes.  Want to turn the git diff above it's own command, say `git_diff_file`?  Start your own plugin, and try this:

```python
import sublime, sublime_plugin
from Commando import commando

class GitDiffFileCommand(commando.TextCommando):
  def cmd(self, input, args):
    self.commando([
      ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
      ["commando_new_file", {"syntax": "Diff", "scratch": True, "ro": True, "name": "Git Diff"}]
    ])
```

And now you can just do:

```json
{ "keys": ["ctrl+shift+d"], "command": "git_diff_file" },
```

# More to come ...
