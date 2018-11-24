#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import argparse
import logging
import numbers
import sys
# external
# internal
from wallpapermgr import display, datafile


logger = logging.getLogger(__name__)


class CommandlineInterface(object):
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description=(
                'wallpapermgr is a modular program to manage/display collections of wallpapers. \n'
                '\n'
                'Wallpapers are categorized into tar archives, and packaged into git project(s) \n'
                'for versioning and file-synchronization between machines. All of this is controlled \n'
                'by this program. \n'
            )
        )
        self.subparsers = self.parser.add_subparsers(dest='subparser_name')

        self.parser.add_argument(
            '-i', '--interval', help='override number of seconds between wallpaper changes',
            #type=numbers.Number,
        )
        self.parser.add_argument(
            '-v', '--verbose', help='enable verbose logging',
            action='store_true',
        )
        self.parser.add_argument(
            '-vv', '--very-verbose', help='enable very verbose logging',
            action='store_true',
        )

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
        self.subparsers.add_parser(
            'stop', help='Request shutdown of the wallpaper-server',
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

        loglvl = logging.WARNING
        if args.verbose:
            loglvl = logging.INFO
        elif args.very_verbose:
            loglvl = logging.DEBUG

        logging.basicConfig(
            level=loglvl,
            format='%(asctime)s %(levelname)-10s - %(message)s',
            datefmt='%Y/%m/%d %H:%M',
        )

        # if no args, start server
        if not subparser:
            if not display.Server.is_active():
                print('starting wallpapermgr server')
                srv = display.Server(interval=args.interval)
                srv.serve_forever()
                return
            elif args.interval:
                if subparser != display.RequestHandler.stop_command:
                    display.Server.request('interval {}'.format(args.interval))
                return

        # interact-with server
        subparser_map = {
            'next': lambda: display.Server.request('next'),
            'prev': lambda: display.Server.request('prev'),
            'reload': lambda: display.Server.request('reload'),
            'ls': datafile.print_archive_list,
            'stop': lambda: display.Server.request(display.RequestHandler.stop_command)
        }

        # subparser handling
        if subparser in subparser_map:
            subparser_map[subparser]()

        elif subparser == 'archive':
            self._parse_subparser_archive(args)

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
