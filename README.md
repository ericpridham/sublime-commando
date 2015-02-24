# What is Commando?

Commando is a command builder plugin for Sublime Text 3.

# How do I use it?

A Commando command looks like this:

```json
"command": "commando",
"args": {
  "commands": [
    ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
    ["commando_new_file", {"syntax": "Diff", "scratch": true, "readonly": true, "name": "Git Diff"}]
  ]
}
```

This opens a thread that calls `git diff` on the file you currently have open and sends the output of that to a new tab called "Git Diff" with "Diff" syntax.  Pretty neat.

Now you can put this anywhere commands can be configured in Sublime.  Let's add this command everywhere.

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

Copy-pasting the same command in several places can get annoying, though, so if you want to take this a step further you can create your own named commands through a plugin.  Select `Tools` > `New Plugin...`, make the file look like this:

```python
from Commando.plugin import CommandoRun

class GitDiffFileCommand(CommandoRun):
  def commands(self):
    return [
      ["commando_exec", {"cmd": ["git", "diff", "$file"]}],
      ["commando_new_file", {"syntax": "Diff", "scratch": True, "readonly": True, "name": "Git Diff"}]
    ]
```

and save it as *My Commands.py*.  Now you have a new Sublime command called `git_diff_file` that you can use everywhere in place of `commando`.  So this:

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

becomes this:

```json
{ "keys": ["ctrl+shift+d"], "command": "git_diff_file" },
```

But wait, there's more!  There are already [several useful commando commands](https://github.com/ericpridham/sublime-commando/wiki/User-Documentation) you can use to build your own command, but if you need to you can also create your own if you want to.  *Documentation coming soon!  For now, check out `commands.py`.*

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

