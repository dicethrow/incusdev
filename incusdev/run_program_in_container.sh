#!/usr/bin/env bash
set -xeuo pipefail # failfast and be verbose

# 21feb2023
# so I can run, for example, wine programs in a incus container easily

container=$1
local_working_dir=$2
remote_working_dir=$3
container_incus_name=$4
programname=$5
arguments=$6

gitrootdir=$(git rev-parse --show-toplevel)

# replace special characters with dashes from these strings 
# file name to make an almost-unique non-special representative string
unspecialprogramname=$(echo $programname | tr "/\ ;.()" -)
unspecialgitrootdir=$(echo $gitrootdir | tr "/\ ;.()" -)

flag_success="."$unspecialprogramname"_flag_success"
flag_program_already_running="."$unspecialprogramname"_flag_already_running"

# check if program is installed in container
if ! ssh $container -- command -v $programname &> /dev/null
then
    echo $programname could not be found
    exit 1
fi

# change directory to current location of this .sh file, from https://stackoverflow.com/questions/3349105/how-can-i-set-the-current-working-directory-to-the-directory-of-the-script-in-ba
# cd "${0%/*}" # yuck syntax
cd $local_working_dir

# echo $container
# echo $local_working_dir
# echo $remote_working_dir
# echo $container_incus_name
# echo $programname
# echo $arguments

if ssh $container -- test -f $flag_success; then
	# remove the success flag
	ssh $container -- rm $flag_success
else
	echo "Changes made last time have not been copied back out of the container"
	echo "Backing up local files, then getting changes from container"
	
	# backup the current files on the host, in case they contain important changes that we don't want to lose
	backup_name="backup_of_"$unspecialgitrootdir".zip"
	echo "Starting backup to: "$backup_name
	zip -q -r /tmp/$backup_name $gitrootdir
	echo "Backup done"

	# overwrite the current files on the host with the changes in the container
	(cd $gitrootdir; incusdev rsync_from_container $container delete)
fi

# determine and flag if program is alreay running, 
# as progam may not be able to be started completely independently within a container
# note! this check assumes that the $programname doesnt contain any special characters etc,
# which is why $unspecialprogramname is used; which will either be the same as the original,
# or be a harmless command that will fail
if ssh $container -- pgrep $unspecialprogramname > /dev/null 2>&1; then
	ssh $container -- touch $flag_program_already_running
	echo $unspecialprogramname" is already running"
else
	if ssh $container -- test -f $flag_program_already_running; then
		# remove the $flag_program_already_running flag
		ssh $container -- rm $flag_program_already_running
	fi
 	echo $unspecialprogramname" is not already running"
fi

# 16nov2022 (noticed this line was removed a few weeks ago, adding it back in)
# note that the ownership of files is copied over as a code that may not align with the user in the container,
# so lets set container user ownership of these files
# incusdev.run_local_cmd(f"incus shell {incus_container_name} -- sh -c \"chown -R ubuntu:ubuntu {remote_working_dir}\"", print_cmd=True, print_result=True)		
# huh! why does the command work below, but not when run as the line above, in python?
#incus shell $container_incus_name -- sh -c "chown -R ubuntu:ubuntu $remote_working_dir"
incus shell $container_incus_name -- sh -c "chown -R ubuntu:ubuntu /home/ubuntu/from_host/" # mod on 14apr23 as the parent folder/s seem to still have the src users UID (e..g 1002 vs 1000)

# copy over files
(cd $gitrootdir; incusdev rsync_to_container $container delete)

incus shell $container_incus_name -- sh -c "chown -R ubuntu:ubuntu $remote_working_dir"


# open program
ssh $container -- "source ~/.profile && " $programname $arguments 

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
	(cd $gitrootdir; incusdev rsync_from_container $container delete)

	ssh $container -- touch $flag_success	
	echo "Success"
fi
