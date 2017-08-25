#!/usr/bin/perl -wT
#
# kreiranje i izmjena dyndns usera
# started Matija Nalis <mnalis-perl@axe.tomsoft.hr> GPLv3+ 2017-08-25
#

my $VER = 'adm_dyndns.cgi v1.00__2017-08-25';

use strict;
use warnings;
use CGI qw(header param);
use IO::Handle;
use Fcntl ':flock';

my $LOGFILE = '/var/log/dyndns.log';
my $HTUSERS = '/var/www/dyndns/.htusers';
my $TINYDNS_ROOT = '/etc/serv/tinydns/root';
my $TINYDNS_DATA = 'data';
my $TINYDNS_BUILD = '/usr/bin/tinydns-data';
my $TINYDNS_LOCK = "$TINYDNS_ROOT/Makefile";

my $verbose = 0;
my $FORCE = 0;

#
# dies a horrible death
#
sub umri
{
	my ($txt) = @_;

	print "<FONT COLOR=red>\n" if $verbose;
	print "$txt\n";
	#warn "$txt";
	mylog ("UMRI: $txt");
	exit 0;
}

# appends text to specified file safely
sub append_text ($$)
{
	my ($file, $text) = @_;

	open (F, '>>', $file) or umri("cannot open for append $file: $!");
	print F "$text\n" or umri("cannot write to $file: $!");
	close (F) or umri ("cannot final write to $file: $!");
}


# logs extra info to logfile
sub mylog($) 
{
	my ($txt) = @_;
	my $timestamp = localtime() . " (PID $$) - ";
	append_text ($LOGFILE, "$timestamp $txt");
}

sub myinfo
{
	my ($text) = @_;
	print "<br>\n" if $verbose;
	print "$text\n";
	mylog($text);
}

sub myinfo_ok
{
	my ($text) = @_;
	print "<FONT COLOR=green>\n" if $verbose;
	myinfo($text);
	print "</FONT>\n" if $verbose;
}

sub myinfo_bad
{
	my ($text) = @_;
	print "<FONT COLOR=red>\n" if $verbose;
	myinfo($text);
	print "</FONT>\n" if $verbose;
}

sub debug_v
{
	my ($text) = @_;
	mylog($text);
	$text .= "\n";
	$text =~ s/\n/<br>\n/g;
	print "$text" if $verbose;
}


# checks param for formating and validates it
sub validate_param($$$)
{
        my ($param, $format, $force) = @_;

        my $value = param($param);
        if ($force and !defined($value)) {
                umri ("$param is required field in this context!");
        }
        
        return undef unless defined($value);

        if ($value =~ /^(${format})$/) {
                $value = $1;
        } else {
                umri ("Invalid format for param $param")
        }
        
        return $value;
}

# checks ENV for formating and validates it
sub validate_env($$$)
{
        my ($env, $format, $force) = @_;

        my $value = $ENV{$env};
        if ($force and !defined($value)) {
                umri ("ENV $env is required in this context!");
        }
        
        return undef unless defined($value);

        if ($value =~ /^(${format})$/) {
                $value = $1;
        } else {
                umri ("Invalid format for env $env")
        }
        
        return $value;
}

# find regex in file, return true if found
sub regex_exists($$)
{
	my ($file, $txt) = @_;
	my $found = 0;
	open my $IN, '<', $file or umri ("can't open $file: $!");
	while (<$IN>) {
		if (/$txt/) { $found = 1; last; }
	}
	close ($IN);
	return $found;
}




#
# here goes the main
#

umask 0022;

# NOTE: maybe comment out next two lines when in production!
use CGI::Carp qw(fatalsToBrowser);
$SIG{__DIE__} = \&confess;

$|=1;
$SIG{__WARN__} = $SIG{__DIE__};	# warnings are fatal!

print header;

my $script_mtime = (stat($0))[9];
append_text ($LOGFILE, '');	# start with empty line
mylog ("adm_dyndns $VER ($script_mtime) starting at " . localtime() . " with PID $$ (USER=$ENV{REMOTE_USER} IP=$ENV{REMOTE_ADDR}) and URI " . $ENV{'REQUEST_URI'} );

