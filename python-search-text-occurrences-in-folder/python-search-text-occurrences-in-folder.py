# Within a folder, find text occurrences of the keywords listed in a file.
# The result is printed in a csv file with this format: keyword, occurrences_count, matched_file_1, matched_file_2, matched_file_3,...

import os

script_path = os.path.abspath(os.path.dirname(__file__))

# The root directory where we want to search for the text occurrences
rootdir = ('C:\\DEV\\15986_PORTALP_RS_installer_app\\android\\portalpcomlibrary\\src\\main\\java\\com\\portalp\\com_library')

# The extension of the files where we want to search for the text occurrences
# Use empty string '' to search all files
extension = '.java'

# UTF8 text file with one keyword per line
keywords_file = script_path + '\\keywords.txt'

# Result output file
output_file = script_path + '\\output.csv'

with open(output_file, 'w') as output_f:
    with open(keywords_file, 'r') as keywords_f:
        for keyword in keywords_f:  # each line is a keyword to search for
            keyword = keyword.strip()
            count = 0
            matched_files = set()
            for folder, dirs, files in os.walk(rootdir):
                for file in files:
                    if file.endswith(extension):
                        fullpath = os.path.join(folder, file)
                        with open(fullpath, 'r') as f:
                            for line in f:
                                if keyword in line:
                                    count = count + line.count(keyword)
                                    matched_files.add(fullpath)
                                    break
            # print(keyword + ',' + str(count) + ',' + ','.join(matched_files) + '\n')
            output_f.write(keyword + ',' + str(count) + ',' + ','.join(matched_files) + '\n')
