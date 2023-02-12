import os, argparse
import lxdev
import textwrap

defined_tasks = [
	"check_dirs",
	"rsync_to_container",
	"rsync_from_container",
	"get_remote_working_directory",

	"init_lxd_git-server_on_host",
	"init_lxd_git-server_access_in_container",
	# "refresh_repo_in_host_and_dev_container", # using git for this purpose seems obfuscatory, too complex

	"open_workspace_in"
]

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("task", type=str, help=f"action to do, out of: {''.join(s + ', ' for s in defined_tasks)}")
	parser.add_argument("remote_hostname", type=str, nargs='?', help="remote_hostname", default="none")
	parser.add_argument("arg2", type=str, nargs='?', help="'delete' or 'keep'? how to handle overwriting files at destination.", default="keep")
	# parser.add_argument("script_dir", type=str, nargs='?', default="none")

	args = parser.parse_args()

	assert args.task in defined_tasks

	if args.task == "check_dirs":
		print("Hello this is the standalone cli file")
		print(f"This .py's path is: {os.path.dirname(os.path.realpath(__file__))}")
		print(f"User dir is: {os.path.expanduser('~')}")
		print(f"Script called from {os.getcwd()}")

	elif args.task == "init_lxd_git-server_on_host": 
		init_lxd_git_server_on_host(args)
	
	elif args.task == "init_lxd_git-server_access_in_container":
		init_lxd_git_server_access_in_container(args)

	elif args.task in ["rsync_to_container", "rsync_from_container", "get_remote_working_directory"]:
		do_rsync(args)

	elif args.task == "open_workspace_in":
		open_workspace_in(args)
		
	else:
		assert 0, "Invalid task given"

def init_lxd_git_server_on_host(args):
	assert "home" in os.getcwd(), "this function is defined for folders within a host users home directory only"

	host = "lxd_git-server" if args.remote_hostname == "none" else args.remote_hostname
	lxd_container_name = assert_we_can_extract_lxd_name_from_hostname(host)
	with  lxdev.RemoteClient(
		host = host, # e.g. lxd_doc-dev
		lxd_container_name = lxd_container_name,
		local_working_directory = os.getcwd() # the directory where this is called from
		) as ssh_remote_client:
			local_git_path, error = lxdev.run_local_cmd(f"git rev-parse --show-toplevel")
			assert error==[], f"Error: {error}"
			
			desired_remote_git_path = ssh_remote_client.get_remote_filename_from_local(local_git_path[0]) + ".git"

			ssh_remote_client.execute_commands([
				f"mkdir -p {desired_remote_git_path}",
				f"git -C {desired_remote_git_path} --bare init",

				# now to disable compression, so things go faster, from https://stackoverflow.com/questions/45955460/disabling-delta-compression-in-git-for-a-single-remote
				f"touch {desired_remote_git_path}/info/attributes",
				f'echo "* -delta" >> {desired_remote_git_path}/info/attributes'
			])
			
			result, error = lxdev.run_local_cmd(f"git remote add lxd_git-server {host}:{desired_remote_git_path}")
			assert error==[], f"Error: {error}"

