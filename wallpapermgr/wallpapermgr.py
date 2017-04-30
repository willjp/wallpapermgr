#!/usr/bin/env python2
"""
Name :          bin/wallpapermgr.py
Created :       August 27 2016
Author :        Will Pittman
Contact :       willjpittman@gmail.com
________________________________________________________________________________
Description :   Randomly chooses a wallpaper from a tar archive, and displays it.
                Also manages git repo (add,remove,etc).


Data:
                ## json file stores image-sequences. refreshes all whenever
                ## json-file is older than archive being read.

                ~/.config/wallpapermgr/wallsequence.json:
                    {

                        'archives':
                            '/home/will/progs/walls/walls.tar' : {
                                'last_fileno': 11,             ## index of last displayed file
                                'sequence'   : [               ## order images will be displayed in
                                                'file_1.png',
                                                'file_2.png',
                                                'file_3.png',
                                              ],
                            }
                        }
                    }
________________________________________________________________________________
"""
## builtins
from __future__  import unicode_literals
from __future__  import absolute_import

from   abc       import ABCMeta
from   datetime  import datetime
from   numbers   import Number
from   random    import shuffle,randint
import subprocess
import logging
import shlex
import json
import os
import sys
import tarfile
import socket

## personal
from .collectiontools import has_items
from . import excepts
from . import filedata
from . import gitoperations

## external
from   supercli.argparse import ArgumentParser
from   six               import StringIO,moves
import daemon
import yaml
import git



## Globals
DATA_DIR  = '{HOME}/.config/wallpapermgr'  ## data-storage location
loc       = locals
logger    = logging.getLogger(__name__)

#!TODO: left off just before testing new push/pull  arguments
#!
#!        \/  DO THIS FIRST THOUGH (also consider standardizing getting data etc) \/
#!

#!TODO: We should be reading from JSON file into data and setting datatypes
#!      at the same time. It's the cleanest way to guarantee that everything works
#!      properly.

#!TODO: using PySide, create window to manage wallpapers (with thumbnails)
#!TODO: experiment with PySide, try to 'fake' setting a wallpaper, simply
#!      by displaying an image on all screens layered behind all other windows.

#!TODO: experiment with trigers for changing wallpapers.


##
## Classes
##

