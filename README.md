# What is Commando?

Commando is a command builder plugin for Sublime Text 3.

# How do I use it?

There are two ways to use Commando.

## Built-In

First, you can quickly build your own commands anywhere Sublime commands can be called.

**Command Palette**

To add a command to the Command Palette menu, create a new .sublime-commands file.  For instance, create a new file called `Packages/User/My Commands.sublime-commands` and put this in it:

```json
[
  {
    "caption": "Diff File",
    "command": "commando",
    "args": {
      "commands": [
        ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
        ["commando_new_file", {"syntax": "Diff", "scratch": true, "readonly": true, "name": "Git Diff"}]
      ]
    }
  }
]
```

Now you can hit `super`+`shift`+`p`, type "Diff File" and this will call `git diff` on the current file you're in and send the output to a new tab.

**Keymaps**

This also works in keymaps files.  Add this to your `Packages/User/Default (<Your OS>).sublime-keymap` file:

```json
{ "keys": ["ctrl+shift+d"], "command": "commando", "args": {
  "commands": [
    ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
    ["commando_new_file", {"syntax": "Diff", "scratch": true, "readonly": true, "name": "Git Diff"}]
  ]
}}
```

Now hitting `ctrl`+`shift`+`d` will the same thing.

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

Check out [the wiki](https://github.com/ericpridham/sublime-commando/wiki) for full documentation.

