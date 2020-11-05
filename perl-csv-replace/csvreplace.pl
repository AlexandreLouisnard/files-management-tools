#!/usr/bin/env perl
use strict;
use warnings;
use Getopt::Long;

# Author Alexandre Louisnard

# Get arguments
printHelp() unless @ARGV;
my $dicFile;
my $outputFile;
my $ignoreCase;
my $separator = ";";
my $logFile;
my $help;
GetOptions ("dictionary=s"	=> \$dicFile,
			"write=s"		=> \$outputFile,
			"ignorecase"	=> \$ignoreCase,
			"separator=s"	=> \$separator,
			"log=s"			=> \$logFile,
			"help|?"		=> \$help)
or die("Error in command line arguments\n");
printHelp() if ($help);
die "Missing argument: -d DICTIONARY.CSV\n" unless $dicFile;
my $inputFile = shift or die "Missing argument: input text file\n";

# Parse dictionary CSV file
open (my $dicFH, '<', $dicFile) or die "Impossible to open the dictionary CSV file \"$dicFile\"\n";
my %dictionary = map { chomp; split($separator, $_, 2);} <$dicFH>;
close $dicFH;
if ($ignoreCase) {
	%dictionary = map { do {lc($_) if ($ignoreCase);}  => $dictionary{$_} } keys %dictionary;
}
my $re = join ('|', map (quotemeta, keys %dictionary));

# Parse input text file and generate output
open (my $inputFH, '<', $inputFile) or die "Impossible to open the input text file \"$inputFile\"\n";
open (my $outputFH, '>', $outputFile) or die "Impossible to write output log file \"$outputFile\"\n" if $outputFile;
my %logDictionary = map {$_ => 0} keys %dictionary;
while (<$inputFH>) {
	$ignoreCase ? s/($re)/$logDictionary{lc($1)}++;"$dictionary{lc($1)}"/egi : s/($re)/$logDictionary{$1}++;"$dictionary{$1}"/eg;
	$outputFH ? print $outputFH $_ : print;
}
close $inputFH;
close $outputFH if $outputFH;

# Write log file
if ($logFile) {
	open (my $logFH, '>', $logFile) or die "Impossible to write output log file \"$logFile\"\n";
	open (my $dicFH, '<', $dicFile) or die "Impossible to open the dictionary CSV file \"$dicFile\"\n";
	while (<$dicFH>) {
		$ignoreCase ? s/($re);(.*)\n?$/$1;$logDictionary{lc($1)}\n/gi : s/($re);(.*)\n?$/$1;$logDictionary{$1}\n/g;
		print $logFH $_;
	}
	close $logFH;
}

# Command-line help and exit
sub printHelp {
	print <<EOF;
DESCRIPTION:
Find and replace some text within a text file with matching values taken from a dictionary CSV file.

USAGE:
./csvreplace.pl -d DICTIONARY.CSV -w OUTPUT.TXT [-i] [-s ";"] [-l LOG.CSV] [-h] INPUT.TXT

PARAMETERS:
-d,--dictionary DICTIONARY.CSV\t\tDictionary CSV file
-w,--write OUTPUT.TXT\t\t\tOutput file
-i,--ignorecase\t\t\t\tCase insensitive matching between the CSV file keys and the input text
-s,--separator "CUSTOM_SEPARATOR"\tCustom separator. Default value is ";"
-l,--log LOG.CSV\t\t\tOutput log file
-h,--help\t\t\t\tHelp

DICTIONARY CSV FILE FORMAT (-s,--separator "CUSTOM_SEPARATOR" optional parameter changes the default ";" separator):
key;value
first name;Alexandre
last name;Louisnard
city and country; Grenoble in France

AUTHOR:
Alexandre Louisnard alouisnard\@gmail.com
EOF
exit;
}