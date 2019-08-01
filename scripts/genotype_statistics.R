# This software is licensed under the CC BY-SA 4.0 licence: https://creativecommons.org/licenses/by-sa/4.0/
#
# Some functions are adapted from TIgGER (https://tigger.readthedocs.io) with thanks to the authors.


# genotype_statistics.R - Derive statistics required by OGRDB for submission of novel alleles
#
# Command Syntax:
#
# Rscript genotype_statistics.R <ref_library> <species> <filename> <chain> [<haplotype-allele>]
#
# <ref_library> - IMGT-aligned reference genes in FASTA format. Header can either be in IMGT's germline library format,
# or simply the allele name. Reference genes in this file MUST correspond to those used to annotate the reads.
# The IMGT set can be downloaded from http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithoutGaps-F+ORF+inframeP
# and used as-is: the script will filter out the records for the nominated species.
#
# <species> This field must be present but is only used to filter records from an IMGT style reference library. It should contain the
# species name used in field 3 of the IMGT germline header, with spaces removed, e.g. Homosapiens for Human.
#
# <inferred_filename> Sequences of inferred novel alleles (FASTA format). Use a dash (-) in place of the filename if there are no novel alleles.
#
# Alleles in this file that are also listed in the reference fill will be ignored. Sequences in this file may either be IMGT-gapped or ungapped.
# Ungapped sequences will be gapped using the closest sequence in the reference as a model
#
# <filename> - annotated reads in AIRR, CHANGEO or IgDiscover format. The format is detected by the script.
#
# <chain> - one of VH, VK, VL, D, JH, JK, JL
#
# <halplotype-gene> - optional argument. If present, the haplotyping columns will be completed based on the usage of the two most frequent alleles of this gene. A J-gene 
# should be used with V- and D- gene inferences, and a V-gene with J-gene inferences. 
#
# AIRR format files must contain the following columns:
# sequence_id, v_call_genotyped, d_call*, j_call, sequence_alignment, cdr3
# In addition for J gene processing they must contain J_sequence_start, J_sequence_end, J_germline_start, J_germline_end
#
# CHANGEO files must contain the following columns:
#
# SEQUENCE_ID, V_CALL_GENOTYPED, D_CALL*, J_CALL, CDR3_IMGT, V_MUT_NC, D_MUT_NC*, J_MUT_NC, SEQUENCE, JUNCTION_START, V_SEQ, D_SEQ*, J_SEQ
#
# IgDiscover files must contain the following columns:
#
# name, V_gene, D_gene*, J_gene, CDR3_nt, V_errors, D_errors*, J_errors, VDJ_nt, V_CDR3_start, V_nt, D_region*, J_nt
#
# Starred fields are only required for heavy chain records.
#
# In AIRR and CHANGEO file formats, v_call_genotyped/V_CALL_GENOTYPED/V_gene should contain the V calls made after the subject's genotype has been inferred
# (including calls of the novel alleles)
#
# The command creates:
#
# <filename>_ogrdb_report.csv - this contains the file ready to be uploaded to OGRDB.
#
# <filename>_ogrdb_plots.pdf - plots showing distribution of close variants of inferred genes, and potential for haplotype analysis


library(tigger)
library(alakazam)
library(stringr)
library(grid)
library(gridExtra)
library(tidyr)
library(dplyr)
library(stringdist)
library(RColorBrewer)


# to install biostrings:
# source("http://bioconductor.org/biocLite.R")
# biocLite("Biostrings")
library("Biostrings")

args = commandArgs(trailingOnly=TRUE)

if(length(args) > 4) {
  ref_filename = args[1]
  species = args[2]
  inferred_filename = args[3]
  filename = args[4]
  chain = args[5]
  hap_gene = NA
  
  if(length(args) >5) {
    hap_gene = args[6]
  }
} else {   # for R Studio Source
  # VH - tigger (Example in Readme)
  # work_dir = 'D:/Research/ogre/scripts'
  # setwd(work_dir)
  # ref_filename = 'IMGT_REF_GAPPED.fasta'
  # species = 'Homosapiens'
  # inferred_filename = 'TWO01A_naive_novel_ungapped.fasta'
  # filename = 'TWO01A_naive_genotyped.tsv'
  # chain = 'VH'
  # hap_gene = 'IGHJ6'

  # JH - tigger
  # work_dir = 'D:/Research/ogre/scripts/tests/JH_tigger'
  # setwd(work_dir)
  # ref_filename = 'IMGT_REF_GAPPED_J_CHANGES.fasta'
  # species = 'Homosapiens'
  # inferred_filename = 'TWO01A_naive_novel.fasta'
  # filename = 'TWO01A_naive.airr.tab'
  # chain = 'JH'
  # hap_gene = 'IGHV2-5'
  
  # D - tigger
  # work_dir = 'D:/Research/ogre/scripts/tests/D_tigger'
  # setwd(work_dir)
  # ref_filename = 'IMGT_REF_GAPPED_D_1_26_01_removed.fasta'
  # species = 'Homosapiens'
  # inferred_filename = 'TWO01A_naive_novel.fasta'
  # filename = 'TWO01A_naive.airr.tab'
  # chain = 'DH'
  # hap_gene = 'IGHJ6'

  # JH - igdiscover
  # work_dir = 'D:/Research/ogre/scripts/tests/JH_igdiscover'
  # setwd(work_dir)
  # ref_filename = 'IMGT_REF_GAPPED_fake_j.fasta'
  # species = 'Homosapiens'
  # inferred_filename = 'J.fasta'
  # filename = 'filtered.tab'
  # chain = 'JH'
  # hap_gene = 'IGHV2-5'
  # 
  # JL - igdiscover
  # just a fake based on JH
  # work_dir = 'D:/Research/ogre/scripts/tests/JL_igdiscover'
  # setwd(work_dir)
  # ref_filename = 'IMGT_REF_GAPPED_fake_j_fake_JK.fasta'
  # species = 'Homosapiens'
  # inferred_filename = 'J.fasta'
  # filename = 'filtered.tab'
  # chain = 'JK'
  # hap_gene = 'IGHV2-5'
  
  # VH - partis
  work_dir = 'D:/Research/ogre/scripts/tests/VH_partis'
  setwd(work_dir)
  ref_filename = 'IMGT_REF_GAPPED.fasta'
  species = 'Homosapiens'
  inferred_filename = 'TW02A_V_OGRDB.fasta'
  filename = 'TW02A_OGRDB.tsv'
  chain = 'VH'
  hap_gene = 'IGHJ6'
  
} 

