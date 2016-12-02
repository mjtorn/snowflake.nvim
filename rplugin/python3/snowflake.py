import abc
import neovim
import os
import subprocess
import uuid
import yaml

from collections import OrderedDict
from collections import namedtuple

MenuStat = namedtuple('MenuStat', ('manager', 'offset', 'line', 'col'))

SNOWFLAKE_YAML = 'snowflake.yaml'
SNOWFLAKE_RST_DIR = 'snowflake-files'
SNOWFLAKE_SCENES_YAML = 'snowflake-scenes.yaml'
SNOWFLAKE_SCENES_DIR = 'snowflake-scenes'
SNOWFLAKE_OUT_DIR = 'out'
SNOWFLAKE_ONE_DOCS_FILE = 'one-docs.rst'

# XXX: Just assume this exists
CONVERSION = ('/usr/bin/rst2odt', '.odt')


class Manager:
    __metaclass__ = abc.ABCMeta

    # They all start collapsed
    expanded = False

    @abc.abstractmethod
    def contribute_to_menu(self, buf):
        """Dummy for contributing to menu
        """

        pass

    @abc.abstractmethod
    def set_layout(self, nvim):
        """Configure the layout
        """

        pass

    @abc.abstractmethod
    def build(self, snowflake):
        """Implement this to build your document(s)
        """

        pass


class SnowflakeManager(Manager):
    """Manage the one-something docs
    """

    title = 'SNOWFLAKE'

    snowflake_files = OrderedDict((
        ('one-line', os.path.join(SNOWFLAKE_RST_DIR, 'one-line.rst')),
        ('one-paragraph', os.path.join(SNOWFLAKE_RST_DIR, 'one-paragraph.rst')),
        ('one-page', os.path.join(SNOWFLAKE_RST_DIR, 'one-page.rst')),
        ('synopsis', os.path.join(SNOWFLAKE_RST_DIR, 'synopsis.rst')),
    ))

    snowflake_defaults = OrderedDict((
        ('one-line', '.. Replace this comment with your one-line summary.'),
        ('one-paragraph', '.. Expand your one-line summary to a paragraph, replace this comment with that.'),
        ('one-page', '.. Expand every sentence from your paragraph to replace this comment with a one-page summary.'),
        ('synopsis', '.. You may also write a longer synopsis instead of this comment.'),
    ))

    def __init__(self):
        """Validate on startup
        """

        if not os.path.exists(SNOWFLAKE_RST_DIR):
            os.mkdir(SNOWFLAKE_RST_DIR)

        if not os.path.exists(SNOWFLAKE_SCENES_DIR):
            os.mkdir(SNOWFLAKE_SCENES_DIR)

        for key, snowflake_file in self.snowflake_files.items():
            if not os.path.exists(snowflake_file):
                with open(snowflake_file, 'wb') as f:
                    f.write(self.snowflake_defaults[key].encode('utf-8'))

    def contribute_to_menu(self, buf):
        """Affect what is shown in the menu in `buf`
        """

        prefix = '-' if self.expanded else '+'
        title = '{}{}'.format(prefix, self.title)

        buf.append(title)
        if self.expanded:
            for snowflake_file in self.snowflake_files.values():
                fname = snowflake_file.rsplit(os.sep, 1)[-1]

                buf.append('  {}'.format(fname))
            buf.append('')

    def set_layout(self, nvim):
        """Create a layout here
        """

        assert len(nvim.windows) == 2

        # nvim.input('<C-w>l')
        nvim.command('wincmd l')

        # Create one-line
        nvim.command('split')
        nvim.command('edit {}'.format(self.snowflake_files['one-line']))
        nvim.command('setlocal nonumber norelativenumber foldcolumn=0')

        # Go down for one-paragraph, one-page and synopsis
        # nvim.input('<C-w>j')
        nvim.command('wincmd j')

        nvim.command('vsplit')
        nvim.command('edit {}'.format(self.snowflake_files['one-paragraph']))
        nvim.command('setlocal textwidth=60')

        # nvim.input('<C-w>l')
        nvim.command('wincmd l')
        nvim.command('edit {}'.format(self.snowflake_files['one-page']))
        nvim.command('setlocal textwidth=80')

        nvim.command('vsplit')
        # nvim.input('<C-w>l')
        nvim.command('wincmd l')
        nvim.command('edit {}'.format(self.snowflake_files['synopsis']))
        nvim.command('setlocal textwidth=90')

        ## XXX: Relying on numbers like this is generally dangerous
        ##      but I think it's ok for this initial case
        # Set the sizes
        nvim.windows[0].width = 30
        nvim.windows[1].height = 3
        nvim.windows[2].width = 60
        nvim.windows[3].width = 80
        nvim.windows[4].width = 90

        # Go to one-liner
        nvim.command('2 wincmd w')

    def build(self, snowflake):
        """Compile the one-docs to one mega doc
        """

        ones_out_path = os.path.join(SNOWFLAKE_OUT_DIR, SNOWFLAKE_ONE_DOCS_FILE)
        with open(ones_out_path, 'wb') as out_f:
            for item in ('one-line', 'one-paragraph', 'one-page'):
                heading = item.rsplit('-', 1)[1]
                heading = 'One {}'.format(heading)

                with open(self.snowflake_files[item], 'rb') as f:
                    out_f.write(heading.encode('utf-8'))
                    out_f.write(b'\n')
                    out_f.write(len(heading.encode('utf-8')) * b'=')
                    out_f.write(b'\n\n')

                    text = f.read().strip()
                    out_f.write(text)
                    out_f.write(b'\n\n')

        synopsis_out_path = os.path.join(SNOWFLAKE_OUT_DIR, 'synopsis.rst')
        with open(synopsis_out_path, 'wb') as out_f:
            with open(self.snowflake_files['synopsis'], 'rb') as f:
                out_f.write(f.read())

        cmd, suffix = CONVERSION
        for path in (ones_out_path, synopsis_out_path):
            converted_path = path.rsplit('.', 1)[0] + suffix

            retval = subprocess.call([cmd, path, converted_path])

            if retval != 0:
                raise RuntimeError('Command failed')


