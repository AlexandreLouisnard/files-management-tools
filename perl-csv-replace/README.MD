# CSV Replace

**Author: Alexandre Louisnard alouisnard@gmail.com**  
**Perl script**  
**2017**

## DESCRIPTION
Find and replace some text within a text file with matching values taken from a dictionary CSV file.

## USAGE
	csvreplace.pl -d DICTIONARY.CSV -w OUTPUT.TXT [-i] [-s ";"] [-h] INPUT.TXT

**Note:** EOF character must be LF (Linux style) and not CR+LF (Windows style).

**PARAMETERS:**  
* -d,--dictionary DICTIONARY.CSV
	* Dictionary CSV file  
* -w,--write OUTPUT.TXT
	* Output file  
* -i,--ignorecase
	* (optional) Case insensitive matching between the CSV file keys and the input text  
* -s,--separator "CUSTOM_SEPARATOR"
	* (optional) Custom separator. Default value is ";"  
* -l,--log LOG.CSV
	* (optional) Output log file
* -h,--help
	* (optional) Help  

**DICTIONARY CSV FILE FORMAT:**  
Note: -s,--separator "CUSTOM_SEPARATOR" optional parameter changes the default ";" separator.  
**dictionary.csv**  
key;value  
first name;Alexandre  
last name;Louisnard  
city and country; Grenoble in France  

## CHANGELOG
* 

## BACKLOG
* Handle CR+LF end-of-line characters.