if(!(chain %in% c('VH', 'VK', 'VL', 'DH', 'JH', 'JK', 'JL'))) {
  stop('Unrecognised chain name.')
}

segment = substr(chain, 1, 1)

if(segment == 'D') {
  chain_type = 'H'
} else {
  if(substr(chain, 2, 2) == 'H') {
    chain_type = 'H'
  } else {
    chain_type = 'L'
  }
}

file_prefix = basename(strsplit(filename, '.', fixed=T)[[1]][1])

pdf(NULL) # this seems to stop an empty Rplots.pdf from being created. I don't know why.

# TImestamped progress report

report = function(x) {
  cat(paste0(Sys.time(), ':', x, '\n'))
}

# Functions to provide reasonable sorting of gene names

gene_family = function(gene_name) {
  if(!grepl('-', gene_name, fixed=T)) {
    return( '000')
  }
  fam = strsplit(gene_name, '-')[[1]][[1]]
  return(substr(fam, nchar(fam), nchar(fam)))
}

gene_number = function(gene_name) {
  if(!grepl('-', gene_name, fixed=T) && grepl('_S', gene_name, fixed=T)) {
    num = strsplit(gene_name, '_S')[[1]][[2]]
  } else {
    spl = strsplit(gene_name, '-')
    
    if(length(spl[[1]]) > 1) {
      num = spl[[1]][[2]]
      } else {
      num = spl[[1]][[1]]
      }
  }
  
  if(grepl('*', num, fixed=T)) {
    num = strsplit(num, '*', fixed=T)[[1]][[1]]
  }
  
  return(str_pad(num, 3, side='left', pad='0'))
}

allele_number = function(gene_name) {
  if(!grepl('*', gene_name, fixed=T)) {
    return('000')
  }
  
  return(str_pad(strsplit(gene_name, '*', fixed=T)[[1]][[2]], 3, side='left', pad='0')) 
}

order_alleles = function(allele_names) {

  allele_names$family = sapply(allele_names$genes, gene_family)
  allele_names$number = sapply(allele_names$genes, gene_number)
  allele_names$allele = sapply(allele_names$genes, allele_number)

  alleles = unique(allele_names$allele)[order(unique(allele_names$allele))]
  allele_names$allele_ind = sapply(allele_names$allele, function(x){which(alleles==x)})
  
  families = unique(allele_names$family)[order(unique(allele_names$family))]
  allele_names$family_ind = sapply(allele_names$family, function(x){which(families==x)})
  
  numbers = unique(allele_names$number)[order(unique(allele_names$number))]
  allele_names$number_ind = sapply(allele_names$number, function(x){which(numbers==x)})
  
  allele_names$index = allele_names$allele_ind + 1000*allele_names$number_ind + 1000000*allele_names$family_ind
  return(order(allele_names$index))
}

sort_alleles = function(allele_vec) {
  allele_names=DataFrame(genes=as.character(unique(allele_vec)))
  return(allele_names$genes[order_alleles(allele_names)])
}

# count unique calls
unique_calls = function(gene, segment, seqs) {
  calls = unique(seqs[seqs$SEG_CALL==gene,][segment])
  calls = calls[!grepl(',', calls[,segment]),]       # count unambiguous calls only
  calls = calls[grepl('IG', calls)]                 #don't count blank calls
  return(length(calls))
}

# count unique CDRs
unique_cdrs = function(gene, segment, seqs) {
  calls = unique(seqs[seqs$SEG_CALL==gene,][segment])
  calls = calls[nchar(calls[,segment]) > 0,]
  return(length(calls))
}

# create list of nt differences between two strings
build_nt_diff_string = function(seq1, seq2, bias) {
  nt_diff_string = ""
  max_length = max(nchar(seq1), nchar(seq2))
  seq1 = str_pad(seq1, max_length, side="right", pad="-")
  seq2 = str_pad(seq2, max_length, side="right", pad="-")
  nt_diff = unlist(getMutatedPositions(seq1, seq2,ignored_regex="\\."))
  ref_nt <- strsplit(seq1,"")[[1]][nt_diff]
  novel_nt <- strsplit(seq2,"")[[1]][nt_diff]
  
  if(length(nt_diff) > 0) {
    nt_diff = sapply((nt_diff-bias), function(x) if(x <= 0) {x-1} else {x} )
    nt_diff_string <- paste(paste(
      ref_nt, 
      nt_diff, 
      replace(novel_nt, is.na(novel_nt), "-"),
      sep=""), collapse=",") 
  }
  return(nt_diff_string)
}

# Find non triplet gaps in a nucleotide sequence
hasNonImgtGaps <- function (seq) {
  len <- ceiling(nchar(seq)/3)*3
  codons <- substring(seq, seq(1, len-2, 3), seq(3, len, 3))
  gaps_lengths <- nchar(gsub("[^\\.\\-]", "", codons))
  if (any(gaps_lengths %% 3 != 0)) {
    TRUE
  } else {
    FALSE
  }
}

# Use a gapped IMGT 'template' to apply gaps to a similar sequence 

insert_at = function(seq, ins, loc) {
  if(nchar(seq) >= loc-1) {
    return(paste0(substr(seq, 1, loc-1), ins, substr(seq, loc, nchar(seq))))
  }
  
  
  return(seq)
}

apply_gaps = function(seq, tem) {
  tem = strsplit(tem, '')[[1]]
  res = seq
  
  for(i in 1:length(tem)) {
    if(tem[i] == '.') {
      res = insert_at(res, '.', i)    
    }
  }
  return(res)
}

# Gap an ungapped sequence, using the nominated reference v_gene as template
# This is used where the inference tool does not provide imgt-aligned sequences.
# It will not handle indels, but it will try to spot them and set the aligned sequence to NA
# junction_start is the location of the first nucleotide of the cysteine preceding the CRD3
# this is location 310 in the IMGT numbering scheme
imgt_gap = function(sequence, cdr3_sequence, junction_start, ref_gene) {
  # Find the cdr3_start in the un-aligned reference gene
  ref_junction_start = 310 - (nchar(ref_gene) - nchar(gsub('.', '', ref_gene, fixed=T)))
  
  # Trim or pad this sequence to match the unaligned ref gene
  if(junction_start < ref_junction_start) {
    pad = strrep('-', ref_junction_start - junction_start)
    sequence = paste0(pad, sequence)
  } else if(junction_start > ref_junction_start) {
    chop = junction_start - ref_junction_start
    sequence = substring(sequence, chop+1)
  }
  
  gapped = apply_gaps(sequence, ref_gene)
  
  # if the alignment is correct, the cdr3 should start at location 313
  # if it doesn't, the sequence probably has indels - set the alignment to NA
  # Ideally we would check CDR1 as well, but as partis doesn't give us CDR1...
  
  aligned_cdr3 = substring(gapped, 313, 313+nchar(cdr3_sequence)-1)
  
  if(cdr3_sequence != aligned_cdr3) {
    gapped = NA
  }
  
  return(gapped)
}