if (!chdir($TINYDNS_ROOT)) {
	umri ("Cannot chdir to $TINYDNS_ROOT: $!");
}

mylog ("opening GLOBAL LOCKFILE $TINYDNS_LOCK ...");
open my $GLOBAL_LOCK, '<', $TINYDNS_LOCK or umri ("can't read $TINYDNS_LOCK: $!");
mylog ("locking GLOBAL LOCKFILE $TINYDNS_LOCK ...");
flock($GLOBAL_LOCK, LOCK_EX) or umri("Could not lock $TINYDNS_LOCK: $!");
mylog ("locked GLOBAL LOCKFILE $TINYDNS_LOCK ...");

if (!defined($ENV{'HTTPS'}) or $ENV{'HTTPS'} ne 'on') {
	umri ("must connect via HTTPS to admin!");
}



#
# parameter validation
#
if (!param()) { umri ('no params. Die.') }
#foreach my $k (keys %ENV) { print "$k=$ENV{$k}\n<br>"; }

my $REGEX_IP   = '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'; # TODO: IPv4 only supported for now
my $REGEX_USER = '[\w\.]{2,20}';	
my $username = validate_param ('username', $REGEX_USER, 1);
my $akcija = validate_param ('akcija', 'dodaj_dyndns|ubij_dyndns|passwd_dyndns', 1);
$verbose = validate_param('verbose', '[01]', 0);
my $password;
if ($akcija =~ /^(dodaj|passwd)_dyndns$/ ) {
	$password = validate_param('password', '[A-Za-z0-9_\.\-\/]{3,100}', 1); 
}

# must be after we get all params, otherwise param() won't work (if we do not have %ENV!)
undef %ENV;
$ENV{'PATH'} = '/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin';

# does user exist (in apache htaccess or tinydns data file)
sub user_exists()
{
	return  regex_exists ($HTUSERS, qr/^\Q${username}\E:/) || 
		regex_exists ($TINYDNS_DATA, qr/^\+\Q${username}\E\.dyndns\.example\.net:/);
}

#
# Let's rock & roll !
#

if ($akcija eq 'dodaj_dyndns') {
	if (user_exists()) { umri ("User $username vec postoji, prekidam!"); }
	dodaj_dyndns();
} elsif ($akcija eq 'passwd_dyndns') {
	if (! user_exists()) { umri ("User $username jos ne postoji, prekidam!"); }
	passwd_dyndns();
} elsif ($akcija eq 'ubij_dyndns') {
	if (! user_exists()) { umri ("User $username jos ne postoji, prekidam!"); }
	ubij_dyndns();
} else {
	umri ("Nepoznata akcija: $akcija");
}

mylog ('finished');
exit 0;


