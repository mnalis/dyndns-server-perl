#!/usr/bin/perl -w
# Matija Nalis <mnalis-perl@axe.tomsoft.hr> GPLv3+ 2013,2014
# dyndns.org-compatible server-side replacement (check)

use strict;
use CGI qw(header);

print header();
print "<html><head><title>Current IP Check</title></head><body>";
print "Current IP Address: " . $ENV{'REMOTE_ADDR'};
print "</body></html>";

exit 0;
