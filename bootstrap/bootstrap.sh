# Bootstrap for vagrant browser server
# @author Matthew Norris

function main() {
	install
	dl_sauce
	pretty_print "Provisioning Complete"
}


# Installation stuff goes here.
function install() {

	DBPASSWD="vagrant"

	pretty_print "PROVISIONING"
	pretty_print "Installing pip"
	apt-get update
	apt-get install -y python3-pip

	pretty_print "Installing BioPython"
	pip3 install biopython

	pretty_print "Installing apache2" # apache 2 is only needed for phpmyadmin
	apt-get install -y apache2

	# install phpmyadmin, with some config options preset - otherwise it'll try to run the GUI installer
	pretty_print "Installing MySQL specific packages and settings"
	export DEBIAN_FRONTEND=noninteractive

	echo "mysql-server mysql-server/root_password password $DBPASSWD" | debconf-set-selections
	echo "mysql-server mysql-server/root_password_again password $DBPASSWD" | debconf-set-selections

	echo "phpmyadmin phpmyadmin/dbconfig-install boolean true" | debconf-set-selections
	echo "phpmyadmin phpmyadmin/app-password-confirm password $DBPASSWD" | debconf-set-selections
	echo "phpmyadmin phpmyadmin/mysql/admin-pass password $DBPASSWD" | debconf-set-selections
	echo "phpmyadmin phpmyadmin/mysql/app-pass password $DBPASSWD" | debconf-set-selections
	echo "phpmyadmin phpmyadmin/reconfigure-webserver multiselect none" | debconf-set-selections
	apt-get -y install mysql-server phpmyadmin > /dev/null 2>&1
	echo "create database rnabrowser" | mysql -u root -p$DBPASSWD

	# create symlink so that apache serves up some delicious phpmyadmin
	ln -s /usr/share/phpmyadmin /var/www/phpmyadmin

	# Install Flask stuff
	pretty_print "Installing Flask"
	pip3 install Flask

	# install a Python3-compatible mysql connector
	pip3 install mysql-connector-python --allow-external mysql-connector-python

	# install the Flask-SQLAlchemy plugin, for ORM shiz
	pip3 install Flask-SQLAlchemy

	pretty_print "Installing git"
	apt-get install -y git

	# Copy handy bash aliases to home folder
	# Must use explicit home folder path, otherwise it'll copy to super user's path instead of vagrant's
	cp /vagrant/bootstrap/.bash_aliases /home/vagrant/.bash_aliases

	# OLD STUFF

	# Install the project and its dependencies
	# python3 setup.py develop 
	# initialize_rnabrowser_db development.ini
	# Let's also add phpmyadmin
	# pretty_print "Installing Rnabrowser Project"
	# cd /vagrant/rnabrowser 
	# easy_install-3.4 pyramid waitress
	#  python3.4 setup.py develop ??
	# Install
	# Django migrate shiz
	# pretty_print "Migrating Database"
	# cd /vagrant/rnabrowser
	# rm rnabrowserapp/migrations/* # otherwise old migrations might bork it
	# python3 manage.py migrate # django setup migration
	# python3 manage.py makemigrations rnabrowserapp
	# python3 manage.py migrate rnabrowserapp
}