# Gap an ungapped inferred germline sequence, using the closest reference gene as a template
# This is used to IMGT-gap inferred alleles, where the gapped sequence is not available
# It assumes full-length sequences and no indels.

imgt_gap_inferred = function(seqname, seqs, ref_genes) {

  # Do we need to gap?
  if(grepl('.', seqs[seqname], fixed=TRUE))
    return(unname(seqs[seqname]))
  
  # Find the closest reference gene
  r = data.frame(GENE=names(ref_genes),SEQ=ref_genes, stringsAsFactors = F)
  r$SEQ = sapply(r$SEQ,str_replace_all,pattern='\\.',replacement='')
  r$dist=sapply(r$SEQ, pairwiseAlignment, subject=seqs[seqname], scoreOnly=T)
  r = r[order(r$dist, decreasing=T),]

  # Gap the sequence
  tem = ref_genes[r[1,]$GENE]
  gapped = apply_gaps(seqs[seqname], tem)
  cat(paste0('Inferred gene ', seqname, ' gapped using ', r[1,]$GENE, ': ', gapped,'\n'))
  return(gapped)
}


# Compare two IMGT gapped sequences and find AA mutations
getMutatedAA <- function(ref_imgt, novel_imgt, ref_name, seq_name, segment, bias) {
  if (grepl("N", ref_imgt)) {
    stop(paste0("Unexpected N in reference sequence ", ref_name))
  }     
  if (grepl("N", novel_imgt)) {
    stop(paste0("Unexpected N in novel sequence ", seq_name))
  }          
  
  if (segment == 'V' && hasNonImgtGaps(ref_imgt)) {
    cat(paste0("Non codon-aligned gaps were found in reference sequence ", ref_name))
  }
  
  if (segment == 'V' && hasNonImgtGaps(novel_imgt)) {
    cat(paste0("Non codon-aligned gaps were found in novel sequence ", seq_name))
  }
  
  ref_imgt <- alakazam::translateDNA(ref_imgt)
  novel_imgt <- alakazam::translateDNA(novel_imgt)
  max_length = max(nchar(ref_imgt), nchar(novel_imgt))
  ref_imgt = str_pad(ref_imgt, max_length, side="right", pad="-")
  novel_imgt = str_pad(novel_imgt, max_length, side="right", pad="-")
  ref_imgt = strsplit(ref_imgt, "")[[1]]
  novel_imgt = strsplit(novel_imgt, "")[[1]]
  
  mutations <- c()
  diff_idx <- which(ref_imgt != novel_imgt)
  if (length(diff_idx)>0) {
    index = sapply((diff_idx-bias), function(x) if(x <= 0) {x-1} else {x} )
    mutations <- paste0(ref_imgt[diff_idx], index,
                        replace(novel_imgt[diff_idx], is.na(novel_imgt[diff_idx]),"-"))
  }
  mutations
}

# Find nearest reference sequences and enumerate differences
find_nearest = function(sequence_ind, ref_genes, prefix, inferred_seqs, segment) {
  sequence = inferred_seqs[[sequence_ind]]
  seq_name = names(inferred_seqs)[[sequence_ind]]
  r = data.frame(GENE=names(ref_genes),SEQ=ref_genes, stringsAsFactors = F)
  
  # pad all Js so that they align on the right
  
  if(segment == 'J') {
    w = as.integer(max(max(nchar(r$SEQ)), nchar(sequence))/3)*3
    r$SEQ = str_pad(r$SEQ, w, 'left', '-')
    sequence = str_pad(sequence, w, 'left', '-')
  }
  
  r$diff = getMutatedPositions(r$SEQ, sequence)
  r$num_diff = sapply(r$diff, length)
  r = r[order(r$num_diff),]
  r = r[1,]
  
  if(segment == 'J') {
    # 'bias' the index position so that the first nucleotide of the reference is 1
    bias = nchar(r$SEQ) - nchar(ref_genes[r$GENE])
  } else {
    bias = 0
  }
  
  nt_diff_string = build_nt_diff_string(r$SEQ, sequence, bias)
  
  diff_aa = getMutatedAA(r$SEQ, sequence, r$GENE, seq_name, segment, (bias/3))
  
  if(length(diff_aa) > 0) {
    aa_diffs = length(diff_aa)
    aa_subs = paste(diff_aa,collapse=",")
  } else {
    aa_diffs = 0
    aa_subs = ""
  }
  
  l = list(closest=r[1,]$GENE, difference=r[1,]$num_diff, nt_diffs=nt_diff_string, aa_difference=aa_diffs, aa_subs=aa_subs)
  names(l) = (paste(prefix, names(l), sep='_'))
  return(l)
}

#######################
# main code starts here

# get the reference set

report('Processing started')

ref_genes = readIgFasta(ref_filename, strip_down_name =F)
set = paste0('IG', substr(chain, 2, 2), segment)
region = paste0(segment, '-REGION')

# process IMGT library, if header is in corresponding format
if(grepl('|', names(ref_genes)[1], fixed=T)) {
  ref_genes = ref_genes[grepl(species, names(ref_genes),fixed=T)]
  ref_genes = ref_genes[grepl(region, names(ref_genes),fixed=T)]  # restrict to V-D-J regions
  ref_genes = ref_genes[grepl(set, names(ref_genes),fixed=T)]
  
  gene_name = function(full_name) {
    return(strsplit(full_name, '|', fixed=T)[[1]][2])
  }
}

names(ref_genes) = sapply(names(ref_genes), gene_name)

# Crude fix for two misaligned human IGHJ reference genes

if(set == 'IGHJ') {
  for(g in c('IGHJ6*02', 'IGHJ6*03')) {
    if(g %in% names(ref_genes) && str_sub(ref_genes[g], start= -1) == 'A') {
      ref_genes[g] = paste0(ref_genes[g], 'G')
      print(paste0('Modified truncated reference gene ', g, ' to ', ref_genes[g]))
    } 
  }
}
  

