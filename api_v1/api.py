from flask import Blueprint, request, jsonify, Response
from pydantic import BaseModel, ValidationError
from api_v1.models import *
from api_v1.models import GermlineSet as GS
import json
from db.germline_set_db import GermlineSet
from head import db
from ogrdb.germline_set.to_airr import germline_set_to_airr
from ogrdb.germline_set.descs_to_fasta import descs_to_fasta
from sqlalchemy import or_
from datetime import datetime

api_bp = Blueprint('api_v1', __name__)

@api_bp.route('/', methods=['GET'])
def get_service_status():
    try:
        response = {"result": "Service is up."}
        return jsonify(response), 200
    except Exception as e:
        error_response = ErrorResponse(message=str(e))
        return jsonify(error_response), 500
    
@api_bp.route('/info', methods=['GET'])
def get_server_info():
    try:
        # Populate the ServiceInfoObject with actual data
        service_info_obj = create_info_object()
        return jsonify(service_info_obj.model_dump()), 200
    
    except Exception as e:
        error_response = ErrorResponse(message=str(e))
        return jsonify(error_response), 500
    
def create_info_object():
    service_info_obj = ServiceInfoObject(
            title="OGRDB API",
            version="1.0.0",
            description="Major Version 1 of the Open Germline Receptor Database (OGRDB) web service application programming interface (API).",
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
                version="1.0.0"
            ),
            schema=InfoObject(
                title="OGRDB API Schema",
                version="1.0.0"
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
            # Assuming that you might have other fields to include, add them as necessary
            ontology_obj = Ontology(label = species_name)
            species_list.append(ontology_obj)

        species_response_obj = SpeciesResponse(species=species_list)
        
        return jsonify(species_response_obj.model_dump()), 200  # Converting directly to JSON and returning a 200 status

    except Exception as e: 
        error_response = {'message': str(e)}  # Ensure you have a way to serialize error responses
        return jsonify(error_response), 500


    
    
@api_bp.route('/germline/sets/<species_id>', methods=['GET'])
def get_germline_sets_by_id(species_id):
    try:
        """ Returns the available sets for a species """
        q = db.session.query(
                GermlineSet.germline_set_id,
                GermlineSet.germline_set_name,
                GermlineSet.species,
                GermlineSet.species_subgroup,
                GermlineSet.species_subgroup_type,
                GermlineSet.locus
            )\
            .filter(GermlineSet.species == species_id)\
            .filter(or_(GermlineSet.status == 'published', GermlineSet.status == 'superceded'))\
            .distinct()
        results = q.all()

        germline_sets_list = []
        for r in results:
            ontology_obj = Ontology(label = r.species)
            germline_sets_list.append(GermlineSpeciesResponseItem(germline_set_id= r.germline_set_id , germline_set_name= r.germline_set_name ,species= ontology_obj,
                                        species_subgroup=r.species_subgroup , species_subgroup_type=r.species_subgroup_type , locus=r.locus))
        
        if germline_sets_list:
            species_response_obj = GermlineSpeciesResponse(germline_species=germline_sets_list)
            
            return jsonify(species_response_obj.model_dump()), 200  # Converting directly to JSON and returning a 200 status
        
        else:
            error_response = {'message': "Invalid request"}  
            return jsonify(error_response), 400
    
    except Exception as e:
        error_response = {'message': str(e)}  
        return jsonify(error_response), 500


@api_bp.route('/germline/sets/<germline_set_id>/<release_version>', methods=['GET'])
def get_germline_sets_by_id_and_version(germline_set_id, release_version):
    try:
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
        
        format = 'airr_ex' if 'Human' in germline_set.species else 'airr'

        if germline_set:
            res = download_germline_set_by_id(germline_set.id, format)
            return res

        else:
            error_response = {'message': str(e)}  
            return jsonify(error_response), 500
    
    except Exception as e:
        error_response = {'message': str(e)}  
        return jsonify(error_response), 500
        

def download_germline_set_by_id(germline_set_id, format):
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
        if 'Human' not in germline_set.species:
            return {'error': 'Set not found'}, 400
        extend = True

    if 'airr' in format:
        dl = germline_set_to_airr(germline_set, extend)
        res = convert_to_GermlineSetResponse_obj(dl)
        dl = json.dumps(dl, indent=4)
        filename = '%s_%s_rev_%d%s.json' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, '_ex' if 'ex' in format else '')
    else:
        dl = descs_to_fasta(germline_set.gene_descriptions, format, fake_allele=True, extend=extend)
        filename = '%s_%s_rev_%d_%s.fasta' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, format)
    
    return Response(dl, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})
  
