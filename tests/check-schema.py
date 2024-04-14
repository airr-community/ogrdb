# check the api schema with pydantic

from openapi_pydantic import OpenAPI
import yaml

x = yaml.safe_load(open('schema/ogrdb-api-openapi3.yaml'))
open_api = OpenAPI.model_validate(x)
