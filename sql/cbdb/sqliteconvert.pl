# perl script to convert SQLite to mySQL

use utf8;
use strict;
use warnings;

{
my ($datei, $dateiname, $zeile, $i, $name, $sub);

print ("UTF-8 SQL-Datei, die ausgewertet werden soll: >>> ");

$datei = <>;
chomp $datei;

open (TEXT, "<:utf8",$datei) or die "Die Datei '$datei' kann nicht geoeffnet werden: $!";
$dateiname = "mysql-$datei";
open (MYSQL, ">:utf8",$dateiname);

$i = 0;
while ($zeile = <TEXT>){
    if (($zeile !~  /BEGIN TRANSACTION/) && ($zeile !~ /COMMIT/) && ($zeile !~ /sqlite_sequence/) && ($zeile !~ /CREATE UNIQUE INDEX/)){

    	if ($zeile =~ /CREATE TABLE \"([a-z_]*)\"(.*)/){
		$name = $1;
		$sub = $2;
		$sub =~ s/\"//g;
		$zeile = "DROP TABLE IF EXISTS $name;\nCREATE TABLE IF NOT EXISTS $name$sub\n";
	}
	elsif ($zeile =~ /INSERT INTO \"([a-z_]*)\"(.*)/){
		$zeile = "INSERT INTO $1$2\n";
		$zeile =~ s/\"/\\\"/g;
		$zeile =~ s/\"/\'/g;
    	} else {
		$zeile =~ s/\'\'/\\\'/g;
	}
	$zeile =~ s/([^\\'])\'t\'(.)/$1THIS_IS_TRUE$2/g;
	$zeile =~ s/THIS_IS_TRUE/1/g;
	$zeile =~ s/([^\\'])\'f\'(.)/$1THIS_IS_FALSE$2/g;
	$zeile =~ s/THIS_IS_FALSE/0/g;
	$zeile =~ s/AUTOINCREMENT/AUTO_INCREMENT/g;
		
	# [] have to be replaced with backticks
	$zeile =~ s/\[/`/g;
	$zeile =~ s/\]/`/g;
	
	#we want to be sure that we don't insert backslashes without escaping them
	$zeile =~ s/\'\\\\'/\'\\\\\\'/g;
	
	# count how many lines there are
	$i++;
	print MYSQL ("$zeile");    
	}
}
print ("Insgesamt $i Zeilen wurden verarbeitet.\n");
close TEXT;
close MYSQL;
}