# Creating Genotype Statistics

genotype_statistics.R can be used to create a Genotype File for upload to OGRDB. The script is independent 
of any particular inference tool. This version is specific to the IGHV genotype and inferences.

### Prerequisites

*Germline_file - FASTA file containing the IGHV germline sequences provided as input to the inference tool.* 

* Sequences must correspond exactly to those used by the tool.
* They must be IMGT-aligned
* The header can either be in IMGT's germline library format, or simply consist of the allele name
* The IMGT set can be [downloaded](http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithoutGaps-F+ORF+inframeP)
  and used as-is: the script will filter out the records for the nominated species. As the IMGT set changes frequently, please make sure that 
  the same version is used by the inference tool and by this script.

*Inferred_file - FASTA file containing the novel alleles inferred by the tool*   
* Sequences must be IMGT-aligned
* The header should simply consist of the allele name as assigned by the tool.

*Read_file - A tab-separated file containing the annotated reads used to infer the genotype, in either MiAIRR or CHANGEO format.*

* The format will be determined automatically by the tool.
* AIRR format files must contain at least the following columns:
`sequence_id, v_call_genotyped, d_call, j_call, sequence_alignment, cdr3`
* CHANGEO files must contain at least the following columns:
`SEQUENCE_ID, V_CALL_GENOTYPED, D_CALL, J_CALL, SEQUENCE_IMGT, CDR3_IMGT`
* In both file formats, `v_call_genotyped/V_CALL_GENOTYPED` should contain the V calls made after the subject's genotype has been inferred
(including calls of the novel alleles)

*R libraries*

The following librfaries are required. They may be installed using the R function `install.packages`: `tigger, alakazam, tidyr, dplyr, stringr, ggplot2, grid, gridExtra`


### Usage

The script is intended to be run by Rscript.

*Command Syntax*

> Rscript genotype_statistics.R \<germline_file\> \<species\> \<inferred_file\> \<read_file\> \[\<haplotyping_gene\>\]

`<species>` must be present, but is only used by the script if the germline file is in IMGT format, in which case
it should contain the species name used in field 3 of the header, with spaces removed, e.g. Homosapiens for Human.

`[<haplotyping_gene>]` specifies, optionally, the gene to be used for haplotyping analysis (see haplotyping section below).

### Output

* `<read_file>_ogrdb_report.csv` - the Genotype File ready to be uploaded to OGRDB.
* `<read_file\>_ogrdb_plots.csv` - plots (see next section for details). 

Please upload the plots file as an attachment to the Notes section of your OGRDB submission.


### Plots

The script produces the following plots:
* For each inferred allele, a histogram showing the number of mutated and unmutated sequences
* A barchart showing usage of the alleles of each J-gene, across the whole genotype. This can be used to identify a suitable J-gene for haplotyping analysis.
* For each potential J-gene haplotyping candidate, a plot comparing the usage of the two most frequently used alleles of that gene.

### Haplotyping

The script should first be run without the optional `<haplotyping_gene>` parameter. If, having consulted the plots, you identify a suitable J-gene
for haplotyping, please run the script again, with this gene specified as `<haplotyping_gene>`. The haplotyping_gene and haplotyping_ratio columns of the genotype file
will be appropriately populated.

### Example

To complete an analysis using the suppliued example file, please [download](http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithoutGaps-F+ORF+inframeP) 
the IMGT germline file and name it IMGT_REF_GAPPED.fasta. Then run the command

> Rscript genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens TWO01A_naive_novel.fasta TWO01A_naive_genotyped.tsv IGHJ6

### Acknowledgements

Some functions are adapted from [TIgGER](https://tigger.readthedocs.io) with thanks to the authors.

The example annotated reads and inferences in this directory are taken from the data of [Rubelt et al](https://www.ncbi.nlm.nih.gov/pubmed/?term=27005435) 
and were downloaded from [VDJServer](https://vdjserver.org/). The genotype was inferred by [TIgGER](https://tigger.readthedocs.io). A small number of 
light-chain records were removed from the data set.

