# This software is licensed under the CC BY-SA 4.0 licence: https://creativecommons.org/licenses/by-sa/4.0/
#
# Some functions are adapted from TIgGER (https://tigger.readthedocs.io) with thanks to the authors.


# genotype_statistics.R - Derive statistics required by OGRDB for submission of novel alleles
#
# Command Syntax:
#
# Rscript genotype_statistics.R <ref_library> <species> <filename> (with no extension on <filename>)
#
# <ref_library> - IMGT-aligned reference genes in FASTA format. Header can either be in IMGT's germline library format,
# or simply the allele name. Reference genes in this file MUST correspond to those used to annotate the reads.
# The IMGT set can be downloaded from http://www.imgt.org/download/GENE-DB/IMGTGENEDB-ReferenceSequences.fasta-nt-WithoutGaps-F+ORF+inframeP
# and used as-is: the script will filter out the records for the nominated species.
#
# <species> This field must be present but is only used to filter records from an IMGT style reference library. It should contain the
# species name used in field 3 of the header, with spaces removed, e.g. Homosapiens for Human.
#
# <filename> - annotated reads in either AIRR or CHANGEO format. The format is detected by the script.
#
# AIRR format files must contain the following columns:
# sequence_id, v_call_genotyped, d_call, j_call, sequence_alignment, cdr3
#
# Correspondingly, CHANGEO files must contain the following columns:
#
# SEQUENCE_ID, V_CALL_GENOTYPED, D_CALL, J_CALL, SEQUENCE_IMGT, CDR3_IMGT
#
# In both file formats, v_call_genotyped/V_CALL_GENOTYPED should contain the V calls made after the subject's genotype has been inferred
# (including calls of the novel alleles)
#
# The command creates:
#
# <filename>_ogrdb_report.csv - this contains the file ready to be uploaded to OGRDB.


library(tigger)
library(alakazam)
library(tidyr)
library(dplyr)
library(stringr)


args = commandArgs(trailingOnly=TRUE)

if(length(args) > 0) {
  ref_filename = args[1]
  species = args[2]
  inferred_filename = args[3]
  filename = args[4]
} else {
  work_dir = 'D:/Research/ogre/scripts'
  setwd(work_dir)
  
  ref_filename = 'IMGT_REF_GAPPED.fasta'
  species = 'Homosapiens'
  inferred_filename = 'TWO01A - naive_novel.fasta'
  filename = 'TWO01A - naive_genotyped.tsv'
} 

file_prefix = strsplit(filename, '.', fixed=T)[[1]][1]


# count unique J and D calls
unique_calls = function(gene, segment, seqs) {
  calls = unique(seqs[seqs$V_CALL_GENOTYPED==gene,][segment])
  calls = calls[!grepl(',', calls[,segment]),]       # count unambiguous calls only
  calls = calls[grepl('IGH', calls)]                 #don't count blank calls
  return(length(calls))
}

# count unique CDRs
unique_cdrs = function(gene, segment, seqs) {
  calls = unique(seqs[seqs$V_CALL_GENOTYPED==gene,][segment])
  calls = calls[nchar(calls[,segment]) > 0,]
  return(length(calls))
}

