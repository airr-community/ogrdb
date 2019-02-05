# Creating Genotype Statistics

genotype_statistics.R can be used to create a Genotype File for upload to OGRDB. The script is independent 
of any particular inference tool. This version is specific to the IGHV genotype and inferences.

### Prerequisites

*Read_file - A tab-separated file containing the annotated reads used to infer the genotype, in either MiAIRR or CHANGEO format.*

* The format will be determined automatically by the tool.

* AIRR format files must contain at least the following columns:
sequence_id, v_call_genotyped, d_call, j_call, sequence_alignment, cdr3

* CHANGEO files must contain at least the following columns:
SEQUENCE_ID, V_CALL_GENOTYPED, D_CALL, J_CALL, SEQUENCE_IMGT, CDR3_IMGT

* In both file formats, v_call_genotyped/V_CALL_GENOTYPED should contain the V calls made after the subject's genotype has been inferred
(including calls of the novel alleles)

*Germline_file - FASTA file containing the IGHV germline sequences provided as input to the inference tool.* 

* Sequences must correspond exactly to those used by the tool.
* They must be IMGT-aligned
* The header can either be in IMGT's germline library format, or simply consist of the allele name
* The IMGT set can be [downloaded](http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithoutGaps-F+ORF+inframeP)
  and used as-is: the script will filter out the records for the nominated species

*Inferred_file - FASTA file containing the sequences inferred by the tool*   
* Sequences must be IMGT-aligned
* The header should simply consist of the allele name as assigned by the tool.

### Usage

the script is intended to be run by Rscript

*Command Syntax*

> Rscript genotype_statistics.R \<germline_file\> \<species\> \<inferred_file\> \<read_file\>




