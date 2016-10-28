data.cdb: data
	[ "`id -un`" = "tinydns" ] &&  /usr/bin/tinydns-data || setuidgid tinydns /usr/local/bin/reload_dyndns
	sync
	