# safely update file, adding or removing line
sub safe_add_remove_tinydns ($$)
{
	my ($addFlag, $removeFlag) = @_;

	my $LOGPRE = "$akcija $username";
	my $HOST = "${username}.dyndns.example.net";
	
	my $TINYDNS_TMP = $TINYDNS_DATA . '.src.tmp';
	debug_v ("$LOGPRE - opening IN $TINYDNS_DATA ...");
	open my $IN, '<', $TINYDNS_DATA or umri ("can't read $TINYDNS_DATA: $!");
	debug_v ("$LOGPRE - locking IN $TINYDNS_DATA ...");
	flock($IN, LOCK_EX) or umri('911', "Could not lock $TINYDNS_DATA: $!");
	debug_v ("$LOGPRE - locked IN $TINYDNS_DATA ...");
	debug_v ("$LOGPRE - opening tmp $TINYDNS_TMP ...");
	open my $OUT, '>', $TINYDNS_TMP or umri ("can't write $TINYDNS_TMP: $!");
	debug_v ("$LOGPRE - locking tmp $TINYDNS_TMP ...");
	flock($OUT, LOCK_EX) or umri('911', "Could not lock $TINYDNS_TMP: $!");
	debug_v ("$LOGPRE - locked tmp $TINYDNS_TMP ...");
	my $found_dynamic = 0;
	my $changed = 0;
	my $written = 0;
	while (my $line = <$IN>) {
		if ($line =~ /^# DYNAMIC IP BELOW/) { $found_dynamic = 1 }
		if ($found_dynamic) {
			# +burek.dyndns.example.net:10.0.99.42:60
			if ($line =~ /^\+\Q${HOST}\E:(${REGEX_IP})(:?.*)$/) {	# found our host!
				if ($removeFlag) {
					$changed = 1;
					next;
				}
			}
		}
		print $OUT $line or umri ("can't append to $TINYDNS_TMP: $!"); $written++;
		#sleep 1;	# FIXME for debug only! 
	}

	if ($addFlag) {
		print $OUT "+${HOST}:127.0.0.1:60\n" or umri ("can't append new host to $TINYDNS_TMP: $!"); $written++;
		$changed = 1;
	}
	
	if ($changed) {
		# hopefully this provides atomicity (but not durabilitly, as we don't fsync dir after rename) -- see http://stackoverflow.com/questions/7433057/is-rename-without-fsync-safe & http://lwn.net/Articles/457667/
		$OUT->flush or umri ("can't flush $TINYDNS_TMP: $!");
		$OUT->sync or umri ("can't fsync $TINYDNS_TMP: $!");
		debug_v ("$LOGPRE - fsynced tmp $TINYDNS_TMP ($. lines, written $written) ...");
		
		#$| = 1; print "b4 rename $$... "; sleep 10;
		rename $TINYDNS_TMP, $TINYDNS_DATA or umri ("can't rename $TINYDNS_TMP to $TINYDNS_DATA: $!");
		debug_v ("$LOGPRE - renamed tmp $TINYDNS_TMP to $TINYDNS_DATA ...");
		#print "b4 system $$... "; sleep 10;
		debug_v ("$LOGPRE - rebuilding CDB using $TINYDNS_BUILD ...");
		system($TINYDNS_BUILD) == 0 or umri ("can't rebuild via $TINYDNS_BUILD: $?");
		debug_v ("$LOGPRE - rebuilt CDB using $TINYDNS_BUILD = $? ...");
		#print "b4 close $$... "; sleep 10; 
		close ($OUT) or umri ("can't close to $TINYDNS_DATA: $!");	# only release lock after .cdb file is built by $TINYDNS_BUILD !
		debug_v ("$LOGPRE - closed $TINYDNS_DATA ...");
		myinfo_ok ("$LOGPRE - finished");
	} else {								# IP was not changed
		unlink $TINYDNS_TMP;
		myinfo_bad ("$LOGPRE - no change on Add=$addFlag/Remove=$removeFlag (aborted at line $., written=$written)");
		close ($OUT);
	}
}




#
# print & execute the command
#
sub doit
{
	my ($cmd) = @_;
	$verbose && print ("<b>Executing:</b> <pre>$cmd</pre>");

	my $output=`$cmd 2>&1`;
	my $err = $?;
#	$output =~ s/\n/<br>\n/g;
	chomp($output);
	myinfo ("Output ($err): $output");

	if ($err and !$FORCE) { umri ("ERROR ($err): $output") }
	return $err;
}



sub dodaj_dyndns
{
	safe_add_remove_tinydns (1, 0);
	if (doit ("htpasswd -b $HTUSERS $username $password") == 0) {	# FIXME security use popen() and "-i"  instead
		myinfo_ok ("password set for $username");
	} else {
		myinfo_bad ("failed setting password for $username");
	}
}

sub ubij_dyndns
{
	safe_add_remove_tinydns (0, 1);
	if (doit ("htpasswd -D $HTUSERS $username") == 0) {
		myinfo_ok ("deleted password for $username");
	} else {
		myinfo_bad ("failed deleting password for $username");
	}
}

sub passwd_dyndns
{
	if (doit ("htpasswd -b $HTUSERS $username $password") == 0) {	# FIXME security use popen() and "-i"  instead
		myinfo_ok ("password updated for $username");
	} else {
		myinfo_bad ("failed updating password for $username");
	}
}
