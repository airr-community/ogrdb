# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Functions for formatting sequences for display
import itertools
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.pairwise2 import format_alignment, align
from flask import Markup


def chunks(l, n):
    " Yield successive n-sized chunks from l."
    for i in range(0, len(l), n):
        yield l[i:i + n]

def format_nuc_sequence(seq, width):
    ind = 1
    ret = ''

    if seq is None or len(seq) == 0:
        return ''

    for frag in chunks(seq, width):
        ret += '%-5d' % ind
        if len(frag) > 10:
            ret += ' '*(len(frag)-10) + '%5d' % (ind + len(frag) - 1)
        ind += len(frag)
        ret += '\n' + frag + '\n\n'

    return ret

def format_fasta_sequence(name, seq, width):
    ret = '>' + name + '\n'

    if seq is None or len(seq) == 0:
        return ret + ' \n'

    for frag in chunks(seq, width):
        ret += frag + '\n'

    return ret

imgt_leg = '                                                                                                       _____________________CDR1_______________________                                                                     _________________CDR2___________________                                                                                                                                                             _CDR3_______'
imgt_num = ' 1   2   3   4   5   6   7   8   9   10  11  12  13  14  15  16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34  35  36  37  38  39  40  41  42  43  44  45  46  47  48  49  50  51  52  53  54  55  56  57  58  59  60  61  62  63  64  65  66  67  68  69  70  71  72  73  74  75  76  77  78  79  80  81  82  83  84  85  86  87  88  89  90  91  92  93  94  95  96  97  98  99 100 101 102 103 104 105 106 107 108 '

def format_imgt_v(seq, width):
    ind = 1
    ret = 1

    fmt_seq = ''
    fmt_aa = ''
    for cd in chunks(seq, 3):
        fmt_seq += cd + ' '
        if '.' in cd or '-' in cd or len(cd) < 3:           # commented out until we install biopython
            fmt_aa += '    '
        else:
            fmt_aa += ' ' + str(Seq(cd, IUPAC.unambiguous_dna).translate()) + '  '

    # this will deliberately truncate at the end of the shortest line - which will never be imgt_leg or imgt_num unless the sequence is longer than it should be...
    return splitlines(imgt_leg + '\n' + imgt_num + '\n' + fmt_aa + '\n' + fmt_seq + '\n', width, 0)


def splitlines(report, maxlength, label_cols):
    """
    Split the report (which is assumed to consist of lines of equal length) into a longer report in which each
    line is maxlength or less. label_cols specifies the width of the label field, which is repeated at the start
    of each line.
    """

    # https://stackoverflow.com/questions/3992735/python-generator-that-groups-another-iterable-into-groups-of-n

    def grouper(n, iterable):
        iterable = iter(iterable)
        return iter(lambda: list(itertools.islice(iterable, n)), [])

    inlines = report.split("\n")[:-1]
    labels = [line[:label_cols] for line in inlines]
    data = [line[label_cols:] for line in inlines]
    outlines = []

    for chunk in grouper(maxlength-label_cols, zip(*data)):
        a = ["".join(line) for line in zip(*chunk)]
        outlines.extend(["".join(line) for line in zip(labels, a)])
        outlines.extend(" ")

    return "\n".join(["".join(line) for line in outlines])

def rem_trailing_dots(s):
    trail = ''
    while(s[-1] == '.'):
        trail += '-'
        s = s[:-1]

    return (s, trail)


def report_dupe(s1, s1_name, s2, s2_name):
    # identical chars 2 points, -1 for non-identical, -2 for opening a gap, -1 for extending it
    alignments = align.globalms(s1, s2, 2, -1, -2, -1, one_alignment_only=True)
    alignment = format_aln(format_alignment(*alignments[0]), s1_name, s2_name, 50) if len(alignments) > 0 else ''
    return(alignment)


def format_aln(alignment, name1, name2, width):
    # Format an alignment returned by Bio.pairwise2: add names to start of each split line
    lines = alignment.split('\n')
    ln = max(len(name1), len(name2)) + 1
    lines[0] = "%-*s" % (ln, name1) + lines[0]
    lines[1] = "%-*s" % (ln, ' ') + lines[1]
    lines[2] = "%-*s" % (ln, name2) + lines[2]
    return(splitlines(lines[0]+'\n'+lines[1]+'\n'+lines[2]+'\n', width, ln))


# Check whether q sequence recorded in a genotype or inferred sequence matches that recorded in gene description
# The 3nt in the genotype sequence closest to the junction with another segment are ignored

IGNORE_NT = 3
def check_duplicate(genotype_seq, desc_seq, sequence_type):
    try:
        if sequence_type == 'V':
            genotype_seq = genotype_seq[:0-IGNORE_NT]
        elif sequence_type == 'J':
            genotype_seq = genotype_seq[IGNORE_NT:]
        elif sequence_type == 'D':
            genotype_seq = genotype_seq[IGNORE_NT:0-IGNORE_NT]
    except:
        return False    # ignore short/nonexistent sequences

    # TODO: other sequence types

    return(genotype_seq in desc_seq or desc_seq in genotype_seq)