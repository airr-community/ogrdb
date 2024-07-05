# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#
import logging
from os.path import isdir
from os import mkdir

from flask import Blueprint, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint

import head
head.create_app()
from head import app, mail, security
import yaml

# Check log file can be opened for writing, default otherwise

try:
    with(open(app.config["LOGPATH"], 'w')) as fp:
        pass
except:
    app.config["LOGPATH"] = 'app.log'

# Make the attachment directory, if it doesn't exist

attach_path = app.config['ATTACHPATH'] + '/'
head.attach_path = attach_path
if not isdir(attach_path):
    mkdir(attach_path)


from flask_babel import Babel
babel = Babel(app)


from forms.useradmin import *
from forms.security import *
from genotype_stats import *

from ogrdb.index.index_routes import *

from custom_logging import init_logging
init_logging(app, mail)

# Read IMGT germline reference sets

from imgt.imgt_ref import init_imgt_ref, init_igpdb_ref
from db.vdjbase import init_vdjbase_ref

init_imgt_ref()
init_igpdb_ref()
init_vdjbase_ref()

# Initialise REST API

from api.restplus import api
from api.sequence.sequence import ns as sequence
from api.sequence.germline import ns as germline

blueprint = Blueprint('api', __name__, url_prefix='/api')
api.init_app(blueprint)
api.add_namespace(sequence)
api.add_namespace(germline)
app.register_blueprint(blueprint)

#Initialise New API
from api_v1.api import api_bp
app.register_blueprint(api_bp, url_prefix='/api_v2')

SWAGGER_URL = '/api_v2/swagger'
API_URL = '/schema/ogrdb-api-openapi3.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "OGRDB API v1"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

with open('schema/ogrdb-api-openapi3.yaml', 'r') as f:
    openapi_schema = yaml.safe_load(f)

# Serve static files (Swagger YAML)
@app.route('/schema/<path:path>', methods=['GET'])
def serve_static(path):
    return send_from_directory('schema', path)


# Database classes are declared here to resolve dependence issues

from db.submission_db import *
from db.repertoire_db import *
from db.inference_tool_db import *
from db.genotype_db import *
from db.genotype_description_db import *
from db.inferred_sequence_db import *
from db.journal_entry_db import *
from db.notes_entry_db import *
from db.germline_set_db import *
from db.gene_description_db import *
from db.primer_set_db import *
from db.primer_db import *
from db.record_set_db import *
from db.sample_name_db import *
from db.attached_file_db import *
from db.dupe_gene_note_db import *
from db.novel_vdjbase_db import *
from db.vdjbase import *
from db.species_lookup import *

# All routes are imported here. No routes are imported in subsidiary files
# in order to avoid circularity between imports

from ogrdb.submission.submission_routes import *
from ogrdb.submission.inferred_sequence_routes import *
from ogrdb.submission.genotype_description_routes import *
from ogrdb.submission.genotype_routes import *
from ogrdb.submission.inference_tool_routes import *
from ogrdb.submission.inferred_sequence_routes import *
from ogrdb.submission.primer_set_routes import *
from ogrdb.submission.submission_from_vdjbase import *

from ogrdb.sequence.sequence_routes import *
from ogrdb.germline_set.germline_set_routes import *
from ogrdb.vdjbase.vdjbase_routes import *
from ogrdb.maint.maint_routes import *
from ogrdb.genotype_stats.genotype_stats_routes import *


