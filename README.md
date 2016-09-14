# git-lock

When working with LaTex or binary files, it is often useful to be able to indicate to other team members that you are
working in a given file to avoid conflicts. Before you begin working, you'd like to be able to see who is working in 
which file.

This plugin lets you do just that without the over head of sending an email or popping into Slack with the hopes that 
the other authors will get back to you quickly.

## Motivation, Design and Limitations

When working with large text documents (that are not code), with binary files (e.g.: pptx's), or with complex file types
(e.g.: iOS Storyboards), git really breaks down.

This plugin lets you and your team mates indicate that you are working in a given file. During times in which others are
making changes in a file, you should avoid working in it unless you are ready to make (potentially complex) merges.

I thought about making a chat bot or using some external database for this, but since most teams work with git using a 
`remote` it seemed easier to simply use git itself.

This works by storing locks in a `lock` file in a dedicated branch to track who is working in which file. There is a
mechanism in place to ensure that if a lock is acquired at the exact same time on separate machines,
one of the users will be prevented from actually acquring the lock.

#### Assumptions

- You have a remote named `origin`.
- You **do not have** a file named `lock` in the root directory of your repo.
   - This is used for a JSON document to store who has which locks.
- You **do not have** a branch named `dist-locking`.
   - This branch is used to create the equivalent to a "transaction" when updating locks.
   
## Installation

- `git clone https://github.com/rsprabery/git-lock.git` - clone this repo
- `cd git-lock`
- `sudo ln -s $(pwd)/git-lock.py /usr/bin/git-lock` - install this script somewhere in your `$PATH`

And of course, the one-liner:

`git clone https://github.com/rsprabery/git-lock.git && cd git-lock && sudo ln -s $(pwd)/git-lock.py /usr/bin/git-lock`

## Usage

```bash
usage: git-lock [-h] {lock,unlock,status} 
```

### Status

Display who has locks on which files.

```bash
git lock status --help                      

usage: git-lock status [-h]

optional arguments:
  -h, --help  show this help message and exit
```

### Locking

Create a lock for a given file. **Important** the filename must be the full path of the file you want to lock in your 
current branch.

```bash
git lock lock --help                      

usage: git-lock lock [-h] filename

positional arguments:
  filename    full path of file in repo to lock.

optional arguments:
  -h, --help  show this help message and exit
```

### Unlocking

Unlock a given file. **Important** the filename must be the full path of the file you want to lock in your current branch.

```bash
git lock unlock --help                      

usage: git-lock unlock [-h] filename

positional arguments:
  filename    full path of file in the repo to unlock.

optional arguments:
  -h, --help  show this help message and exit
```

## Workflow

This plugin works best if you follow a well defined flow.

**It is not possible to enforce locks in git!** - this means that the **team must have a good process**. If this process
is abused, this plugin doesn't do you any good.

I suggest the following work flow:

- Try and lock a file
  - If it fails to lock:
     - Wait for a reasonable amount of time
     - Try again (or message the person holding the lock)
- Do your work on your locked file
  - Commit your changes
- **Remember** to unlock the file!

If you honor these rules, you find this very useful in helping teams coordinate difficult to merge files.