# get the genotype and novel alleles in this set

if(inferred_filename != '-') {
  inferred_seqs = readIgFasta(inferred_filename, strip_down_name=T)
} else {
  inferred_seqs = c()
}

# ignore inferred genes that are listed in the reference. gap any that aren't already gapped.

inferred_seqs = inferred_seqs[!(names(inferred_seqs) %in% names(ref_genes))]

if(segment == 'V') {
	inferred_seqs = sapply(names(inferred_seqs), imgt_gap_inferred, seqs=inferred_seqs, ref_genes=ref_genes)
}

# Read the sequences. Changeo format is assumed unless airr or IgDiscover format is identified
# TODO - check and give nice error message if any columns are missing

report('reading sequences')

s = read.delim(filename, stringsAsFactors=F)

if('sequence_id' %in% names(s))
{
  # airr format - convert wanted fields to changeo
  # TODO - would be better to get the field ranges from the CIGAR string, given that it's a required field
  # https://www.bioconductor.org/packages/devel/bioc/manuals/GenomicAlignments/man/GenomicAlignments.pdf
  
  # add a dummy D_CALL to light chain repertoires, for ease of processing
  
  if(chain_type == 'L' && !('d_call' %in% names(s))) {
    s$d_call = ''
  }
  
  req_names = c('sequence', 'sequence_id', 'v_call_genotyped', 'd_call', 'j_call', 'sequence_alignment', 'cdr3')
  col_names = c('SEQUENCE_INPUT', 'SEQUENCE_ID', 'V_CALL_GENOTYPED', 'D_CALL', 'J_CALL', 'SEQUENCE_IMGT', 'CDR3_IMGT')

  if(segment != 'V') {
    a_seg = tolower(segment)
    req_names = c(req_names, paste0(a_seg, '_sequence_start'), paste0(a_seg, '_sequence_end'), paste0(a_seg, '_germline_start'), paste0(a_seg, '_germline_end'))
    col_names = c(col_names, 'SEG_SEQ_START', 'SEG_SEQ_END', 'SEG_GERM_START', 'SEG_GERM_END')
  }
  
  s = select(s, req_names)
  names(s) = col_names 
  
  s$SEG_SEQ_LENGTH = s$SEG_SEQ_END - s$SEG_SEQ_START + 1
  s$SEG_GERM_LENGTH = s$SEG_GERM_END - s$SEG_GERM_START + 1
  
} else if('V_gene' %in% names(s)) {
  # IgDiscover format
  #  s = uncount(s, count)  for consistency with IgDiscover results, count each unique record in the file only once, regardless of 'count'
  
  # add a dummy D_CALL to light chane repertoires, for ease of processing
  
  if(chain_type == 'L' && !('D_gene' %in% names(s))) {
    s$D_gene = ''
    s$D_errors = ''
    s$D_region = ''
  }

    if(chain_type == 'L' && !('VDJ_nt' %in% names(s))) {
    s$VDJ_nt = s$VJ_nt
  }
  
  col_names = c('SEQUENCE_ID', 'V_CALL_GENOTYPED', 'D_CALL', 'J_CALL', 'CDR3_IMGT', 'V_MUT_NC', 'D_MUT_NC', 'J_MUT_NC', 'SEQUENCE', 'JUNCTION_START', 'V_SEQ', 'D_SEQ', 'J_SEQ')
  s = select(s, name, V_gene, D_gene, J_gene, CDR3_nt, V_errors, D_errors, J_errors, VDJ_nt, V_CDR3_start, V_nt, D_region, J_nt)
  names(s) = col_names 
  # adjust IgDiscover's V_CDR3_START to the 1- based location of the conserved cysteine
  s$JUNCTION_START = s$JUNCTION_START - 2
  s$SEQUENCE = toupper(s$SEQUENCE)
  
  if(segment == 'V') {
    s = rename(s, c('V_MUT_NC'='SEG_MUT_NC', 'V_SEQ'='SEG_SEQ'))
  } else if(segment == 'D') {
    s = rename(s, c('D_MUT_NC'='SEG_MUT_NC', 'D_SEQ'='SEG_SEQ'))
  } else {
    s = rename(s, c('J_MUT_NC'='SEG_MUT_NC', 'J_SEQ'='SEG_SEQ'))
  }
}

if(segment == 'V') {
  s = rename(s, c('V_CALL_GENOTYPED'='SEG_CALL'))
} else if(segment == 'D') {
  s = rename(s, c('D_CALL'='SEG_CALL'))
} else {
  s = rename(s, c('J_CALL'='SEG_CALL'))
}

if('V_CALL_GENOTYPED' %in% names(s)) {
  if('V_CALL' %in% names(s)) {
    s = subset(s, select = -c('V_CALL'))
  }
  s = rename(s, c('V_CALL_GENOTYPED'='V_CALL'))
}

s$CDR3_IMGT = toupper(s$CDR3_IMGT)

# At this point, s contains Changeo-named columns with all data required for calculations

#remove sequences with ambiguous calls, or no call, in the target segment

s = s[!grepl(',', s$SEG_CALL),]
s = s[!(s$SEG_CALL == ''),]

# Warn if we don't have genotype statistics for any of the inferred alleles
# this can happen, for example, with Tigger, if novel alleles are detected but do not pass subsequent criteria for being included in the genotype.

genotype_alleles = unique(s$SEG_CALL)
missing = inferred_seqs[!(names(inferred_seqs) %in% genotype_alleles)]

if(length(missing) >= 1) {
  cat(paste('Novel sequence(s)', paste0(names(missing), collapse=' '), 'are not listed in the genotype and will be ignored.', sep=' ', '\n'))
  inferred_seqs = inferred_seqs[(names(inferred_seqs) %in% genotype_alleles)]
}

genotype_alleles = genotype_alleles[!(genotype_alleles %in% names(inferred_seqs))]
genotype_seqs = lapply(genotype_alleles, function(x) {ref_genes[x]})
genotype_db = setNames(c(genotype_seqs, inferred_seqs), c(genotype_alleles, names(inferred_seqs)))


# Check we have sequences for all alleles named in the reads - either from the reference set or from the inferred sequences
# otherwise - one of these two is incomplete!

if(any(is.na(genotype_db))) {
  cat(paste0("Sequence(s) for allele(s) ", names(genotype_db[is.na(genotype_db)]), " can't be found in the reference set or the novel alleles file.\n"))
  
  cat('\nAlleles in reads:\n')
  print(unique(names(genotype_db)))
  
  cat('\nAlleles in reference set:\n')
  print(unique(names(ref_genes)))
  
  cat('\nNovel Alleles:\n')
  print(names(inferred_seqs))
  cat('\n')
  stop()
}

