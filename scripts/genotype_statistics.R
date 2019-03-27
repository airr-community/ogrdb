# This software is licensed under the CC BY-SA 4.0 licence: https://creativecommons.org/licenses/by-sa/4.0/
#
# Some functions are adapted from TIgGER (https://tigger.readthedocs.io) with thanks to the authors.


# genotype_statistics.R - Derive statistics required by OGRDB for submission of novel alleles
#
# Command Syntax:
#
# Rscript genotype_statistics.R <ref_library> <species> <filename> [<haplotype-allele>]
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
# <filename> - annotated reads in either AIRR or CHANGEO format. The format is detected by the script.
#
# <halplotype-gene> - optional argument. If present, the haplotyping columns will be completed based on the usage of the two most frequent alleles of this J-gene
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
#
# <filename>_ogrdb_plots.pdf - plots showing distribution of close variants of inferred genes, and potential for haplotype analysis


library(tigger)
library(alakazam)
library(tidyr)
library(dplyr)
library(stringr)
library(grid)
library(gridExtra)


args = commandArgs(trailingOnly=TRUE)

if(length(args) > 3) {
  ref_filename = args[1]
  species = args[2]
  inferred_filename = args[3]
  filename = args[4]
  hap_gene = NA
  
  if(length(args >4)) {
    hap_gene = args[5]
  }
} else 
  {   # for R Studio Source
  work_dir = 'D:/Research/Rubelt twin study/work/TW05A'
  setwd(work_dir)
  
  ref_filename = '../../repo/IMGT_REF_GAPPED.fasta'
  species = 'Homosapiens'
  inferred_filename = 'TW05A_novel.fasta'
  filename = 'TW05A_genotyped.tsv'
  hap_gene = 'IGHJ6'
} 

file_prefix = strsplit(filename, '.', fixed=T)[[1]][1]

pdf(NULL) # this seems to stop an empty Rplots.pdf from being created. I don't know why.

# a reasonable order for the v-alleles

