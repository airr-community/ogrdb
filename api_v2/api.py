from flask import Blueprint, jsonify, Response
from pydantic import BaseModel
from api_v2.models import ErrorResponse, ServiceInfoObject, Contact, License, InfoObject, Ontology, GermlineSpeciesResponseItem, \
    GermlineSpeciesResponse, VersionsResponse, GermlineSetResponse, SpeciesSubgroupType, Locus, \
    AlleleDescription, SequenceType, InferenceType, SequenceDelineationV, Strand, UnrearrangedSequence, RearrangedSequence, \
    Derivation, ObservationType, CurationalTag, SpeciesResponse, Acknowledgement
from api_v2.models import GermlineSet as GS
from db.germline_set_db import GermlineSet
from db.species_lookup_db import SpeciesLookup
from head import db
from ogrdb.germline_set.to_airr import germline_set_to_airr
from ogrdb.germline_set.descs_to_fasta import descs_to_fasta
from sqlalchemy import or_
from datetime import datetime
from pydantic.fields import FieldInfo
from typing import Any, Union, get_args, get_origin
from enum import Enum

api_bp = Blueprint('api_v2', __name__)


def encode_germline_set_id(species_id, germline_set_name, species_subgroup, species_subgroup_type):
    """
    Encode a germline set id from its components
    
    Returns:
        germline_set_id
    """
    return f"{species_id}.{germline_set_name.replace('/', '.sl.')}" if species_subgroup_type == 'none' else f"{species_id}.{germline_set_name.replace('/', '.sl.')}.{species_subgroup.replace('/', '.sl.')}"


def parse_germline_set_id(germline_set_id):
    """
    Parse a germline set id from an API call into its components
    
    Returns:
        species_id
        germline_set_name
        species_subgroup
    """
    germline_set_id = germline_set_id.replace('.sl.', '/')
    ids = germline_set_id.split('.')

    if len(ids) < 2 or len(ids) > 3:
        error_response = {'message': "Invalid germline set ID"}
        return jsonify(error_response), 400
    if len(ids) == 2:
        species_id = ids[0]
        germline_set_name = ids[1]
        species_subgroup = None
        
    elif len(ids) == 3:
        species_id = ids[0]
        germline_set_name = ids[1]
        species_subgroup = ids[2]

    return species_id, germline_set_name, species_subgroup
    


@api_bp.route('/', methods=['GET'])
def get_service_status():
    """
    Check the service status.
    
    Returns:
        JSON response indicating the service status.
    """
    try:
        response = {"result": "Service is up."}
        return jsonify(response), 200
    except Exception as e:
        error_response = ErrorResponse(message=str(e))
        return jsonify(error_response), 500
    
@api_bp.route('/info', methods=['GET'])
def get_server_info():
    """
    Get the server information.
    
    Returns:
        JSON response containing server information.
    """
    try:
        # Populate the ServiceInfoObject with actual data
        service_info_obj = create_info_object()
        return jsonify(service_info_obj.model_dump()), 200
    
    except Exception as e:
        error_response = ErrorResponse(message=str(e))
        return jsonify(error_response), 500
    
    
def create_info_object():
    """
    Create the service info object.
    
    Returns:
        ServiceInfoObject containing detailed service information.
    """
    service_info_obj = ServiceInfoObject(
            title="OGRDB API",
            version="2.0.0",
            description="Major Version 2 of the Open Germline Receptor Database (OGRDB) web service application programming interface (API).",
            contact=Contact(
                name="AIRR Community",
                url="http://ogrdb.airr-community.org/",
                email="join@airr-community.org"
            ),
            license=License(
                name="European Union Public License version 1.2",
                url="https://perma.cc/DK5U-NDVE"
            ),
            api=InfoObject(
                title="OGRDB API Detailed",
                version="2.0.0"
            ),
            schema=InfoObject(
                title="OGRDB API Schema",
                version="2.0.0"
            )
        )
    
    return service_info_obj

