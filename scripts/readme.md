# The OGRDB Genotype File

### Creating a Genotype File with genotype_statistics.R

[genotype_statistics.R](https://github.com/airr-community/ogre/blob/master/scripts/genotype_statistics.R) is a script 
that can be used to create an analysis of gene usage in a receptor repertoire. The analysis consists of 
[usage statistics](https://github.com/airr-community/ogre/blob/master/static/docs/genotype_1.csv) and  [plots](https://github.com/airr-community/ogre/raw/master/static/docs/example_ogrdb_genotype_report.pdf). 
The report includes an analysis of inferred alleles: the script was originally written to be used in conjunction with a novel allele inference tool such
as those listed below, but it can be run on any repertoire, whether or not it contains novel alleles. 

### OGRDB Submission Requirements

If you wish to submit novel alleles to OGRDB, you will be asked to upload a genotype file. genotype_statistics.R is the preferred way
to create this. The following references are provided for additional information: 

- A [blank template](https://github.com/airr-community/ogre/blob/master/static/templates/genotype_template.csv)
- An [example genotype file](https://github.com/airr-community/ogre/blob/master/static/docs/genotype_1.csv)
- [Definitions](https://github.com/airr-community/ogre/blob/master/static/templates/genotype_fields.csv) of the fields used in the genotype.

### Script Prerequisites

*Germline_file - FASTA file containing the IMGT gap-aligned reference germline sequences.* 

* All sequences that are called in the read file (apart from those of novel alleles) should be included. 
* The sequences must be IMGT gap-aligned
* The header can either be in IMGT's germline library format, or simply consist of the allele name
* The IMGT set can be [downloaded](http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithGaps-F+ORF+inframeP)
  and used as-is: the script will filter out the records for the nominated species. As the IMGT set changes from time to time, please make sure that 
  the same version is used by the inference tool and by this script.
* A warning will be given if any V-calls in the read file do not have a corresponding sequence. Unmutated counts will not be provided for thse sequences.

*Inferred_file - FASTA file containing the inferred novel alleles*   
* Sequences in the inferred file should all be of the same type: VH, VK, VL, D, JH, JK, or JL
* The header should simply consist of the allele name as assigned by the tool.
* If there are no inferred alleles, please provide an empty file.
* V-gene sequences may either be IMGT-aligned or not aligned. If they are not aligned, the script will determine
the nearest reference gene and use it as a template. If you are not satisfied with the resulting
alignment, just align the sequence in the inferred file as you prefer. 
* If a gene with the same name is present in both the germline file and the inferred file,
its presence in the inferred file will be ignored. This makes it easier to use the script with 
inference tools that do not write the inferred sequences to a separate file.  

*Read_file - A tab-separated file containing the annotated reads used to infer the genotype, in MiAIRR, CHANGEO or IgDiscover format.*

* The format will be determined automatically by the script.
* MiAIRR format files must contain at least the following columns:
`sequence_id, v_call_genotyped, d_call, j_call, sequence_alignment, cdr3`. For J or D inferences they must also contain 
`J_sequence_start`, `J_sequence_end`, `J_germline_start`, `J_germline_end`, or the equivalent fields for D genes. [IgBLAST](https://www.ncbi.nlm.nih.gov/igblast/)'s 
 `--format airr` creates compatible MiAIRR format files.
* CHANGEO files must contain at least the following columns:
`SEQUENCE_ID, V_CALL_GENOTYPED, D_CALL, J_CALL, SEQUENCE_IMGT, CDR3_IMGT`, `V_MUT_NC`, `D_MUT_NC`, `J_MUT_NC`, `SEQUENCE`, `JUNCTION_START`, `V_SEQ`, `D_SEQ`, `J_SEQ`. 
If you would like to process files from IMGT V-Quest, please [parse them with CHANGEO](https://changeo.readthedocs.io/en/stable/examples/imgt.html) to convert them to CHANGEO format.

* D- related fields are only required for heavy chain records.

* In both the above file formats, `v_call_genotyped/V_CALL_GENOTYPED` should contain the V calls made after the subject's V-gene genotype has been inferred
(including calls of the novel alleles). Sequences should be IMGT-aligned. Determining the personalised V-gene genotype is recommended when processing D or J
gene inferences, so that V-gene usage counts are accurate. However, this step can be omitted for D or J gene processing by providing a V_CALL field instead of V_CALL_GENOTYPED. 

* For IgDiscover, the file 'final/filtered.tab' should be used - see section below.

*R libraries*

The following libraries are required: `tigger, alakazam, tidyr, dplyr, stringr, ggplot2, grid, gridExtra, Biostrings, stringdist, RColorBrewer`

With the exception of Biostrings, they may be installed using the R function `install.packages`. For Biostrings,
use the following commands from within R:

```
source("http://bioconductor.org/biocLite.R")
biocLite("Biostrings")
```

### Usage

The script is intended to be run by Rscript.

*Command Syntax*

> Rscript genotype_statistics.R \<germline_file\> \<species\> \<inferred_file\> \<read_file\> \<chain\> \[\<haplotyping_gene\>\]

`<species>` must be present, but is only used by the script if the germline file is in IMGT format, in which case
it should contain the species name used in field 3 of the header, with spaces removed, e.g. Homosapiens for Human.

`<chain>` is one of  VH, VK, VL, D, JH, JK, JL. It should correspond to the sequence type provided in the inferred_file - or the sequence type you would like analysed, if there are no inferences. 

`[<haplotyping_gene>]` specifies, optionally, the gene to be used for haplotyping analysis (see haplotyping section below).

### Output

* `<read_file>_ogrdb_report.csv` - the Genotype File ready to be uploaded to OGRDB.
* `<read_file>_ogrdb_plots.csv` - plots (see next section for details). 

Note that the read_file name is used as a prefix to the output file names. They will be written to the directory containing the read file.

If you are submitting inferences to OGRDB, you will be prompted to upload the genotype file. Please upload the plots file as an attachment to the Notes section of your submission.


### Plots

The script produces the following plots:
* For each allele used in the the read file, a histogram showing the number of mutated and unmutated sequences
* Barcharts showing nucleotide usage at locations in the IMGT-aligned sequence: both across the sequence as a whole, and in more detail at the 3' end
* A barchart showing usage of the alleles of potential haplotyping genes, across the whole genotype. This can be used to identify a suitable gene for haplotyping analysis.
* For each potential haplotyping candidate (selected by the tool from the usage chart above), a plot comparing the usage of the two most frequently used alleles of that gene.

The nucleotide usage plots are not produced from IgDiscover output, as aligned V-sequences are not available.

### Haplotyping

The script should first be run without the optional `<haplotyping_gene>` parameter. If, having consulted the plots, you identify a suitable gene
for haplotyping, please run the script again, with this gene specified as `<haplotyping_gene>`. The haplotyping_gene and haplotyping_ratio columns of the genotype file
will be appropriately populated.  A J-gene should be used with V- and D- gene inferences, and a V-gene with J-gene inferences. 

### Example

To complete an analysis using the supplied example file and a downloaded IMGT reference file, run the following commands:

```angular2
wget -O IMGT_REF_GAPPED.fasta http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithGaps-F+ORF+inframeP
Rscript genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens TWO01A_naive_novel.fasta TWO01A_naive_genotyped.tsv VH IGHJ6
``` 

### Usage Notes

Usage notes are indicative only and are not intended to discount other approaches. Notes for other tools will follow.

### Usage Notes - TIgGER

To conduct a V-gene analysis with TIgGER:
* Use `findNovelAlleles` to identify novel alleles in a Change-O-formatted data set. Write these to a FASTA file. 
* Use `inferGenotype` or `inferGenotypeBayesian` to infer the genotype.
* Use `reassignAlleles` to correct allele calls in the data set, based on the inferred genotype
* Provide the resulting Change-O file, together with the FASTA file containing the novel alleles, to `genotype_statistics.R`.

Note that `inferGenotype` will not necessarily include every inferred allele produced by `findNovelAlleles` in the genotype that it produces. Only those
alleles included in the genotype will be considered by `genotype_statistics.R` because, leaving other considerations aside, no sequences are assigned to other alleles.

TIgGER provides additonal information, including its own plots and statistics We encourage you to take these into consideration, and to upload them as attachments to your submission if they are informative.

### Usage Notes - IgDiscover

Assuming that you have copied the script file to IgDiscover's `final` directory following an IgDiscover run, the following
commands will download the IMGT reference file and run a VH gene analysis:

```
$ wget -O IMGT_REF_GAPPED.fasta http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithGaps-F+ORF+inframeP
$ unzip final.tab.gz
$ Rscript genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens database/V.fasta filtered.tab VH
```

alternatively, to produce a JH gene analysis:

```
$ Rscript genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens database/J.fasta filtered.tab JH
```


### Usage Notes - partis

The information required by generate_statstics.R is split between partis's normal YAML output and that provided by 
the 'presto-output' mode. A python script,
convert_partis.py, is is provided here. This will combine output from partis's yaml and presto annotations, producing
CHANGEO format annotations and a FASTA file of genotype V-sequences. These files can then passed to generate_statistics.R.
convert_partis.py is written in python 2.7 for compatibility with partis, and can be run from the command line in the same virtual 
environment.

Usage of convert_partis.py:

```
python convert_partis.py [-h] partis_yaml partis_tsv ogrdb_recs ogrdb_vs

positional arguments:
  partis_yaml  .yaml file created by partis
  partis_tsv   .tsv file created by partis presto-output mode
  ogrdb_recs   annotation output file (.tsv)
  ogrdb_vs     v_gene sequences (.fasta)

optional arguments:
  -h, --help   show this help message and exit
```

Although partis must be run twice - once without the presto-output option, and once with it - it will use cached information 
provided other parameters remain the same, so that the overall impact on run time is low. Typical processing steps are shown below.
Note that --presto-output requires an IMGT-gapped V-gene germline file. This can be extracted from the full germline library downloaded
from IMGT (see 'Prerequisites' above), but partis will report as an error any duplicated identical sequences in the library: duplicates must be removed from the file
before processing will complete successfully. Note in the examples below the --extra-annotations option. The CDR3 is
required by generate_statistics.R: the other fields are included for reference.

```
# Run partis to produce annotations in YAML format
partis annotate --extra-annotation-columns cdr3_seqs:invalid:in_frames:stops --infname TW01A.fasta --outfname TW01A.yaml --n-procs 5
# Run partis again with additional --presto-output option. This will produce TSV-formatted output from cached data
partis annotate --extra-annotation-columns cdr3_seqs:invalid:in_frames:stops --infname TW01A.fasta --outfname TW01A.tsv --presto-output \
 --aligned-germline-fname IMGT_REF_GAPPED_DEDUPED.fasta --n-procs 5
# Extract and merge required information from YAML and TSV files
python convert_partis.py TW01A.yaml TW01A.tsv TW01A_OGRDB.tsv TW01A_V_OGRDB.fasta
# Process the resulting output to produce the genotye file and plots
Rscript genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens TW01A_V_OGRDB.fasta TW01A_OGRDB.tsv VH

```

### Usage Notes - IMPre

IMPre does not provide a set of sequences annotated with the novel allele calls. The sequences must be
annotated by a separate tool in order to provide the information needed for the OGRDB genotype. One possible approach
is as follows:

* Annotate with IgBLAST using a custom germline set that includes the novel alleles inferred by IMPre. Details for
creating IgBLAST's germline database are given in the [setup notes](https://ncbi.github.io/igblast/cook/How-to-set-up.html).
The novel alleles inferred by IMPre can be added to the germline sequences downloaded from IMGT, before running
makeblastdb. 
* Select the AIRR output format, and provide the resulting annotion file to genotype_statistics.R, along with the 
novel inferences provided by IMPre

### Acknowledgements

Some functions are adapted from [TIgGER](https://tigger.readthedocs.io) with thanks to the authors.

The example annotated reads and inferences in this directory are taken from the data of [Rubelt et al](https://www.ncbi.nlm.nih.gov/pubmed/?term=27005435) 
and were downloaded from [VDJServer](https://vdjserver.org/). The genotype was inferred by [TIgGER](https://tigger.readthedocs.io). A small number of 
light-chain records were removed from the data set.


