import os, subprocess

def as_array(result_or_error):
	return result_or_error.decode("utf-8").split("\n")[:-1] if result_or_error != None else []

def run_local_cmd(cmd):
	# print(cmd, flush=True)
	p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, error = p.communicate()

	return as_array(output), as_array(error)