@api_bp.route('/germline/species', methods=['GET'])
def get_germline_species():
    """ Returns the species for which sequences are available """
    try: 
        q = db.session.query(GermlineSet.species).filter(or_(GermlineSet.status == 'published', GermlineSet.status == 'superceded')).distinct()
        results = q.all()
        species = [r[0] for r in results] if results else []
        species_list = []
        for species_name in species:
            id = db.session.query(SpeciesLookup.ncbi_taxon_id).filter(SpeciesLookup.binomial == species_name).one_or_none()
            id = str(id[0]) if id else ""
            ontology_obj = Ontology(label=species_name, id=id)
            species_list.append(ontology_obj)

        species_response_obj = SpeciesResponse(species=species_list)
        
        return jsonify(species_response_obj.model_dump()), 200  # Converting directly to JSON and returning a 200 status

    except Exception as e: 
        error_response = {'message': str(e)}  # Ensure you have a way to serialize error responses
        return jsonify(error_response), 500


@api_bp.route('/germline/sets/<species_id>', methods=['GET'])
def get_germline_sets_by_id(species_id):
    """
    Get the available sets for a species by ID.
    
    Args:
        species_id: The ID of the species.
    
    Returns:
        JSON response containing the list of germline sets for the species.
    """
    try:
        """ Returns the available sets for a species """

        species = db.session.query(SpeciesLookup.binomial).filter(SpeciesLookup.ncbi_taxon_id == species_id).one_or_none()

        if not species:
            error_response = {'message': "Invalid species ID"}  
            return jsonify(error_response), 400
        else:
            species = species[0]

        q = db.session.query(
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

        included_sets = []
        germline_sets_list = []
        for r in results:
            ontology_obj = Ontology(label=r.species, id=str(species_id))
            germline_set_id = encode_germline_set_id(species_id, r.germline_set_name, r.species_subgroup, r.species_subgroup_type)

            if germline_set_id in included_sets:
                continue        # this works around the fact that species_subgroup can be either '' or None when there is no subgroup

            germline_sets_list.append(
                GermlineSpeciesResponseItem(
                    germline_set_id=germline_set_id,
                    germline_set_name=r.germline_set_name,
                    species=ontology_obj,
                    species_subgroup=r.species_subgroup, 
                    species_subgroup_type=r.species_subgroup_type, 
                    locus=r.locus
                )
            )
            included_sets.append(germline_set_id)

        if germline_sets_list:
            species_response_obj = GermlineSpeciesResponse(germline_species=germline_sets_list)

            return jsonify(species_response_obj.model_dump()), 200  # Converting directly to JSON and returning a 200 status

        else:
            error_response = {'message': "Invalid request"}  
            return jsonify(error_response), 400

    except Exception as e:
        error_response = {'message': str(e)}
        return jsonify(error_response), 500


@api_bp.route('/germline/set/<germline_set_id>/<release_version>/<format>')
@api_bp.route('/germline/set/<germline_set_id>/<release_version>', defaults={'format': None}, methods=['GET'])
def get_germline_sets_by_id_and_version(germline_set_id, release_version, format):
    """
    Get a version of a germline set by ID and release version.
    
    Args:
        germline_set_id: The ID of the germline set.
        release_version: The release version of the germline set.
    
    Returns:
        Response containing the germline set in the specified format.
    """
    try:
        species_id, germline_set_name, species_subgroup = parse_germline_set_id(germline_set_id)
        species = db.session.query(SpeciesLookup.binomial).filter(SpeciesLookup.ncbi_taxon_id == species_id).one_or_none()[0]

        q = db.session.query(GermlineSet) \
            .filter(GermlineSet.species == species) \
            .filter(GermlineSet.germline_set_name == germline_set_name)
        
        if species_subgroup:
            q = q.filter(GermlineSet.species_subgroup == species_subgroup)

        if release_version == 'published' or release_version == 'latest':
            q = q.filter(GermlineSet.status == 'published')
        else:
            q = q.filter(GermlineSet.release_version == release_version)

        germline_set = q.one_or_none()

        if not germline_set:
            error_response = {'message': "Set not found"}
            return jsonify(error_response), 404

        if not format:
            format = 'airr_ex' if 'Homo sapiens' in germline_set.species else 'airr'

        if germline_set:
            res = download_germline_set_by_id(germline_set.id, format)
            return res

        else:
            error_response = {'message': str(e)}
            return jsonify(error_response), 500
    
    except Exception as e:
        error_response = {'message': str(e)}
        return jsonify(error_response), 500



@api_bp.route('/germline/set/<germline_set_id>/versions', methods=['GET'])
def list_all_versions_of_germline_set(germline_set_id):
    try:
        species_id, germline_set_name, species_subgroup = parse_germline_set_id(germline_set_id)
        species = db.session.query(SpeciesLookup.binomial).filter(SpeciesLookup.ncbi_taxon_id == species_id).one_or_none()[0]

        q = db.session.query(GermlineSet) \
            .filter(GermlineSet.species == species) \
            .filter(GermlineSet.germline_set_name == germline_set_name)
        
        if species_subgroup:
            q = q.filter(GermlineSet.species_subgroup == species_subgroup)

        q = q.all()

        # Base query to filter by germline_set_id
        versions_list = []

        for germline_set in q:
            versions_list.append(germline_set.release_version)

        response = VersionsResponse(versions=versions_list)
        return jsonify(response.model_dump()), 200

    except Exception as e:
        error_response = {'message': str(e)}
        return jsonify(error_response), 500


def download_germline_set_by_id(germline_set_id, format):
    """
    Download a germline set by ID and format.

    Args:
        germline_set_id: The ID of the germline set.
        format: The format of the germline set (e.g., gapped, ungapped, airr).

    Returns:
        Response containing the germline set data.
    """
    if format not in ['gapped', 'ungapped', 'airr', 'gapped_ex', 'ungapped_ex', 'airr_ex']:
        return {'error': 'invalid format specified'}, 400

    q = db.session.query(GermlineSet).filter(GermlineSet.id == germline_set_id)
    germline_set = q.one_or_none()

    if not germline_set:
        return {'error': 'Set not found'}, 400

    if len(germline_set.gene_descriptions) < 1:
        return {'error': 'No sequences to download'}, 400

    extend = False
    if '_ex' in format:
        if 'Homo sapiens' not in germline_set.species:
            return {'error': 'Set not found'}, 400
        extend = True

    if 'airr' in format:
        taxonomy = db.session.query(SpeciesLookup.ncbi_taxon_id).filter(SpeciesLookup.binomial == germline_set.species).one_or_none()
        taxonomy = taxonomy[0] if taxonomy else 0

        dl = germline_set_to_airr(germline_set, extend, taxonomy)

        try:
            germline_set_response = convert_to_GermlineSetResponse_obj(dl)
            germline_set_response = germline_set_response.model_dump_json(by_alias=True)  # Convert the object to a dictionary
        except Exception as e:
            return {'message': f'Error constructing response: {e}'}, 500
        
        filename = '%s_%s_rev_%d%s.json' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, '_ex' if 'ex' in format else '')

    else:
        dl = descs_to_fasta(germline_set.gene_descriptions, format, fake_allele=True, extend=extend)
        filename = '%s_%s_rev_%d_%s.fasta' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, format)
        germline_set_response = dl

    return Response(germline_set_response, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})


