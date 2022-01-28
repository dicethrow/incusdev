import os, argparse
import lxdev

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("task", type=str, help="action to do")
	parser.add_argument("arg2", type=str, help="multi-purpose second argument")
	args = parser.parse_args()

	if args.task == "check_dirs":
		print("Hello this is the standalone cli file")
		print(f"This .py's path is: {os.path.dirname(os.path.realpath(__file__))}")
		print(f"User dir is: {os.path.expanduser('~')}")
		print(f"Script called from {os.getcwd()}")

	elif args.task == "rsync_to_container":
		assert "home" in os.getcwd(), "this function is defined for folders within a host users home directory only"
		
		lxd_container_name = args.arg2.replace("lxd_", "") # e.g. lxd_doc-dev -> doc-dev
		result, error = lxdev.run_local_cmd(f"lxc info {lxd_container_name}")
		assert "Error: Not Found" not in result+error, f"Invalid lxd container name inferred of: {lxd_container_name}"

		with  lxdev.RemoteClient(
			host = args.arg2, # e.g. lxd_doc-dev
			lxd_container_name = lxd_container_name,
			local_working_directory = os.getcwd() # the directory where this is called from
			) as ssh_remote_client:

				# print("Connected!")
				ssh_remote_client.rsync_to_container()
			
	else:
		assert 0, "Invalid task given"



