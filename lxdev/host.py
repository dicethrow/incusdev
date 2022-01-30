import os, subprocess

def as_array(result_or_error):
	return result_or_error.decode("utf-8").split("\n")[:-1] if result_or_error != None else []

def run_local_cmd(cmd, **kwargs):
	# print(cmd, flush=True)
	p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
	output, error = p.communicate()

	return as_array(output), as_array(error)

def run_local_gui_cmd(cmd):
	subprocess.run(cmd, shell=True)