class WallpaperArchiveBase(object):
    __metaclass__ = ABCMeta
    def __init__(self):
        """
        Class to be used as base for all major functions of wallpapermgr.
        Provides standardized methods/attrs for interacting with:

            * user config (archives, locations, display-methods, ...)
            * stored data (sequence-order, last-file)
        """

        ## Configuration/Data

        data_dir        = DATA_DIR.format(**os.environ)
        self.datafile   = '{data_dir}/data.json'.format(**loc())

        self.lib_configfile  = '{data_dir}/config.yml'.format(**loc())
        self.user_configfile = os.path.dirname( os.path.realpath(__file__) ) +'/config.yml'
        self.configfile      = None     ## location of used configfile (user or default)
        self.config          = {}       ## contents of configfile
        self.data            = {}       ## stored archive-data from json file.


        ## Attributes
        self.archive_name  = None  ## name of archive we are retrieving wallpapers from
        self.archive_path  = None  ## path/filename of chosen tar-archive containing wallpapers
        self.archive_info  = {}    ## dict of information for the selected archive
        self.wall_sequence = []    ## list of files in tar-archive in the order they will be displayed.
        self.last_fileno   = None  ## index of the last file displayed (in self.wall_sequence)


        ## START!
        self._validate_dependencies()
        self._choose_cfgfiles()

    def _validate_dependencies(self):
        """
        ensure that 'feh' are installed.
        """
        pass

    def _choose_cfgfiles(self):
        if os.path.isfile( self.user_configfile ):
            self.configfile = self.user_configfile
        else:
            self.configfile = self.lib_configfile


    def get_userconfig(self):
        """
        Reads user's configfile, stores in self.config
        """

        config      = filedata.ConfigFileIO( self.configfile ).read()
        self.config = config
        return self

    def get_saveddata(self):
        """
        Reads existing datafile, or creates config skeleton.
        (just enough that rest of program can run without crashing, )
        (or hundreds of conditional statements)
        """
        datafile  = self.datafile
        self.data = filedata.DataFileIO(self.datafile).read()

        return self.data


    def get_archive(self, archive_name=None):
        """
        Resolves configured conditions to decide which archive to use,
        or retrieves information about a specific archive if 'archive_name'
        is provided.

        ________________________________________________________________
        OUTPUT:
        ________________________________________________________________
            sets keys:
                self.archive_path
                self.archive_info
                self.archive_name
        """
        config = self.config


        if not archive_name:
            archive_name = self._determine_archive()

        if 'archives' not in config:
            raise RuntimeError('config has no section "archives": "%s"' % self.configfile )

        if archive_name in config['archives']:
            self._test_archiveexists( config, archive_name )

            self.archive_path = config['archives'][ archive_name ]['archive']
            self.archive_info = config['archives'][ archive_name ]
            self.archive_name = archive_name
            return
        else:
            raise ConfigKeyMissing('No archive named "%s" in user config' % archive_name )

    def _test_archiveexists(self, config, archive_name ):
        """
        If the archive does not exist, prompts the user
        to find out if the want to clone the gitrepo
        """

        archive_info = config['archives'][ archive_name ]
        archive_path = archive_info['archive']


        if not os.path.isfile( archive_path ):

            ## If archive doesn't exist (and no gitconfig), warn user and exit
            if not has_items( archive_info, ('gitroot','gitsource' )):
                logger.error('archive path does not exist: "%s"' % archive_info['archive'] )
                sys.exit(1)

            ## otherwise, if there is a git configuration, ask if user
            ## wants to clone git repository.
            else:
                gitsource = archive_info['gitsource']
                gitroot   = archive_info['gitroot']
                if self.confirm((
                        'Archive is not present, clone from configured gitroot?\n'
                        'gitroot:   "%s" \n'
                        'gitsource: "%s" \n'
                        ) % (gitroot,gitsource)
                    ):
                    gitoperations.Git().git_clone( gitsource, gitroot )

                else:
                    logger.error('Cancelled by User')
                    sys.exit(1)

    def _determine_archive(self):
        """
        Using the conditions key, determine which archive to pull
        wallpapers from on this computer.
        """
        config = self.config

        condition_results = {}
        default_archive   = None


        for archive_name in config['archives']:

            conditions = config['archives'][ archive_name ]['conditions']
            conditions_satisfied = 0

            if not hasattr( conditions, '__iter__' ):
                if conditions in ('default','is_default'):
                    default_archive = conditions

            for (condition,accepted_values) in conditions.items():

                ## keep an eye out for the default condition
                ## in case we don't find a more specific match
                if condition in ('default','is_default'):
                    default_archive = archive_name
                    continue

                ## accepted_values evaluated as list
                if not hasattr( accepted_values, '__iter__' ):
                    accepted_values = ( accepted_values, )

                ## get results of condition
                if condition in condition_results:
                    result = condition_results[ condition ]
                else:
                    result = self._eval_condition( condition )
                    condition_results[ condition ] = result

                ## if accepted value, increment conditions_satisfied
                if result in accepted_values:
                    conditions_satisfied +=1


            if conditions_satisfied == len(conditions):
                logger.info('All conditions matched for archive: {archive_name}'.format(**loc()) )
                return archive_name


        ## if no archive had all of it's conditions satified,
        ## use the default
        logger.info("No Archive satisfied all it's conditions. Using Default Archive: {default_archive}".format(**loc()) )
        return default_archive

    def _eval_condition(self, condition ):
        """
        Runs a single test condition.
        """

        conditionpaths = []

        ## Add official conditions dir
        scriptdir      = os.path.dirname( os.path.realpath(__file__) )
        lib_conditions = '{scriptdir}/archive_conditions'.format(**loc())
        conditionpaths.insert( 0, lib_conditions )

        ## find and run condition-script
        for conditionpath in conditionpaths:
            if condition in os.listdir(conditionpath):
                cmd         = '{conditionpath}/{condition}'.format(**loc())
                return_raw  = subprocess.check_output( shlex.split(cmd), universal_newlines=True )
                return_json = self._parse_returnjson_raw( return_raw )

                return return_json['return']


    def get_wallsequence(self, reload_tarfiles=False ):
        """
        Creates or loads a random sequence of wallpapers.

        reloads every time the archive containing walls' timestamp
        changes.
        """
        datafile = self.datafile
        wall_sequence = []


        ## create dir if not exist
        if not os.path.isdir( os.path.dirname(datafile) ):
            os.makedirs( os.path.dirname(datafile) )


        ## if datafile does not exist, create
        ##
        ## otherwise read/create archive info if missing
        if not os.path.isfile( datafile ) or reload_tarfiles == True:
            (data, last_fileno, wall_sequence) = self._refresh_wallsequences( datafile )
        else:
            (data, last_fileno, wall_sequence) = self._get_saved_wallsequence()


        self.last_fileno   = last_fileno
        self.wall_sequence = wall_sequence
        self.data          = data
        last_file    = wall_sequence[ last_fileno ]
        logger.debug('last wallpaper({last_fileno}): "{last_file}"'.format(**loc()) )

    def _get_saved_wallsequence(self):
        """
        Retrieves the wallsequence from the JSON file.

        If the JSON file is older than the archive, all archives
        are re-read, and a new sequence is made for each archive.

        _________________________________________________________
        OUTPUT:
        _________________________________________________________
            ## A randomized list of walls from 'archive'.
            ## This is the sequence in which they will be displayed.

            wall_sequence = [
                    'fileA.png',
                    'fileB.png',
                    'fileC.png',
                    ...
                    ]
        """
        logging.debug('Datafile is up-to-date, getting sequence and last-displayed file')

        archive_path = self.archive_path
        datafile     = self.datafile

        ## if timestamp on json file is older than archive,
        ## read the archive, and create a new wallsequence
        archive_timestamp = datetime.fromtimestamp( os.path.getmtime( archive_path ) )
        json_timestamp    = datetime.fromtimestamp( os.path.getmtime( datafile ) )

        if json_timestamp < archive_timestamp:
            wall_sequence = self._refresh_wallsequences( datafile )

        else:
            data = self.get_saveddata()

            ## jsonfile timestamp is >= archive
            ## and archive info exists in jsonfile (reuse conts)
            if archive_path in data['archives']:
                wall_sequence = data['archives'][ archive_path ]['sequence']
                last_fileno   = data['archives'][ archive_path ]['last_fileno']

            ## jsonfile does not contain info from archive
            else:
                (data, last_fileno, wall_sequence) = self._refresh_wallsequences( datafile )

        return (data, last_fileno, wall_sequence)

    def _refresh_wallsequences(self, datafile ):
        """
        update the json file (for all archives)
        and return sequence for the archive being used.

        ___________________________________________________________
        INPUT:
        ___________________________________________________________
        archive       | '/path/to/archive.tar' |       | the archive we are setting a sequence
                      |                        |       | of walls for
                      |                        |       |
        ___________________________________________________________
        OUTPUT:
        ___________________________________________________________
            (
                0                       ,   ## last_fileno:  index number of last displayed wallpaper
                ['fileA.png','fileB.png'],  ## wallsequenc:  list of files contained in archive.tar
            )
        """

        logger.info('Reloading images in all archives...')

        ## refresh the list of contents for each
        ## tar-archive of wallpapers
        config       = self.config

        data = self.get_saveddata()
        for archive_name in config['archives']:
            archive_path = config['archives'][ archive_name ]['archive']
            archive_path = archive_path

            if os.path.isfile( archive_path ):
                logger.info('Reading files in Archive: "{archive_path}"'.format(**loc()) )
                new_data = self._refresh_wallsequence( data, archive_path )
                if new_data:
                    data.update( new_data )

        if not data:
            raise RuntimeError('Data variable is empty. No wallpapers to display')


        ## write sequence_info to json file
        with open( datafile, 'w' ) as fw:
            fw.write( json.dumps(data, indent=2) )



        ## get the information pertaining to the
        ## specific archive we ar pulling images from
        last_fileno  = data['archives'][ self.archive_path ]['last_fileno']
        wallsequence = data['archives'][ self.archive_path ]['sequence']


        return (data, last_fileno, wallsequence)

    def _refresh_wallsequence(self,data,archive_path):
        """
        produces a list of all files in a tar archive,
        and stores it in the dict 'data'.

        _________________________________________________________________________
        INPUT:
        _________________________________________________________________________
        archive_path | '/path/to/file.tar' |  | path to a tar archive containing
                     |                     |  | a set of images.
        _________________________________________________________________________
        OUTPUT:
        _________________________________________________________________________
            data = {
                    '/path/to/file.tar' : {
                        'last_fileno' : 0,
                        'sequence'    : [
                                'fileA.png',
                                'fileB.png',
                                'fileC.png',
                               ],
                         },
                   }
        """

        datafile = self.datafile

        if os.path.isfile( archive_path ):
            ## get walls from archive
            with tarfile.open( archive_path, 'r' ) as archive:
                wallsequence = archive.getnames()
            shuffle( wallsequence )
            last_fileno  = 0


            ## write/update existing json data
            if os.path.isfile( datafile ):
                with open( datafile, 'r' ) as stream:
                    contents = json.load(stream)

            if 'archives' not in data:
                data['archives'] = {}

            if archive_path not in data['archives']:
                data['archives'][ archive_path ] = {}

            data['archives'][ archive_path ]['sequence']    = wallsequence
            data['archives'][ archive_path ]['last_fileno'] = 0

        return data


    def _parse_returnjson_raw(self,return_raw):



        if not return_raw:
            raise excepts.InvalidJSONReturn('No return-value detected at all')


        ## strip leading info until we get the first line with the
        ## JSON output.
        json_raw = ''
        for line in return_raw.split('\n'):
            if not json_raw:
                if line[0] == '{':
                    json_raw += line
            else:
                json_raw += line

        if not json_raw:
            raise excepts.InvalidJSONReturn('No json found in output')


        ## parse json
        return_json = json.loads( json_raw )


        if 'return' not in return_json:
            raise excepts.InvalidJSONReturn('Returned JSON is missing "return" key')


        return return_json


    def confirm(self,message):
        """
        prompts user with a message asking for (Y/N).
        """
        while True:
            reply = moves.input( '\n\n' + message +'\n(y/n) ' )

            if reply in ('y','n','Y','N'):
                if reply in ('y','Y'):
                    return True
                else:
                    return False
            else:
                print('Invalid Response')



