#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import supercli.argparse
import sys
# external
# internal
from wallpapermgr2 import display, datafile


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

        shortcut_map = dict(
            next=display.next,
            prev=display.prev,
            reload=display.reload,
        )
        subparser = args.subparser_name
        if subparser in shortcut_map:
            shortcut_map[subparser]()
            return

        if subparser == 'display':
            if args.archive_name:
                display.set_archive(args.archive_name)

            if args.next:
                display.next()

            if args.prev:
                display.prev()

            if args.reload:
                display.reload()

            return

        if subparser == 'archive':
            raise NotImplementedError()


class CommandlineInterface2(object):
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

        self._build_args()
        self._build_subparser_archive()

    def _build_args(self):
        self.subparsers.add_parser(
            'next', help=(
                'Display next wallpaper\n'
                '(short for `wallmgr display --next`)'
            ),
        )
        self.subparsers.add_parser(
            'prev', help=(
                'Display previous wallpaper\n '
                '(short for `wallmgr display --prev`)'
            )
        )
        self.subparsers.add_parser(
            'ls', help='List configured archives'
        )
        self.subparsers.add_parser(
            'reload', help='Reload/Shuffle order of items in archives',
        )

    def _build_subparser_archive(self):
        parser = self.subparsers.add_parser(
            'archive', help='Set current archive or modify/retrieve an archive'
        )
        parser.add_argument(
            'archive', help=(
                'The target archive. If used alone, sets archive '
                'wallpapers are read from'
            ),
        )
        parser.add_argument(
            '--add', help='Add images to an archive',
            nargs='*',
        )
        parser.add_argument(
            '--remove', help='Remove images from an archive',
            nargs='*',
        )
        parser.add_argument(
            '--pull', help='Git Pull an archive',
            action='store_true',
        )
        parser.add_argument(
            '--push', help='Git Push an archive',
            action='store_true',
        )

    def parse_args(self):
        args = self.parser.parse_args()
        subparser = args.subparser_name

        # common args
        subparser_map = {
            'next': display.next,
            'prev': display.prev,
            'reload': display.reload,
            'ls': datafile.print_archive_list,
        }

        if subparser in subparser_map:
            subparser_map[subparser]()
            return

        elif subparser == 'archive':
            self._parse_subparser_archive(args)

        else:
            print('starting wallpapermgr server')
            srv = display.Server()
            srv.serve_forever()

    def _parse_subparser_archive(self, args):
        # change archive
        all_args = (args.add, args.remove, args.pull, args.push)
        if len([x for x in all_args if x]) == 0:
            display.set_archive(args.archive)
            return

        # add/remove
        if args.add and args.remove:
            print('cannot use --add and --remove together')
            sys.exit(1)
        elif args.add:
            raise NotImplementedError('todo')
        elif args.remove:
            raise NotImplementedError('todo')

        # pull/push
        if args.pull and args.push:
            print('cannot use --pull and --push together')
            sys.exit(1)
        elif args.pull:
            raise NotImplementedError('todo')
        elif args.push:
            raise NotImplementedError('todo')


if __name__ == '__main__':
    cli = CommandlineInterface2()
    cli.parse_args()
