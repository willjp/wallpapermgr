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
# external
import xdg.BaseDirectory
# internal
from wallpapermgr2 import datafile


logger = logging.getLogger(__name__)


def change_archive(archive):
    Server.request('archive {}'.format(archive))


def next():
    Server.request('next')


def prev():
    Server.request('prev')


def show(index):
    Server.request('show {}'.format(index))


class RequestHandler(socketserver.BaseRequestHandler):
    """ SocketServer RequestHandler, parses/executes commands.
    """
    @property
    def command_map(self):
        return dict(
            next=dict(handler=self._handle_next, desc='show next wallpaper'),
            prev=dict(handler=self._handle_prev, desc='show prev wallpaper'),
            stop=dict(handler=self._handle_stop, desc='stop wallpaper daemon'),
            help=dict(handler=self._handle_help, desc='print help message'),
        )

    def handle(self):
        rawdata = self.request.recv(1024)
        if not rawdata:
            return

        data = rawdata.decode()
        data = str(data).strip()
        self._run_command(data)

    def _run_command(self, command):
        if command not in self.command_map:
            msg = 'invalid command: "{}"'.format(command)
            self.request.send(msg.encode())
            return

        self.command_map[command]['handler']()

    def _handle_next(self):
        self.request.send(b'display next')

    def _handle_prev(self):
        self.request.send(b'display prev')

    def _handle_stop(self):
        self.request.send(b'shutting down server..')
        t = threading.Thread(target=self.server.shutdown)
        t.start()

    def _handle_help(self):
        reply = [
            '',
            'available commands:',
            '===================',
        ]
        for cmd in self.command_map:
            reply.append('  {}:  {}'.format(cmd, self.command_map[cmd]['desc']))

        self.request.send('\n'.join(reply).encode() + b'\n\n')


class Server(socketserver.UnixStreamServer):
    """ SocketServer that manages changing the wallpaper.
    """

    sockfile = '{}/wallpapermgr.sock'.format(
        xdg.BaseDirectory.save_data_path('wallpapermgr')
    )

    def __init__(self, start=False):
        super(Server, self).__init__(self.sockfile, RequestHandler)

        if start:
            self.serve_forever()

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
                sanitized_request = request
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


if __name__ == '__main__':
    # server = Server()
    # server.serve_forever()

    reply = Server.request(b'next')
    print(reply)