class SceneManager(Manager):
    """To maintain a list of scenes
    """

    title = 'SCENES'

    def __init__(self):
        """Set initial data
        """

        if os.path.exists(SNOWFLAKE_SCENES_YAML):
            with open(SNOWFLAKE_SCENES_YAML, 'rb') as f:
                self.scenes = yaml.load(f.read())
        else:
            self.scenes = []

    def contribute_to_menu(self, buf):
        """Affect what is shown in the menu in `buf`
        """

        prefix = '-' if self.expanded else '+'
        title = '{}{}'.format(prefix, self.title)

        buf.append(title)

        if self.expanded:
            for scene in self.scenes:
                buf.append('  {}'.format(scene['title']))
                buf.append('   {}'.format(scene['descr']))

    def build(self, snowflake):
        """Compile the one-docs to one mega doc
        """

        out_filename = '{}.rst'.format(snowflake['info']['name'])
        out_path = os.path.join(SNOWFLAKE_OUT_DIR, out_filename)
        with open(out_path, 'wb') as out_f:
            for scene in self.scenes:
                in_filename = scene['filename']
                with open(in_filename, 'rb') as in_f:
                    out_f.write(in_f.read())
                    out_f.write(b'\n')

        cmd, suffix = CONVERSION
        converted_path = out_path.rsplit('.', 1)[0] + suffix

        retval = subprocess.call([cmd, out_path, converted_path])

        if retval != 0:
            raise RuntimeError('Command failed')

    def add_at(self, idx, nvim):
        """Add an entry at given list index (0-indexed)
        """

        fname = '{}.rst'.format(uuid.uuid4())
        fname = os.path.join(SNOWFLAKE_SCENES_DIR, fname)

        title = nvim.funcs.input('Scene title> ')
        descr = nvim.funcs.input('Scene description> ')
        scene = OrderedDict((
            ('title', title),
            ('descr', descr),
            ('filename', fname),
        ))

        if not self.scenes:
            assert idx == 0
        else:
            assert idx >= 0

        self.scenes.insert(idx, scene)

        with open(fname, 'wb') as f:
            f.writelines((
                '.. {}\n'.format(scene['title']).encode('utf-8'),
                '.. {}\n'.format(scene['descr']).encode('utf-8'),
                b'\n',
            ))

        self.save()

    def save(self):
        """Flush the thing to disk
        """

        with open(SNOWFLAKE_SCENES_YAML, 'wb') as f:
            f.write(yaml.dump(self.scenes).encode('utf-8'))

    def move(self, from_idx, to_idx):
        """Move a list entry
        """

        assert from_idx >= 0
        assert to_idx >= 0

        self.scenes.insert(to_idx, self.scenes.pop(from_idx))

        self.save()

    def get_file_by_idx(self, idx):
        """Look at the scene list and return the relevant file name
        """

        if self.scenes:
            scene = self.scenes[idx]

            return scene['filename']