# gap the sequences if necessary

find_template = function(call) {
  tem = ref_genes[call]
  if(is.na(tem))
    tem = inferred_seqs[call]
  
  return(tem)
}

s$SEG_REF_IMGT = sapply(s$SEG_CALL, find_template)

if(!('SEQUENCE_IMGT' %in% names(s))) {
  report('gapping the reads')
  s$SEQUENCE_IMGT = mapply(imgt_gap, s$SEQUENCE,s$CDR3_IMGT, s$JUNCTION_START, s$SEG_REF_IMGT)
  report('finished gapping')
}

s$SEQUENCE_IMGT = toupper(s$SEQUENCE_IMGT)

# unmutated count for each allele


if(!('SEG_MUT_NC' %in% names(s))) {
  if(segment == 'V') {
    # We take the count up to the 2nd CYS at 310
    # This matches IgDiscover practice and facilitates Tigger's reassignAlles approach which does not re-analyse the junction with the novel V-allele
    s$SEQUENCE_IMGT_TRUNC = sapply(s$SEQUENCE_IMGT, substring, first=1, last=309)
    s$SEG_MUT_NC = unlist(getMutCount(s$SEQUENCE_IMGT_TRUNC, s$SEG_CALL, genotype_db))
  } else {
    s$SEG_SEQ = mapply(substr, s$SEQUENCE_INPUT, s$SEG_SEQ_START, s$SEG_SEQ_START+s$SEG_SEQ_LENGTH-1)   
    s$SEG_REF_SEQ = mapply(substr, s$SEG_REF_IMGT, s$SEG_GERM_START, s$SEG_GERM_START+s$SEG_GERM_LENGTH-1)   
    s$SEG_MUT_NC = stringdist(s$SEG_SEQ, s$SEG_REF_SEQ, method="hamming")
  }
}

report('calculated mutation count')

# make a space-alignment of D sequences for the usage histogram (V and J use the IMGT alignment)

if(segment == 'D') {
  s$SEG_SEQ_ALIGNED = mapply(paste0, sapply(s$SEG_GERM_START, function(x) {paste(rep(' ', x), collapse='')}), s$SEG_SEQ)
  width = max(str_length(s$SEG_SEQ_ALIGNED))
  s$SEG_SEQ_ALIGNED = sapply(s$SEG_SEQ_ALIGNED, function(x) {str_pad(x, width, side='right')})
}

s0 = s[s$SEG_MUT_NC == 0,]
genotype = s0 %>% group_by(SEG_CALL) %>% summarize(unmutated_sequences = n())

if(any(is.na(genotype$unmutated_sequences))) {
  genotype[is.na(genotype$unmutated_sequences),]$unmutated_sequences = 0
}

total_unmutated = sum(genotype$unmutated_sequences)
genotype$unmutated_frequency = round(100*genotype$unmutated_sequences/total_unmutated, digits=2)

s_totals = s %>% group_by(SEG_CALL) %>% summarize(sequences = n())
genotype = merge(genotype, s_totals, all=T)

genotype$GENE = sapply(genotype$SEG_CALL, function(x) {if(grepl('*', x, fixed=T)) {strsplit(x, '*', fixed=T)[[1]][1]} else {x}})
allelic_totals = genotype %>% group_by(GENE) %>% summarise(allelic_total=sum(sequences))
genotype = merge(genotype, allelic_totals, all=T)
genotype$allelic_percentage = round(100*genotype$sequences/genotype$allelic_total)

su=s[s$SEG_MUT_NC==0,]

if(segment != 'V') {
  genotype$unique_vs = sapply(genotype$SEG_CALL, unique_calls, segment='V_CALL', seqs=s)
  genotype$unique_vs_unmutated = sapply(genotype$SEG_CALL, unique_calls, segment='V_CALL', seqs=su)
}

if(segment != 'D' && chain_type == 'H') {
  genotype$unique_ds = sapply(genotype$SEG_CALL, unique_calls, segment='D_CALL', seqs=s)
  genotype$unique_ds_unmutated = sapply(genotype$SEG_CALL, unique_calls, segment='D_CALL', seqs=su)
}

if(segment != 'J') {
  genotype$unique_js = sapply(genotype$SEG_CALL, unique_calls, segment='J_CALL', seqs=s)
  genotype$unique_js_unmutated = sapply(genotype$SEG_CALL, unique_calls, segment='J_CALL', seqs=su)
}

genotype$unique_cdr3s = sapply(genotype$SEG_CALL, unique_cdrs, segment='CDR3_IMGT', seqs=s)
genotype$unique_cdr3s_unmutated = sapply(genotype$SEG_CALL, unique_cdrs, segment='CDR3_IMGT', seqs=su)

genotype$assigned_unmutated_frequency = round(100*genotype$unmutated_sequences/genotype$sequences, digits=2)

report('determined unique calls')

# closest in genotype and in reference (inferred alleles only)
# Inferred D alleles should be aligned for best match (if this is an allele of an existing D-gene, align against a knon allele of that gene)

if (length(inferred_seqs) == 0) {
  cat('Warning - no inferred sequences found.\n')
  
  genotype$reference_closest = NA
  genotype$host_closest = NA
  genotype$reference_difference = NA
  genotype$reference_nt_diffs = NA
  genotype$reference_aa_difference = NA
  genotype$reference_aa_subs = NA
  genotype$host_difference = NA
} else {
  nearest_ref = data.frame(t(sapply(seq_along(inferred_seqs), find_nearest, ref_genes=ref_genes, prefix='reference', inferred_seqs=inferred_seqs, segment=segment)))
  nearest_ref$SEG_CALL = names(inferred_seqs)
  genotype = merge(genotype, nearest_ref, by='SEG_CALL', all.x=T)
  
  nearest_ref = data.frame(t(sapply(seq_along(inferred_seqs), find_nearest, ref_genes=ref_genes[names(ref_genes) %in% genotype$SEG_CALL], prefix='host', inferred_seqs=inferred_seqs, segment=segment)))
  nearest_ref$SEG_CALL = names(inferred_seqs)
  genotype = merge(genotype, nearest_ref, by='SEG_CALL', all.x=T)
}


genotype$nt_sequence = sapply(genotype$SEG_CALL, function(x) genotype_db[x][[1]])