def convert_to_GermlineSetResponse_obj(dl):
    """
    Convert the downloaded germline set data to a GermlineSetResponse object.

    Args:
        dl: The downloaded germline set data.

    Returns:
        GermlineSetResponse object.
    """
    service_info_obj = create_info_object()
    germline_set_list = []

    for i in range(len(dl["GermlineSet"])):

        temp_dl = fill_missing_required_fields(GS,  dl["GermlineSet"][i])  # Fill missing fields

        germline_set = GS(
            germline_set_id=temp_dl['germline_set_id'],
            author=temp_dl['author'],
            lab_name=temp_dl['lab_name'],
            lab_address=temp_dl['lab_address'],
            acknowledgements=create_acknowledgements_list(temp_dl['acknowledgements']),
            release_version=temp_dl['release_version'],
            release_description=temp_dl['release_description'],
            release_date=datetime.strptime(temp_dl['release_date'], '%Y-%m-%d'),
            germline_set_name=temp_dl['germline_set_name'],
            germline_set_ref=temp_dl['germline_set_ref'],
            pub_ids=temp_dl['pub_ids'],
            species=Ontology(id=temp_dl['species']['id'], label=temp_dl['species']['label']),
            species_subgroup=temp_dl['species_subgroup'],
            species_subgroup_type=temp_dl['species_subgroup_type'],
            locus=Locus(temp_dl['locus']),
            allele_descriptions=create_allele_description_list(temp_dl['allele_descriptions']),
            curation=temp_dl.get('curation', None)
        )
        germline_set_list.append(germline_set)

    germline_set_response = GermlineSetResponse(Info=service_info_obj, GermlineSet=germline_set_list)

    return germline_set_response


