This is server written (mostly) in perl that is compatible with dyndns
clients (the ones which allow you to specify dyndns server instead of using
hardcoded dyndns.org)

Examples assume your host is named "dyndns.example.net" and running on 
IPv4 address "192.0.2.1", and there are two users already added: 
"foo" and "bar"  (with passwords same as usernames)


Installation:

- requires tinydns up and running as user "tinydns":
  upstream (and configuration information) http://cr.yp.to/djbdns/tinydns.html
  in Debian unstable for example: "apt-get install dbndns daemontools daemontools-run perl apache2
  make"

- requires apache (or some other web server) up and running for selected domain
  with enabled CGI support ("a2enmod cgi" in Debian)

- install bin/* to /usr/local/bin

- install var/www/dyndns/* to /var/www/dyndns

- create empty file /var/log/dyndns.log writeable by tinydns user

- modify and install service/tinydns/* to your /service/tinydns directory

- modify all "example.net" and "192.0.2.1" references to your own domain and IP



Testing:
- point your web browser to  http://dyndns.example.net/checkip.cgi 
  (replace example.net with your actual domain, as always!) and verify 
  it returns your IP address

- if it works, configure your dyndns client (like ddclient or dyndns packages
  in Debian, or your home router) to use your hostname (dyndns.example.net
  in examples) with user "foo" and password "foo" (or "bar"/"bar")

- check if "dig a foo.dyndns.example.net" returns updated IP address

- use "make" in your /service/tinydns/root directory to force DNS reload for testing purposes

Using:
- when ready for production, remove test users from var/www/htusers

- use "dodaj_dyndns username" to add new user to dyndns (you will be asked for password)