numify = function(gene) {
  gg = strsplit(gsub('IGHV', '', gene, fixed=T), split='-', fixed=T)
  gs = c(gg[[1]][[1]])
  gg = strsplit(gg[[1]][[2]], split='*', fixed=T)
  gs = c(gs, gg[[1]])
  
  for(i in 1:3) {
    gs[i] = str_pad(gs[i], 4, pad = "0")
  }
  
  return(paste0(gs, collapse=''))
}


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
getMutatedAA <- function(ref_imgt, novel_imgt, ref_name, seq_name) {
  if (grepl("N", ref_imgt)) {
    stop(paste0("Unexpected N in reference sequence ", ref_name))
  }     
  if (grepl("N", novel_imgt)) {
    stop(paste0("Unexpected N in novel sequence ", seq_name))
  }          
  
  if (hasNonImgtGaps(ref_imgt)) {
    warning(paste0("Non codon-aligned gaps were found in reference sequence ", ref_name))
  }
  
  if (hasNonImgtGaps(novel_imgt)) {
    warning(paste0("Non codon-aligned gaps were found in novel sequence ", seq_name))
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
find_nearest = function(sequence_ind, ref_genes, prefix, inferred_seqs) {
  sequence = inferred_seqs[[sequence_ind]]
  seq_name = names(inferred_seqs)[[sequence_ind]]
  r = data.frame(GENE=names(ref_genes),SEQ=ref_genes, stringsAsFactors = F)
  r$diff = getMutatedPositions(r$SEQ, sequence)
  r$num_diff = sapply(r$diff, length)
  r = r[order(r$num_diff),]
  
  nt_diff_string = build_nt_diff_string(ref_genes[[r[1,]$GENE]], sequence)
  
  diff_aa = getMutatedAA(ref_genes[[r[1,]$GENE]], sequence, r[1,]$GENE, seq_name)
  
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

s$SEQUENCE_IMGT = toupper(s$SEQUENCE_IMGT )
s$CDR3_IMGT = toupper(s$CDR3_IMGT)

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

# remove sequences with ambiguous nucleotide calls
#s = s[!grepl('[nN]', s$SEQUENCE_IMGT),]

# get the genotype and novel alleles in this set

if(inferred_filename != '-') {
  inferred_seqs = readIgFasta(inferred_filename, strip_down_name=F)
} else {
  inferred_seqs = c()
}

genotype_alleles = unique(s$V_CALL_GENOTYPED)

# Warn if we don't have genotype statistics for any of the inferred alleles
# this can happen, for example, with Tigger, if novel alleles are detected but do not pass subsequent criteria for being included in the genotype.

missing = inferred_seqs[!(names(inferred_seqs) %in% genotype_alleles)]

if(length(missing) >= 1) {
  warning(paste('Novel sequence(s)', paste0(names(missing), collapse=' '), 'are not listed in the genotype and will be ignored.', sep=' '))
  inferred_seqs = inferred_seqs[(names(inferred_seqs) %in% genotype_alleles)]
}

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

genotype$assigned_unmutated_frequency = round(100*genotype$unmutated_sequences/genotype$sequences, digits=2)

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
  nearest_ref = data.frame(t(sapply(seq_along(inferred_seqs), find_nearest, ref_genes=ref_genes, prefix='reference', inferred_seqs=inferred_seqs)))
  nearest_ref$V_CALL_GENOTYPED = names(inferred_seqs)
  genotype = merge(genotype, nearest_ref, by='V_CALL_GENOTYPED', all.x=T)
  
  nearest_ref = data.frame(t(sapply(seq_along(inferred_seqs), find_nearest, ref_genes=ref_genes[names(ref_genes) %in% genotype$V_CALL_GENOTYPED], prefix='host', inferred_seqs=inferred_seqs)))
  nearest_ref$V_CALL_GENOTYPED = names(inferred_seqs)
  genotype = merge(genotype, nearest_ref, by='V_CALL_GENOTYPED', all.x=T)
}

genotype$nt_sequence = sapply(genotype$V_CALL_GENOTYPED, function(x) genotype_db[x][[1]])

genotype = rename(genotype, sequence_id=V_CALL_GENOTYPED, closest_reference=reference_closest, closest_host=host_closest, 
                   nt_diff=reference_difference, nt_substitutions=reference_nt_diffs, aa_diff=reference_aa_difference,
                   aa_substitutions=reference_aa_subs)

genotype$unmutated_umis = ''
genotype$nt_sequence = gsub('-', '', genotype$nt_sequence, fixed=T)
genotype$nt_sequence = gsub('.', '', genotype$nt_sequence, fixed=T)
genotype = unnest(genotype)

# Postpone writing the genotype file until haplotyping analysis is complete...

# bar charts for all alleles

plot_allele_seqs = function(allele, s, inferred_seqs, genotype) {
  g = genotype[genotype$sequence_id==allele,]
  recs = s[s$V_CALL_GENOTYPED==allele,]
  recs = recs[recs$V_MUT_NC < 21,]

  label_text = paste0(g$unmutated_sequences, ' (', round(g$unmutated_sequences*100/g$sequences, digits=1), '%) exact matches\n',
                      g$unique_cdr3s, ' unique CDR3\n',
                      g$unique_js, ' unique J')
  
  g = ggplot(data=recs, aes(x=V_MUT_NC)) + 
    geom_bar(width=1.0) +
    labs(x='Nucleotide Difference', 
         y='Frequency', 
         title=paste0('Gene ', allele),
         subtitle=paste0(g$sequences, ' sequences assigned')) +
    theme_classic(base_size=12) +
    theme(aspect.ratio = 1/1) +
    geom_label(label=label_text, aes(x=Inf,y=Inf,hjust=1,vjust=1), size=2)
  
  return(ggplotGrob(g))
}

barplot_grobs = lapply(names(genotype_db)[order(sapply(names(genotype_db), numify))], plot_allele_seqs, s=s, inferred_seqs=inferred_seqs, genotype=genotype)

# nucleotide composition plots for novel alleles

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

# Plot base composition from nominated nucleotide position to the end or to optional endpos.
# Only include gaps, n nucleotides if filter=F
plot_base_composition = function(s, gene_sequences, pos, gene_name, filter, end_pos=999) {
  max_pos = nchar(gene_sequences[gene_name])
  
  if(max_pos < pos) {
    return(NA)
  }
  
  max_pos = min(max_pos, end_pos)
  
  recs = strsplit(s[s$V_CALL_GENOTYPED==gene_name,]$SEQUENCE_IMGT, "")
  
  if(length(recs) < 1) {
    return(NA)
  }
  
  ref = strsplit(gene_sequences[gene_name], "")
  x = do.call('rbind', lapply(seq(pos,max_pos), nucs_at, seqs=recs, filter=filter))

  g = ggplot(data=x, aes(x=pos, fill=nuc)) + 
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

end_composition_grobs = lapply(names(inferred_seqs), plot_base_composition, s=s, gene_sequences=inferred_seqs, pos=313, filter=T)
end_composition_grobs = end_composition_grobs[!is.na(end_composition_grobs)]

whole_composition_grobs = lapply(names(inferred_seqs), plot_base_composition, s=s, gene_sequences=inferred_seqs, pos=1, filter=F)
whole_composition_grobs = whole_composition_grobs[!is.na(whole_composition_grobs)]

# uncomment to sample an additional region - also uncomment line around 512
#snap_composition_grobs = lapply(names(inferred_seqs), plot_base_composition, s=s, gene_sequences=inferred_seqs, pos=210, end_pos=230, filter=F)
#snap_composition_grobs = snap_composition_grobs[!is.na(snap_composition_grobs)]

# J-allele usage and haplotype plots

sj = s[!grepl(',', s$J_CALL),]            # unique J-calls only
sj$j_gene = sapply(sj$J_CALL, function(x) {strsplit(x, '*', fixed=T)[[1]][[1]]})
sj$j_allele = sapply(sj$J_CALL, function(x) {strsplit(x, '*', fixed=T)[[1]][[2]]})

su = select(sj, J_CALL, j_gene, j_allele)
j_genes = sort(unlist(unique(su$j_gene)))


# calc percentage of each allele in a gene
allele_props = function(gene, su) {
  alleles = su %>% filter(j_gene==gene) %>% group_by(j_allele) %>% summarise(count=n())
  alleles$j_gene = gene
  total = sum(alleles$count)
  alleles$percent = 100*alleles$count/total
  return(alleles)
} 

j_props = do.call('rbind', lapply(j_genes, allele_props, su=su))

j_allele_plot = ggplot() + geom_bar(aes(y=percent, x=j_gene, fill=j_allele), data=j_props, stat='identity') + 
  labs(x='J Gene', 
       y='Allele %', 
       title='J Allele Usage') +
  theme_classic(base_size=15) +
  theme(legend.title = element_blank(), plot.margin=margin(1,4,19,4, 'cm'), axis.text.x = element_text(angle = 270, hjust = 0,vjust=0.5))


sj = sj[!grepl(',', sj$V_CALL_GENOTYPED),]        # remove ambiguous V-calls
all_v = data.frame(gene=unique(sj$V_CALL_GENOTYPED), stringsAsFactors = F)
all_v$order = sapply(all_v$gene, numify)
all_v = all_v[order(all_v$order),]
sj$V_CALL_GENOTYPED = factor(sj$V_CALL_GENOTYPED, all_v$gene)


# differential plot by allele usage - if we have good alleles for this gene

plot_differential = function(gene, j_props, sj) {
  jp = j_props[j_props$j_gene==gene,]
  jp = jp[order(jp$percent, decreasing=T),]
  
  if(nrow(jp) < 2 || jp[1,]$percent > 75 || jp[2,]$percent < 20) {
    return(NA)
  }
  
  a1 = jp[1,]$j_allele
  a2 = jp[2,]$j_allele
  recs = sj %>% filter(j_gene==gene) %>% filter(j_allele==a1 | j_allele==a2)
  recs = recs %>% select(V_CALL_GENOTYPED, j_allele) %>% group_by(V_CALL_GENOTYPED, j_allele) %>% summarise(count=n())
  recs$pos = sapply(recs$j_allele, function(x) {if(x==a1) {1} else {-1}})
  recs$count = recs$count * recs$pos
  g = ggplot(recs, aes(x=V_CALL_GENOTYPED,y=count, fill=j_allele)) + 
      geom_bar(stat='identity', position='identity') +
      labs(x='', 
         y='Count', 
         title=paste0('Sequence Count by ', gene, ' allele usage')) +
      theme(panel.border = element_blank(), panel.grid.major = element_blank(), panel.grid.minor = element_blank(), 
          panel.background = element_blank(), axis.ticks = element_blank(), legend.position=c(0.9, 0.9),
          axis.text=element_text(size=8), axis.title =element_text(size=15), axis.text.x = element_text(angle = 270, hjust = 0,vjust=0.5),
          plot.margin=margin(1,1,15,1, 'cm')) +
      scale_fill_discrete(name  ="J- Allele")
  return(ggplotGrob(g))
}

haplo_grobs = lapply(j_genes, plot_differential, j_props=j_props, sj=sj)
haplo_grobs = haplo_grobs[!is.na(haplo_grobs)]


# Save all graphics to plot file

pdf(paste0(file_prefix, '_ogrdb_plots.pdf'), width=210/25,height=297/25)  
x=print(marrangeGrob(end_composition_grobs, nrow=3, ncol=2,top=NULL))
x=print(marrangeGrob(whole_composition_grobs, nrow=3, ncol=1,top=NULL))
x = print(marrangeGrob(barplot_grobs, nrow=3, ncol=3,top=NULL))
#x=print(marrangeGrob(snap_composition_grobs, nrow=3, ncol=1,top=NULL))
grid.arrange(j_allele_plot)
x=print(marrangeGrob(haplo_grobs, nrow=1, ncol=1,top=NULL))
dev.off()



# Haplotyping analysis for genotype file

genotype$haplotyping_gene = ''
genotype$haplotyping_ratio = ''

if(!is.na(hap_gene)) {
  jp = j_props[j_props$j_gene==hap_gene,]
  jp = jp[order(jp$percent, decreasing=T),]
  
  if(nrow(jp) < 2 || jp[1,]$percent > 75 || jp[2,]$percent < 20 || (jp[1,]$percent+jp[2,]$percent < 90)) {
    print(paste0('Alellelic ratio is unsuitable for haplotyping analysis based on ', hap_gene))
  } else
  {
    genotype$haplotyping_gene = hap_gene
    genotype = select(genotype, -c(haplotyping_ratio))
    
    a1 = jp[1,]$j_allele
    a2 = jp[2,]$j_allele
    print(paste0('Haplotyping analysis is based on gene ', hap_gene, ' alleles ', a1, ':', a2))
    recs = sj %>% filter(j_gene==hap_gene) %>% filter(j_allele==a1 | j_allele==a2)
    recs = recs %>% select(sequence_id=V_CALL_GENOTYPED, j_allele) %>% group_by(sequence_id, j_allele) %>% summarise(count=n()) %>% spread(j_allele, count)
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
  
  
  

# Save Genotype file

g = select(genotype, sequence_id, sequences, closest_reference, closest_host, nt_diff, nt_substitutions, aa_diff,
           aa_substitutions, assigned_unmutated_frequency, unmutated_frequency, unmutated_sequences, unmutated_umis, allelic_percentage, unique_ds,
           unique_js,unique_cdr3s, haplotyping_gene, haplotyping_ratio, nt_sequence)
g[is.na(g)] = ''

write.csv(g, paste0(file_prefix, '_ogrdb_report.csv'), row.names=F)