'''
keep this one for MiAIRR v2.x
def create_acknowledgements_list(acknowledgements):
    """
    Create a list of Contributors from OGRDB's acknowledgements data.

    """
    acknowledgements_list = []

    if acknowledgements is not None:
        for acknowledgement in acknowledgements:
            acknowledgement['contributor_id'] = acknowledgement['acknowledgement_id']
            acknowledgement['orcid_id'] = acknowledgement['ORCID_id'] if 'ORCID_id' in acknowledgement else None
            temp_contributor = fill_missing_required_fields(Contributor, acknowledgement)
            # can't see we can do much with institution names, so just ignore it for now

            contributor_obj = Contributor(
                acknowledgement_id=temp_contributor['acknowledgement_id'],
                name=temp_contributor['name'],
                orcid_id=temp_contributor['orcid_id']
            )
            acknowledgements_list.append(contributor_obj)

    return acknowledgements_list if len(acknowledgements_list) > 0 else None
'''


def create_acknowledgements_list(acknowledgements):
    """
    Create a list of acknowledgements from the given data.

    Args:
        acknowledgements: The list of acknowledgements data.

    Returns:
        List of Acknowledgement objects.
    """
    acknowledgements_list = []

    if acknowledgements is not None:
        for i in range(len(acknowledgements)):
            temp_acknowledgement = fill_missing_required_fields(Acknowledgement, acknowledgements[i])
            acknowledgement_obj = Acknowledgement(
                acknowledgement_id=temp_acknowledgement['acknowledgement_id'],
                name=temp_acknowledgement['name'],
                institution_name=temp_acknowledgement['institution_name'],
                orcid_id=temp_acknowledgement['ORCID_id']
            )
            acknowledgements_list.append(acknowledgement_obj)

    return acknowledgements_list if len(acknowledgements_list) > 0 else None


# Convert enum to snake case
def enum_to_snake_case(name):
    if name is not None:
        if name == 'None':
            return None
        return name.replace(' ', '_').lower()
    return None


