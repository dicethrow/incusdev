#!/usr/bin/env bash

# Copy the current git repo to the container, edit/build in vscode in the container, then on closing vscode, copy them back to the host.

# 23oct22 moved this file to lxdev, so there's only one copy
container=$1
local_working_dir=$2
remote_working_dir=$3
container_lxd_name=$4

gitrootdir=$(git rev-parse --show-toplevel)


# 22oct22 added flag files to indicate whether the last run failed - ie to prevent overwriting data that wasn't copied back last time

# container="lxd_doc-dev"
# remote_dir=$(lxdev get_remote_working_directory $container keep)
# echo "hello there! from "$container" and "$local_working_dir" and "$remote_working_dir

# change directory to current location of this .sh file, from https://stackoverflow.com/questions/3349105/how-can-i-set-the-current-working-directory-to-the-directory-of-the-script-in-ba
# cd "${0%/*}" # yuck syntax
cd $local_working_dir

if ssh $container -- test -f .flag_success; then
	# remove the success flag
	ssh $container -- rm .flag_success
else
	echo "Changes made last time have not been copied back out of the container"
	echo "Backing up local files, then getting changes from container"
	
	# backup the current files on the host, in case they contain important changes that we don't want to lose
	backup_name="backup_of_"$gitrootdir".zip"
	backup_name=${backup_name//\//\-} # replace forbidden slashes with dashes
	echo "Starting backup to: "$backup_name
	zip -q -r /tmp/$backup_name .
	echo "Backup done"

	# overwrite the current files on the host with the changes in the container
	(cd $gitrootdir; lxdev rsync_from_container $container delete)
fi

# determine and flag if codium is alreay running, 
# as codium can't be started completely independently within a container
if ssh $container -- pgrep codium > /dev/null 2>&1; then
	ssh $container -- touch .flag_codium_already_running
	echo "Codium is already running"
else
	ssh $container -- rm .flag_codium_already_running > /dev/null 2>&1 # to silence it if it doesn't exist
 	echo "Codium is not already running"
fi

# copy over files
(cd $gitrootdir; lxdev rsync_to_container $container delete)

# 16nov2022 (noticed this line was removed a few weeks ago, adding it back in)
# note that the ownership of files is copied over as a code that may not align with the user in the container,
# so lets set container user ownership of these files
# lxdev.run_local_cmd(f"lxc shell {lxd_container_name} -- sh -c \"chown -R ubuntu:ubuntu {remote_working_dir}\"", print_cmd=True, print_result=True)		
# huh! why does the command work below, but not when run as the line above, in python?
lxc shell $container_lxd_name -- sh -c "chown -R ubuntu:ubuntu $remote_working_dir"


# open codium
ssh $container -- codium "${remote_working_dir}/*.code-workspace" --disable-gpu #--no-xshm #1> /dev/null 2> /dev/null # assuming there's only one .code-workspace file
# --no-xshm is from https://github.com/microsoft/vscode/issues/101069, as I am getting that grey screen error the first attempt usually
# this source says that a warning message is printed, but can be ignored https://github.com/microsoft/vscode/issues/111372

### gets to this point if codium was closed, often doesn't get to this point if the computer is shutdown ###

# set the flag. no effect if it already is set
if ssh $container -- test -f .flag_codium_already_running; then
	# remove the flag as we're no longer using it
	# also don't flag this as success - this means changes will be copied over next
	ssh $container -- rm .flag_codium_already_running
	echo "Failure, will copy files next time."
	echo "Recommend to briefly rerun ths script again when you close codium to copy the files over, "
	echo "and then close all codium instances with: 'ssh "$container" -- pkill codium'"
	read -p "Press enter to close" userinput

else
	# overwrite the current files on the host with the changes in the container
	# if this script returns from codium() immediately, it won't contain changes, hence will be redundant
	(cd $gitrootdir; lxdev rsync_from_container $container delete)

	ssh $container -- touch .flag_success	
	echo "Success"
fi

