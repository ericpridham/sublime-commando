# What is Commando?

Commando is a command builder plugin for Sublime Text 3.

# How do I use it?

There are two ways to use Commando.

## Built-In

First, you can quickly build your own commands anywhere Sublime commands can be called.  Lets create a command that calls `git diff` on the current file and put it everywhere.

**Menus**

In your `Packages/User/` directory create these files:

*Main.sublime-menu*
```json
[
  {
    "caption": "Tools",
    "id": "tools",
    "children": [
      {
        "caption": "My Commands",
        "id": "my-commands",
        "children": [
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
      }
    ]
  }
]
```

*Context.sublime-menu*
```json
[
  {
    "caption": "My Commands",
    "id": "my-commands",
    "children": [
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
  }
]
```

And now you have your own Tools > My Commands menu, as well as a context menu called My Commands (right click on any file).

**Command Palette**

To add a command to the Command Palette menu, create a new .sublime-commands file.  Create a new file called `Packages/User/My Commands.sublime-commands` and put this in it:

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

Now open up the command pallet and type "Diff File".

**Keymaps**

This also works in keymaps files.  Add this to your `Packages/User/Default (<Your OS>).sublime-keymap` file:

```json
[
  {
    "keys": ["ctrl+shift+d"],
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

Now hitting `ctrl`+`shift`+`d` do the diff as well.

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

## Package Control

The package is registered in [Package Control](https://packagecontrol.io/) under the name `Commando`.

## Manual

Clone this repository as a subdirectory of your Sublime Text 3 Packages directory with the name `Commando`.  So, for instance:

```bash
cd ~/Library/Application\ Support/Sublime\ Text\ 3/Packages
git clone https://github.com/ericpridham/sublime-commando.git Commando
```

# Get Into It

Check out [the wiki](https://github.com/ericpridham/sublime-commando/wiki) for full documentation.