genotype = dplyr::rename(genotype, sequence_id=SEG_CALL, closest_reference=reference_closest, closest_host=host_closest, 
                   nt_diff=reference_difference, nt_diff_host=host_difference, nt_substitutions=reference_nt_diffs, aa_diff=reference_aa_difference,
                   aa_substitutions=reference_aa_subs)

genotype$unmutated_umis = ''
genotype$nt_sequence = gsub('-', '', genotype$nt_sequence, fixed=T)
genotype$nt_sequence = gsub('.', '', genotype$nt_sequence, fixed=T)
genotype = unnest(genotype)

# Check for duplicate germline sequences

concat_names = function(x) {
  paste(x, collapse=', ')
}

warn_dupes = function(x) {
  cat(paste0('Warning: ', x, ' have identical germline sequences.\n'))
}

dupes = aggregate(genotype["sequence_id"], by=genotype["nt_sequence"], FUN=concat_names)
dupes = dupes$sequence_id[grepl(',', dupes$sequence_id, fixed=T)]

if(length(dupes) > 0) {
  x = lapply(dupes, warn_dupes)  
}

# Postpone writing the genotype file until haplotyping analysis is complete...

# bar charts for all alleles

report('plotting bar charts')

plot_allele_seqs = function(allele, s, inferred_seqs, genotype) {
  g = genotype[genotype$sequence_id==allele,]
  recs = s[s$SEG_CALL==allele,]
  recs = recs[recs$SEG_MUT_NC < 21,]

  if(nrow(recs) == 0) {
    return(NA)
  }
  
  if(is.na(g$unmutated_sequences)) {
    g$unmutated_sequences = 0
  }
  
  if(g$unmutated_sequences != 0) {
    if(segment == 'V') {  
      label_text = paste0(g$unmutated_sequences, ' (', round(g$unmutated_sequences*100/g$sequences, digits=1), '%) exact matches, in which:\n',
                          g$unique_cdr3s_unmutated, ' unique CDR3\n',
                          g$unique_js_unmutated, ' unique J')
    } else {
      label_text = paste0(g$unmutated_sequences, ' (', round(g$unmutated_sequences*100/g$sequences, digits=1), '%) exact matches, in which:\n',
                          g$unique_cdr3s_unmutated, ' unique CDR3\n',
                          g$unique_vs_unmutated, ' unique V')
    }
  } else {
    label_text = 'No exact matches.\n'
  }
  
  g = ggplot(data=recs, aes(x=SEG_MUT_NC)) + 
    geom_bar(width=1.0) +
    labs(x='Nucleotide Difference', 
         y='Count', 
         title=allele,
         subtitle=paste0(g$sequences, ' sequences assigned\n', label_text)) +
         theme_classic(base_size=12) +
    theme(aspect.ratio = 1/1, plot.subtitle=element_text(size=8)) 
  

  return(ggplotGrob(g))
}

barplot_grobs = lapply(sort_alleles(names(genotype_db)), plot_allele_seqs, s=s, inferred_seqs=inferred_seqs, genotype=genotype)
barplot_grobs=barplot_grobs[!is.na(barplot_grobs)]

# nucleotide composition plots for novel alleles

report('nucleotide plots')

nuc_at = function(seq, pos, filter) {
  if(length(seq) >= pos) {
    if(filter) {
      if(seq[pos] %in% c('N', 'X', '.', '-')) {
        return(NA)
      }
    } 
    return(seq[pos])
  } else {
    return(NA)
  }
}

nucs_at = function(seqs, pos, filter) {
  if(filter) {
    ret = data.frame(pos=as.character(c(pos)), nuc=(factor(sapply(seqs, nuc_at, pos=pos, filter=filter), levels=c('A', 'C', 'G', 'T'))))
  } else {
    ret = data.frame(pos=as.character(c(pos)), nuc=(factor(sapply(seqs, nuc_at, pos=pos, filter=filter), levels=c('A', 'C', 'G', 'T', 'N', 'X', '.', '-'))))
  }
  ret = ret[!is.na(ret$nuc),]
  return(ret)
}

label_nuc = function(pos, ref) {
  return(paste0(pos, "\n", ref[[1]][pos]))
}

report('base composition')

# Plot base composition from nominated nucleotide position to the end or to optional endpos.
# Only include gaps, n nucleotides if filter=F
# if pos is negative, SEQUENCE_IMGT contains a certain number of trailing nucleotides. Plot them all.
plot_base_composition = function(gene_name, recs, ref, pos=1, filter=T, end_pos=999, r_justify=F) {
  max_pos = nchar(ref)
  
  if(max_pos < pos || length(recs) < 1) {
    return(NA)
  }
  
  max_pos = min(max_pos, end_pos)
  min_pos = max(pos, 1)
  
  if(r_justify) {
    recs = str_pad(recs, max_pos-min_pos+1, 'left')
  }

  recs = strsplit(recs, "")
  ref = strsplit(ref, "")
  
  x = do.call('rbind', lapply(seq(min_pos,max_pos), nucs_at, seqs=recs, filter=filter))

  g = ggplot(data=x, aes(x=pos, fill=nuc)) + 
		   scale_fill_brewer(palette='Dark2') +
           geom_bar(stat="count") +
           labs(x='Position', y='Count', fill='', title=paste0('Gene ', gene_name)) +
           theme_classic(base_size=12) + 
           scale_y_continuous(expand=c(0,0)
    )
  
  if(filter) {
    b =sapply(seq(pos,max_pos), label_nuc, ref=ref)
    g = g + scale_x_discrete(labels=b)
  } else {
    g = g +   theme(axis.text.x=element_blank(), axis.ticks.x=element_blank())
  }
  
  return(ggplotGrob(g))
}


label_5_nuc = function(pos, ref) {
  if(pos %% 5 == 0) {
    n = pos
  } else {
    n = ''
  }
  
  return(paste0(n, "\n", ref[[1]][pos]))
}

report('segment composition')

