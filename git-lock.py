#!/usr/bin/env python

import os
import subprocess
from abc import abstractmethod, ABCMeta
import json
import os.path
import argparse
import time

class GitRemoteAction(object):

    __metaclass__ = ABCMeta

    LOCK_BRANCH_NAME = 'dist-locking'
    LOCK_FILE = 'lock'

    def __init__(self, edits=False):
        self.edits = edits

    @abstractmethod
    def action(self):
        raise NotImplementedError

    def pre_actions(self):
        return False

    def commit(self, filename=""):
        self.git_command("git add %s" % self.LOCK_FILE)

        if len(filename) == 0:
            self.git_command("git commit -m 'Adding lock for %s - %s'" % (self.git_username(), self.git_email()))
        else:
            self.git_command("git commit -m 'Adding lock on %s for %s - %s'" % (filename,
                                                                               self.git_username(),
                                                                               self.git_email()))
        output = self.git_command("git push -u origin %s" % self.LOCK_BRANCH_NAME)
        if "%s set up to track remote branch %s" % (self.LOCK_BRANCH_NAME, self.LOCK_BRANCH_NAME) in output:
            return True
        else:
            return False

    def revert(self):
        self.git_command('git reset --hard HEAD~')

    def create_branch(self):
        self.git_command("git checkout -b %s" % self.LOCK_BRANCH_NAME)
        os.system("echo "" >> %s" % self.LOCK_FILE)

    def git_username(self):
        return self.git_command("git config user.name").strip('\n')

    def git_email(self):
        return self.git_command("git config user.email").strip('\n')

    def update(self):
        if self.LOCK_BRANCH_NAME in self.branches():
            self.git_command("git checkout %s" % self.LOCK_BRANCH_NAME)
            self.git_command("git pull origin %s" % self.LOCK_BRANCH_NAME)
        else:
            if self.edits:
                self.create_branch()
            else:
                print("No one has created any locks!")
                exit(0)

    def branches(self):
        output = self.git_command('git branch --no-color')
        if len(output) == 0:
            print("Please commit something to the 'master' branch before using 'git lock'")
        lines = output.split('\n')
        branches = []
        active_branch = None
        for line in lines:
            if '*' in line:
                active_branch = line[2:]
            else:
                branches.append(line[2:])
        # Store active branch as the last element
        branches.append(active_branch)
        return branches

    @staticmethod
    def git_command(command):
        output = subprocess.check_output(command, shell=True)

        if 'fatal' in output:
            print(output)
            exit(1)

        return output

    def run(self):
        self.pre_actions()
        attempt = 0
        active_branch = self.branches()[-1]
        while attempt < 5:
            self.update()  # checks out the 'dist-locking' branch, must checkout the active branch at the end
            if self.action():
                if self.edits:
                    if not self.commit():
                        self.revert()
                        attempt += 1
                        print "Something went wrong... attempting again in 3 seconds...."
                        time.sleep(3)
                    else:
                        break
            else:  # if the action does not want us to commit anything, simply checkout the original branch
                break

        if attempt == 5:
            print('Something went wrong!')

        self.git_command("git checkout %s" % active_branch)  # re-checkout the branch the user was on before

class LocksMixin(object):

    def __init__(self):
        super(LocksMixin, self).__init__()
        self.locks = {}

    def load_locks(self, lock_file):
        with open(lock_file) as f:
            try:
                self.locks = json.load(f)
            except ValueError as e:
                self.locks = {}

    def add_and_lock(self, lock_file, filename, username, email):
        if self.is_locked(filename, username, email):
            return False
        else:
            self.locks[filename] = {'user': username, 'email': email}
            with open(lock_file, 'w') as f:
                json.dump(self.locks, f)
                return True
        return False

    def unlock(self, lock_file, filename, username, email):
        locked_by = self.locked_by(filename)
        if locked_by != {'user': username, 'email': email}:
            return False
        else:
            self.locks[filename] = {'user': '', 'email': ''}
            with open(lock_file, 'w') as f:
                json.dump(self.locks, f)
                return True
        return False

    def is_locked(self, filename, username, email):
        if filename in self.locks.keys():
            if {'user': username, 'email': email} == self.locks[filename]:
                return False
            elif {'user': '', 'email': ''} == self.locks[filename]:
                return False
            else:
                return True
        else:
            return False

    def locked_by(self, filename):
        if filename in self.locks.keys():
            return self.locks[filename]
        else:
            return {'user': '', 'email': ''}


class GitLock(GitRemoteAction, LocksMixin):
    def __init__(self, filename):
        super(GitLock, self).__init__(edits=True)
        self.filename = filename

    def pre_actions(self):
        # make sure filename exists in current branch, otherwise exit
        if not os.path.isfile(self.filename):
            print("%s is not a valid path in the current repo!" % self.filename)
            exit(1)

    def action(self):
        self.load_locks(self.LOCK_FILE)
        success = self.add_and_lock(self.LOCK_FILE, self.filename, self.git_username(), self.git_email())
        if not success:
            locked_by = self.locked_by(self.filename)
            print("%s is locked by: %s - %s" % (self.filename, locked_by['user'], locked_by['email']))
            return False
        return True

class GitLockStatus(GitRemoteAction, LocksMixin):

    def __init__(self):
        super(GitLockStatus, self).__init__(edits=False)

    def action(self):
        self.load_locks(self.LOCK_FILE)
        other_have_locks = False
        print "\n"
        for filename in self.locks.keys():
            locked_by = self.locked_by(filename)
            if locked_by['user'] != '':
                print("%s locked by %s - %s" % (filename, locked_by['user'], locked_by['email']))

            if self.is_locked(filename, self.git_username(), self.git_email()):
                other_have_locks = True

        if not other_have_locks:
            print("You currently hold the only locks!\n")

        return False

class GitUnlock(GitRemoteAction, LocksMixin):

    def __init__(self, filename):
        super(GitUnlock, self).__init__(edits=True)
        self.filename = filename

    def pre_actions(self):
        # make sure filename exists in current branch, otherwise exit
        if not os.path.isfile(self.filename):
            print("%s is not a valid path in the current repo!" % self.filename)
            exit(1)

    def action(self):
        self.load_locks(self.LOCK_FILE)
        success = self.unlock(self.LOCK_FILE, self.filename, self.git_username(), self.git_email())
        if not success:
            locked_by = self.locked_by(self.filename)
            print("%s is locked by: %s - %s" % (self.filename, locked_by['user'], locked_by['email']))
            return False

        return True

def lock(args):
    git_lock = GitLock(args.filename)
    git_lock.run()

def unlock(args):
    git_unlock = GitUnlock(args.filename)
    git_unlock.run()

def status(args):
    git_status = GitLockStatus()
    git_status.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Coordinates locking files in your git repo.")
    subparser = parser.add_subparsers()

    lock_parser = subparser.add_parser("lock", help="Lock a give filename.")
    lock_parser.add_argument("filename", type=str, help="full path of file in repo to lock.")
    lock_parser.set_defaults(func=lock)

    unlock_parser = subparser.add_parser("unlock", help="Unlock a file you have locked.")
    unlock_parser.add_argument("filename", type=str, help="full path of file in the repo to unlock.")
    unlock_parser.set_defaults(func=unlock)

    status_parser = subparser.add_parser("status", help="List files that have been locked.")
    status_parser.set_defaults(func=status)

    args = parser.parse_args()

    args.func(args)