# Grabs lots of genome data files. These will be parsed and used to seed the SNP database.
function dl_sauce() {
	# TODO
	# grab raw genome data from network if available. 
	# otherwise, download the data from its origin

	pretty_print "Grabbing Sauce Data"

	cd /vagrant/sauce_data

	# Grab sequence annotation files, relative to both strain-of-interest and reference, for each strain
	urlbase="http://mus.well.ox.ac.uk/19genomes/annotations/consolidated_annotation_9.4.2011/gene_models/"

	# This is the reference sequence annotation
	fetch_extract_gff3 $urlbase "consolidated_annotation.Col_0.Col_0"
	fetch_extract_gff3 $urlbase "consolidated_annotation.Col_0"

	# fetch_extract_gff3 $urlbase "consolidated_annotation.Bur_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Bur_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Can_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Can_0"
	
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Ct_1.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Ct_1"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Edi_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Edi_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Hi_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Hi_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Kn_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Kn_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Ler_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Ler_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Mt_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Mt_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.No_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.No_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Oy_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Oy_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Po_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Po_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Rsch_4.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Rsch_4"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Sf_2.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Sf_2"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Tsu_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Tsu_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Wil_2.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Wil_2"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Ws_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Ws_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Wu_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Wu_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Zu_0.Col_0"
	# fetch_extract_gff3 $urlbase "consolidated_annotation.Zu_0"


	# Fetch the chromosomal TAIR10 reference sequence. We'll get the RNAs out using the .gff3 annotation
	urlbase="ftp://ftp.arabidopsis.org/home/tair/Sequences/whole_chromosomes/"
	fetch_raw $urlbase "TAIR10_chr1.fas"
	fetch_raw $urlbase "TAIR10_chr2.fas"
	fetch_raw $urlbase "TAIR10_chr3.fas"
	fetch_raw $urlbase "TAIR10_chr4.fas"
	fetch_raw $urlbase "TAIR10_chr5.fas"
	fetch_raw $urlbase "TAIR10_chrC.fas"
	fetch_raw $urlbase "TAIR10_chrM.fas"

	# Combine all the chromosome files together - this will make the parsing easier
	cat TAIR10_chr* > TAIR10_combined.fas

	# we need to concatenate each file 

	# Grab chromosomal sequences for each of the 18 other strains
	# commented out to make it quicker for testing

	# urlbase="http://mus.well.ox.ac.uk/19genomes/fasta/MASKED/"
	# fetch_raw $urlbase "bur_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "can_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "ct_1.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "edi_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "hi_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "kn_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "ler_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "mt_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "no_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "oy_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "po_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "rsch_4.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "sf_2.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "tsu_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "wil_2.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "ws_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "wu_0.v7.PR_in_lowercase.fas"
	# fetch_raw $urlbase "zu_0.v7.PR_in_lowercase.fas"
}

# Prints aesthetically pleasing messages into the terminal.
function pretty_print() {
	printf "\n-=-=-=-=[ $1 ]=-=-=-=-\n"
    len=${#1} ch='-'
    padding=$(printf '%*s' "$len" | tr ' ' "$ch")
    printf "          $padding\n\n"
}

# Fetch a .bz2 file and extract it
function fetch_extract_gff3() {
	base_sauce_url=$1
	base_filename=$2
	sauce_url="$base_sauce_url$base_filename"

	echo "Processing [$base_filename]..."
	if [ ! -f "$base_filename.gff3" ]
		then
		echo "Fetching..."
		curl "$sauce_url.gff3.bz2" -o "$base_filename.gff3.bz2" >&/dev/null # fetch compressed file
		bunzip2 "$base_filename.gff3.bz2" # decompress to get the .gff3 file
		echo "...Done."
	else
		echo "...Already exists!"
	fi
}

# Fetch a file and save it.
function fetch_raw() {
	base_sauce_url=$1
	base_filename=$2
	sauce_url="$base_sauce_url$base_filename"

	echo "Processing [$base_filename]..."

	if [ ! -f "$base_filename" ] # if file does not exist...
		then
		echo "Fetching..."
		curl "$sauce_url" -o "$base_filename" >&/dev/null
		echo "...Done."
	else
		echo "...Already exists!"
	fi
	
}

# this is only really useful in the production environment
# since we prefer Flask's own web server for development
function install_apache_wsgi() {
	pretty_print "Installing Apache WSGI"
	apt-get install -y apache2
	sudo apt-get install -y libapache2-mod-wsgi
	cp /vagrant/bootstrap/000-default.conf /etc/apache2/sites-available/000-default.conf
	sudo service apache2 restart
}

# get the party started
main