def init_lxd_git_server_access_in_container(args):
	# result, error = lxdev.run_local_cmd(f"git remote -v | grep lxd_git-server")
	# assert result != [], f"Error: Access to the lxd_git-server has not been setup on the host yet: {result}"
	# assert error==[], f"Error: {error}"
	
	host = args.remote_hostname
	assert host != "none", "The container that wants to access lxd_git-server needs to be specified"

	# Get the public ssh key of the development container
	# Make it it it doesn't exist 
	lxd_container_name = assert_we_can_extract_lxd_name_from_hostname(host)
	with lxdev.RemoteClient(
		host = host,
		lxd_container_name = lxd_container_name,
		local_working_directory = os.getcwd() # the directory where this is called from
		) as ssh_remote_client:
			
			_, error = ssh_remote_client.execute_commands("cat ~/.ssh/id_rsa.pub > /dev/null", get_stderr=True)
			for line in error:
				if "No such file or directory" in line: # then we need to set up a key
					# from https://unix.stackexchange.com/questions/69314/automated-ssh-keygen-without-passphrase-how
					ssh_remote_client.execute_commands('< /dev/zero ssh-keygen -q -N "" > /dev/null')
			dev_container_key = "".join(ssh_remote_client.execute_commands("cat ~/.ssh/id_rsa.pub"))

			# also add the name resolution from 'lxd_git-server' to ipaddress
			result, error = ssh_remote_client.execute_commands("touch ~/.ssh/config && cat ~/.ssh/config", get_stderr=True) # touch in case it doesn't exist
			assert error == []
			found = False
			for line in result:
				if "lxd_git-server" in line:
					found = True
			if not found:
				name_resolution_lines = textwrap.dedent(""" 
				Host lxd_git-server
					HostName 10.40.119.159
					User ubuntu
					IdentityFile ~/.ssh/id_rsa
					ForwardAgent Yes
					ForwardX11 Yes

				""")
				for line in name_resolution_lines.split("\n"):
					ssh_remote_client.execute_commands(f"echo '{line}' >> ~/.ssh/config")
			
	# now let's copy the public key to the known keys of lxd_git-server, using the default location
	with lxdev.RemoteClient(
		host = "lxd_git-server",
		lxd_container_name = "git-server",
		local_working_directory = os.getcwd() # the directory where this is called from
		) as ssh_remote_client:
			# first, check that we haven't already got this key in the destination file
			contains_key = False
			for key_to_check in ssh_remote_client.execute_commands('cat ~/.ssh/authorized_keys'):
				if dev_container_key in key_to_check:
					contains_key = True
			
			if not contains_key:
				ssh_remote_client.execute_commands(f"echo {dev_container_key} >> ~/.ssh/authorized_keys")
	
	# now the dev container has ssh access to the lxd_git-server container
	# set up the dev container's git worktree, if not set up yet
	with lxdev.RemoteClient(
		host = host,
		lxd_container_name = lxd_container_name,
		local_working_directory = os.getcwd() # the directory where this is called from
		) as ssh_remote_client:
			local_git_path, error = lxdev.run_local_cmd(f"git rev-parse --show-toplevel")
			assert error==[], f"Error: {error}"

			desired_remote_git_path = ssh_remote_client.get_remote_filename_from_local(local_git_path[0])
			print(desired_remote_git_path)

			result = ssh_remote_client.execute_commands(f"git -C {desired_remote_git_path} status")
			for line in result:
				if "not a git repository" in line:
					# then we need to make the repo
					ssh_remote_client.execute_commands([f"git -C {desired_remote_git_path} init"])
			
			result = ssh_remote_client.execute_commands(f"git -C {desired_remote_git_path} remote -v | grep lxd_git-server")
			
			if result == []: # then we haven't yet added the new remote
				ssh_remote_client.execute_commands(f"git -C {desired_remote_git_path} remote add lxd_git-server lxd_git-server:{desired_remote_git_path}.git")

			# also make sure the dev container's git name and email, for this repo, matches the host
			host_git_repo_user_name = lxdev.run_local_cmd("git config user.name")[0][0]
			host_git_repo_user_email = lxdev.run_local_cmd("git config user.email")[0][0]
			ssh_remote_client.execute_commands(f"git -C {desired_remote_git_path} config user.name {host_git_repo_user_name}")
			ssh_remote_client.execute_commands(f"git -C {desired_remote_git_path} config user.email {host_git_repo_user_email}")

	""" 
	How to deal with this interactive situation?
	logging in and manually doing the first pull/push...

	ubuntu@doc-dev $ git push lxd_git-server 
	The authenticity of host '10.40.119.159 (10.40.119.159)' can't be established.
	ECDSA key fingerprint is SHA256:uY4aidND95NrlQqHLlVWa5CvGU7OopxCvEvSk5mQdEM.
	Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
	Warning: Permanently added '10.40.119.159' (ECDSA) to the list of known hosts.
	To lxd_git-server:/home/ubuntu/from_host/x/Documents/git_repos/documentation/projects/prototyping_workflows.git
	"""




def do_rsync(args):
	assert "home" in os.getcwd(), "this function is defined for folders within a host users home directory only"
		
	lxd_container_name = assert_we_can_extract_lxd_name_from_hostname(args.remote_hostname)

	if args.task in ["rsync_to_container", "rsync_from_container"]:
		if args.arg2 == "delete":
			delete = True
		elif args.arg2 == "keep":
			delete = False
		else:
			assert 0, "Invalid arg2 argument passed, should be 'delete' or 'keep'"

	with  lxdev.RemoteClient(
		host = args.remote_hostname, # e.g. lxd_doc-dev
		lxd_container_name = lxd_container_name,
		local_working_directory = os.getcwd() # the directory where this is called from
		) as ssh_remote_client:

			# print("Connected!")
			if args.task == "rsync_to_container":
				ssh_remote_client.rsync_to_container(delete=delete)

			elif args.task == "rsync_from_container":
				ssh_remote_client.rsync_from_container(delete=delete)

			elif args.task == "get_remote_working_directory":
				print(ssh_remote_client.remote_working_directory, end="") 
				# this 'print' is used to save the result as a variable in some bash scripts, 
				# e.g. remote_dir=$(lxdev get_remote_working_directory lxd_doc-dev keep)

			else:
				assert 0	