# Plot composition of a segment rather than the whole IMGT-aligned sequence
plot_segment_composition = function(gene_name, recs, ref, pos=1,  filter=T, end_pos=999, r_justify=F) {
  max_pos = nchar(ref)
  
  if(max_pos < pos || length(recs) < 1) {
    return(NA)
  }
  
  max_pos = min(max_pos, end_pos)
  min_pos = max(pos, 1)
  
  if(r_justify) {
    recs = str_pad(recs, max_pos-min_pos+1, 'left')
  }

  recs = strsplit(recs, "")
  ref = strsplit(ref, "")
  
  x = do.call('rbind', lapply(seq(min_pos,max_pos), nucs_at, seqs=recs, filter=filter))
  
  g = ggplot(data=x, aes(x=pos, fill=nuc)) + 
    scale_fill_brewer(palette='Dark2') +
    geom_bar(stat="count") +
    labs(x='Position', y='Count', fill='', title=paste0('Gene ', gene_name)) +
    theme_classic(base_size=12) + 
    scale_y_continuous(expand=c(0,0)
    )
  
  b =sapply(seq(pos, max_pos), label_5_nuc, ref=ref)
  g = g + scale_x_discrete(labels=b)
  
  return(ggplotGrob(g))
}

report('whole composition')

whole_composition_grobs = c()
end_composition_grobs = c()

if('SEQUENCE_IMGT' %in% names(s)) {
  if(segment == 'V') {
    recs = lapply(names(inferred_seqs), function(x) {s[s$SEG_CALL==x,]$SEQUENCE_IMGT})
    refs = lapply(names(inferred_seqs), function(x) {inferred_seqs[x]})

    end_composition_grobs = mapply(plot_base_composition, names(inferred_seqs), recs, refs, pos=313, filter=T)
    end_composition_grobs = end_composition_grobs[!is.na(end_composition_grobs)]

    whole_composition_grobs = mapply(plot_base_composition, names(inferred_seqs), recs, refs, pos=1, filter=F)
    whole_composition_grobs = whole_composition_grobs[!is.na(whole_composition_grobs)]
  } else if(segment == 'J') {
    recs = lapply(names(inferred_seqs), function(x) {s[s$SEG_CALL==x,]$SEG_SEQ})
    refs = lapply(names(inferred_seqs), function(x) {inferred_seqs[x]})

    whole_composition_grobs = mapply(plot_segment_composition, names(inferred_seqs), recs, refs, pos=1, filter=F, r_justify=T)
    whole_composition_grobs = whole_composition_grobs[!is.na(whole_composition_grobs)]
  } else if(segment == 'D') {
    recs = lapply(names(inferred_seqs), function(x) {s[s$SEG_CALL==x,]$SEG_SEQ_ALIGNED})
    refs = lapply(names(inferred_seqs), function(x) {inferred_seqs[x]})
    
    whole_composition_grobs = mapply(plot_segment_composition, names(inferred_seqs), recs, refs, pos=1, filter=F)
    whole_composition_grobs = whole_composition_grobs[!is.na(whole_composition_grobs)]
  }
}

report('haplotype plots')

# haplotype plots

if(segment == 'V' || segment == 'D') {
  sa = s[!grepl(',', s$J_CALL),]            # unique J-calls only
  sa = rename(sa, J_CALL='A_CALL')
} else {
  sa = s[!grepl(',', s$V_CALL),]            
  sa = rename(sa, V_CALL='A_CALL')
}

sa$a_gene = sapply(sa$A_CALL, function(x) {strsplit(x, '*', fixed=T)[[1]][[1]]})
sa$a_allele = sapply(sa$A_CALL, function(x) {strsplit(x, '*', fixed=T)[[1]][[2]]})
sa$a_gene = factor(sa$a_gene, sort_alleles(unique(sa$a_gene)))

su = select(sa, A_CALL, a_gene, a_allele)
a_genes = sort(unlist(unique(su$a_gene)))


# calc percentage of each allele in a gene
allele_props = function(gene, su) {
  alleles = su %>% filter(a_gene==gene) %>% group_by(a_allele) %>% summarise(count=n())
  alleles$a_gene = gene
  total = sum(alleles$count)
  alleles$percent = 100*alleles$count/total
  return(alleles)
} 

a_props = do.call('rbind', lapply(a_genes, allele_props, su=su))

if(segment == 'V') {
  theme = theme(legend.title = element_blank(), plot.margin=margin(1,4,19,4, 'cm'), axis.text.x = element_text(angle = 270, hjust = 0,vjust=0.5))
} else {
  theme = theme(legend.title = element_blank(), plot.margin=margin(4,1,15,1, 'cm'), axis.text.x = element_text(angle = 270, hjust = 0,vjust=0.5, size=7))
}

# color_brewer doesn't work with large numbers of categories

if(length(unique(a_props$a_allele)) > 6) {
a_allele_plot = ggplot() + geom_bar(aes(y=percent, x=a_gene, fill=a_allele), data=a_props, stat='identity') + 
  labs(x='Gene', 
       y='Allele %', 
       title='Allele Usage') +
  theme_classic(base_size=15) +
  theme
} else {
  a_allele_plot = ggplot() + geom_bar(aes(y=percent, x=a_gene, fill=a_allele), data=a_props, stat='identity') + 
    scale_fill_brewer(palette='Dark2') +
    labs(x='Gene', 
         y='Allele %', 
         title='Allele Usage') +
    theme_classic(base_size=15) +
    theme
}

sa = sa[!grepl(',', sa$SEG_CALL),]        # remove ambiguous V-calls
sa$SEG_CALL = factor(sa$SEG_CALL, sort_alleles(unique(sa$SEG_CALL)))

report('differential plots')

# differential plot by allele usage - if we have good alleles for this gene

plot_differential = function(gene, a_props, sa) {
  ap = a_props[a_props$a_gene==gene,]
  ap = ap[order(ap$percent, decreasing=T),]

  if(nrow(ap) < 2 || ap[1,]$percent > 75 || ap[2,]$percent < 20) {
    return(NA)
  }

  if(segment == 'V') {
    margins = 1
  } else {
    margins = 4
  }
  
    
  a1 = ap[1,]$a_allele
  a2 = ap[2,]$a_allele
  recs = sa %>% filter(a_gene==gene) %>% filter(a_allele==a1 | a_allele==a2)
  recs = recs %>% select(SEG_CALL, a_allele) %>% group_by(SEG_CALL, a_allele) %>% summarise(count=n())
  recs$pos = sapply(recs$a_allele, function(x) {if(x==a1) {1} else {-1}})
  recs$count = recs$count * recs$pos
  
  # don't let columns get too broad
  ncols = nrow(recs)
  if(ncols < 15) {
    width = 21 - 2*margins
    width = width * ncols/15
    margins = (21 - width)/2
  }
  
  g = ggplot(recs, aes(x=SEG_CALL, y=count, fill=a_allele)) + 
      geom_bar(stat='identity', position='identity') +
      scale_fill_brewer(palette='Dark2') +
     labs(x='', 
         y='Count', 
         title=paste0('Sequence Count by ', gene, ' allele usage'),
         fill = 'Allele') +
      theme(panel.border = element_blank(), panel.grid.major = element_blank(), panel.grid.minor = element_blank(), 
          panel.background = element_blank(), axis.ticks = element_blank(), legend.position=c(0.9, 0.9),
          axis.text=element_text(size=4), axis.title =element_text(size=15), axis.text.x = element_text(angle = 270, hjust = 0,vjust=0.5),
          plot.margin=margin(1,margins,15,margins, 'cm'))
  return(ggplotGrob(g))
}

