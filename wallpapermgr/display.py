#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import glob
import logging
import numbers
import os
import socket
import socketserver
import subprocess
import sys
import tarfile
import threading
import time
# external
import xdg.BaseDirectory
# internal
from wallpapermgr import datafile


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


def change_interval(seconds):
    """ If set to a value above 0, a new wallpaper will be displayed every N `seconds` . (WIP)
    """
    Server.request('interval {}'.format(seconds))


class RequestHandler(socketserver.BaseRequestHandler):
    """ SocketServer RequestHandler, parses/executes commands.
    """
    stop_command = 'stop'  # command that issues poison-pill to kill Server.

    @property
    def command_map(self):
        return {
            'next': dict(
                handler=self._handle_next,
                desc='show next wallpaper'
            ),
            'prev': dict(
                handler=self._handle_prev,
                desc='show prev wallpaper'
            ),
            'interval': dict(
                handler=self._handle_interval,
                desc='show wallpaper every N seconds',
            ),
            'archive': dict(
                handler=self._handle_archive,
                desc='change archive wallpapers are loaded from.',
            ),
            self.stop_command: dict(
                handler=self._handle_stop,
                desc='stop wallpaper daemon'
            ),
            'reload': dict(
                handler=self._handle_reload,
                desc='reload from configfile/datafile'
            ),
            'help': dict(
                handler=self._handle_help,
                desc='print help message'
            ),
        }

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

    def _handle_interval(self, seconds):
        self.server.set_change_interval(float(seconds))
        msg = 'setting display interval to {}s'.format(seconds)
        self.request.send(msg.encode())

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

    def __init__(self, interval=None):
        """ constructor.

        Args:
            interval (numbers.Number, optional):
                numer of seconds between wallpaper changes
        """
        super(Server, self).__init__(self.sockfile, RequestHandler)
        self.__config = datafile.Config()

        if interval is None:
            interval = self.config.read().get('change_interval', None)

        self.__data = datafile.Data()
        self.__timer = _ChangeWallpaperTimer(interval=interval)
        self.__extract_in_progress = False
        self.__last_extracted = None

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

        logger.debug('received request: {}'.format(request))

        # if server is not started, and attempting to stop, do nothing.
        if str(request) == str(RequestHandler.stop_command):
            if not Server.is_active():
                return

        # if not the 'stop' command, start the server before issuing command.
        if str(request) != str(RequestHandler.stop_command):
            pidfile = datafile.PidFile()
            if not pidfile.is_active():
                logger.debug('server not running, restarting...')
                cmds = [sys.executable, '-c']
                pycmds = (
                    'from wallpapermgr import display',
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
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(cls.sockfile)
                break
            except(FileNotFoundError, ConnectionRefusedError):
                if tries != tries:
                    logger.warning(
                        'Unable to contact server - retrying in 0.5s'
                    )
                tries -= 1
                time.sleep(0.5)

        if not sock:
            raise RuntimeError('unable to connect')

        sanitized_request = request.encode()
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
            logger.info('starting wallpaper server...')
            pidfile = datafile.PidFile()
            pidfile.open()
            self.__timer.start()
            return super(Server, self).serve_forever(poll_interval)
        finally:
            logger.debug('shutdown initiated...')
            self._delete_extracted()
            logger.debug('delete pending wallpaper.. successful')
            self.__timer.shutdown()
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            logger.debug('socket shutdown..successful')
            os.unlink(self.sockfile)
            self.data.write()
            logger.debug('data dump..successful')
            if os.path.exists(self.sockfile):
                os.unlink(self.sockfile)
            self.__timer.join()
            logger.debug('timer shutdown..successful')
            pidfile.close()
            logger.debug('pidfile close..successful')

    def reload(self):
        logger.info('reloading wallpaper configs..')
        self.__config.read(force=True)
        self.__data.read(force=True)
        self.__archive = self.__config.determine_archive()
        self.__index = self.__data.index(self.__archive)

    def shutdown(self):
        logger.debug('requesting shutdown...')
        return super(Server, self).shutdown()

    def display(self, archive, index):
        data = self.data.read()
        if index >= self.data.archive_len(archive):
            raise RuntimeError(
                'invalid index {} for archive {}'.format(index, archive)
            )

        # create wallpaperdir
        wallpaper_dir = os.path.dirname(self.wallpaperfile)
        if not os.path.isdir(wallpaper_dir):
            os.makedirs(wallpaper_dir)

        # extract wallpaper if not exist
        if self.__last_extracted:
            extracted_path = self.__last_extracted
        else:
            extracted_path = self._extract_wallpaper(archive, index, wait=True)

        # display wallpaper
        self._display_wallpaper(extracted_path)
        self.__archive = archive
        self.__index = index
        self.data.set_index(archive, index)
        self.__change_interval = time.time()

        # delete last wallpaper
        self._delete_extracted()

        # extract next wallpaper in advance
        if (index + 1) < self.data.archive_len(archive):
            self._extract_wallpaper(archive, index + 1)
        else:
            self._extract_wallpaper(archive, 0)

    def _delete_extracted(self):
        for old_wallpaper in glob.glob(self.wallpaperfile.format(ext='.*')):
            os.remove(old_wallpaper)

    def _extract_wallpaper_1(self, archive, index):
        """
        Returns:
            str: filepath to extracted wallpaper
        """
        self.__extract_in_progress = False
        try:
            archive_path = self.config.archive_path(archive)
            with tarfile.open(archive_path, 'r') as archive_fd:
                item_path = self.data.wallpaper(archive, index)
                logger.debug('extracting archive/path:n{}({})'.format(
                        archive_path, item_path
                ))
                ext = os.path.splitext(item_path)[-1]
                extracted_path = self.wallpaperfile.format(ext=ext)
                try:
                    fr = archive_fd.extractfile(item_path)
                    with open(extracted_path, 'wb') as fw:
                        fw.write(fr.read())
                finally:
                    if fr:
                        fr.close()
        finally:
            self.__extract_in_progress = False

        return extracted_path

    def _extract_wallpaper(self, archive, index, wait=False):
        """
        Returns:
            str: filepath to extracted wallpaper
        """
        self.__extract_in_progress = True
        self.__last_extracted = None
        thread = _ExtractWallpaperWorker(
            self.config,
            self.data,
            archive,
            index,
            finished_callback=self._wallpaper_extracted,
        )
        if wait:
            return thread.run()
        else:
            thread.start()

    def _wallpaper_extracted(self, filepath):
        self.__last_extracted = filepath

    def _display_wallpaper(self, filepath):
        logger.debug('displaying wallpaper: {}'.format(filepath))
        subprocess.check_call(
            self.config.show_wallpaper_cmd(filepath),
            stdin=None, stdout=None, stderr=None
        )

    def set_archive(self, archive):
        data = self.data.read()
        index = data['archives'][archive]['last_index']
        self.display(archive, index)

    def set_change_interval(self, seconds):
        self.__timer.set_interval(seconds)


class _ChangeWallpaperTimer(threading.Thread):
    """ Started by Server, periodically sends instructions to change wallpaper.
    """
    def __init__(self, interval=None):
        if interval is None:
            interval = 0

        self.__interval = interval
        self.__time_changed = time.time()
        self.__lock = threading.RLock()
        self.__request_stop = False

        super(_ChangeWallpaperTimer, self).__init__()

    def set_interval(self, interval):
        self.__lock.acquire()
        try:
            if not isinstance(interval, numbers.Number):
                raise TypeError('invalid interval: {}'.format(interval))
            self.__interval = interval
        finally:
            self.__lock.release()

    def reset(self):
        self.__lock.acquire()
        try:
            self.__time_changed = time.time()
        finally:
            self.__lock.release()

    def shutdown(self):
        self.__lock.acquire()
        try:
            self.__request_stop = True
        finally:
            self.__lock.release()

    def run(self):
        init = True
        while not self.__request_stop:
            # interval of 0, -1 are ignored.
            # (never change wallpaper automatically)
            if not self.__interval > 0:
                continue

            if (time.time() + self.__interval) >= self.__time_changed:
                next()
                self.__lock.acquire()
                self.__time_changed = time.time()
                self.__lock.release()
                init = False
                continue

            # only sleep if not first run
            if init is True:
                init = False
            else:
                time.sleep(1)


class _ExtractWallpaperWorker(threading.Thread):
    def __init__(
        self,
        config,
        data,
        archive,
        index,
        finished_callback=None
    ):
        self.__config = config
        self.__data = data
        self.__archive = archive
        self.__index = index
        self.__finished_callback = finished_callback
        self.__filepath = None

        super(_ExtractWallpaperWorker, self).__init__()

    @property
    def config(self):
        return self.__config

    @property
    def data(self):
        return self.__data

    @property
    def filepath(self):
        return self.__filepath

    def run(self):
        archive_path = self.config.archive_path(self.__archive)
        with tarfile.open(archive_path, 'r') as archive_fd:
            item_path = self.data.wallpaper(self.__archive, self.__index)
            logger.debug('extracting archive/path:n{}({})'.format(
                    self.__archive, item_path
            ))
            ext = os.path.splitext(item_path)[-1]
            extracted_path = Server.wallpaperfile.format(ext=ext)
            try:
                fr = archive_fd.extractfile(item_path)
                with open(extracted_path, 'wb') as fw:
                    fw.write(fr.read())
                self.__finished_callback(extracted_path)
                return extracted_path
            except:
                self.__finished_callback(None)
            finally:
                if fr:
                    fr.close()
                self.__filepath = extracted_path


if __name__ == '__main__':
    # ==============
    # for debugging:
    # ==============
    #server = Server()
    #server.serve_forever()

    # =======================================
    # starts daemon, AND shows next wallpaper
    # =======================================
    reply = Server.request('next')
    print(reply)
