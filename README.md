# What is Commando?

Commando is a command builder plugin for Sublime Text 3.

# How do I use it?

There are two ways to use Commando.

## Keymaps

First, you can quickly build your own commands through custom keymap actions.  Just put this in a sublime-keymap file:

```json
{ "keys": ["ctrl+shift+d"], "command": "commando", "args": {
  "commands": [
    ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
    ["commando_new_file", {"syntax": "Diff", "scratch": true, "readonly": true, "name": "Git Diff"}]
  ]
}}
```

This will run a `git diff` on the current file and output the results in a new tab.

## Plugins

Commando also makes this command building functionality available to plugin developers through a couple new classes,
`CommandoRun` and `CommandoCmd`.

`CommandoRun` is used to create new high-level commands. Essentialy it is a way of packaging a keymap action into it's
own named command.  For example, you can create a new plugin file with this:

```python
from Commando.plugin import CommandoRun

class GitDiffFileCommand(CommandoRun):
  def commands(self):
    return [
      ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
      ["commando_new_file", {"syntax": "Diff", "scratch": True, "readonly": True, "name": "Git Diff"}]
    ]
```

And now you have a new Sublime command, `git_diff_file`.  Then you can update your keymap to just:

```json
{ "keys": ["ctrl+shift+d"], "command": "git_diff_file" },
```

`CommandoCmd` is used to create your own individual commands that can be chained together in a commando run, like
`commando_exec` and `command_new_file` in the above example.

# Installation

## Manual

Clone this repository as a subdirectory of your Sublime Text 3 Packages directory with the name "Commando".  So, for instance:

```bash
cd ~/Library/Application\ Support/Sublime\ Text\ 3/Packages
git clone https://github.com/ericpridham/sublime-commando.git Commando
```

# Get Into It

Check out [the wiki](../../wiki) for full documentation.

