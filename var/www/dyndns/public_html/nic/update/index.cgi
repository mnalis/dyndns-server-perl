#!/usr/bin/perl -wT
# Matija Nalis <mnalis-perl@axe.tomsoft.hr> GPLv3+ 2013,2014,2015
# dyndns.org-compatible server-side replacement (update)

use strict;
use CGI qw(header param);
use CGI::Carp qw(fatalsToBrowser);
use IO::Handle;
use Fcntl ':flock';

my $LOGFILE = '/var/log/dyndns.log';

# dies with error code
sub umri($$)
{
	my ($code, $text) = @_;
	print "$code: $text\n";
	warn "$code: $text";
	exit 0;
}

# logs extra info
sub debug($) 
{
	my ($txt) = @_;
	
	open my $LOGFILE, '>>', $LOGFILE  or umri('911', "can't log to $LOGFILE: $!");
	my $timestamp = "$$ - " . localtime() . " - ";
	print $LOGFILE "$timestamp $txt\n" or umri ('911', "can't write to $LOGFILE: $!");;
	close $LOGFILE or umri ('911', "can't finish writing to $LOGFILE: $!");
}

# FIXME - error codes fix!

#
# checks param for formating and validates it
#
sub validate_param($$$)
{
        my ($param, $format, $force) = @_;

        my $value = param($param);
        if ($force and !defined($value)) {
                umri ('911', "$param is required field in this context!");
        }
        
        return undef unless defined($value);

        if ($value =~ /^(${format})$/) {
                $value = $1;
        } else {
                umri ('911', "Invalid format for param $param")
        }
        
        return $value;
}

#
# checks ENV for formating and validates it
#
sub validate_env($$$)
{
        my ($env, $format, $force) = @_;

        my $value = $ENV{$env};
        if ($force and !defined($value)) {
                umri ('911', "ENV $env is required in this context!");
        }
        
        return undef unless defined($value);

        if ($value =~ /^(${format})$/) {
                $value = $1;
        } else {
                umri ('911', "Invalid format for env $env")
        }
        
        return $value;
}

#
# here goes the main
#

print header('text/plain');

$ENV{'PATH'} = '/bin:/usr/bin';
my $TINYDNS_ROOT = '/etc/serv/tinydns/root';
my $TINYDNS_DATA = 'data';
my $TINYDNS_BUILD = '/usr/bin/tinydns-data';
my $TINYDNS_LOCK = "$TINYDNS_ROOT/Makefile";

my $script_mtime = (stat($0))[9];
debug('started v'.$script_mtime);

if (!chdir($TINYDNS_ROOT)) {
	umri ('911', "Cannot chdir to $TINYDNS_ROOT: $!");
}

debug ("opening GLOBAL LOCKFILE $TINYDNS_LOCK ...");
open my $GLOBAL_LOCK, '<', $TINYDNS_LOCK or umri ('911', "can't read $TINYDNS_LOCK: $!");
debug ("locking GLOBAL LOCKFILE $TINYDNS_LOCK ...");
flock($GLOBAL_LOCK, LOCK_EX) or umri('911', "Could not lock $TINYDNS_LOCK: $!");
debug ("locked GLOBAL LOCKFILE $TINYDNS_LOCK ...");

#if (!defined($ENV{'HTTPS'}) or $ENV{'HTTPS'} ne 'on') {
#	umri ('911', "must connect via HTTPS to update!");	# FIXME - dyndns.org does not seem to use it, although HTTP basic auth is security risk in plaintext!
#}

# foreach my $k (keys %ENV) { print "$k=$ENV{$k}\n<br>"; }

my $REGEX_IP   = '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}';	# TODO: IPv4 only supported for now
my $REGEX_USER = '[\w\.]{2,20}';	
my $REGEX_HOST = '[\w\.\-]{2,40}';			# HOSTNAME must be in format xxxx.dyndns.example.net, but we check for that later

my $HOST = validate_param('hostname', $REGEX_HOST, 1);
my $USER = validate_env('REMOTE_USER', $REGEX_USER, 1);
my $IP2  = validate_env('REMOTE_ADDR', $REGEX_IP, 1);	# TODO - try to identify proxies?
my $IP   = validate_param('myip', $REGEX_IP, 0);

if (defined($IP)) {		# do we have IP override specified?
	if ($IP ne $IP2) {
		# FIXME - allow IP overrides?
#		umri ('911', "IP mismatch: specified IP $IP not equal to origin IP $IP2");
	}
} else {
	$IP = $IP2;
}

