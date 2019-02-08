#!/bin/sh

source /etc/profile.d/modules.sh
module load python3

cd /l_mnt/as14/d/website/ogrdb.airr-community.org/ogre
python imgt/track_imgt_ref.py imgt/track_imgt_config.yaml

