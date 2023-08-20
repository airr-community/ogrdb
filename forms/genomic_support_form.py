
# FlaskForm class definitions for GenomicSupport
# This file is automatically generated from the schema by schema/build_from_schema.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, HiddenField, validators, MultipleFileField
class GenomicSupportForm(FlaskForm):
    sequence_type = SelectField('Type', choices=[('Locational', 'Locational'), ('Nonlocational', 'Nonlocational'), ('Inferred', 'Inferred')], description="Locational should be used where the unrearranged sequence includes multiple genes, enabling the location of this gene to be determined relative to others")
    sequence = TextAreaField('Sequence', [validators.Length(max=10000)], description="Sequence of interest described in this record (typically this will include gene and promoter region)")
    notes = TextAreaField('Notes', [validators.Length(max=10000)], description="Notes")
    repository = StringField('Repository', [validators.Length(max=255)], description="Name of the repository in which the assembly or sequence is deposited")
    accession = StringField('Accession', [validators.Length(max=255)], description="Accession number of the assembly or sequence within the repository")
    url = StringField('URL', [validators.Length(max=255)], description="Link to record")
    patch_no = StringField('Patch', [validators.Length(max=255)], description="Patch number of the assembly or sequence within the repository")
    gff_seqid = StringField('gff seqid', [validators.Length(max=255)], description="name of the chromosome or scaffold (for assemblies only)")
    sequence_start = IntegerField('Start', [validators.Optional()], description="start co-ordinate of the sequence of this gene in the assembly or sequence")
    sequence_end = IntegerField('End', [validators.Optional()], description="end co-ordinate of the sequence of this gene in the assembly or sequence")
    sense = SelectField('Sense', choices=[('forward', 'forward'), ('reverse', 'reverse')], description="+ (forward) or - (reverse)")
    gene_start = IntegerField('Gene start', [validators.Optional()], description="Co-ordinate in the assembly or sequence of the first nucleotide in the coding_sequence field")
    gene_end = IntegerField('Gene end', [validators.Optional()], description="Co-ordinate in the assembly or sequence of the last gene-coding nucleotide in the coding_sequence field")
    utr_5_prime_start = IntegerField('UTR 5\' Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 5 prime UTR (V-genes only)")
    utr_5_prime_end = IntegerField('UTR 5\' End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 5 prime UTR (V-genes only)")
    leader_1_start = IntegerField('L-PART1 Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of L-PART1 (V-genes only)")
    leader_1_end = IntegerField('L-PART1 End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of L-PART1 (V-genes only)")
    leader_2_start = IntegerField('L-PART2 Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of L-PART2 (V-genes only)")
    leader_2_end = IntegerField('L-PART2 End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of L-PART2 (V-genes only)")
    v_rs_start = IntegerField('v_rs_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of V recombination site (V-genes only)")
    v_rs_end = IntegerField('v_rs_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of V recombination site (V-genes only)")
    d_rs_3_prime_start = IntegerField('d_rs_3_prime_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 3 prime D recombination site (D-genes only)")
    d_rs_3_prime_end = IntegerField('d_rs_3_prime_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 3 prime D recombination site (D-genes only)")
    d_rs_5_prime_start = IntegerField('d_rs_5_prime_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 5 prime D recombination site (D-genes only)")
    d_rs_5_prime_end = IntegerField('d_rs_5_prime_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 5 prime D recombination site (D-genes only)")
    j_rs_start = IntegerField('j_rs_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of J recombination site (J-genes only)")
    j_rs_end = IntegerField('j_rs_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of J recombination site (J-genes only)")
    j_codon_frame = SelectField('Codon Frame', choices=[('1', '1'), ('2', '2'), ('3', '3')], description="Codon position of the first sequence symbol in the Coding Sequence. Mandatory for J genes. Not used for V or D genes. ('1' means the sequence is in-frame, '2' means that the first bp is missing from the first codon, '3' means that the first 2 bp are missing)")
    j_cdr3_end = IntegerField('J CDR3 End', [validators.Optional()], description="In the case of a J-gene, the co-ordinate in the assembly or sequence of the first nucelotide of the conserved PHE or TRP (IMGT codon position 118)")



# FlaskForm class definitions for GenomicSupport
# This file is automatically generated from the schema by schema/build_from_schema.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, HiddenField, validators, MultipleFileField
class GenomicSupportForm(FlaskForm):
    sequence_type = SelectField('Type', choices=[('Locational', 'Locational'), ('Nonlocational', 'Nonlocational'), ('Inferred', 'Inferred')], description="Locational should be used where the unrearranged sequence includes multiple genes, enabling the location of this gene to be determined relative to others")
    sequence = TextAreaField('Sequence', [validators.Length(max=10000)], description="Sequence of interest described in this record (typically this will include gene and promoter region)")
    notes = TextAreaField('Notes', [validators.Length(max=10000)], description="Notes")
    repository = StringField('Repository', [validators.Length(max=255)], description="Name of the repository in which the assembly or sequence is deposited")
    accession = StringField('Accession', [validators.Length(max=255)], description="Accession number of the assembly or sequence within the repository")
    url = StringField('URL', [validators.Length(max=255)], description="Link to record")
    patch_no = StringField('Patch', [validators.Length(max=255)], description="Patch number of the assembly or sequence within the repository")
    gff_seqid = StringField('gff seqid', [validators.Length(max=255)], description="name of the chromosome or scaffold (for assemblies only)")
    sequence_start = IntegerField('Start', [validators.Optional()], description="start co-ordinate of the sequence of this gene in the assembly or sequence")
    sequence_end = IntegerField('End', [validators.Optional()], description="end co-ordinate of the sequence of this gene in the assembly or sequence")
    sense = SelectField('Sense', choices=[('forward', 'forward'), ('reverse', 'reverse')], description="+ (forward) or - (reverse)")
    gene_start = IntegerField('Gene start', [validators.Optional()], description="Co-ordinate in the assembly or sequence of the first nucleotide in the coding_sequence field")
    gene_end = IntegerField('Gene end', [validators.Optional()], description="Co-ordinate in the assembly or sequence of the last gene-coding nucleotide in the coding_sequence field")
    utr_5_prime_start = IntegerField('UTR 5\' Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 5 prime UTR (V-genes only)")
    utr_5_prime_end = IntegerField('UTR 5\' End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 5 prime UTR (V-genes only)")
    leader_1_start = IntegerField('L-PART1 Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of L-PART1 (V-genes only)")
    leader_1_end = IntegerField('L-PART1 End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of L-PART1 (V-genes only)")
    leader_2_start = IntegerField('L-PART2 Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of L-PART2 (V-genes only)")
    leader_2_end = IntegerField('L-PART2 End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of L-PART2 (V-genes only)")
    v_rs_start = IntegerField('v_rs_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of V recombination site (V-genes only)")
    v_rs_end = IntegerField('v_rs_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of V recombination site (V-genes only)")
    d_rs_3_prime_start = IntegerField('d_rs_3_prime_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 3 prime D recombination site (D-genes only)")
    d_rs_3_prime_end = IntegerField('d_rs_3_prime_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 3 prime D recombination site (D-genes only)")
    d_rs_5_prime_start = IntegerField('d_rs_5_prime_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 5 prime D recombination site (D-genes only)")
    d_rs_5_prime_end = IntegerField('d_rs_5_prime_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 5 prime D recombination site (D-genes only)")
    j_rs_start = IntegerField('j_rs_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of J recombination site (J-genes only)")
    j_rs_end = IntegerField('j_rs_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of J recombination site (J-genes only)")
    j_codon_frame = SelectField('Codon Frame', choices=[('1', '1'), ('2', '2'), ('3', '3')], description="Codon position of the first sequence symbol in the Coding Sequence. Mandatory for J genes. Not used for V or D genes. ('1' means the sequence is in-frame, '2' means that the first bp is missing from the first codon, '3' means that the first 2 bp are missing)")
    j_cdr3_end = IntegerField('J CDR3 End', [validators.Optional()], description="In the case of a J-gene, the co-ordinate in the assembly or sequence of the first nucelotide of the conserved PHE or TRP (IMGT codon position 118)")



# FlaskForm class definitions for GenomicSupport
# This file is automatically generated from the schema by schema/build_from_schema.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, HiddenField, validators, MultipleFileField
class GenomicSupportForm(FlaskForm):
    sequence_type = SelectField('Type', choices=[('Locational', 'Locational'), ('Nonlocational', 'Nonlocational'), ('Inferred', 'Inferred')], description="Locational should be used where the unrearranged sequence includes multiple genes, enabling the location of this gene to be determined relative to others")
    sequence = TextAreaField('Sequence', [validators.Length(max=10000)], description="Sequence of interest described in this record (typically this will include gene and promoter region)")
    notes = TextAreaField('Notes', [validators.Length(max=10000)], description="Notes")
    repository = StringField('Repository', [validators.Length(max=255)], description="Name of the repository in which the assembly or sequence is deposited")
    accession = StringField('Accession', [validators.Length(max=255)], description="Accession number of the assembly or sequence within the repository")
    url = StringField('URL', [validators.Length(max=255)], description="Link to record")
    patch_no = StringField('Patch', [validators.Length(max=255)], description="Patch number of the assembly or sequence within the repository")
    gff_seqid = StringField('gff seqid', [validators.Length(max=255)], description="name of the chromosome or scaffold (for assemblies only)")
    sequence_start = IntegerField('Start', [validators.Optional()], description="start co-ordinate of the sequence of this gene in the assembly or sequence")
    sequence_end = IntegerField('End', [validators.Optional()], description="end co-ordinate of the sequence of this gene in the assembly or sequence")
    sense = SelectField('Sense', choices=[('forward', 'forward'), ('reverse', 'reverse')], description="+ (forward) or - (reverse)")
    gene_start = IntegerField('Gene start', [validators.Optional()], description="Co-ordinate in the assembly or sequence of the first nucleotide in the coding_sequence field")
    gene_end = IntegerField('Gene end', [validators.Optional()], description="Co-ordinate in the assembly or sequence of the last gene-coding nucleotide in the coding_sequence field")
    utr_5_prime_start = IntegerField('UTR 5\' Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 5 prime UTR (V-genes only)")
    utr_5_prime_end = IntegerField('UTR 5\' End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 5 prime UTR (V-genes only)")
    leader_1_start = IntegerField('L-PART1 Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of L-PART1 (V-genes only)")
    leader_1_end = IntegerField('L-PART1 End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of L-PART1 (V-genes only)")
    leader_2_start = IntegerField('L-PART2 Start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of L-PART2 (V-genes only)")
    leader_2_end = IntegerField('L-PART2 End', [validators.Optional()], description="End co-ordinate in the assembly or sequence of L-PART2 (V-genes only)")
    v_rs_start = IntegerField('v_rs_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of V recombination site (V-genes only)")
    v_rs_end = IntegerField('v_rs_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of V recombination site (V-genes only)")
    d_rs_3_prime_start = IntegerField('d_rs_3_prime_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 3 prime D recombination site (D-genes only)")
    d_rs_3_prime_end = IntegerField('d_rs_3_prime_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 3 prime D recombination site (D-genes only)")
    d_rs_5_prime_start = IntegerField('d_rs_5_prime_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of 5 prime D recombination site (D-genes only)")
    d_rs_5_prime_end = IntegerField('d_rs_5_prime_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of 5 prime D recombination site (D-genes only)")
    j_rs_start = IntegerField('j_rs_start', [validators.Optional()], description="Start co-ordinate in the assembly or sequence of J recombination site (J-genes only)")
    j_rs_end = IntegerField('j_rs_end', [validators.Optional()], description="End co-ordinate in the assembly or sequence of J recombination site (J-genes only)")
    j_codon_frame = SelectField('Codon Frame', choices=[('1', '1'), ('2', '2'), ('3', '3')], description="Codon position of the first sequence symbol in the Coding Sequence. Mandatory for J genes. Not used for V or D genes. ('1' means the sequence is in-frame, '2' means that the first bp is missing from the first codon, '3' means that the first 2 bp are missing)")
    j_cdr3_end = IntegerField('J CDR3 End', [validators.Optional()], description="In the case of a J-gene, the co-ordinate in the assembly or sequence of the first nucelotide of the conserved PHE or TRP (IMGT codon position 118)")