if ($HOST =~ /^(.+)\.dyndns\.tomsoft\.hr/) {
	my $HOST_SHORT=$1;
	if ($HOST_SHORT ne $USER) {
		umri ('911', "Permission mismatch: user $USER tried to modify host $HOST");
	}
	
	my $TINYDNS_TMP = $TINYDNS_DATA . '.src.tmp';
	debug ("$HOST $IP - opening IN $TINYDNS_DATA ...");
	open my $IN, '<', $TINYDNS_DATA or umri ('911', "can't read $TINYDNS_DATA: $!");
	debug ("$HOST $IP - locking IN $TINYDNS_DATA ...");
	flock($IN, LOCK_EX) or umri('911', "Could not lock $TINYDNS_DATA: $!");
	debug ("$HOST $IP - locked IN $TINYDNS_DATA ...");
	debug ("$HOST $IP - opening tmp $TINYDNS_TMP ...");
	open my $OUT, '>', $TINYDNS_TMP or umri ('911', "can't write $TINYDNS_TMP: $!");
	debug ("$HOST $IP - locking tmp $TINYDNS_TMP ...");
	flock($OUT, LOCK_EX) or umri('911', "Could not lock $TINYDNS_TMP: $!");
	debug ("$HOST $IP - locked tmp $TINYDNS_TMP ...");
	my $found_dynamic = 0;
	my $changed = 0;
	my $written = 0;
	while (my $line = <$IN>) {
		if ($line =~ /^# DYNAMIC IP BELOW/) { $found_dynamic = 1 }
		if ($found_dynamic) {
			# +burek.dyndns.example.net:10.0.99.42:60
			if ($line =~ /^\+\Q${HOST}\E:(${REGEX_IP})(:?.*)$/) {	# found our host! replace IP
				my $old_ip = $1; 
				my $old_moredata = $2;
				if ($old_ip ne $IP) {				# do the actual IP update!
					print $OUT "+$HOST:$IP$old_moredata\n" or umri ('911', "can't change $TINYDNS_TMP: $!"); $written++;
					$changed = 1;
					next;
				} else {
					last;					# abort early if host found, but IP not changed!
				}
			}
		}
		print $OUT $line or umri ('911', "can't append to $TINYDNS_TMP: $!"); $written++;
		#sleep 1;	# FIXME for debug only! 
	}
	
	if ($changed) {
		# hopefully this provides atomicity (but not durabilitly, as we don't fsync dir after rename) -- see http://stackoverflow.com/questions/7433057/is-rename-without-fsync-safe & http://lwn.net/Articles/457667/
		$OUT->flush or umri ('911', "can't flush $TINYDNS_TMP: $!");
		$OUT->sync or umri ('911', "can't fsync $TINYDNS_TMP: $!");
		debug ("$HOST $IP - fsynced tmp $TINYDNS_TMP ($. lines, written $written) ...");
		
		#$| = 1; print "b4 rename $$... "; sleep 10;
		rename $TINYDNS_TMP, $TINYDNS_DATA or umri ('911', "can't rename $TINYDNS_TMP to $TINYDNS_DATA: $!");
		debug ("$HOST $IP - renamed tmp $TINYDNS_TMP to $TINYDNS_DATA ...");
		#print "b4 system $$... "; sleep 10;
		debug ("$HOST $IP - rebuilding CDB using $TINYDNS_BUILD ...");
		system($TINYDNS_BUILD) == 0 or umri ('911', "can't rebuild via $TINYDNS_BUILD: $?");
		debug ("$HOST $IP - rebuilt CDB using $TINYDNS_BUILD = $? ...");
		#print "b4 close $$... "; sleep 10; 
		close ($OUT) or umri ('911', "can't close to $TINYDNS_DATA: $!");	# only release lock after .cdb file is built by $TINYDNS_BUILD !
		debug ("$HOST $IP - closed $TINYDNS_DATA ...");
		print "good $IP";
	} else {								# IP was not changed
		unlink $TINYDNS_TMP;
		close ($OUT);
		print "nochg $IP";
		debug ("$HOST $IP - no change (aborted at line $., written=$written)");
	}
	
} else {
	umri ('911', "hostname $HOST not in format xxxx.dyndns.example.net");
}

debug("finished\n");
exit 0;
