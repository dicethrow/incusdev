import os

def main():
	print("Hello this is the standalone cli file")

	dir_path = os.path.dirname(os.path.realpath(__file__))
	print(dir_path)

	a = os.path.expanduser('~')
	print(a)