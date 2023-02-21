#!/usr/bin/env bash

# 21feb2023
# so I can run, for example, wine programs in a lxd container easily

container=$1
local_working_dir=$2
remote_working_dir=$3
container_lxd_name=$4
programname=$5
arguments=$6

# change directory to current location of this .sh file, from https://stackoverflow.com/questions/3349105/how-can-i-set-the-current-working-directory-to-the-directory-of-the-script-in-ba
# cd "${0%/*}" # yuck syntax
cd $local_working_dir

# echo $container
# echo $local_working_dir
# echo $remote_working_dir
# echo $container_lxd_name
# echo $programname
# echo $arguments

flag_success="."$programname"_flag_success"
flag_program_already_running="."$programname"_flag_already_running"


if ssh $container -- test -f $flag_success; then
	# remove the success flag
	ssh $container -- rm $flag_success
else
	echo "Changes made last time have not been copied back out of the container"
	echo "Backing up local files, then getting changes from container"
	
	# backup the current files on the host, in case they contain important changes that we don't want to lose
	backup_name="backup_of_"$(pwd)".zip"
	backup_name=${backup_name//\//\-} # replace forbidden slashes with dashes
	echo "Starting backup to: "$backup_name
	zip -q -r /tmp/$backup_name .
	echo "Backup done"

	# overwrite the current files on the host with the changes in the container
	(cd $(git rev-parse --show-toplevel); lxdev rsync_from_container $container delete)
fi

# determine and flag if program is alreay running, 
# as progam may not be able to be started completely independently within a container
if ssh $container -- pgrep $programname > /dev/null; then
	ssh $container -- touch $flag_program_already_running
	echo $programname" is already running"
else
	ssh $container -- rm $flag_program_already_running > /dev/null # to silence it if it doesn't exist
 	echo $programname" is not already running"
fi

# copy over files
(cd $(git rev-parse --show-toplevel); lxdev rsync_to_container $container delete)

# 16nov2022 (noticed this line was removed a few weeks ago, adding it back in)
# note that the ownership of files is copied over as a code that may not align with the user in the container,
# so lets set container user ownership of these files
# lxdev.run_local_cmd(f"lxc shell {lxd_container_name} -- sh -c \"chown -R ubuntu:ubuntu {remote_working_dir}\"", print_cmd=True, print_result=True)		
# huh! why does the command work below, but not when run as the line above, in python?
lxc shell $container_lxd_name -- sh -c "chown -R ubuntu:ubuntu $remote_working_dir"



# open program
ssh $container -- $programname $arguments 

### gets to this point if program was closed, often doesn't get to this point if the computer is shutdown ###

# set the flag. no effect if it already is set
if ssh $container -- test -f $flag_program_already_running; then
	# remove the flag as we're no longer using it
	# also don't flag this as success - this means changes will be copied over next
	ssh $container -- rm $flag_program_already_running
	echo "Failure, will copy files next time."
	echo "Recommend to briefly rerun ths script again when you close codium to copy the files over, "
	echo "and then close all "$programname" instances with: 'ssh "$container" -- pkill "$programname"'"
	read -p "Press enter to close" userinput

else
	# overwrite the current files on the host with the changes in the container
	# if this script returns from codium() immediately, it won't contain changes, hence will be redundant
	(cd $(git rev-parse --show-toplevel); lxdev rsync_from_container $container delete)

	ssh $container -- touch $flag_success	
	echo "Success"
fi
