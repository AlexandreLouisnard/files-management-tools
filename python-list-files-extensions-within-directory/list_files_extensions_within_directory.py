#!/usr/bin/python
# coding: utf-8

# Author Alexandre Louisnard

import sys
import os
import re

try:
	sys.argv[1]
except (NameError, IndexError):
	dirPath = "."
else:
	dirPath = sys.argv[1]

extensions = {}

for root, dirs, files in os.walk(dirPath, topdown=False):
	for name in files:
		regex = r".*\.(.*)$"
		capture = re.findall(regex, name)
		if capture:
			extensions[capture[0]] = extensions.get(capture[0], 0) + 1


print("File extensions within directory: " + dirPath)
for key in sorted(extensions, key=extensions.__getitem__, reverse=True):
	print(key + "\t" + str(extensions[key]))
