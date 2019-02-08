#!/bin/sh

cd /l_mnt/as14/d/website/ogrdb.airr-community.org/ogre/static/docs
wget -O igpdb.fasta --post-data "paper=0&study=0&type=All&file=true&submit=Download" http://cgi.cse.unsw.edu.au/~ihmmune/IgPdb/download.php
touch ../../ogre.wsgi