# create list of nt differences between two strings
build_nt_diff_string = function(seq1, seq2) {
  nt_diff_string = ""
  max_length = max(nchar(seq1), nchar(seq2))
  seq1 = str_pad(seq1, max_length, side="right", pad="-")
  seq2 = str_pad(seq2, max_length, side="right", pad="-")
  nt_diff = unlist(getMutatedPositions(seq1, seq2,ignored_regex="\\."))
  ref_nt <- strsplit(seq1,"")[[1]][nt_diff]
  novel_nt <- strsplit(seq2,"")[[1]][nt_diff]
  
  if(length(nt_diff) > 0) {
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

# Compare two IMGT gapped sequences and find AA mutations
getMutatedAA <- function(ref_imgt, novel_imgt) {
  if (grepl("N", ref_imgt)) {
    stop("Unexpected N in ref_imgt")
  }     
  if (grepl("N", novel_imgt)) {
    stop("Unexpected N in novel_imgt")
  }          
  
  if (hasNonImgtGaps(ref_imgt)) {
    warning("Non IMGT gaps found in ref_imgt")
  }
  
  if (hasNonImgtGaps(novel_imgt)) {
    warning("Non IMGT gaps found in novel_imgt")
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
    mutations <- paste0(ref_imgt[diff_idx], diff_idx,
                        replace(novel_imgt[diff_idx], is.na(novel_imgt[diff_idx]),"-"))
  }
  mutations
}

# Find nearest reference sequences and enumerate differences
find_nearest = function(sequence, ref_genes, prefix) {
  r = data.frame(GENE=names(ref_genes),SEQ=ref_genes, stringsAsFactors = F)
  r$diff = getMutatedPositions(r$SEQ, sequence)
  r$num_diff = sapply(r$diff, length)
  r = r[order(r$num_diff),]
  
  nt_diff_string = build_nt_diff_string(ref_genes[[r[1,]$GENE]], sequence)
  
  diff_aa = getMutatedAA(ref_genes[[r[1,]$GENE]], sequence)
  
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


s = read.delim(filename, stringsAsFactors=F)

if('sequence_id' %in% names(s))
{
  # airr format - convert wanted fields to changeo
  
  wanted_cols = c('sequence_id', 'v_call_genotyped', 'd_call', 'j_call', 'sequence_alignment', 'cdr3')
  col_names = c('SEQUENCE_ID', 'V_CALL_GENOTYPED', 'D_CALL', 'J_CALL', 'SEQUENCE_IMGT', 'CDR3_IMGT')
  
  s = select(seqs, sequence_id, v_call_genotyped, d_call, j_call, sequence_alignment, cdr3)
  names(s) = col_names 
}

# get the reference set

ref_genes = readIgFasta(ref_filename, strip_down_name =F)

# process IMGT library, if header is in corresponding format
if(grepl('|', names(ref_genes)[1], fixed=T)) {
  ref_genes = ref_genes[grepl(species, names(ref_genes),fixed=T)]
  
  gene_name = function(full_name) {
    return(strsplit(full_name, '|', fixed=T)[[1]][2])
  }
}

names(ref_genes) = sapply(names(ref_genes), gene_name)
ref_genes = ref_genes[grepl('IGHV|IGHJ|IGHD', names(ref_genes))]


#remove sequences with ambiguous V-calls
s = s[!grepl(',', s$V_CALL_GENOTYPED),]

# get the genotype and novel alleles in this set

inferred_seqs = readIgFasta(inferred_filename, strip_down_name=F)

genotype_alleles = unique(s$V_CALL_GENOTYPED)
genotype_alleles = genotype_alleles[!(genotype_alleles %in% names(inferred_seqs))]
genotype_seqs = lapply(genotype_alleles, function(x) {ref_genes[x]})
genotype_db = setNames(c(genotype_seqs, inferred_seqs), c(genotype_alleles, names(inferred_seqs)))

# Check we have sequences for all alleles named in the reads - either from the reference set or from the inferred sequences
# otherwise - one of these two is incomplete!


if(any(is.na(genotype_db))) {
  stop(paste0("Sequence(s) for allele(s) ", names(genotype_db[is.na(genotype_db)]), " can't be found in the reference set or the novel alleles file."))
}

# unmutated count for each allele
s$V_MUT_NC = unlist(getMutCount(s$SEQUENCE_IMGT, s$V_CALL_GENOTYPED, genotype_db))
s0 = s[s$V_MUT_NC == 0,]
genotype = s0 %>% group_by(V_CALL_GENOTYPED) %>% summarize(unmutated_sequences = n())

if(any(is.na(genotype$unmutated_sequences))) {
  genotype[is.na(genotype$unmutated_sequences),]$unmutated_sequences = 0
}

total_unmutated = sum(genotype$unmutated_sequences)
genotype$unmutated_frequency = round(100*genotype$unmutated_sequences/total_unmutated, digits=2)

s_totals = s %>% group_by(V_CALL_GENOTYPED) %>% summarize(sequences = n())
genotype = merge(genotype, s_totals, all=T)

genotype$GENE = sapply(genotype$V_CALL_GENOTYPED, function(x) {if(grep('*', x, fixed=T)) {strsplit(x, '*', fixed=T)[[1]][1]} else {x}})
allelic_totals = genotype %>% group_by(GENE) %>% summarise(allelic_total=sum(sequences))
genotype = merge(genotype, allelic_totals, all=T)
genotype$allelic_percentage = round(100*genotype$sequences/genotype$allelic_total)

genotype$unique_ds = sapply(genotype$V_CALL_GENOTYPED, unique_calls, segment='D_CALL', seqs=s)
genotype$unique_js = sapply(genotype$V_CALL_GENOTYPED, unique_calls, segment='J_CALL', seqs=s)
genotype$unique_cdr3s = sapply(genotype$V_CALL_GENOTYPED, unique_cdrs, segment='CDR3_IMGT', seqs=s)

# closest in genotype and in reference (inferred alleles only)

if (length(inferred_seqs) == 0) {
  warning('Warning - no inferred sequences found.')
  
  genotype$reference_closest = NA
  genotype$host_closest = NA
  genotype$reference_difference = NA
  genotype$reference_nt_diffs = NA
  genotype$reference_aa_difference = NA
  genotype$reference_aa_subs = NA
} else {
  nearest_ref = data.frame(t(sapply(inferred_seqs, find_nearest, ref_genes=ref_genes, prefix='reference')))
  nearest_ref$V_CALL_GENOTYPED = rownames(nearest_ref)
  genotype = merge(genotype, nearest_ref, by='V_CALL_GENOTYPED', all.x=T)
  
  nearest_ref = data.frame(t(sapply(inferred_seqs, find_nearest, ref_genes=ref_genes[names(ref_genes) %in% genotype$V_CALL_GENOTYPED], prefix='host')))
  nearest_ref$V_CALL_GENOTYPED = rownames(nearest_ref)
  genotype = merge(genotype, nearest_ref, by='V_CALL_GENOTYPED', all.x=T)
}


genotype$nt_sequence = sapply(genotype$V_CALL_GENOTYPED, function(x) genotype_db[x][[1]])

genotype = rename(genotype, sequence_id=V_CALL_GENOTYPED, closest_reference=reference_closest, closest_host=host_closest, 
                   nt_diff=reference_difference, nt_substitutions=reference_nt_diffs, aa_diff=reference_aa_difference,
                   aa_substitutions=reference_aa_subs)
genotype$unmutated_umis = ''
genotype$haplotyping_gene = ''
genotype$haplotyping_ratio = ''

genotype = unnest(genotype)
g = select(genotype, sequence_id, sequences, closest_reference, closest_host, nt_diff, nt_substitutions, aa_diff,
           aa_substitutions, unmutated_frequency, unmutated_sequences, unmutated_umis, allelic_percentage, unique_ds,
           unique_js,unique_cdr3s, haplotyping_gene, haplotyping_ratio, nt_sequence)
g[is.na(g)] = ''

write.csv(g, paste0(file_prefix, '_ogrdb_report.csv'))