class DisplayWallpaper(WallpaperArchiveBase):
    def __init__(self, archive_name=None, index=None, offset=None ):
        super( DisplayWallpaper, self ).__init__()

        ## Arguments
        self.index        = index         ## a fixed index to use
        self.offset       = offset        ## 5/-5  determines index of wallpaper to display
        self.archive_name = archive_name  ## manually determine the archive to use

        ## START!!
        self.main()


    def main(self):
        self._validate_args()

        self.get_userconfig()
        self.get_archive( self.archive_name )
        self.get_wallsequence()
        self.display_wallpaper()

    def _validate_args(self):
        offset = self.offset
        index  = self.index

        if index and offset:
            raise TypeError('index and offset cannot be used together')

        if index==None  and  offset==None:
            raise TypeError('index or offset must be used')


        if index != None   and   not isinstance( index, int ):
            raise TypeError( 'index must be a positive integer (ex: 10): {index}'.format(**loc()) )
        if index != None   and   index < 0:
            raise TypeError( 'index must be a positive integer (ex: 10): {index}'.format(**loc()) )


        if offset != None   and   not isinstance( offset, int ):
            raise TypeError( 'offset must be a positive or negative integer (1/-1): {offset}'.format(**loc()) )


    def display_wallpaper(self):
        """
        * extracts wallpaper from archive,
        * displays wallpaper using configured module,
        * deletes extracted wallpaper,
        * updates datafile's last-viewed wallpaper
        """

        archive_info            = self.archive_info
        (index, nextfile, ext)  = self._get_nextfile()
        filepath                = self._extract_file( index, nextfile )
        (args,kwds,specialvars) = self._parse_apply_args( archive_info, filepath )

        self._run_apply_method( index, filepath, args, kwds, specialvars )
        self._remove_file( filepath )

        self._update_datafile( index )

    def _get_nextfile(self):
        archive_path  = self.archive_path

        ## get filename of next file
        next_fileno = self._get_next_fileno()
        nextfile    = self.wall_sequence[ next_fileno ]


        ## get file extension
        if '.' in nextfile:
            ext = '.'+ nextfile.split('.')[-1]
        else:
            ext = ''

        return (next_fileno, nextfile, ext)

    def _get_next_fileno(self):
        """
        Calculate index of the next wallpaper to display
        """
        wall_sequence = self.wall_sequence
        index         = self.index
        offset        = self.offset
        last_fileno   = self.last_fileno


        if index != None:
            return index

        else:
            if (offset + last_fileno) < len(wall_sequence):
                next_fileno = (offset + last_fileno)
            elif (offset + last_fileno) >= 0:
                next_fileno = ((offset + last_fileno) % wall_sequence) - len(wall_sequence)
            else:
                next_fileno = len(wall_sequence) - ((offset + last_fileno) % wall_sequence)

        return next_fileno


    def _parse_apply_args(self, archive_info, filepath ):
        """
        The user is allowed to use special variables in their args/kwds.
        they are marked between {}s.
        """

        ## special variables
        special_vars = {
            'filepath' : filepath,
        }

        ## parse all variables in args,kwds, or kwd-vals
        args = []
        kwds = {}

        if 'apply_args' in archive_info:
            if hasattr( archive_info['apply_args'], '__iter__' ):
                for arg in archive_info['apply_args']:
                    if isinstance( arg, basestring ):
                        args.append( arg.format(**special_vars) )
                    elif isinstance( arg, dict ):
                        args.append( repr(arg).format(**special_vars) )
                    else:
                        raise TypeError('Invalid Datatype for argument: %s' % arg)

            else:
                args.append( archive_info['apply_args'].format(**special_vars) )

        if 'apply_kwds' in archive_info:
            for (kwd,val) in archive_info['apply_kwds'].items():
                kwds.update({ kwd.format(**special_vars) : val.format(**special_vars) } )

        return (args,kwds,special_vars)


    def _extract_file(self, index, nextfile ):
        """
        extract,rename,display next file
        """
        archive_path = self.archive_path

        with tarfile.open( archive_path, 'r' ) as archive:
           archive.extract( nextfile, '/var/tmp/' )

        filepath = '/var/tmp/{nextfile}'.format(**loc())
        logger.debug('Extracted file: "%s"' % filepath)
        return filepath

    def _remove_file(self, filepath):
        """
        after displaying the image, delete it
        """
        logger.debug('Deleting File: "%s"' % filepath)
        os.remove( filepath )


    def _run_apply_method(self, index, filepath, args, kwds, specialvars):

        logger.info('Displaying Wallpaper ({index}): "{filepath}"'.format(**loc()) )
        archive_path = self.archive_path

        ## determine apply-method
        scriptdir    = os.path.dirname( os.path.realpath(__file__) )
        apply_method = self.archive_info['apply_method']
        apply_script = '{scriptdir}/apply_methods/{apply_method}'.format(**loc())

        if not os.path.isfile( apply_script ):
            raise IOError('Expected script at: "{apply_script}"'.format(**loc()) )


        ## create JSON ready for script's stdin
        applyargs_raw     = {
                                'args':args   ,'kwds':kwds,
                                'specialvars' : specialvars,
                                'loglevel'    : logging.root.level
                            }
        applyargs_json    = json.dumps( applyargs_raw )
        applyargs_jsonfd  = StringIO( applyargs_json )

        logger.debug( '{applyargs_json} | {apply_script}'.format(**loc()) )
        pipe      = subprocess.Popen( apply_script, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True )
        (out,err) = pipe.communicate( applyargs_jsonfd.read() )

        if pipe.returncode != 0:
            logger.error('\nRESULT STDOUT:\n'+ out +'\nRESULT STDERR:\n' + err )
        else:
            logger.debug('\nRESULT STDOUT:\n'+ out +'\nRESULT STDERR:\n' + err )


    def _update_datafile(self, index ):
        """
        updates datafile with the new index
        """

        archive_path = self.archive_path
        datafile     = self.datafile

        ## read sequence_info
        self.data['archives'][ archive_path ]['last_fileno'] = index


        ## write sequence_info to json file (after incrementing next_fileno)
        with open( datafile, 'w' ) as fw:
            fw.write( json.dumps(self.data, indent=2) )


    def display_on_interval(self, interval=120):
        """
        Starts a process that runs in the background,
        periodically changing the wallpaper.
        """
        with daemon.DaemonContext( detach_process=True ):
            self._display_interval_loop(interval)

    def _display_interval_loop(self,interval):
        """
        Starts a loop that periodically displays a wallpaper
        """

        while True:
            pass



