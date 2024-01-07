import os, sys, subprocess, time

def as_array(result_or_error):
	return result_or_error.decode("utf-8").split("\n")[:-1] if result_or_error != None else []

def run_local_cmd(cmd, **kwargs):
	# print(cmd, flush=True)
	print_result = kwargs.pop("print_result", False)
	print_error = kwargs.pop("print_error", False)
	print_cmd = kwargs.pop("print_cmd", False)
	
	timeout_sec = kwargs.pop("timeout_sec", None)

	if print_cmd:
		print("\n$ " + cmd)

	p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
	
	# if timeout, sleep for that time, then kill it
	# that will make p.communicate() nonblocking
	# technique from https://stackoverflow.com/questions/21936597/blocking-and-non-blocking-subprocess-calls
	if timeout_sec != None:
		time.sleep(timeout_sec)
		p.terminate() 
	
	output, error = p.communicate()
	output = as_array(output)
	error = as_array(error)

	if print_result:
		for line in output:
			print(line)
	
	if print_error:
		for line in error:
			print(line)

	return output, error

def run_local_cmd_realtime(cmd, **kwargs):
	# 9may22
	# from https://www.codegrepper.com/code-examples/python/realtime+output+subprocess

	process = subprocess.Popen(cmd.split(), shell = True,bufsize = 1,
                           stdout=subprocess.PIPE, stderr = subprocess.STDOUT,encoding='utf-8', errors = 'replace', **kwargs) 
	while True:
		realtime_output = process.stdout.readline()
		if realtime_output == '' and process.poll() is not None:
			break
		if realtime_output:
			print(realtime_output.strip(), flush=False)
			sys.stdout.flush()

def run_local_gui_cmd(cmd):
	subprocess.run(cmd, shell=True)