def open_workspace_in(args):
	# this is to replace having complexity in the `open_workspace_in_xxx.sh` files
	assert "home" in os.getcwd(), "this function is defined for folders within a host users home directory only"
	
	host = args.remote_hostname
	lxd_container_name = assert_we_can_extract_lxd_name_from_hostname(host)
	local_working_dir = os.path.abspath(args.arg2)
	# print(local_working_dir)

	with lxdev.RemoteClient(
		host = host, # e.g. lxd_doc-dev
		lxd_container_name = lxd_container_name,
		local_working_directory = local_working_dir
		) as ssh_remote_client:
			remote_working_dir = ssh_remote_client.remote_working_directory

	# print(remote_working_dir)

	# as it currently works in a .sh file, just use that, for now
	script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "open_workspace_in_container.sh")

	lxdev.run_local_gui_cmd(f"{script_path} {host} {local_working_dir} {remote_working_dir} {lxd_container_name}")


def assert_we_can_extract_lxd_name_from_hostname(hostname):
	lxd_container_name = hostname.replace("lxd_", "") # e.g. lxd_doc-dev -> doc-dev
	result, error = lxdev.run_local_cmd(f"lxc info {lxd_container_name}")
	assert "Error: Not Found" not in result+error, f"Invalid lxd container name inferred of: {lxd_container_name}"
	return lxd_container_name



# elif args.task == "refresh_repo_in_host_and_dev_container":
	# 	# from https://stackoverflow.com/questions/171550/find-out-which-remote-branch-a-local-branch-is-tracking
	# 	get_upstream_branch_name_cmd_part1 = "git symbolic-ref -q HEAD"
	# 	get_upstream_branch_name_cmd = f"git for-each-ref --format='%(upstream:short)' \"$({get_upstream_branch_name_cmd_part1})\""

		
	# 	# If this fails, make sure to call 'init_lxd_git-server_on_host' and 'init_lxd_git-server_access_in_container' first
	# 	host = args.remote_hostname
	# 	assert host != "none", "The container for development needs to be specified"
	# 	lxd_container_name = assert_we_can_extract_lxd_name_from_hostname(host)
	# 	with lxdev.RemoteClient(
	# 		host = host,
	# 		lxd_container_name = lxd_container_name,
	# 		local_working_directory = os.getcwd() # the directory where this is called from
	# 		) as ssh_remote_client:

	# 			# get changes from host
	# 			symbolic_ref = lxdev.run_local_cmd(get_upstream_branch_name_cmd_part1)[0][0]
	# 			original_upstream_branch = lxdev.run_local_cmd(f"git for-each-ref --format='%(upstream:short)' {symbolic_ref}")[0][0]

	# 			# original_upstream_branch = lxdev.run_local_cmd(get_upstream_branch_name_cmd, print_result=True, print_error=True, print_cmd=True)[0][0]
	# 			print(original_upstream_branch)
	# 			original_remote, original_branch = original_upstream_branch.split("/")
	# 			git_server_branch = f"lxd_git-server/{original_branch}"
	# 			lxdev.run_local_cmd(f"git branch --set-upstream-to {git_server_branch}")

	# 			status = lxdev.run_local_cmd(f"git status")[0]
	# 			for line in status:
	# 				if "Changes not staged for commit" in line: # this means that the commit_changes_from_dev_container task didn't run last time
	# 					lxdev.run_local_cmd(f"git add -A")
	# 					lxdev.run_local_cmd(f"git commit -m '{input('Enter commit message for changes in container: ')}'")
					
	# 				elif "Your branch is ahead" in line: # then there are unpushed changes
	# 					lxdev.run_local_cmd(f"git pull lxd_git-server")
	# 					lxdev.run_local_cmd("git push lxd_git-server")
				
	# 			lxdev.run_local_cmd(f"git branch --set-upstream-to {original_upstream_branch}")

	# 			####### and now in dev container,


	# 			local_git_path, error = lxdev.run_local_cmd(f"git rev-parse --show-toplevel")
	# 			assert error==[], f"Error: {error}"
	# 			remote_git_path = ssh_remote_client.get_remote_filename_from_local(local_git_path[0])
				
	# 			# let's temporarily set the lxd_git-server repo as upstream for now, assuming dev and host are the same				
	# 			ssh_remote_client.execute_commands(f"git branch --set-upstream-to {git_server_branch}")

	# 			status = ssh_remote_client.execute_commands(f"git status")
	# 			for line in status:
	# 				if "Changes not staged for commit" in line: # this means that the commit_changes_from_dev_container task didn't run last time
	# 					ssh_remote_client.execute_commands([
	# 						f"git add -A",
	# 						f"git commit -m '{input('Enter commit message for changes in container: ')}'"
	# 					])
					
	# 				elif "Your branch is ahead" in line: # then there are unpushed changes
	# 					ssh_remote_client.execute_commands([
	# 						f"git pull lxd_git-server", # ass
	# 						f"git push lxd_git-server"
	# 					])
					
	# 				# elif 

	# 			# and undo it
	# 			ssh_remote_client.execute_commands(f"git branch --set-upstream-to {original_upstream_branch}")

	# 	# now get the changes on the host from lxd_git-server
