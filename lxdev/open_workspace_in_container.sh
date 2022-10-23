#!/usr/bin/env bash

# Copy the current git repo to the container, edit/build in vscode in the container, then on closing vscode, copy them back to the host.

# 23oct22 moved this file to lxdev, so there's only one copy
container=$1
local_working_dir=$2
remote_working_dir=$3

# 22oct22 added flag files to indicate whether the last run failed - ie to prevent overwriting data that wasn't copied back last time

# container="lxd_doc-dev"
# remote_dir=$(lxdev get_remote_working_directory $container keep)
# echo "hello there! from "$container" and "$local_working_dir" and "$remote_working_dir

# change directory to current location of this .sh file, from https://stackoverflow.com/questions/3349105/how-can-i-set-the-current-working-directory-to-the-directory-of-the-script-in-ba
# cd "${0%/*}" # yuck syntax
cd $local_working_dir

if ssh $container -- test -f .flag_success; then
	ssh $container -- rm .flag_success
else
	echo "Changes made last time have not been copied back out of the container"
	echo "Backing up local files, then getting changes from container"
	
	# backup the current files on the host, in case they contain important changes that we don't want to lose
	backup_name="backup_of_"$(pwd)".zip"
	backup_name=${backup_name//\//\-} # replace forbidden slashes with dashes
	echo "Backup saved to: "$backup_name
	zip -q -r /tmp/$backup_name .

	# overwrite the current files on the host with the changes in the container
	(cd $(git rev-parse --show-toplevel); lxdev rsync_from_container $container delete)
fi

# copy over files
(cd $(git rev-parse --show-toplevel); lxdev rsync_to_container $container delete)

# open codium
ssh $container -- codium "${remote_working_dir}/*.code-workspace" --disable-gpu #--no-xshm 1> /dev/null 2> /dev/null # assuming there's only one .code-workspace file
# --no-xshm is from https://github.com/microsoft/vscode/issues/101069, as I am getting that grey screen error the first attempt usually
# this source says that a warning message is printed, but can be ignored https://github.com/microsoft/vscode/issues/111372

### gets to this point if codium was closed, often doesn't get to this point if the computer is shutdown ###

# overwrite the current files on the host with the changes in the container
(cd $(git rev-parse --show-toplevel); lxdev rsync_from_container $container delete)

# set the flag. no effect if it already is set
ssh $container -- touch .flag_success
