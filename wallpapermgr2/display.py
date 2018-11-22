#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import logging
import subprocess
import os
import socket
import socketserver
import threading
import time
import sys
import tarfile
import glob
# external
import xdg.BaseDirectory
# internal
from wallpapermgr2 import datafile


logger = logging.getLogger(__name__)


def change_archive(archive_name):
    """ Set archive that wallpapers are being displayed from,
    starting server if not running.
    """
    Server.request('archive {}'.format(archive_name))


def next():
    """ Show next wallpaper within current archive,
    starting server if not running.
    """
    Server.request('next')


def prev():
    """ Show previous wallpaper within current archive,
    starting server if not running.
    """
    Server.request('prev')


def reload():
    """ Re-reads each archive, shuffles order,
    and if server is already running, reloads data within server.

    .. note::
        does *not* start server if not already running.

    """
    data = datafile.Data()
    data.reload_archive()
    if Server.is_active():
        Server.request('reload')


def stop():
    """ Request shutdown of the wallpapermgr server.
    """
    Server.request('stop')


class RequestHandler(socketserver.BaseRequestHandler):
    """ SocketServer RequestHandler, parses/executes commands.
    """
    @property
    def command_map(self):
        return dict(
            next=dict(
                handler=self._handle_next,
                desc='show next wallpaper'
            ),
            prev=dict(
                handler=self._handle_prev,
                desc='show prev wallpaper'
            ),
            archive=dict(
                handler=self._handle_archive,
                desc='change archive wallpapers are loaded from.',
            ),
            stop=dict(
                handler=self._handle_stop,
                desc='stop wallpaper daemon'
            ),
            reload=dict(
                handler=self._handle_reload,
                desc='reload from configfile/datafile'
            ),
            help=dict(
                handler=self._handle_help,
                desc='print help message'
            ),
        )

    def handle(self):
        rawdata = self.request.recv(1024)
        if not rawdata:
            return

        data = rawdata.decode()
        data = str(data).strip()
        self._run_command(data)

    def _run_command(self, command):
        keyword = command.split()[0]
        args = command.split()[1:]
        if keyword not in self.command_map:
            msg = 'invalid command: "{}"'.format(command)
            self.request.send(msg.encode())
            return

        self.command_map[keyword]['handler'](*args)

    def _handle_next(self):
        data = self.server.data
        archive = self.server.current_archive
        index = self.server.current_index

        if (index + 1) < data.archive_len(archive):
            index = index + 1
        else:
            index = 0

        self._display(archive, index)

    def _handle_prev(self):
        data = self.server.data
        archive = self.server.current_archive
        index = self.server.current_index

        if (index - 1) >= 0:
            index = index - 1
        else:
            index = data.archive_len(archive) - 1

        self._display(archive, index)

    def _handle_archive(self, archive):
        self.server.set_archive(archive)
        msg = 'switching to archive {}'.format(archive)
        self.request.send(msg.encode())

    def _handle_stop(self):
        # shutdown requests hang if performed in same thread as server
        self.request.send(b'shutting down server..')
        t = threading.Thread(target=self.server.shutdown)
        t.start()

    def _handle_reload(self):
        self.request.send(b'reloading from saved data/config files..')

    def _handle_help(self):
        reply = [
            '',
            'available commands:',
            '===================',
        ]
        for cmd in self.command_map:
            reply.append('  {}:  {}'.format(cmd, self.command_map[cmd]['desc']))

        self.request.send('\n'.join(reply).encode() + b'\n\n')

    def _display(self, archive, index):
        self.server.display(archive, index)
        msg = 'displaying {}({})'.format(archive, index)
        self.request.send(msg.encode())


class Server(socketserver.UnixStreamServer):
    """ SocketServer that manages changing the wallpaper.
    """

    sockfile = '{}/wallpapermgr.sock'.format(
        xdg.BaseDirectory.save_data_path('wallpapermgr')
    )
    wallpaperfile = '{}/wallpapers/wallpaper{{ext}}'.format(
        xdg.BaseDirectory.save_data_path('wallpapermgr')
    )

    def __init__(self):
        super(Server, self).__init__(self.sockfile, RequestHandler)
        self.__config = datafile.Config()
        self.__data = datafile.Data()

        self.reload()

    @property
    def data(self):
        return self.__data

    @property
    def config(self):
        return self.__config

    @property
    def current_archive(self):
        return self.__archive

    @property
    def current_index(self):
        return self.__index

    @staticmethod
    def is_active():
        pidfile = datafile.PidFile()
        return pidfile.is_active()

    @classmethod
    def request(cls, request):
        """ Send a command to the wallpapermgr Server.
        """
        pidfile = datafile.PidFile()
        if not pidfile.is_active():
            cmds = [sys.executable, '-c']
            pycmds = (
                'from wallpapermgr2 import display',
                'srv=display.Server()',
                'srv.serve_forever()',
            )
            cmds.append(';'.join(pycmds))
            subprocess.Popen(cmds, stdin=None, stdout=None, stderr=None)

        # request
        sock = None
        tries = 6
        while tries > 0:
            try:
                sanitized_request = request.encode()
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(cls.sockfile)
                break
            except(FileNotFoundError, ConnectionRefusedError):
                tries -= 1
                time.sleep(0.5)

        if not sock:
            raise RuntimeError('unable to connect')

        sock.send(sanitized_request)
        reply = sock.recv(1024)
        sock.close()

        return reply

    def server_bind(self):
        # islink, isfile both fail
        if os.path.exists(self.sockfile):
            os.unlink(self.sockfile)

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.sockfile)

    def serve_forever(self, poll_interval=0.5):
        try:
            pidfile = datafile.PidFile()
            pidfile.open()
            return super(Server, self).serve_forever(poll_interval)
        finally:
            pidfile.close()
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            os.unlink(self.sockfile)
            self.data.write()

    def reload(self):
        self.__config.read(force=True)
        self.__data.read(force=True)
        self.__archive = self.__config.determine_archive()
        self.__index = self.__data.index(self.__archive)

    def display(self, archive, index):
        if index >= self.data.archive_len(archive):
            raise RuntimeError(
                'invalid index {} for archive {}'.format(index, archive)
            )

        # create wallpaperdir
        wallpaper_dir = os.path.dirname(self.wallpaperfile)
        if not os.path.isdir(wallpaper_dir):
            os.makedirs(wallpaper_dir)

        # delete last wallpaper
        for old_wallpaper in glob.glob(self.wallpaperfile.format(ext='.*')):
            os.remove(old_wallpaper)

        # extract wallpaper
        archive_path = self.config.archive_path(archive)
        with tarfile.open(archive_path, 'r') as archive_fd:
            item_path = self.data.wallpaper(archive, index)
            ext = os.path.splitext(item_path)[-1]
            extracted_path = self.wallpaperfile.format(ext=ext)
            try:
                fr = archive_fd.extractfile(item_path)
                with open(extracted_path, 'wb') as fw:
                    fw.write(fr.read())
            finally:
                fr.close()

        # display wallpaper
        subprocess.check_call(
            self.config.show_wallpaper_cmd(extracted_path),
            stdin=None, stdout=None, stderr=None
        )
        self.__archive = archive
        self.__index = index
        self.data.set_index(archive, index)

    def set_archive(self, archive):
        data = self.data.read()
        index = data['archives'][archive]['last_index']
        self.display(archive, index)


if __name__ == '__main__':
    # ==============
    # for debugging:
    # ==============
    server = Server()
    server.serve_forever()

    # =======================================
    # starts daemon, AND shows next wallpaper
    # =======================================
    # reply = Server.request(b'next')
    # print(reply)
