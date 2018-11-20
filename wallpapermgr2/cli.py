#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import supercli.argparse
# external
# internal


class CommandlineInterface(object):
    def __init__(self):
        self.parser = supercli.argparse.ArgumentParser(
            autocomp_cmd='wallmgr',
            description=(
                'wallpapermgr is a modular program to manage/display collections of wallpapers. \n'
                '\n'
                'Wallpapers are categorized into tar archives, and packaged into git project(s) \n'
                'for versioning and file-synchronization between machines. All of this is controlled \n'
                'by this program. \n'
            )
        )
        self.subparsers = self.parser.add_subparsers(dest='subparser_name')
        self._build_subparser_shortucts()
        self._build_subparser_display()
        self._build_subparser_archive()

    def _build_supbarser_shortcuts(self):
        self.subparsers.add_parser(
            'next',
            help=(
                'Display next wallpaper\n'
                '(short for `wallmgr display --next`)'
            ),
        )
        self.subparsers.add_parser(
            'prev',
            help=(
                'Display previous wallpaper\n '
                '(short for `wallmgr display --prev`)'
            )
        )
        # self.subparsers.add_parser(
        #     'shuffle',
        #     help=(
        #         'Shuffle existing order of wallpapers\n'
        #         '(short for `wallmgr data --shuffle-order`)'
        #     )
        # )
        # self.subparsers.add_parser(
        #     'pull',
        #     help='Pull latest wallpapers from git repository'
        # )
        # self.subparsers.add_parser(
        #     'push',
        #     help='Push wallpapers to git remote'
        # )
        self.subparsers.add_parser(
            'ls',
            help='List configured archives'
        )

    def _build_subparser_display(self):
        parser = self.subparsers.add_parser(
            'display',
            help=(
                'Commands related to Displaying wallpapers\n'
                '(see `wallmgr display --help`)'
            )
        )

        parser.add_argument(
            '-an', '--archive_name',
            help='Manually set the archive to display wallpapers from',
        )

        parser.add_argument(
            '-n', '--next',
            help='Display next wallpaper in sequence (looping if necessary)',
            action='store_true',
        )

        parser.add_argument(
            '-p', '--prev',
            help='Display previous wallpaper in sequence (looping if necessary)',
            action='store_true',
        )

        parser.add_argument(
            '-s', '--shuffle-order',
            help='Re-Randomize the order of wallpapers',
            action='store_true',
        )

    def _build_subparser_archive(self):
        parser = self.subparsers.add_parser(
            'archive',
            help=(
                'Manage archives containing wallpapers '
                '(append,create,delete,...)\n'
                '(see `wallmgr archive --help`)'
            )
        )

        parser.add_argument(
            '-l', '--list-archives',
            help='List all archives, and their descriptions',
            action='store_true',
        )

        parser.add_argument(
            '-an', '--archive_name',
            help='Manually set the archive to display wallpapers from',
        )

        parser.add_argument(
            '-a', '--append', nargs='+',
            help=(
                'Add wallpapers to an archive. If archive doesn\'t exist, '
                'it is created',
            ),
            metavar='horiz3x',
        )

        parser.add_argument(
            '--push',
            help=(
                'If gitroot/gitsource are defined in config, push any changes '
                'to gitroot to the repo'
            ),
            action='store_true',
        )

        parser.add_argument(
            '--pull',
            help=(
                'If gitroot/gitsource are defined in config, pull changes '
                'to gitroot to the repo (cloning if necessary)'
            ),
            action='store_true',
        )

    def parse_args(self):
        args = self.parser.parse_args()

        raise NotImplementedError()