class WallpaperDaemon(object):
    def __init__(self,socket):
        self._socket = socket

    def _validat_args(self):
        if not isinstance( self._socket, socket.socket ):
            raise TypeError('socket argument must be of type socket.socket')

    def start(self):
        sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]

        ## create a JSON lockfile that stores:
        ## pid, sock(fam/type), addr,
        ##
        ## (check to see if modifying the lockfile's contents is possible using the lockfile module)
        ## (or if info should be stored elsewhere)

    def send_message(self,message):
        ## messages should be valid json.
        ## json format should match apply_methods.
        pass



class DataFile(WallpaperArchiveBase):
    def __init__(self, shuffle=False, recreate_datafile=False ):
        super( DataFile, self ).__init__()

        ## Arguments
        self.shuffle           = shuffle
        self.recreate_datafile = recreate_datafile

        ## START!!
        self.main()


    def main(self):
        self._validate_args()

        shuffle           = self.shuffle
        recreate_datafile = self.recreate_datafile

        if   shuffle:           self.do_shuffle()
        elif recreate_datafile: self.do_recreate_datafile()

    def _validate_args(self):
        shuffle           = self.shuffle
        recreate_datafile = self.recreate_datafile

        if not shuffle and not recreate_datafile:
            raise TypeError('DataFile() received no arguments')

        if shuffle not in (True,False):
            raise TypeError("Expected True/False value for argument 'shuffle'. Received '%'" % shuffle )

        if recreate_datafile not in (True,False):
            raise TypeError("Expected True/False value for argument 'recreate_datafile'. Received '%'" % recreate_datafile )


    def do_shuffle(self):
        """
        Re-Randomizes the order of the wallpapers.
        """
        datafile = self.datafile
        data     = self.get_saveddata()

        for archive_path in data['archives']:
            shuffle( data['archives'][ archive_path ]['sequence'] )
            first = data['archives'][ archive_path ]['sequence'][0]
            last  = data['archives'][ archive_path ]['sequence'][-1]
            total = len( data['archives'][ archive_path ]['sequence'] )
            logger.info('"{archive_path}":   first: {first} last: {last} total: {total}'.format(**loc()) )

        with open( self.datafile, 'w' ) as fw:
            fw.write( json.dumps(data, indent=2) )

    def do_recreate_datafile(self):
        logger.info('deleting file: %s' % self.datafile )
        if os.path.isfile( self.datafile ):
            os.remove( self.datafile )

        ## creates new, empty datafile
        self.get_saveddata()



