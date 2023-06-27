# REST services for OGRDB germline sets

from flask_restx import Resource
from sqlalchemy import or_
from api.restplus import api
from db.germline_set_db import GermlineSet
from head import db
from ogrdb.germline_set.to_airr import germline_set_to_airr


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


@ns.route('/set/<germline_set_id>/<release_version>')
@api.response(404, 'Not found')
class versionsApi(Resource):
    def get(self, germline_set_id, release_version):
        """ Returns a version of a germline set. Use 'published' for the current published version """
        q = db.session.query(GermlineSet).filter(GermlineSet.germline_set_id == germline_set_id)

        if release_version == 'published':
            q = q.filter(GermlineSet.status == 'published')
        else:
            q = q.filter(GermlineSet.release_version == release_version)

        result = q.one_or_none()

        if result:
            return germline_set_to_airr(result, False)
        else:
            return {'error': 'Set not found'}


