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
            '--pull', help='Git Pull an archive. (clones if not present)',
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
            display.change_archive(args.archive)
            return

        archive = datafile.Archive(args.archive)

        # add/remove
        if args.add and args.remove:
            print('cannot use --add and --remove together')
            sys.exit(1)
        elif args.add:
            archive.add(args.add)
        elif args.remove:
            archive.remove(args.remove)

        # pull/push
        if args.pull and args.push:
            print('cannot use --pull and --push together')
            sys.exit(1)
        elif args.pull:
            archive.pull()
        elif args.push:
            archive.push()

    @staticmethod
    def show():
        cli = CommandlineInterface()
        cli.parse_args()


if __name__ == '__main__':
    CommandlineInterface.show()
