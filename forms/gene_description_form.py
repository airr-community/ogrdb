
# FlaskForm class definitions for GeneDescription
# This file is automatically generated from the schema by schema/build_from_schema.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class GeneDescriptionForm(FlaskForm):
    description_id = StringField('Sequence ID', [validators.Length(max=255)], description="Unique identifier of this gene sequence")
    author = StringField('Author', [validators.Length(max=255)], description="Corresponding author")
    lab_address = StringField('Author address', [validators.Length(max=255)], description="Institutional address of corresponding author")
    release_version = IntegerField('Version', [], description="Version number of this record, updated whenever a revised version is published or released")
    release_date = DateField('Release Date', description="Date of this release")
    release_description = TextAreaField('release notes', [validators.Length(max=10000)], description="Brief descriptive notes of the reason for this release and the changes embodied")
    organism = StringField('Organism', [validators.Length(max=255)], description="Binomial designation of subject's species")
    sequence_name = StringField('Sequence Name', [validators.Length(max=255)], description="The canonical name of this sequence (i.e., the name which the curators determine should be used by preference)")
    alt_names = StringField('Alternative names', [validators.Length(max=255)], description="Alternative names for this sequence")
    locus = SelectField('Locus', choices=[('Heavy', 'Heavy'), ('Light-Kappa', 'Light-Kappa'), ('Light-Lambda', 'Light-Lambda'), ('Alpha', 'Alpha'), ('Beta', 'Beta'), ('Gamma', 'Gamma')], description="Gene locus")
    domain = SelectField('Domain', choices=[('V', 'V'), ('D', 'D'), ('J', 'J'), ('C', 'C')], description="Sequence domain (V, D, J or Constant)")
    functional = BooleanField('functional', [], description="Functional")
    inference_type = SelectField('inference_type', choices=[('Genomic and Rearranged', 'Genomic and Rearranged'), ('Genomic Only', 'Genomic Only'), ('Rearranged Only', 'Rearranged Only')], description="Type of inference(s) from which this gene sequence was inferred (Genomic and Rearranged, Genomic Only, Rearranged Only)")
    affirmation_level = SelectField('Affirmation Level', choices=[(1, 1), (2, 2), (3, 3)], description="Count of independent studies in which this allele as been affirmed by IARC (1,2,3 or more)")
    status = SelectField('status', choices=[('published', 'published'), ('draft', 'draft'), ('retired', 'retired'), ('withdrawn', 'withdrawn')], description="Status of record")
    gene_subgroup = StringField('Gene Subgroup', [validators.Length(max=255)], description="Gene subgroup (family), as (and if) identified for this species and gene")
    subgroup_designation = StringField('Gene Designation', [validators.Length(max=255)], description="Gene designation within this subgroup")
    allele_designation = StringField('Allele Designation', [validators.Length(max=255)], description="Allele designation")
    sequence = StringField('Full Sequence', [ValidNucleotideSequence(ambiguous=False)], description="nt sequence of the gene. This should cover the full length that is available, including where possible 5' UTR and lead-in for V-gene sequences")
    coding_seq_imgt = StringField('Coding Sequence', [ValidNucleotideSequence(ambiguous=False, gapped=True)], description="nucleotide sequence of the coding region, aligned, in the case of a V-gene, with the IMGT numbering scheme")
    codon_frame = SelectField('Codon Frame', choices=[(1, 1), (2, 2), (3, 3)], description="Codon position of the first sequence symbol in the Coding Sequence. Mandatory for J genes. Not used for V or D genes. ('1' means the sequence is in-frame, '2' means that the first bp is missing from the first codon, '3' means that the first 2 bp are missing)")
    j_cdr3_end = IntegerField('J CDR3 End', [], description="In the case of a J-gene, the co-ordinate in the Coding Sequence of the first nucelotide of the conserved PHE or TRP (IMGT codon position 118)")
    utr_5_prime_start = IntegerField('UTR 5' Start', [], description="Start co-ordinate in the Full Sequence of 5 prime UTR")
    utr_5_prime_end = IntegerField('UTR 5' End', [], description="End co-ordinate in the Full Sequence of 5 prime UTR")
    l_region_start = IntegerField('L Region Start', [], description="Start co-ordinate in the Full Sequence of L region")
    l_region_end = IntegerField('L Region End', [], description="End co-ordinate in the Full Sequence of L region")
    v_rs_start = IntegerField('v_rs_start', [], description="Start co-ordinate in the Full Sequence of V recombination site (V genes only)")
    v_rs_end = IntegerField('v_rs_end', [], description="End co-ordinate in the Full Sequence of V recombination site (V-genes only)")
    d_rs_3_prime_start = IntegerField('d_rs_3_prime_start', [], description="Start co-ordinate in the Full Sequence of 3 prime D recombination site (D-genes only)")
    d_rs_3_prime_end = IntegerField('d_rs_3_prime_end', [], description="End co-ordinate in the Full Sequence of 3 prime D recombination site (D-genes only)")
    d_rs_5_prime_start = IntegerField('d_rs_5_prime_start', [], description="Start co-ordinate in the Full Sequence of 5 prime D recombination site (D-genes only)")
    d_rs_5_prime_end = IntegerField('d_rs_5_prime_end', [], description="End co-ordinate in the Full Sequence of 5 prime D recombination site (D-genes only)")
    j_rs_start = IntegerField('j_rs_start', [], description="Start co-ordinate in the Full Sequence of J recombination site (J-genes only)")
    j_rs_end = IntegerField('j_rs_end', [], description="End co-ordinate in the Full Sequence of J recombination site (J-genes only)")
    paralogs = StringField('paralogs', [validators.Length(max=255)], description="Canonical names of 0 or more paralogs")
    notes = TextAreaField('Notes', [validators.Length(max=10000)], description="Notes")