def create_allele_description_list(allele_descriptions):
    """
    Create a list of allele descriptions from the given data.
    
    Args:
        allele_descriptions: The list of allele descriptions data.
    
    Returns:
        List of AlleleDescription objects.
    """
    allele_description_list = []

    for i in range(len(allele_descriptions)):
        temp_allele_descriptions = fill_missing_required_fields(AlleleDescription, allele_descriptions[i])
        temp_allele_descriptions['inference_type'] = enum_to_snake_case(temp_allele_descriptions['inference_type'])
        allele_description_obj = AlleleDescription(
            allele_description_id=temp_allele_descriptions['allele_description_id'],
            allele_description_ref=temp_allele_descriptions['allele_description_ref'],
            maintainer=temp_allele_descriptions['maintainer'],
            acknowledgements=create_acknowledgements_list(temp_allele_descriptions['acknowledgements']),
            lab_address=temp_allele_descriptions['lab_address'],
            release_version=temp_allele_descriptions['release_version'],
            release_date=datetime.strptime(temp_allele_descriptions['release_date'], '%d-%b-%Y'),
            release_description=temp_allele_descriptions['release_description'],
            label=temp_allele_descriptions['label'],
            sequence=temp_allele_descriptions['sequence'],
            coding_sequence=temp_allele_descriptions['coding_sequence'],
            aliases=temp_allele_descriptions['aliases'],
            locus=Locus(temp_allele_descriptions['locus']),
            chromosome=temp_allele_descriptions['chromosome'],
            sequence_type=SequenceType(temp_allele_descriptions['sequence_type']),
            functional=temp_allele_descriptions['functional'],
            inference_type=InferenceType(temp_allele_descriptions['inference_type']),
            species=Ontology(id=temp_allele_descriptions['species']['id'], label=temp_allele_descriptions['species']['label']),
            species_subgroup=temp_allele_descriptions['species_subgroup'],
            species_subgroup_type=temp_allele_descriptions['species_subgroup_type'],
            subgroup_designation=temp_allele_descriptions['subgroup_designation'],
            gene_designation=temp_allele_descriptions['gene_designation'],
            allele_designation=temp_allele_descriptions['allele_designation'],
            j_codon_frame=temp_allele_descriptions.get('j_codon_frame', None),
            gene_start=temp_allele_descriptions['gene_start'],
            gene_end=temp_allele_descriptions['gene_end'],
            utr_5_prime_start=temp_allele_descriptions.get('utr_5_prime_start', None),
            utr_5_prime_end=temp_allele_descriptions.get('utr_5_prime_end', None),
            leader_1_start=temp_allele_descriptions.get('leader_1_start', None),
            leader_1_end=temp_allele_descriptions.get('leader_1_end', None),
            leader_2_start=temp_allele_descriptions.get('leader_2_start', None),
            leader_2_end=temp_allele_descriptions.get('leader_2_end', None),
            v_rs_start=temp_allele_descriptions.get('v_rs_start', None),
            v_rs_end=temp_allele_descriptions.get('v_rs_end', None),
            d_rs_3_prime_start=temp_allele_descriptions.get('d_rs_3_prime_start', None),
            d_rs_3_prime_end=temp_allele_descriptions.get('d_rs_3_prime_end', None),
            d_rs_5_prime_start=temp_allele_descriptions.get('d_rs_5_prime_start', None),
            d_rs_5_prime_end=temp_allele_descriptions.get('d_rs_5_prime_end', None),
            j_cdr3_end=temp_allele_descriptions.get('j_cdr3_end', None),
            j_rs_start=temp_allele_descriptions.get('j_rs_start', None),
            j_rs_end=temp_allele_descriptions.get('j_rs_end', None),
            j_donor_splice=temp_allele_descriptions.get('j_donor_splice', None),
            v_gene_delineations=create_sequence_delineationV_list(temp_allele_descriptions.get('v_gene_delineations', None)),
            unrearranged_support=create_unrearranged_support_list(temp_allele_descriptions['unrearranged_support'], temp_allele_descriptions['curation']),
            rearranged_support=create_rearranged_support_list(temp_allele_descriptions['rearranged_support'], temp_allele_descriptions['curation']),
            paralogs=temp_allele_descriptions['paralogs'],
            curation=temp_allele_descriptions['curation'],
            curational_tags=create_curational_tags_list(temp_allele_descriptions['curational_tags'])
        )
        allele_description_list.append(allele_description_obj)

    return allele_description_list