@neovim.plugin
class SnowflakePlugin(object):
    """Plugin to work with RST files in a Snowflake fashion
    """

    initial_info = OrderedDict((
        ('name', None),
        ('author', None),
        ('copyright-year', None),
    ))

    snowflake_prompts = OrderedDict((
        ('name', 'Snowflake name> '),
        ('author', 'Author name> '),
        ('copyright-year', 'Copyright year> '),
    ))

    managers = OrderedDict((
        ('snowflake', SnowflakeManager()),
        ('scene', SceneManager()),
    ))

    def __init__(self, nvim):
        self.nvim = nvim
        self.manager = self.managers['snowflake']

        self.snowflake = OrderedDict()
        self.snowflake['info'] = self.initial_info
        self.snowflake['file-list'] = OrderedDict((
            ('snowflake', self.managers['snowflake'].snowflake_files),
            ('scenes', self.managers['scene'].scenes),
        ))

        self.menu_win_handle = None

        # I use MiniBufExplorer, but not here
        self.nvim.vars['miniBufExplAutoStart'] = 0

    @neovim.command('Snowflake', range='', nargs='*')
    def init_snowflake(self, args, range):
        """Set the current environment up for working
        """

        # Simple check to see if we're inited already
        if self.menu_win_handle is not None:
            return

        if os.path.exists(SNOWFLAKE_YAML):
            self.load_snowflake()

        self.check_snowflake()
        self.save_snowflake(SNOWFLAKE_YAML)

        self.make_menu_pane()
        self.update_menu()
        self.manager.set_layout(self.nvim)

    @neovim.command('SnowflakeBuild', nargs=0)
    def build_snowflake(self):
        """Build documents
        """

        # XXX: Could change to nargs=1 and have config files
        #      or maybe just have one config file

        for manager in self.managers.values():
            manager.build(self.snowflake)

    @neovim.function('SnowflakeToggleMenu', sync=True)
    def toggle_menu(self, args):
        """Menu toggler
        """

        menu_stat = self.menu_stat()

        if menu_stat.manager is not None:
            menu_stat.manager.expanded = not menu_stat.manager.expanded
            self.update_menu()

            self.nvim.funcs.cursor(menu_stat.line, menu_stat.col)

    @neovim.function('SnowflakeSetLayout', sync=True)
    def set_layout(self, args):
        """Set layout based on current menu
        """

        menu_stat = self.menu_stat()

        if menu_stat.manager is not None:
            self.clean_windows()
            menu_stat.manager.set_layout(self.nvim)
            self.update_menu()

    @neovim.function('SnowflakePrependScene', sync=True)
    def prepend_scene(self, args):
        """Add a scene above cursor
        """

        menu_stat = self.menu_stat()

        # Be lazy and deny prepending in an empty list, use append instead
        if menu_stat.offset == 0:
            return

        idx = menu_stat.offset - 1 if menu_stat.offset > 0 else menu_stat.offset

        idx //= 2

        if callable(getattr(menu_stat.manager, 'add_at', None)):
            menu_stat.manager.add_at(idx, self.nvim)

            if not menu_stat.manager.expanded:
                menu_stat.manager.expanded = True

            self.update_menu(menu_stat)

    @neovim.function('SnowflakeAppendScene', sync=True)
    def append_scene(self, args):
        """Add a scene
        """

        menu_stat = self.menu_stat()

        if menu_stat.offset > 0 and menu_stat.offset % 2 == 1:
            idx = menu_stat.offset + 1
        else:
            idx = menu_stat.offset

        idx //= 2

        if callable(getattr(menu_stat.manager, 'add_at', None)):
            menu_stat.manager.add_at(idx, self.nvim)

            if not menu_stat.manager.expanded:
                menu_stat.manager.expanded = True

            self.update_menu(menu_stat)

    @neovim.function('SnowflakeMoveScene', sync=True)
    def move_scene(self, args):
        """Move a scene above cursor
        """

        assert len(args) == 1
        direction = args[0]
        assert direction in (-1, +1)

        menu_stat = self.menu_stat()

        # Do nothing with a list too small, or a bad position
        if menu_stat.offset < 3 and direction == -1:
            return

        idx = menu_stat.offset - 1 if menu_stat.offset > 0 else menu_stat.offset

        idx //= 2

        if callable(getattr(menu_stat.manager, 'move', None)):
            dst_idx = idx + direction
            menu_stat.manager.move(idx, idx + direction)

            # Forge a new MenuStat to track the cursor
            self.update_menu(MenuStat(menu_stat.manager, 1 + (2 * dst_idx), menu_stat.line, menu_stat.col))

    @neovim.function('SnowflakeEditScene', sync=True)
    def edit_scene(self, args):
        """Open a scene file for editing
        """

        menu_stat = self.menu_stat()

        self.clean_windows()
        menu_stat.manager.set_layout(self.nvim)
        self.update_menu()

        # Do some trickery to get from vim's line numbers
        # for titles and descriptions to the actual structure
        if menu_stat.offset == 0:
            # Don't allow editing when there's nothing to edit
            return
        else:
            idx = menu_stat.offset - 1

        idx //= 2

        for window in self.nvim.windows:
            if window.handle != self.menu_win_handle:
                break
        else:
            window = None

        if window is not None:
            # Pass as a dummy value to ensure the correct layout here
            # self.set_layout(None)

            if callable(getattr(menu_stat.manager, 'get_file_by_idx', None)):
                fname = menu_stat.manager.get_file_by_idx(idx)
                if fname is not None:
                    self.nvim.command('{} wincmd w'.format(window.number))
                    self.nvim.command('edit {}'.format(fname))

    @neovim.autocmd('BufWritePost', pattern='*.rst', eval='expand("<afile>")', sync=True)
    def on_bufwritepost_updatemenu(self, filename):
        self.update_menu()

    def load_snowflake(self):
        """Load a Snowflake file
        """

        with open(SNOWFLAKE_YAML, 'rb') as f:
            self.snowflake.update(yaml.load(f.read()))

    def check_snowflake(self):
        """Ensure the project state
        """

        for key, prompt in self.snowflake_prompts.items():
            if self.snowflake['info'].get(key) is None:
                self.snowflake['info'][key] = self.nvim.funcs.input(prompt)

        if not os.path.exists(SNOWFLAKE_OUT_DIR):
            os.mkdir(SNOWFLAKE_OUT_DIR)

    def save_snowflake(self, out_file):
        """Store the project state
        """

        with open(SNOWFLAKE_YAML, 'wb') as f:
            f.write(yaml.dump(self.snowflake).encode('utf-8'))

    def menu_stat(self):
        """Get the current menu manager we're at
        """

        # Good thing this doesn't have to be web scale

        win_number = self.nvim.funcs.win_id2win(self.menu_win_handle)

        menuwin = self.nvim.windows[win_number - 1]
        menubuf = menuwin.buffer

        curr_line = self.nvim.funcs.line('.')
        curr_col = self.nvim.funcs.col('.')

        in_manager = None
        menu_line = None
        for i, line in enumerate(menubuf):
            if not line:
                continue

            prefix = line[0]
            rest = line[1:]

            # vim indexes from 1
            if prefix in ('+', '-') and i <= curr_line - 1:
                for manager in self.managers.values():
                    if rest == manager.title:
                        in_manager = manager
                        menu_line = i + 1
                        break

        offset = curr_line - menu_line

        return MenuStat(in_manager, offset, menu_line, curr_col)

    def clean_windows(self):
        """Reap all windows, but leave menu and another one so
        managers can assume they have another window to go.
        """

        for window in self.nvim.windows:
            if window.handle != self.menu_win_handle:
                ret = self.nvim.funcs.win_gotoid(window.handle)
                assert ret == 1
                self.nvim.command('close!')
            if len(self.nvim.windows) == 2:
                break

    def make_menu_pane(self):
        """Split out what will be the menu
        """

        for buffer in self.nvim.buffers:
            if buffer.options['buflisted']:
                self.nvim.command('bdelete! {}'.format(buffer.number))

        self.nvim.command('vsplit')

        self.menu_win_handle = self.nvim.funcs.win_getid()
        win_number = self.nvim.funcs.win_id2win(self.menu_win_handle)

        # Want to deal with the tree
        self.nvim.command('nmap <silent><buffer> <Space> :call SnowflakeToggleMenu()<CR>')
        self.nvim.command('nmap <silent><buffer> L :call SnowflakeSetLayout()<CR>')
        self.nvim.command('nmap <silent><buffer> A :call SnowflakePrependScene()<CR>')
        self.nvim.command('nmap <silent><buffer> a :call SnowflakeAppendScene()<CR>')
        self.nvim.command('nmap <silent><buffer> o :call SnowflakeEditScene()<CR>')
        self.nvim.command('nmap <silent><buffer> K :call SnowflakeMoveScene(-1)<CR>')
        self.nvim.command('nmap <silent><buffer> J :call SnowflakeMoveScene(+1)<CR>')

        self.nvim.windows[win_number - 1].buffer.options['buflisted'] = False

    def update_menu(self, menu_stat=None):
        """Update the menu with whatever we're currently doing.
        Optional `menu_stat` resets the cursor location
        """

        win_number = self.nvim.funcs.win_id2win(self.menu_win_handle)

        menuwin = self.nvim.windows[win_number - 1]
        menubuf = menuwin.buffer

        menubuf.options['modifiable'] = True

        menubuf[:] = ['']
        menubuf[0] = 'MENU'
        menubuf.append('====')
        menubuf.append('')

        for manager in self.managers.values():
            manager.contribute_to_menu(menubuf)

        menubuf.options['modifiable'] = False
        menubuf.options['buftype'] = 'nofile'
        menubuf.options['bufhidden'] = 'hide'

        menuwin.options['number'] = False
        menuwin.options['relativenumber'] = False
        menuwin.options['foldcolumn'] = 0
        menuwin.options['wrap'] = False

        self.nvim.windows[win_number - 1].width = 30

        if menu_stat is not None:
            self.nvim.funcs.cursor(menu_stat.line + menu_stat.offset, menu_stat.col)