def convert_to_GermlineSetResponse_obj(dl):
    service_info_obj = create_info_object()
    germline_set_list = []
    try:
        for i in range(len(dl["GermlineSet"])):
            temp = dl["GermlineSet"][i]
            germiline_set = GS(
                germline_set_id = temp['germline_set_id'],
                author = temp['author'],
                lab_name = temp['lab_name'],
                lab_address = temp['lab_address'],
                #acknowledgements = , dont know
                release_version = temp['release_version'],
                release_description = temp['release_description'],
                release_date = datetime.strptime(temp['release_date'], '%Y-%m-%d'),
                germline_set_name = temp['germline_set_name'],
                germline_set_ref = temp['germline_set_ref'],
                pub_ids = temp['pub_ids'],
                species = Ontology(id = temp['species']['id'], label = temp['species']['label']),
                species_subgroup = temp ['species_subgroup'],
                species_subgroup_type = SpeciesSubgroupType(temp['species_subgroup_type']) if temp['species_subgroup_type'] is not None else None,
                locus = Locus(temp['locus']),
                allele_descriptions = create_allele_description_list(temp['allele_descriptions']),
                #curation = temp['curation'], there is more than one 

            )
            germline_set_list.append(germiline_set)

    except Exception as e:
        pass

    germline_set_response = GermlineSetResponse(Info = service_info_obj, GermlineSet = germline_set_list)

def create_allele_description_list(allele_descriptions):
    allele_description_list = []

    for i in range(len(allele_descriptions)):
        allele_description_obj = AlleleDescription(
            allele_description_id = allele_descriptions[i]['allele_description_id'],
            allele_description_ref = allele_descriptions[i]['allele_description_ref'],
            maintainer = allele_descriptions[i]['maintainer'],
            #acknowledgements dont know which one
            lab_address = allele_descriptions[i]['lab_address'],
            release_version = allele_descriptions[i]['release_version'],
            release_date = datetime.strptime(allele_descriptions[i]['release_date'], '%d-%b-%Y'),
            release_description = allele_descriptions[i]['release_description'],
            label = allele_descriptions[i]['label'],
            sequence = allele_descriptions[i]['sequence'],
            coding_sequence = allele_descriptions[i]['coding_sequence'],
            aliases = allele_descriptions[i]['aliases'],
            locus = Locus(allele_descriptions[i]['locus']),
            chromosome = allele_descriptions[i]['chromosome'],
            sequence_type = SequenceType(allele_descriptions[i]['sequence_type']),
            functional = allele_descriptions[i]['functional'],
            inference_type = InferenceType(allele_descriptions[i]['inference_type']),
            species = Ontology(id = allele_descriptions[i]['species']['id'], label = allele_descriptions[i]['species']['label']),
            species_subgroup = allele_descriptions[i]['species_subgroup'],
            species_subgroup_type = SpeciesSubgroupType(allele_descriptions[i]['species_subgroup_type']) if allele_descriptions[i]['species_subgroup_type'] is not None else None,
            subgroup_designation = allele_descriptions[i]['subgroup_designation'],
            gene_designation = allele_descriptions[i]['gene_designation'],
            allele_designation = allele_descriptions[i]['allele_designation'],
            #j_codon_frame dont know which one
            gene_start = allele_descriptions[i]['gene_start'],
            gene_end = allele_descriptions[i]['gene_end'],
            utr_5_prime_start = allele_descriptions[i].get('utr_5_prime_start', None),
            utr_5_prime_end = allele_descriptions[i].get('utr_5_prime_end', None),
            leader_1_start = allele_descriptions[i].get('leader_1_start', None),
            leader_1_end = allele_descriptions[i].get('leader_1_end',None),
            leader_2_start = allele_descriptions[i].get('leader_2_start',None),
            leader_2_end = allele_descriptions[i].get('leader_2_end',None),
            v_rs_start = allele_descriptions[i].get('v_rs_start',None),
            v_rs_end = allele_descriptions[i].get('v_rs_end',None),
            #d_rs_3_prime_start cant find
            #d_rs_3_prime_end cant find
            #d_rs_5_prime_start cant find
            #d_rs_5_prime_end cant find
            #j_cdr3_end cant find
            #j_rs_start cant find
            #j_rs_end cant find
            #j_donor_splice cant find
            v_gene_delineations = create_sequence_delineationV_list(allele_descriptions[i].get('v_gene_delineations',None)),
            unrearranged_support = create_unrearranged_support_list(allele_descriptions[i]['unrearranged_support'], allele_descriptions[i]['curation']),
            rearranged_support = create_rearranged_support_list(allele_descriptions[i]['rearranged_support'], allele_descriptions[i]['curation']),
            paralogs = allele_descriptions[i]['paralogs'],
            curation = allele_descriptions[i]['curation'],
            curational_tags = create_curational_tags_list(allele_descriptions[i]['curational_tags'])
        )
        allele_description_list.append(allele_description_obj)

    return allele_description_list

