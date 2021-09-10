# REST services for OGRDB

from flask import request
from flask_restx import Resource, reqparse, fields, marshal, inputs
from api.restplus import api
from db.gene_description_db import make_GeneDescription_view
from werkzeug.exceptions import BadRequest
from imgt.imgt_ref import get_imgt_reference_genes, get_igpdb_ref, get_vdjbase_ref, get_reference_v_codon_usage, find_family, get_imgt_gapped_reference_genes, find_gapped_index, gap_sequence
from app import db
from db.misc_db import Committee
from db.gene_description_db import GeneDescription
from datetime import datetime


ns = api.namespace('sequence', description='Sequences corresponding to IMGT- or IARC- issued names')

@ns.route('/species')
@api.response(404, 'Not found')
class speciesApi(Resource):
    def get(self):
        """ Returns the species for which sequences are available """
        imgt_ref = get_imgt_reference_genes()

        return {
            'species': list(imgt_ref.keys())
        }


@ns.route('/imgt_name/<string:species>/<string:name>')
@api.response(404, 'Not found')
class imgtNameApi(Resource):
    def get(self, species, name):
        """ Returns the sequence given the IMGT name """
        imgt_ref = get_imgt_reference_genes()
        imgt_ref_gapped = get_imgt_gapped_reference_genes()

        if species in imgt_ref and name in imgt_ref[species]:
            ungapped = str(imgt_ref[species][name])
            gapped = str(imgt_ref_gapped[species][name])

            return {
                'species': species,
                'imgt_name': name,
                'sequence': ungapped,
                'coding_seq_imgt': gapped
            }
        else:
            return 'Not found', 404

@ns.route('/iarc/<string:species>')
@api.response(404, 'Not found')
class iarcSetApi(Resource):
    def descs_to_airr(self, descs):
        ret = {}
        for desc in descs:
            name = desc.sequence_name
            if desc.imgt_name != '':
                name += '|' + desc.imgt_name
            d = make_GeneDescription_view(desc)
            ret[desc.sequence_name] = {}
            for row in d.items:
                if isinstance(row['value'], datetime):
                    row['value'] = row['value'].date().isoformat()
                ret[desc.sequence_name][row['field']] = row['value']

        return ret

    def get(self, species):
        """ Returns the set of IARC-affirmed sequences for the species """
        imgt_ref = get_imgt_reference_genes()

        if species not in imgt_ref:
            return 'Not found', 404

        all_species = db.session.query(Committee.species).all()
        all_species = [s[0] for s in all_species]
        if species not in all_species:
            return []

        q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.affirmation_level != '0', GeneDescription.species == species)
        results = q.all()

        dl = self.descs_to_airr(results)
        return dl
