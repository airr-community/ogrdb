# REST services for OGRDB germline sets

from urllib import parse

from flask import Response
from flask_restx import Resource
from sqlalchemy import or_
from api.restplus import api
import json

from db.germline_set_db import GermlineSet
from head import db
from ogrdb.germline_set.to_airr import germline_set_to_airr
from ogrdb.germline_set.descs_to_fasta import descs_to_fasta
from db.species_lookup_db import SpeciesLookup


ns = api.namespace('germline', description='Germline sets available from OGRDB')

@ns.route('/species')
@api.response(404, 'Not found')
class speciesApi(Resource):
    def get(self):
        """ Returns the species for which sequences are available """
        q = db.session.query(GermlineSet.species).filter(or_(GermlineSet.status == 'published', GermlineSet.status == 'superceded')).distinct()
        results = q.all()
        species = [r[0] for r in results] if results else []

        return {
            'species': species
        }


@ns.route('/sets/<species>')
@api.response(404, 'Not found')
class setsApi(Resource):
    def get(self, species):
        """ Returns the available sets for a species """
        q = db.session.query(
                GermlineSet.germline_set_id,
                GermlineSet.germline_set_name,
                GermlineSet.species,
                GermlineSet.species_subgroup,
                GermlineSet.species_subgroup_type,
                GermlineSet.locus
            )\
            .filter(GermlineSet.species == species)\
            .filter(or_(GermlineSet.status == 'published', GermlineSet.status == 'superceded'))\
            .distinct()
        results = q.all()

        return [r._asdict() for r in results] if results else []


@ns.route('/versions/<germline_set_id>')
@api.response(404, 'Not found')
class versionsApi(Resource):
    def get(self, germline_set_id):
        """ Returns the available versions of a set """
        q = db.session.query(
                GermlineSet.release_version,
                GermlineSet.release_date,
                GermlineSet.status
            ) \
            .filter(GermlineSet.germline_set_id == germline_set_id) \
            .filter(or_(GermlineSet.status == 'published', GermlineSet.status == 'superceded'))
        results = q.all()

        return [r._asdict() for r in results] if results else []


@ns.route('/set/<germline_set_id>/<release_version>/<format>')
@ns.route('/set/<germline_set_id>/<release_version>', defaults={'format': None})
@api.response(404, 'Not found')
class versionsApi(Resource):
    def get(self, germline_set_id, release_version, format):
        """ Returns a version of a germline set. Use 'published' for the current published version 
        format can be gapped, ungapped, airr, gapped_ex, ungapped_ex, airr_ex (the _ex suffix specifies the extended 
        set, which should normally be used for AIRR-seq analysis). 
        """

        q = db.session.query(GermlineSet).filter(GermlineSet.germline_set_id == germline_set_id)

        if release_version == 'published' or release_version == 'latest':
            q = q.filter(GermlineSet.status == 'published')
        else:
            q = q.filter(GermlineSet.release_version == release_version)

        germline_set = q.one_or_none()
        if not format:
            format = 'airr_ex' if 'Homo sapiens' in germline_set.species else 'airr'

        if germline_set:
            return download_germline_set_by_id(germline_set.id, format)
        else:
            return {'error': 'Set not found'}, 404


@ns.route('/set/<species>/<set_name>/<release_version>/<format>')
@api.response(404, 'Not found')
class versionsApi(Resource):
    def get(self, species, set_name, release_version, format):
        """ Returns a version of a germline set, specifying the species, species subgroup and set name. 
        Use 'published' for the current published version. Replace any / in the species name or subgroup with %252F.
        format can be gapped, ungapped, airr, gapped_ex, ungapped_ex, airr_ex (the _ex suffix specifies the extended 
        set, which should normally be used for AIRR-seq analysis). 
        """
        return download_set_by_name(species, None, set_name, release_version, format)


@ns.route('/set/<species>/<species_subgroup>/<set_name>/<release_version>/<format>')
@api.response(404, 'Not found')
class versionsApi(Resource):
    def get(self, species, species_subgroup, set_name, release_version, format):
        """ Returns a version of a germline set, specifying the species, species subgroup and set name. 
        Use 'published' for the current published version. Replace any / in the species name or subgroup with %252F.
        format can be gapped, ungapped, airr, gapped_ex, ungapped_ex, airr_ex (the _ex suffix specifies the extended 
        set, which should normally be used for AIRR-seq analysis). 
        """
        return download_set_by_name(species, species_subgroup, set_name, release_version, format)


def download_set_by_name(species, subspecies, germline_set_name, version, format):
    subspecies = parse.unquote(parse.unquote(subspecies)) if subspecies else None
    germline_set_name = parse.unquote(parse.unquote(germline_set_name))

    # check for common species name

    requested_species = species

    q = db.session.query(SpeciesLookup).filter(SpeciesLookup.common == species).one_or_none()
    if q:
        species = q.binomial

    q = db.session.query(
            GermlineSet.id,
        )\
        .filter(GermlineSet.species == species)\
        .distinct()
    
    result = q.all()

    if not result:
        return {'error': 'Species not found'}, 404

    if subspecies:
        q = q.filter(GermlineSet.species_subgroup == subspecies)


    if not result:
        return {'error': 'Subspecies not found'}, 404

    result = q.all()

    q = q.filter(GermlineSet.germline_set_name == germline_set_name)
    
    result = q.all()

    if not result:
        return {'error': 'Germline set name not found'}, 404

    if version == 'published' or version == 'latest':
        q = q.filter(GermlineSet.status == 'published')
    else:
        if not version.isdigit():
            return {'error': 'Invalid release_version'}, 404
        
        q = q.filter(GermlineSet.release_version == int(version))\
            .filter(or_(GermlineSet.status == 'published', GermlineSet.status == 'superceded'))

    result = q.one_or_none()

    if result:
        return download_germline_set_by_id(result[0], format, requested_species)
    else:
        return {'error': 'Germline set version not found'}, 404

def download_germline_set_by_id(germline_set_id, format, use_species_name=None):
    if format not in ['gapped', 'ungapped', 'airr', 'gapped_ex', 'ungapped_ex', 'airr_ex']:
        return {'error': 'invalid format specified'}, 404

    q = db.session.query(GermlineSet).filter(GermlineSet.id == germline_set_id)
    germline_set = q.one_or_none()

    if not germline_set:
        return {'error': 'Set not found'}, 404

    if len(germline_set.gene_descriptions) < 1:
        return {'error': 'No sequences to download'}, 404
    
    extend = False
    if '_ex' in format:
        if 'Homo sapiens' not in germline_set.species:
            return {'error': 'Set not found'}, 404
        extend = True

    species_for_file = use_species_name if use_species_name else germline_set.species
    species_for_file = species_for_file.replace(' ', '_')

    if 'airr' in format:
        taxonomy = db.session.query(SpeciesLookup.ncbi_taxon_id).filter(SpeciesLookup.binomial == germline_set.species).one_or_none()
        taxonomy = taxonomy[0] if taxonomy else 0
        dl = germline_set_to_airr(germline_set, extend, taxonomy)
        dl = json.dumps(dl, indent=4)
        filename = '%s_%s_rev_%d%s.json' % (species_for_file, germline_set.germline_set_name, germline_set.release_version, '_ex' if 'ex' in format else '')
    else:
        dl = descs_to_fasta(germline_set.gene_descriptions, format, fake_allele=True, extend=extend)
        filename = '%s_%s_rev_%d_%s.fasta' % (species_for_file, germline_set.germline_set_name, germline_set.release_version, format)
    
    return Response(dl, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})

