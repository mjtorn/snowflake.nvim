import abc
import neovim
import os
import subprocess
import yaml

from collections import OrderedDict
from collections import namedtuple

MenuStat = namedtuple('MenuStat', ('manager', 'line', 'col'))

SNOWFLAKE_YAML = 'snowflake.yaml'
SNOWFLAKE_RST_DIR = 'snowflake-files'
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

        self.scenes = []

    def contribute_to_menu(self, buf):
        """Affect what is shown in the menu in `buf`
        """

        prefix = '-' if self.expanded else '+'
        title = '{}{}'.format(prefix, self.title)

        buf.append(title)


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

        return MenuStat(in_manager, menu_line, curr_col)

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