haplo_grobs = lapply(a_genes, plot_differential, a_props=a_props, sa=sa)
haplo_grobs = haplo_grobs[!is.na(haplo_grobs)]

report('saving graphics')

# Save all graphics to plot file

x=pdf(paste0(file_prefix, '_ogrdb_plots.pdf'), width=210/25,height=297/25) 
if('SEQUENCE_IMGT' %in% names(s)) {
  if(length(end_composition_grobs) > 0) {
    x=print(marrangeGrob(end_composition_grobs, nrow=3, ncol=2,top=NULL))
  }
  if(length(whole_composition_grobs) > 0) {
    x=print(marrangeGrob(whole_composition_grobs, nrow=3, ncol=1,top=NULL))
  }
} 

if(length(barplot_grobs) > 0) {
  x = print(marrangeGrob(barplot_grobs, nrow=3, ncol=3,top=NULL))
}

#x=print(marrangeGrob(snap_composition_grobs, nrow=3, ncol=1,top=NULL))
grid.arrange(a_allele_plot)
x=print(marrangeGrob(haplo_grobs, nrow=1, ncol=1,top=NULL))
x=dev.off()



# Haplotyping analysis for genotype file

genotype$haplotyping_gene = ''
genotype$haplotyping_ratio = ''

if(!is.na(hap_gene)) {
  ap = a_props[a_props$a_gene==hap_gene,]
  ap = ap[order(ap$percent, decreasing=T),]
  
  if(nrow(ap) < 2 || ap[1,]$percent > 75 || ap[2,]$percent < 20 || (ap[1,]$percent+ap[2,]$percent < 90)) {
    cat(paste0('Alelleic ratio is unsuitable for haplotyping analysis based on ', hap_gene, '\n'))
  } else
  {
    genotype$haplotyping_gene = hap_gene
    genotype = select(genotype, -c(haplotyping_ratio))
    
    a1 = ap[1,]$a_allele
    a2 = ap[2,]$a_allele
    cat(paste0('Haplotyping analysis is based on gene ', hap_gene, ' alleles ', a1, ':', a2, '\n'))
    recs = sa %>% filter(a_gene==hap_gene) %>% filter(a_allele==a1 | a_allele==a2)
    recs = recs %>% select(sequence_id=SEG_CALL, a_allele) %>% group_by(sequence_id, a_allele) %>% summarise(count=n()) %>% spread(a_allele, count)
    recs[is.na(recs)] = 0
    names(recs) = c('sequence_id', 'a1', 'a2')
    recs$totals = recs$a1 + recs$a2
    recs$a1 = round(100 * recs$a1/ recs$totals, 0)    
    recs$a2 = round(100 * recs$a2/ recs$totals, 0)
    recs$haplotyping_ratio = paste0(' ', recs$a1, ':', recs$a2, ' ')
    recs = recs %>% select(sequence_id, haplotyping_ratio)
    genotype = merge(genotype, recs)
  }
}
  
  
report('saving stats')  

# Save Genotype file
genotype = genotype[order_alleles(DataFrame(genes=as.character(genotype$sequence_id))),]

if(chain_type == 'H') {
  if(segment == 'V') {
    g = select(genotype, sequence_id, sequences, closest_reference, closest_host, nt_diff, nt_diff_host, nt_substitutions, aa_diff,
             aa_substitutions, assigned_unmutated_frequency, unmutated_frequency, unmutated_sequences, unmutated_umis, allelic_percentage, unique_ds,
             unique_js,unique_cdr3s, unique_ds_unmutated, unique_js_unmutated, unique_cdr3s_unmutated, haplotyping_gene, haplotyping_ratio, nt_sequence)
  } else if(segment == 'D') {
    g = select(genotype, sequence_id, sequences, closest_reference, closest_host, nt_diff, nt_diff_host, nt_substitutions, aa_diff,
               aa_substitutions, assigned_unmutated_frequency, unmutated_frequency, unmutated_sequences, unmutated_umis, allelic_percentage, unique_vs,
               unique_js,unique_cdr3s, unique_vs_unmutated, unique_js_unmutated, unique_cdr3s_unmutated, haplotyping_gene, haplotyping_ratio, nt_sequence)
  } else if(segment == 'J') {
    g = select(genotype, sequence_id, sequences, closest_reference, closest_host, nt_diff, nt_diff_host, nt_substitutions, aa_diff,
               aa_substitutions, assigned_unmutated_frequency, unmutated_frequency, unmutated_sequences, unmutated_umis, allelic_percentage, unique_vs,
               unique_ds,unique_cdr3s, unique_vs_unmutated, unique_ds_unmutated, unique_cdr3s_unmutated, haplotyping_gene, haplotyping_ratio, nt_sequence)
  } 
} else {
  if(segment == 'V') {
    g = select(genotype, sequence_id, sequences, closest_reference, closest_host, nt_diff, nt_diff_host, nt_substitutions, aa_diff,
               aa_substitutions, assigned_unmutated_frequency, unmutated_frequency, unmutated_sequences, unmutated_umis, allelic_percentage, 
               unique_js,unique_cdr3s, unique_js_unmutated, unique_cdr3s_unmutated, haplotyping_gene, haplotyping_ratio, nt_sequence)
  } else if(segment == 'J') {
    g = select(genotype, sequence_id, sequences, closest_reference, closest_host, nt_diff, nt_diff_host, nt_substitutions, aa_diff,
               aa_substitutions, assigned_unmutated_frequency, unmutated_frequency, unmutated_sequences, unmutated_umis, allelic_percentage, unique_vs,
               unique_cdr3s, unique_vs_unmutated, unique_cdr3s_unmutated, haplotyping_gene, haplotyping_ratio, nt_sequence)
  } 
}

g[is.na(g)] = ''

write.csv(g, paste0(file_prefix, '_ogrdb_report.csv'), row.names=F)