def create_sequence_delineationV_list(v_gene_delineations):
    """
    Create a list of sequence delineations from the given data.
    
    Args:
        v_gene_delineations: The list of sequence delineations data.
    
    Returns:
        List of SequenceDelineationV objects.
    """
    sequence_delineationV_list = []

    if v_gene_delineations is not None:
        for i in range(len(v_gene_delineations)):
            temp_v_gene_delineations = fill_missing_required_fields(SequenceDelineationV, v_gene_delineations[i])
            sequence_delineationV_obj = SequenceDelineationV(
                sequence_delineation_id=temp_v_gene_delineations['sequence_delineation_id'],
                delineation_scheme=temp_v_gene_delineations['delineation_scheme'],
                fwr1_start=temp_v_gene_delineations['fwr1_start'] if temp_v_gene_delineations['fwr1_start'] is not None else 0,
                fwr1_end=temp_v_gene_delineations['fwr1_end'] if temp_v_gene_delineations['fwr1_end'] is not None else 0,
                cdr1_start=temp_v_gene_delineations['cdr1_start'] if temp_v_gene_delineations['cdr1_start'] is not None else 0,
                cdr1_end=temp_v_gene_delineations['cdr1_end'] if temp_v_gene_delineations['cdr1_end'] is not None else 0,
                fwr2_start=temp_v_gene_delineations['fwr2_start'] if temp_v_gene_delineations['fwr2_start'] is not None else 0,
                fwr2_end=temp_v_gene_delineations['fwr2_end'] if temp_v_gene_delineations['fwr2_end'] is not None else 0,
                cdr2_start=temp_v_gene_delineations['cdr2_start'] if temp_v_gene_delineations['cdr2_start'] is not None else 0,
                cdr2_end=temp_v_gene_delineations['cdr2_end'] if temp_v_gene_delineations['cdr2_end'] is not None else 0,
                fwr3_start=temp_v_gene_delineations['fwr3_start'] if temp_v_gene_delineations['fwr3_start'] is not None else 0,
                fwr3_end=temp_v_gene_delineations['fwr3_end'] if temp_v_gene_delineations['fwr3_end'] is not None else 0,
                cdr3_start=temp_v_gene_delineations['cdr3_start'] if temp_v_gene_delineations['cdr3_start'] is not None else 0,
                alignment=temp_v_gene_delineations['alignment_labels']
            )
            sequence_delineationV_list.append(sequence_delineationV_obj)

    else:
        return None

    return sequence_delineationV_list


def create_unrearranged_support_list(unrearranged_support, curation):
    """
    Create a list of unrearranged support sequences from the given data.
    
    Args:
        unrearranged_support: The list of unrearranged support sequences data.
        curation: The curation data.
    
    Returns:
        List of UnrearrangedSequence objects.
    """
    unrearranged_support_list = []

    if unrearranged_support is not None:
        for i in range(len(unrearranged_support)):
            temp_unrearranged_support = fill_missing_required_fields(UnrearrangedSequence, unrearranged_support[i])
            unrearranged_sequence_obj = UnrearrangedSequence(
                sequence_id=temp_unrearranged_support['sequence_id'],
                sequence=temp_unrearranged_support['sequence'],
                curation=curation,
                repository_name=temp_unrearranged_support['repository_name'],
                repository_ref=temp_unrearranged_support['repository_ref'],
                patch_no=temp_unrearranged_support['patch_no'],
                gff_seqid=temp_unrearranged_support['gff_seqid'] if temp_unrearranged_support['gff_seqid'] is not None else "",
                gff_start=temp_unrearranged_support['gff_start'],
                gff_end=temp_unrearranged_support['gff_end'],
                strand=Strand(temp_unrearranged_support['strand']) if temp_unrearranged_support['strand'] is not None else '+'
            )
            unrearranged_support_list.append(unrearranged_sequence_obj)

    return unrearranged_support_list