def create_sequence_delineationV_list(v_gene_delineations):
    sequence_delineationV_list = []

    if v_gene_delineations is not None:
        for i in range(len(v_gene_delineations)):
            sequence_delineationV_obj = SequenceDelineationV(
                sequence_delineation_id = v_gene_delineations[i]['sequence_delineation_id'],
                delineation_scheme = v_gene_delineations[i]['delineation_scheme'],
                fwr1_start = v_gene_delineations[i]['fwr1_start'] if v_gene_delineations[i]['fwr1_start'] is not None else 0,
                fwr1_end = v_gene_delineations[i]['fwr1_end'] if v_gene_delineations[i]['fwr1_end'] is not None else 0,
                cdr1_start = v_gene_delineations[i]['cdr1_start'] if v_gene_delineations[i]['cdr1_start'] is not None else 0,
                cdr1_end = v_gene_delineations[i]['cdr1_end'] if v_gene_delineations[i]['cdr1_end'] is not None else 0,
                fwr2_start = v_gene_delineations[i]['fwr2_start'] if v_gene_delineations[i]['fwr2_start'] is not None else 0,
                fwr2_end = v_gene_delineations[i]['fwr2_end'] if v_gene_delineations[i]['fwr2_end'] is not None else 0,
                cdr2_start = v_gene_delineations[i]['cdr2_start'] if v_gene_delineations[i]['cdr2_start'] is not None else 0,
                cdr2_end = v_gene_delineations[i]['cdr2_end'] if v_gene_delineations[i]['cdr2_end'] is not None else 0,
                fwr3_start = v_gene_delineations[i]['fwr3_start'] if v_gene_delineations[i]['fwr3_start'] is not None else 0,
                fwr3_end = v_gene_delineations[i]['fwr3_end'] if v_gene_delineations[i]['fwr3_end'] is not None else 0,
                cdr3_start = v_gene_delineations[i]['cdr3_start'] if v_gene_delineations[i]['cdr3_start'] is not None else 0,
                alignment = v_gene_delineations[i]['alignment_labels']
            )
            sequence_delineationV_list.append(sequence_delineationV_obj)

    else:
        return None

    return sequence_delineationV_list


def create_unrearranged_support_list(unrearranged_support, curation):
    unrearranged_support_list = []

    if unrearranged_support != None:
        for i in range(len(unrearranged_support)):
            unrearranged_sequence_obj = UnrearrangedSequence(
                sequence_id = unrearranged_support[i]['sequence_id'],
                sequence = unrearranged_support[i]['sequence'],
                curation = curation,
                repository_name = unrearranged_support[i]['repository_name'],
                repository_ref = unrearranged_support[i]['repository_ref'],
                patch_no = unrearranged_support[i]['patch_no'],
                gff_seqid = unrearranged_support[i]['gff_seqid'] if unrearranged_support[i]['gff_seqid'] is not None else "",
                gff_start = unrearranged_support[i]['gff_start'],
                gff_end = unrearranged_support[i]['gff_end'],
                strand = Strand(unrearranged_support[i]['strand']) if unrearranged_support[i]['strand'] is not None else '+'
            )
            unrearranged_support_list.append(unrearranged_sequence_obj)

    return unrearranged_support_list


def create_rearranged_support_list(rearranged_support, curation):
    rearranged_support_list = []

    if rearranged_support is not None:
        for i in range(len(rearranged_support)):
            rearranged_sequence_obj = RearrangedSequence(
                sequence_id = rearranged_support[i]['sequence_id'],
                sequence = rearranged_support[i]['sequence'],
                derivation = Derivation(rearranged_support[i]['derivation']) if rearranged_support[i]['derivation'] is not None else None,
                observation_type = ObservationType(rearranged_support[i]['observation_type']) if rearranged_support[i]['observation_type'] is not None else None,
                curation = curation,
                repository_name = rearranged_support[i]['repository_name'],
                repository_ref = rearranged_support[i]['repository_ref'],
                deposited_version = rearranged_support[i]['deposited_version'],
                sequence_start = rearranged_support[i]['sequence_start'],
                sequence_end = rearranged_support[i]['sequence_end'],
                )
            
            rearranged_support_list.append(rearranged_sequence_obj)

    return rearranged_support_list

def create_curational_tags_list(curational_tags):
    curational_tags_list = []

    if curational_tags is not None:
        for i in range(len(curational_tags)):
            curational_tag_obj = CurationalTag(curational_tags[i])
            curational_tags_list.append(curational_tag_obj)

    return curational_tags_list