class Archive(WallpaperArchiveBase):
    def __init__(self):
        self._archive_name = None

        WallpaperArchiveBase.__init__(self)

    def _main(self):
        self.get_userconfig()
        self.get_saveddata()

    def append(self, archive_name, filepaths ):
        """
        Append images to an archive of wallpapers.
        """

        self.get_userconfig()
        self.get_archive( archive_name )

        data         = self.get_saveddata()
        archive_path = self.archive_path

        if not filepaths:
            logger.error('No files designated to filepaths')
            sys.exit(1)

        archive_data = data['archives'][ archive_path ]


        ## if gitroot/gitsource, make sure we have the latest version
        ## before adding to the archive.
        archive_files = []
        if has_items( archive_data, ('gitroot','gitsource') ):
            gitoperations.Git().git_pull( archive_data['gitroot'] )

        ## get a list of existing files
        logger.info('getting list of existing wallpapers in archive...')
        with tarfile.open( self.archive_path, 'r' ) as archive:
            archive_files = archive.getnames()


        if not self.confirm('Append files to archive:    "%s" ("%s")?' % (archive_name,archive_path)):
            print('Operation Cancelled by User')
            sys.exit(1)


        ## add files to the tarfile if they are not already there.
        logger.info('appending files to archive: "%s"' % archive_path )
        with tarfile.open( archive_path, 'a' ) as archive:

            for filepath in filepaths:
                if os.path.basename(filepath) not in archive_files:
                    logger.info('   adding "%s"' % filepath )
                    archive.add( filepath, arcname=os.path.basename(filepath) )
                else:
                    logger.info('   exists "%s"' % filepath )



        ## if the user has configured a gitroot/gitsource - also add,commit,and push archive.
        if has_items( archive_data, ('gitroot','gitsource') ):
            gitoperations.Git().git_commitpush( archive_data['gitroot'] )

        ## add all the new files to the datafile
        self.get_wallsequence( reload_tarfiles=True )


    def remove(self, archive_name):
        """
        Delete an archive
        """
        pass

    def git_operation(self, archive_name, operation):
        """
        Performs a git operation. (push/pull)
        ___________________________________________________________
        INPUT:
        ___________________________________________________________
        operation | 'push','pull' | | the git operation to perform.
        """

        self.get_userconfig()
        self.get_saveddata()
        self.get_archive( archive_name )
        git_info = gitoperations.Git().git_configured( self.config, self.data, archive_name )
        if git_info['configured']:

            if operation == 'push':
                gitoperations.Git().git_commitpush( git_info['gitroot'] )

            elif operation == 'pull':
                gitoperations.Git().git_pull( git_info['gitroot'] )

    def print_archives(self):
        """
        list all configured archives, and their locations
        """

        self.get_userconfig()

        if 'archives' not in self.config:
            print('no archives configured in : "%s"' % self.configfile )
            return

        print('')
        print(' Archive Name       Description ' + ' '*70 +'Location' )
        print('===============    =============' + ' '*70 +'========' )
        for archive_name in self.config['archives']:
            info = {'name':archive_name}
            info.update(self.config['archives'][archive_name])
            print( '{name:>15} -  {desc:<80}   "{archive}"'.format(**info) )
        print('')




