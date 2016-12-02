# Snowflake.nvim

A [Neovim](https://neovim.io/) plugin written in [Python 3](https://docs.python.org/3/) for writing in a [Snowflake](http://www.advancedfictionwriting.com/articles/snowflake-method/) fashion. Licensed under WTFPL2, see
LICENSE for details.

## How?

### Snowflake

Launch it with `:Snowflake` and it will set up a writing evironment or load one if it exists already.
It will prompt you with basic information when setting up something new.

`snowflake.nvim` uses YAML files for metadata and configuration.

The actual text is written in [RST](http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html).
I chose RST because it supports comments. You may use it for its more advanced
features if you want to, of course, but for me it's the comments.

Of course you may choose not to follow the Snowflake method at all. That's fine, of course; `snowflake.nvim`
might still work for you.

### SnowflakeBuild

`:SnowflakeBuild` will build your documents under the `out/` directory.

Currently only ODT is supported (beside RST), so make sure `python-docutils` is installed!

### Menu

  * `<Space>` opens and collapses the current menu item.
  * `L` on a menu item sets the layout.
  * `a` appends a scene after the cursor line in the `SCENES` menu.
  * `A` prepeds a scene before the cursor line in the `SCENES` menu.
  * `o` opens a scene for editing.
  * `J` moves a scene down in the list
  * `K` moves a scene up in the list

## Why?

I'm a huge fan of [Liquid Story Binder XE](http://www.blackobelisksoftware.com/index.html).
Unfortunately any way to run it in Linux is a bit shoddy, and last I heard, there are no plans to
port it to Linux.

I use Neovim in my day job for programming and editing documents, so it's logical to want to leverage
it for this purpose.

I use Python 3 almost exclusively as my programming language of choice, therefore why not go with it?

As a bonus you can use whatever other plugins you want to for eg. version control.

## Contribution?

Despite the license, pull requests are welcome. I hope to get tons of writing done, instead of letting
the hobby and this tool fade away.

