## Replace text within file using CSV dictionary file to match replacements ##

import re
import csv
import os

script_path = os.path.abspath(os.path.dirname(__file__))

# Original file containing some text to replace. Will not be modified
target_file = script_path + '\\test.txt'
# Dictionary CSV UTF8 file with each line format: text_to_match,replacement_text)
dictionary_csv_file = script_path + '\\dic.csv'
# Output file
output_file = script_path + '\\test_out.txt'


# Open dictionary CSV file
dic = {}
with open(dictionary_csv_file, mode='r') as f:
    reader = csv.reader(f)
    dic = {rows[0]:rows[1] for rows in reader}

# Open target file
target_file = open(target_file,"r")
text = target_file.read() 

# Make replacements
for k, l in dic.items():
    text = re.sub(r"\b%s\b"%k, l, text) 

print(text) 

# Write to output file
with open(output_file, 'w') as f:
    f.write(text)