class CLI_Interface():
    def __init__(self):
        self.parser = ArgumentParser(
            autocomp_cmd = 'wallmgr',
            description  = (
                'wallpapermgr is a modular program to manage/display collections of wallpapers. \n'
                '\n'
                'Wallpapers are categorized into tar archives, and packaged into git project(s) \n'
                'for versioning and file-synchronization between machines. All of this is controlled \n'
                'by this program. \n'
                )
            )
        self.subparsers = self.parser.add_subparsers( dest='subparser_name' )

        ## START!!
        self.main()

    def main(self):
        self.subparser_display()
        self.subparser_data()
        self.subparser_archive()
        self.subparser_shortcmds()

        args = self.parser.parse_args()

    def subparser_shortcmds(self):
        parser = self.subparsers.add_parser( 'next',    help='Display next wallpaper\n (short for `wallmgr display --next`)' )
        parser = self.subparsers.add_parser( 'prev',    help='Display previous wallpaper\n (short for `wallmgr display --prev`)' )
        parser = self.subparsers.add_parser( 'shuffle', help='Shuffle existing order of wallpapers\n (short for `wallmgr data --shuffle-order`)' )
        parser = self.subparsers.add_parser( 'pull',    help='Pull latest wallpapers from git repository')
        parser = self.subparsers.add_parser( 'push',    help='Push wallpapers to git remote')
        parser = self.subparsers.add_parser( 'ls',      help='List configured archives')

    def subparser_display(self):
        parser = self.subparsers.add_parser( 'display', help='Commands related to Displaying wallpapers\n (see `wallmgr display --help`)' )

        parser.add_argument(
            '-an', '--archive_name', help='Manually set the archive to display wallpapers from',
            )

        parser.add_argument(
            '-n', '--next', help='Display next wallpaper in sequence (looping if necessary)',
            action = 'store_true',
            )

        parser.add_argument(
            '-p', '--prev', help='Display previous wallpaper in sequence (looping if necessary)',
            action = 'store_true',
            )

        parser.add_argument(
            '-o', '--offset', help=(
                                'Display wallpaper that is N images away in the sequence (ex: 10/-10)\n'
                                '(looping if necessary)'
                                ),
            metavar = -10,
            )
        parser.add_argument(
            '-i', '--index', help='Index of wallpaper that you want to display',
            metavar = 15,
            )

        parser.add_argument(
            '-d', '--daemonize', nargs='?',  help=(
                                'Run in the background, and change wallpapers every N seconds.\n'
                                '(Defaults to 120s)'
                            ),
            metavar = 120,
            )

    def subparser_data(self):
        parser = self.subparsers.add_parser( 'data', help="Manage the program's internal datafile, image-order, etc\n (see `wallmgr data --help`)" )

        parser.add_argument(
            '-s', '--shuffle-order', help='Re-Randomize the order of wallpapers',
            action = 'store_true',
            )

        parser.add_argument(
            '--recreate-datafile', help='Deletes and recreates json file containing programdata (archive-paths, sequence-order, ...)',
            action = 'store_true',
            )

    def subparser_archive(self):
        parser = self.subparsers.add_parser( 'archive', help="Manage archives containing wallpapers (append,create,delete,...)\n (see `wallmgr archive --help`)" )

        parser.add_argument(
            '-l','--list-archives', help='List all archives, and their descriptions',
            action='store_true',
        )

        parser.add_argument(
            '-an', '--archive_name', help='Manually set the archive to display wallpapers from',
            )

        parser.add_argument(
            '-a', '--append', nargs='+', help="Add wallpapers to an archive. If archive doesn't exist, it is created",
            metavar='horiz3x',
            )

        parser.add_argument(
            '--push', help="If gitroot/gitsource are defined in config, push any changes to gitroot to the repo",
            action='store_true',
            )

        parser.add_argument(
            '--pull', help="If gitroot/gitsource are defined in config, pull changes to gitroot to the repo (cloning if necessary)",
            action='store_true',
            )


    def parse(self):
        """
        Handle subparser-type by passing off to appropriate method.
        If no arguments and no subparser, default to `wallpapermgr.py display --next`.
        """
        args = self.parser.parse_args()

        ## quick-commands
        if   args.subparser_name == 'next':    DisplayWallpaper( offset=  1 )
        elif args.subparser_name == 'prev':    DisplayWallpaper( offset= -1 )
        elif args.subparser_name == 'shuffle': DataFile( shuffle=True )
        elif args.subparser_name == 'push':    DisplayWallpaper( offset=  1 )
        elif args.subparser_name == 'pull':    DisplayWallpaper( offset= -1 )
        elif args.subparser_name == 'ls':      Archive().print_archives()

        elif args.subparser_name == 'display':
            self._parse_display( args )

        elif args.subparser_name == 'data':
            self._parse_data( args )

        elif args.subparser_name == 'archive':
            self._parse_archive( args )

        ## argparse disallows command without subparser

    def _parse_display(self, args ):

        def error_singlearg():
            print("use of (--prev, --next, --offset, --index)   cannot be used with any other argument")
            sys.exit(1)


        ## prev,next,offset
        if args.prev or args.next or args.offset:
            if args.prev:
                if args.next or args.daemonize or args.offset or args.index:
                    error_singlearg()
                offset = -1
            if args.next:
                if args.prev or args.daemonize or args.offset or args.index:
                    error_singlearg()
                offset = 1
            if args.offset:
                if args.prev or args.daemonize or args.next or args.index:
                    error_singlearg()
                offset = int(args.offset)

            DisplayWallpaper(
                    archive_name = args.archive_name,
                    offset       = offset,
                )
            sys.exit(0)


        ## index
        elif args.index:
            if args.prev or args.next or args.offset or args.daemonize:
                error_singlearg()
            DisplayWallpaper(
                        archive_name = args.archive,
                        index        = int(args.index),
                    )
            sys.exit(0)

        ## daemonize
        elif args.daemonize:
            print("daemonize is not ready yet")
            sys.exit(1)


        ## default behaviour is '--next'
        else:
            DisplayWallpaper( offset=1 )
            sys.exit(0)

    def _parse_data(self, args):

        if args.shuffle_order:
            DataFile( shuffle=True )
            sys.exit(0)

        elif args.recreate_datafile:
            DataFile( recreate_datafile=True )
            sys.exit(0)

        else:
            print('manage requires arguments. see `wallpapermgr.py manage --help`')
            sys.exit(1)

    def _parse_archive(self, args):

        if args.append!=None or args.push!=None or args.pull!=None:

            if args.list_archives:
                Archive().print_archives()

            elif  args.append:
                Archive().append(
                    archive_name = args.archive_name,
                    filepaths    = args.append,
                )

            elif args.push:
                Archive().git_operation(
                    archive_name = args.archive_name,
                    operation    = 'push',
                )
            elif args.pull:
                Archive().git_operation(
                    archive_name = args.archive_name,
                    operation    = 'pull',
                )


    def create_autocompleters(self,autocomp_cmd):
        comptxt = self.parser.create_autocompleters(cli_commandname)



if __name__ == '__main__':
    from . import wallpapermgr

    cli = wallpapermgr.CLI_Interface()
    print( cli )

