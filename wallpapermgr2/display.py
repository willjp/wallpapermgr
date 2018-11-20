#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import logging
import multiprocessing
import os
import socket
import socketserver
import threading
import time
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
    def handle(self):
        rawdata = self.request.recv(1024)
        if not rawdata:
            return

        data = rawdata.decode()
        data = str(data).strip()
        self._run_command(data)

    def _run_command(self, command):
        command_map = {
            'next': self._handle_next,
            'prev': self._handle_prev,
            'stop': self._handle_stop,
        }
        if command not in command_map:
            msg = 'invalid command: "{}"'.format(command)
            self.request.send(msg.encode())
            return

        command_map[command]()

    def _handle_next(self):
        self.request.send(b'display next')

    def _handle_prev(self):
        self.request.send(b'display prev')

    def _handle_stop(self):
        self.request.send(b'shutting down server..')
        t = threading.Thread(target=self.server.shutdown)
        t.start()


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
        # NOTE: kick-starting the daemon like this is not working.
        pidfile = datafile.PidFile()
        if not pidfile.is_active():
            process = multiprocessing.Process(target=Server, args=(True,))
            process.daemon = True
            process.start()

        # request
        sock = None
        tries = 6
        while tries > 0:
            try:
                sanitized_request = request
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(cls.sockfile)
                break
            except(FileNotFoundError):
                tries -= 1
                time.sleep(0.5)

        if not sock:
            raise RuntimeError('unable to connect')

        sock.send(sanitized_request)
        reply = sock.recv(1024)
        sock.close()

        return reply


if __name__ == '__main__':
    #server = Server()
    #server.serve_forever()

    Server.request(b'next')
