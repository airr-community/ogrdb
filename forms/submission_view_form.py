# Composite tables for View Submission page - defined manually

from db.submissiondb import *
from db.repertoiredb import *
from db.editable_table import *
from db.genotype_description_db import *
from db.inference_tool_db import *
from db.inferred_sequence_db import *
from forms.submissioneditform import ToolNameCol, SeqNameCol, GenNameCol

def setup_submission_view_forms_and_tables(sub, db, private):
    tables = {}
    tables['submission'] = make_Submission_view(sub, private)
    tables['ack'] = make_Acknowledgements_table(sub.acknowledgements)
    tables['repertoire'] = make_Repertoire_view(sub.repertoire[0])
    tables['pub'] = make_PubId_table(sub.repertoire[0].pub_ids)
    tables['fw_primer'] = make_ForwardPrimer_table(sub.repertoire[0].forward_primer_set)
    tables['rv_primer'] = make_ReversePrimer_table(sub.repertoire[0].reverse_primer_set)

    t = make_InferenceTool_table(sub.inference_tools)
    t.add_column('id', ActionCol("View", delete=False, view_route='inference_tool'))
    tables['inference_tool'] = t

    t = make_GenotypeDescription_table(sub.genotype_descriptions)
    t.add_column('toolname', ToolNameCol('Tool/Setting Name'))
    t.add_column('id', ActionCol("View", delete=False, view_route='genotype'))
    tables['genotype_description'] = t

    t = make_InferredSequence_table(sub.inferred_sequences)
    t2 = make_InferredSequence_table(sub.inferred_sequences)
    t3 = make_InferredSequence_table(sub.inferred_sequences)
    t.add_column('Sequence', SeqNameCol('Sequence'))
    t.add_column('Genotype', GenNameCol('Genotype'))
    tables['inferred_sequence'] = t
    foo=t.__html__()

    return tables
