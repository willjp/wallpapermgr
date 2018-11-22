#!/usr/bin/env python2
"""
Name :          wallpapermgr/gitoperations.py
Created :       August 31 2016
Author :        Will Pittman
Contact :       willjpittman@gmail.com
________________________________________________________________________________
Description :   git operations used by wallpapermgr
________________________________________________________________________________
"""
# builtin
from __future__ import unicode_literals
from __future__ import absolute_import
import logging
import sys
import uuid
# external
import git

logger = logging.getLogger(__name__)


class Git(object):
    def __init__(self):
        pass

    def git_configured(self, config, data, archive_name):
        """

        Returns:

            .. code-block:: python

                # if not fully configured
                {
                    'configured':False,
                    'gitroot':   None
                    'gitsource': None
                }


            .. code-block:: python

                # if fully configured
                {
                    'configured':True,
                    'gitroot':'/home/src',
                    'gitsource':'http://....'
                }
        """
        archive_info = config['archives'][archive_name]
        archive_path = archive_info['archive']

        try:
            gitroot = archive_info['gitroot']
            gitsource = archive_info['gitsource']
            return {
                'configured': True,
                'gitroot': gitroot,
                'gitsource': gitsource,
            }
        except:
            return {
                'configured': False,
                'gitroot': None,
                'gitsource': None,
            }

    def git_clone(self, gitsource, gitroot):
        """ Clones a git repository.

        Args:
            gitsource (str): ``(ex: 'ssh://gitbox:22/home/git/wallpapers' )``
                address to pull wallpapers from.

            gitroot (str): ``(ex: '~/.wallpapers')``
                path we are cloning git repository to.

        """
        # if git-project is present, just pull
        try:
            repo = git.Repo(gitroot)
            self.git_pull(gitroot)

        # if git-project doesn't exist yet, clone it
        except(git.InvalidGitRepositoryError, git.NoSuchPathError):
            repo = git.Repo.init(gitroot)
            origin = repo.create_remote('origin', url=gitsource)

            if not origin.exists():
                raise RuntimeError('Gitsource is unavailable: %s' % gitsource)

            origin.pull('master')

    def git_pull(self, gitroot):
        """ Pulls latest gitrepo.

        Args:
            gitroot (str): ``(ex: '~/.wallpapers' )``
                The path we are cloning git repository to.
        """

        # if git project does not exist, clone it.
        repo = git.Repo(gitroot)
        remote = repo.remote()

        if repo.is_dirty():
            logger.error(
                'Uncommitted changes in local gitrepo. Resolve manually and try again')
            sys.exit(1)
        if not remote.exists():
            logger.error(
                "gitsource url unavailable. Abandoning: {}".format(remote.url)
            )
            sys.exit(1)

        remote.pull('master')

    def git_commitpush(self, gitroot):
        """ Adds all unstaged/modified files, commits, and pushes to repo.

        Args:
            gitroot (str): ``(ex: '~/.wallpapers')``
                The path we are cloning git repository to.
        """

        repo = git.Repo(gitroot)
        remote = repo.remote()

        staged_files = set([item.a_path for item in repo.index.diff(None)])
        staged_files.update(set(repo.untracked_files))

        if not remote.exists():
            logger.error(
                "gitsource url unavailable. Abandoning: %s" % remote.url)
            sys.exit(1)
        if repo.is_dirty():
            logger.info('adding staged files to git: %s' % staged_files)

            if not staged_files:
                logger.info('no files are currently staged. aborting')
                return

            repo.index.add(staged_files)
            logger.info('committing changes..')
            repo.index.commit(uuid.uuid4().hex)
            logger.info('pushing to branch "master"..')
            remote.push('master')
        else:
            logger.info('git repo is not dirty, nothing to push')


if __name__ == '__main__':
    pass