def create_rearranged_support_list(rearranged_support, curation):
    """
    Create a list of rearranged support sequences from the given data.
    
    Args:
        rearranged_support: The list of rearranged support sequences data.
        curation: The curation data.
    
    Returns:
        List of RearrangedSequence objects.
    """
    rearranged_support_list = []

    if rearranged_support is not None:
        for i in range(len(rearranged_support)):
            temp_rearranged_support = fill_missing_required_fields(RearrangedSequence, rearranged_support[i])
            rearranged_sequence_obj = RearrangedSequence(
                sequence_id=temp_rearranged_support['sequence_id'],
                sequence=temp_rearranged_support['sequence'],
                derivation=Derivation(temp_rearranged_support['derivation']) if temp_rearranged_support['derivation'] is not None else None,
                observation_type=ObservationType(enum_to_snake_case(temp_rearranged_support['observation_type'])) if temp_rearranged_support['observation_type'] is not None else None,
                curation=curation,
                repository_name=temp_rearranged_support['repository_name'],
                repository_ref=temp_rearranged_support['repository_ref'],
                deposited_version=temp_rearranged_support['deposited_version'],
                sequence_start=temp_rearranged_support['sequence_start'],
                sequence_end=temp_rearranged_support['sequence_end'],
                )
            
            rearranged_support_list.append(rearranged_sequence_obj)

    return rearranged_support_list


def create_curational_tags_list(curational_tags):
    """
    Create a list of curational tags from the given data.
    
    Args:
        curational_tags: The list of curational tags data.
    
    Returns:
        List of CurationalTag objects.
    """
    curational_tags_list = None

    if curational_tags is not None: 
        curational_tags = [x for x in curational_tags if x is not None]
        if len(curational_tags) > 0:
            curational_tags_list = []
            for i in range(len(curational_tags)):
                curational_tag_obj = CurationalTag(curational_tags[i])
                curational_tags_list.append(curational_tag_obj)

    return curational_tags_list


def get_default_value(field_type: Any) -> Any:
    """
    Get the default value for a given field type.
    
    Args:
        field_type: The type of the field.
    
    Returns:
        The default value for the field type.
    """
    if get_origin(field_type) is Union:
        args = get_args(field_type)
        field_type = args[0] if args[1] is type(None) else args[1]

    if field_type == 'int':
        return 0
    elif field_type == 'float':
        return 0.0
    elif field_type == 'str':
        return ""
    elif field_type == 'bool':
        return False
    elif field_type == 'list':
        return []
    elif field_type == 'dict':
        return {}
    elif field_type == 'datetime':
        return datetime.now()
    else:
        if issubclass(globals()[field_type], Enum):
            # Get the first value of the Enum
            return next(iter(globals()[field_type])).value

    return None


def fill_missing_required_fields(model_cls: type[BaseModel], data: dict) -> dict:
    """
    Fill missing required fields in the given data with default values.
    
    Args:
        model_cls: The Pydantic model class.
        data: The data dictionary.
    
    Returns:
        The data dictionary with missing required fields filled.
    """
    filled_data = data.copy()

    for field_name, field_info in model_cls.model_fields.items():
        if field_name in data and data[field_name] is None:
            if is_required(field_info):
                field_type = model_cls.__annotations__[field_name]
                if field_type.startswith('Optional'):
                    continue
                default_value = get_default_value(field_type)
                if default_value is not None:
                    filled_data[field_name] = default_value

    return filled_data


def is_required(field_info: FieldInfo) -> bool:
    """
    Check if a field is required.
    
    Args:
        field_info: The field information.
    
    Returns:
        Boolean indicating if the field is required.
    """
    if 'required=True' in str(field_info):
        return True
    
    return False