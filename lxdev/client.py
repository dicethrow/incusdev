"""Client to handle connections and actions executed against a remote host."""
import subprocess, sys, os, glob, traceback, time, tempfile, textwrap, shutil
from typing import List

from paramiko import RSAKey, SSHClient, SSHConfig, ProxyCommand, RejectPolicy
from paramiko.ssh_exception import (
    SSHException,
    AuthenticationException,
    BadAuthenticationType,
    PartialAuthentication,
	NoValidConnectionsError
)

from .log import LOGGER 

def ensure_container_is_on(container_name):
	# turn on the doc-dev container if it is not already on
	any_started = False
	for response_line in subprocess.check_output("lxc list".split()).decode("utf-8").split("\n"):
		if all(x in response_line for x in [container_name, "STOPPED"]):
			LOGGER.info(f"{container_name} was off, starting up")
			subprocess.run(f"lxc start {container_name}".split())
			any_started = True
	if any_started:	
		LOGGER.info(f"waiting...")
		count = 5
		for i in range(count):	
			time.sleep(1)
			LOGGER.info(f"{count-i}")

class myRemoteException(Exception):
	pass


class RemoteClient:
	"""Client to interact with a remote host via SSH & SCP."""

	def __init__(
		self,
		host: str,
		lxd_container_name: str,
		local_working_directory: str,
		user = "ubuntu",
		ssh_config_filepath="~/.ssh/config",
	):
		self.host = host
		self.lxd_container_name = lxd_container_name
		self.local_working_directory = local_working_directory
		self.remote_working_directory = self.local_working_directory.replace("/home/", "~/from_host/")
		self.user = user
		self.ssh_config_filepath = ssh_config_filepath
		self.client = None
		
		assert "home" in self.local_working_directory, "content must be in the host user's home folder"

	def __enter__(self):
		"""Open SSH connection to remote host."""
		try:
			ensure_container_is_on(self.lxd_container_name)


			# 10, 11 dec 2021
			# from https://gist.github.com/acdha/6064215
			cfg = {'hostname': self.host, 'username': self.user}

			self.client = SSHClient()
			self.client.load_system_host_keys()
			self.client._policy = RejectPolicy()
			ssh_config = SSHConfig()
			user_config_file = os.path.expanduser(self.ssh_config_filepath)
			if os.path.exists(user_config_file):
				with open(user_config_file) as f:
					ssh_config.parse(f)
			
			user_config = ssh_config.lookup(cfg['hostname'])
			for k in ('hostname', 'username', 'port'):
				if k in user_config:
					cfg[k] = user_config[k]

			if 'proxycommand' in user_config:
				cfg['sock'] = ProxyCommand(user_config['proxycommand'])

			self.client.connect(**cfg)
			return self

		except AuthenticationException as e:
			LOGGER.error(
				f"AuthenticationException occurred; did you remember to generate an SSH key? {e}"
			)
			raise e
		except NoValidConnectionsError as e:
			LOGGER.error(f"NoValidConnectionsError occurred, host is unreachable. Is the server on?: {e}")
			raise e
		except Exception as e:
			LOGGER.error(f"Unexpected error occurred: {e}")
			raise e

	def __exit__(self, exc_type, exc_value, traceback):
		"""Close SSH connection"""
		self.client.close()

	

	def rsync(self, delete = False, direction = "local_to_remote", rel_local_dir = "content", rel_remote_dir = "invalid_dir"):
		# 10dec2021 from https://discuss.linuxcontainers.org/t/rsync-files-into-container-from-host/822
		# rsync docs https://linux.die.net/man/1/rsync
		# -avPz means --archive --verbose --partial --progress --compress"
		# the extra --delete is so deleted files are removed

		# 6jan2022
		# tempfile technique from here https://stackoverflow.com/questions/28410137/python-create-temp-file-namedtemporaryfile-and-call-subprocess-on-it
		fake_ssh_fp = tempfile.NamedTemporaryFile(delete=True)
		with open(fake_ssh_fp.name, "w") as f:
			f.write(textwrap.dedent("""
				#!/bin/sh
				ctn="${1}"
				shift
				exec lxc exec "${ctn}" -- "$@"
			""".lstrip("\n")))
		os.chmod(fake_ssh_fp.name, 0x0777)
		fake_ssh_fp.file.close()

		success = True
		try:
			if direction == "local_to_remote":
				self.execute_commands(f"mkdir -p /home/ubuntu/Documents/{rel_remote_dir}") # make remote directory tree if it doesn't exist
				self.execute_commands(f"mkdir -p /home/ubuntu/Documents/Outputs") # make remote directory tree if it doesn't exist

				log_str = f"Used rsync from local {rel_local_dir} to {self.host}:/home/ubuntu/Documents/{rel_remote_dir}"
				cmd = f"rsync -avPz {rel_local_dir}/ -e {fake_ssh_fp.name} {self.lxd_container_name}:/home/ubuntu/Documents/{rel_remote_dir}/{' --delete' if delete else ''}"

			elif direction == "remote_to_local":
				log_str = f"Used rsync from {self.host}:/home/ubuntu/Documents/{rel_remote_dir} to local {rel_local_dir}"
				cmd = f"rsync -avPz -e {fake_ssh_fp.name} {self.lxd_container_name}:/home/ubuntu/Documents/{rel_remote_dir}/ {rel_local_dir}/{' --delete' if delete else ''}"

			LOGGER.opt(ansi=True).info(f"<green>{log_str}</green>")
			
			for response_line in subprocess.check_output(cmd.split(" ")).decode("utf-8").split("\n"):
				if any(x in response_line for x in ["rsync error", "failed"]):
					success = False
					LOGGER.error(f"rsync failed: {response_line}")
				else:
					LOGGER.opt(ansi=True).info(f"<light-blue>{response_line}</light-blue>")

			assert success, "Aborting after rsync failure"
				
		except FileNotFoundError as error:
			LOGGER.error(error)
			raise e
		except Exception as e:
			LOGGER.error(f"Unexpected error occurred: {e}")
			raise e

	
	def interactive_shell(self, commands, within_remote_working_dir=False):
		
		assert type(commands) == list, "only a list of commands makes sense here"

		if within_remote_working_dir:
			# execute in remote working dir?
			commands = [f"cd {self.remote_working_directory} && "] + commands

		channel = self.client.invoke_shell()
		stdin = channel.makefile('wb')
		stdout = channel.makefile('r')

		while True:
			result = ""
			time.sleep(0.2)

			while channel.recv_ready():
				result += channel.recv(999).decode("utf-8")
				time.sleep(0.2)
			print(result, end="")

			if channel.send_ready():

				if len(commands) > 0:
					next_cmd = commands[0]
					commands = commands[1:]
				else:
					next_cmd = input("")
					
				channel.sendall(str(next_cmd + "\r\n").encode("utf-8"))

	
	def execute_commands(self, commands, ignore_failures = False, get_stderr = False, within_remote_working_dir=False, pass_to_stdin=None):
		"""
		Execute multiple commands in succession.

		:param commands: List of unix commands as strings.
		:type commands: List[str]
		"""

		if type(commands) == str:
			combined_cmd = commands
		elif type(commands) == list:
			combined_cmd = ""
			for i, cmd in enumerate(commands):
				if i == 0:
					combined_cmd = cmd 
				else:
					combined_cmd += " && " + cmd
		
		if within_remote_working_dir:
			# execute in remote working dir?
			combined_cmd = f"cd {self.remote_working_directory} && " + combined_cmd

		# print(combined_cmd)

		LOGGER.opt(ansi=True).info(f"<green>{self.user}@{self.host} $ {combined_cmd}</green>")

		stdin, stdout, stderr = self.client.exec_command(combined_cmd)

		if pass_to_stdin != None:
			stdin.channel.send(pass_to_stdin)
			stdin.channel.shutdown_write()			

		result_lines = []
		# stdout.channel.recv_exit_status()  # not used? 28jan2022
		try:
			while True: # prints as each line is ready, form https://stackoverflow.com/questions/55642555/real-time-output-for-paramiko-exec-command
				line = stdout.readline()
				if not line:
					break			
				line = line.strip("\n")
				LOGGER.trace(f"INPUT: {combined_cmd}")
				LOGGER.info(f"{line}")
				result_lines.append(line)
		except Exception as e:
			print(e)
			LOGGER.error(f"INPUT: {combined_cmd}")
			LOGGER.error("Failed to read from stdout.readlines() , probably due to non-utf8 encoding")

		# stderr.channel.recv_exit_status() # not used? 28jan2022
		success = True
		error_lines = []
		while True: # prints as each line is ready, form https://stackoverflow.com/questions/55642555/real-time-output-for-paramiko-exec-command
			error_line = stderr.readline()
			if not error_line:
				break
			error_line = error_line.strip("\n")
			if ("WARNING" in error_line):
				pass # don't fail on warnings?
				LOGGER.info(f"{error_line}")
			else:
				success = False
				# LOGGER.error(f"{error_line}")
				try:
					LOGGER.opt(ansi=True).error(f"{error_line}") # for colours printed on stderr
				except:
					LOGGER.error(f"{error_line}")
			error_lines.append(error_line)

		if (not ignore_failures) and (not success):
			# raise myRemoteException(error_lines)
			pass

		if get_stderr:
			return result_lines, error_lines, 
		else:
			return result_lines
	
	def clean(self): # obsolete
		folders_to_delete =  ["Outputs", "Uploads"]
		for folder in folders_to_delete:
			if len(self.execute_commands(f"ls ~/Documents/{folder}/")) > 0:
				self.execute_commands(f"rm -r ~/Documents/{folder}/*")


	### new

	def empty_folders(self, folders_to_delete, local_or_remote):
		assert local_or_remote in ["local", "remote", "local_and_remote"]
	
		"from here https://www.geeksforgeeks.org/delete-an-entire-directory-tree-using-python-shutil-rmtree-method/"
		for folder in folders_to_delete:
			if local_or_remote in ["local", "local_and_remote"]:
				path = os.path.join(self.local_working_directory, folder)
				if os.path.isdir(path):
					shutil.rmtree(path)
				os.mkdir(path) # so the folder exists and is empty

			if local_or_remote in ["remote", "local_and_remote"]:
				path = os.path.join(self.remote_working_directory, folder)
				if len(self.execute_commands(f"ls {path}")) > 0:
					self.execute_commands(f"rm -r {path}/*")


	def rsync_abs(self, delete = False, direction = "local_to_remote", abs_local_dir = "content", abs_remote_dir = "invalid_dir"):
		# 26jan2022
		# changed to use abs paths
		# next: phase out the old rsync and replace it with this

		# 10dec2021 from https://discuss.linuxcontainers.org/t/rsync-files-into-container-from-host/822
		# rsync docs https://linux.die.net/man/1/rsync
		# -avPz means --archive --verbose --partial --progress --compress"
		# the extra --delete is so deleted files are removed

		# 6jan2022
		# tempfile technique from here https://stackoverflow.com/questions/28410137/python-create-temp-file-namedtemporaryfile-and-call-subprocess-on-it
		fake_ssh_fp = tempfile.NamedTemporaryFile(delete=True)
		with open(fake_ssh_fp.name, "w") as f:
			f.write(textwrap.dedent("""
				#!/bin/sh
				ctn="${1}"
				shift
				exec lxc exec "${ctn}" -- "$@"
			""".lstrip("\n")))
		os.chmod(fake_ssh_fp.name, 0x0777)
		fake_ssh_fp.file.close()

		success = True
		try:
			# assuming this will always be used with lxd with an ubuntu user,
			abs_remote_dir = abs_remote_dir.replace("~", "/home/ubuntu")

			if direction == "local_to_remote":
				self.execute_commands(f"mkdir -p {abs_remote_dir}") # make remote directory tree if it doesn't exist
				# self.execute_commands(f"mkdir -p /home/ubuntu/Documents/Outputs") # make remote directory tree if it doesn't exist

				log_str = f"Used rsync from local {abs_local_dir} to {self.host}:{abs_remote_dir}"
				cmd = f"rsync -avz {abs_local_dir}/ -e {fake_ssh_fp.name} {self.lxd_container_name}:{abs_remote_dir}/{' --delete' if delete else ''}"

			elif direction == "remote_to_local":
				log_str = f"Used rsync from {self.host}:{abs_remote_dir} to local {abs_local_dir}"
				cmd = f"rsync -avz -e {fake_ssh_fp.name} {self.lxd_container_name}:{abs_remote_dir}/ {abs_local_dir}/{' --delete' if delete else ''}"

			# LOGGER.opt(ansi=True).info(f"<green>{log_str}</green>")
			
			for response_line in subprocess.check_output(cmd.split(" ")).decode("utf-8").split("\n"):
				response_line = response_line.replace("\r", "") # so things stay on one line
				# print(response_line.encode("utf-8"))
				if any(x in response_line for x in ["rsync error", "failed"]):
					success = False
					LOGGER.error(f"rsync failed: {response_line}")
				else:
					LOGGER.opt(ansi=True).info(f"<light-blue>{response_line}</light-blue>")

			assert success, "Aborting after rsync failure"
				
		except FileNotFoundError as error:
			LOGGER.error(error)
			raise e

		except Exception as e:
			LOGGER.error(f"Unexpected error occurred: {e}")
			raise e
		
		finally:
			LOGGER.opt(ansi=True).info(f"<green>{log_str}</green>")

	def rsync_to_container(self):
		""" 
		An alternative to using a shared folder approach.
		For a self.local_working_directory of 
			~/Documents/git_repos/a/b/c
		rsync the given directory to the container in the dir
			~/from_host/<host-username>/Documents/git_repos/a/b/c
		"""

		self.rsync_abs(
			delete = False,
			direction = "local_to_remote",
			abs_local_dir=self.local_working_directory,
			abs_remote_dir=self.remote_working_directory
		)

	def rsync_from_container(self):
		""" 
		The opposite of 'rsync_to_container'
		"""
		self.rsync_abs(
			delete = False,
			direction = "remote_to_local",
			abs_local_dir=self.local_working_directory,
			abs_remote_dir=self.remote_working_directory
		)
		


		
