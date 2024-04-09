- 9apr24
	- try to deal with this issue:
	- idea: modify `self.client.load_system_host_keys()` to be passed a filename that just has keys for incus contaner access?
	- this is the prompt that is opened, which askes for my password for my aws key, which isn't needed for incus stuff
	- and here is what is printed when I reject the popup:

	```
		(pyvenv311) x@e595 $ ./open_ltspice_in_wine_in_elec-dev.sh 
		/home/x/Documents/pyvenv311/lib/python3.11/site-packages/jupyter_client/connect.py:22: DeprecationWarning: Jupyter is migrating its paths to use standard platformdirs
		given by the platformdirs library.  To remove this warning and
		see the appropriate new directories, set the environment variable
		`JUPYTER_PLATFORM_DIRS=1` and then run `jupyter --paths`.
		The use of platformdirs will be the default in `jupyter_core` v6
		from jupyter_core.paths import jupyter_data_dir, jupyter_runtime_dir, secure_write
		Exception (client): key cannot be used for signing
		Traceback (most recent call last):
		File "/home/x/Documents/pyvenv311/lib/python3.11/site-packages/paramiko/transport.py", line 2185, in run
			handler(m)
		File "/home/x/Documents/pyvenv311/lib/python3.11/site-packages/paramiko/auth_handler.py", line 404, in _parse_service_accept
			sig = self.private_key.sign_ssh_data(blob, algorithm)
				^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
		File "/home/x/Documents/pyvenv311/lib/python3.11/site-packages/paramiko/agent.py", line 496, in sign_ssh_data
			raise SSHException("key cannot be used for signing")
		paramiko.ssh_exception.SSHException: key cannot be used for signing

		04-09-2024 10:06:36 | ERROR: Unexpected error occurred: No existing session
		Traceback (most recent call last):
		File "/home/x/Documents/pyvenv311/bin/incusdev", line 8, in <module>
			sys.exit(main())
					^^^^^^
		File "/home/x/Documents/git_repos/software/tools/remote-dev-tools-with-incus/incusdev/standalone_cli.py", line 59, in main
			run_program_in(args)
		File "/home/x/Documents/git_repos/software/tools/remote-dev-tools-with-incus/incusdev/standalone_cli.py", line 313, in run_program_in
			with incusdev.RemoteClient(
		File "/home/x/Documents/git_repos/software/tools/remote-dev-tools-with-incus/incusdev/client.py", line 97, in __enter__
			raise e
		File "/home/x/Documents/git_repos/software/tools/remote-dev-tools-with-incus/incusdev/client.py", line 84, in __enter__
			self.client.connect(**cfg)
		File "/home/x/Documents/pyvenv311/lib/python3.11/site-packages/paramiko/client.py", line 489, in connect
			self._auth(
		File "/home/x/Documents/pyvenv311/lib/python3.11/site-packages/paramiko/client.py", line 822, in _auth
			raise saved_exception
		File "/home/x/Documents/pyvenv311/lib/python3.11/site-packages/paramiko/client.py", line 798, in _auth
			self._transport.auth_publickey(username, key)
		File "/home/x/Documents/pyvenv311/lib/python3.11/site-packages/paramiko/transport.py", line 1648, in auth_publickey
			raise SSHException("No existing session")
		paramiko.ssh_exception.SSHException: No existing session
		sys:1: ResourceWarning: unclosed <socket.socket fd=4, family=1, type=1, proto=0, raddr=/run/user/1000/keyring/ssh>
	```

	- although... when I run it again, I didn't get the popup! so maybe I just need to try/auto-reject-any-popups/catch once ?