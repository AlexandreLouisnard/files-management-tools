import os
import mmap

# Directories
script_path = os.path.abspath(os.path.dirname(__file__))
print('* script_path=' + script_path)

script_filename = os.path.basename(__file__)
print('* script_filename=' + script_filename)

working_dir = os.getcwd()
print('* working_dir=' + working_dir)

# Write files
file = open('test.txt', 'w')
file.write('test1\ntest2')
file.close()

# Create dir
dir = 'test_dir'
if os.path.isdir(dir):
    print('* Dir "' + dir + '" already exists')
else:
    print('* mkdir() "' + dir + '"')
    os.mkdir('test_dir')

# List files
dir = os.getcwd()
print('* os.listdir() in ' + dir)
for file in os.listdir(dir):
    filePath = os.path.join(dir, file)
    isFile = os.path.isfile(filePath)
    print(('file: ' if isFile else 'dir: ') + filePath)

# Read files
file = open('test.txt', 'r')
print('* file.read(): ' + file.read())
file.seek(0)
print('* file.readlines(): ' + str(file.readlines()))
file.seek(0)
print('* file.readline(): ' + str(file.readline()))
file.seek(0)

# Find text in files
keyword = 'test2'
print('* Find text with file.read()')
content = file.read()
if keyword in content:
    print('Found "' + keyword + '"')
file.seek(0)
print('* Find text with file.readlines()')
for line in file.readlines():
    if keyword in line:
        print('Found "' + keyword + '": ' + line)
        break
file.seek(0)
print('* Find text with enumerate(file)')
# More memory efficient than looping on readlines()
for line_no, line in enumerate(file):
    if keyword in line:
        print('Found "' + keyword + '": ' + str(line_no) + ': ' + line)
        break
file.seek(0)
print('* Find text with mmap')
# Even more memory efficient than looping on enumerate(file)
content = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
if content.find(str.encode(keyword)) != -1:
    print('Found "' + keyword + '"')
