import traceback

from flask_restplus import Api
from app import app
from sqlalchemy.orm.exc import NoResultFound

# Template modelled after https://github.com/postrational/rest_api_demo by Michał Karzyński

api = Api(version='1.0', title='OGRDB API', description='API for OGRDB gene data')

@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occurred.'
    app.logger.log.exception(message)

    if not app.config.FLASK_DEBUG:
        return {'message': message}, 500


@api.errorhandler(NoResultFound)
def database_not_found_error_handler(e):
    app.logger.log.warning(traceback.format_exc())
    return {'message': 'A database result was required but none was found.'}, 404
