# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Functions for formatting sequences for display
import itertools
from Bio.Seq import Seq
from Bio.pairwise2 import format_alignment, align


def chunks(l, n):
    " Yield successive n-sized chunks from l."
    for i in range(0, len(l), n):
        yield l[i:i + n]

def apply_annots(frag, startpos, ra, gapped):
    if not ra:
        return frag

    ret = ''
    pos = startpos

    for i in range(len(frag)):
        if not gapped or (frag[i] != '.' and frag[i] != ' '):
            if pos in ra:
                ret += "<span class='highlight-nuc' data-toggle='tooltip' title='%s'>" % ra[pos] + frag[i] + "</span>"
            else:
                ret += frag[i]
            pos += 1
        else:
            ret += frag[i]

    return ret


def format_nuc_sequence(seq, width, ra=None, gapped=False):
    ind = 1
    ungapped_ind = 1
    ret = ''

    if seq is None or len(seq) == 0:
        return ''

    for frag in chunks(seq, width):
        ret += '%-5d' % ind
        if len(frag) > 10:
            ret += ' '*(len(frag)-10) + '%5d' % (ind + len(frag) - 1)
        ret += '\n' + apply_annots(frag, ungapped_ind-1, ra, gapped) + '\n\n'
        ind += len(frag)
        ungapped_ind += len(frag.replace('.', '')) if gapped else len(frag)

    return ret

# Format an unarranged sequence, including feature annotations for
# whatever indeces we have
def format_unrearranged_sequence(seq, width, gv_items):
    if seq is None or len(seq) == 0:
        return ''

    possible_features = {'utr_5_prime': 'UTR', 'leader_1': 'LDR1', 'leader_2': 'LDR2', 'v_rs': 'RSS', 'd_rs_3_prime': "3' RSS", 'd_rs_5_prime': "5' RSS", 'j_rs': 'RSS',
                         'c_exon_1': 'EXON_1', 'c_exon_2': 'EXON_2', 'c_exon_3': 'EXON_3', 'c_exon_4': 'EXON_4', 'c_exon_5': 'EXON_5', 'c_exon_6': 'EXON_6', 'c_exon_7': 'EXON_7', 'c_exon_8': 'EXON_8', 'c_exon_9': 'EXON_9',
                         'utr_3_prime': 'UTR'}
    feature_string = ' ' * len(seq)
    for feature in possible_features.keys():
        if feature + '_start' in gv_items and feature + '_end' in gv_items and gv_items[feature + '_start']['value'] and gv_items[feature + '_end']['value']:
            try:
                start = gv_items[feature + '_start']['value'] - 1
                end = gv_items[feature + '_end']['value']

                if start < end and start >= 0 and end <= len(feature_string) and end - start > len(possible_features[feature]) + 2:
                    feat = possible_features[feature].center(end-start - 2, '-')
                    feat = f"<{feat}>"
                    feature_string = feature_string[:start] + feat + feature_string[end:]
            except:
                pass

    ind = 1
    ret = ''

    for frag in chunks(seq, width):
        ret += '%-5d' % ind
        if len(frag) > 10:
            ret += ' '*(len(frag)-10) + '%5d' % (ind + len(frag) - 1)
        ret += '\n' + frag + '\n' + feature_string[ind-1:ind-1+len(frag)] + '\n\n'
        ind += len(frag)

    return ret


def format_fasta_sequence(name, seq, width):
    ret = '>' + name + '\n'

    if seq is None or len(seq) == 0:
        return ret + ' \n'

    for frag in chunks(seq, width):
        ret += frag + '\n'

    return ret

annot_num = ' 1   2   3   4   5   6   7   8   9   10  11  12  13  14  15  16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34  35  36  37  38  39  40  41  42  43  44  45  46  47  48  49  50  51  52  53  54  55  56  57  58  59  60  61  62  63  64  65  66  67  68  69  70  71  72  73  74  75  76  77  78  79  80  81  82  83  84  85  86  87  88  89  90  91  92  93  94  95  96  97  98  99 100 101 102 103 104 105 106 107 108 '

def format_annot_v(seq, width, ra=None):
    try:
        sequence = seq.coding_seq_imgt
    except:
        sequence = seq              # if we are not called with an AlleleDescription, assume we've been called with a plain gapped sequence
        seq = None

    annot_num = ''
    codon_num = 0
    annot_leg = ''
    fmt_aa = ''
    fmt_seq = ''
    ungapped_ind = 0

    def in_cdr(pos, seq):
        if seq is None:
            return '    '

        try:
            if pos + seq.gene_start >= seq.cdr1_start and pos + seq.gene_start <= seq.cdr1_end:
                return '1111'
            if pos + seq.gene_start >= seq.cdr2_start and pos + seq.gene_start <= seq.cdr2_end:
                return '2222'
            if pos + seq.gene_start >= seq.cdr3_start:
                return '3333'
            return '    '
        except:
            return '    '

    fmt_seq = ''
    fmt_aa = ''
    for cd in chunks(sequence, 3):
        codon_num += 1
        annot_num += str(codon_num).rjust(3) + ' '
        annot_leg += in_cdr(ungapped_ind, seq)

        fmt_seq += cd + ' '
        if '.' in cd or '-' in cd or len(cd) < 3:
            fmt_aa += '    '
        else:
            ungapped_ind += 3
            try:
                fmt_aa += ' ' + str(Seq(cd).translate()) + '  '
            except:
                fmt_aa += ' X  '

    # replace the blocks of 1s, 2s, and 3s with CDR1, CDR2, CDR3 centred in the block, with underlines on each side
    # find the position of each block in the string

    for c in '1', '2', '3':
        start = annot_leg.find(c)
        end = annot_leg.rfind(c)
        # replace the block with the CDR name, centred in the block and surrounded by underlines
        lblock_len = int((end - start - 3)/2)
        rblock_len = (end - start + 1) - lblock_len - 4
        annot_leg = annot_leg[:start] + '_'*lblock_len + 'CDR' + c + '_'*rblock_len + annot_leg[end+1:]
    



    # this will deliberately truncate at the end of the shortest line - which will never be imgt_leg or imgt_num unless the sequence is longer than it should be...
    res = splitlines(annot_leg + '\n' + annot_num + '\n' + fmt_aa + '\n' + fmt_seq + '\n', width, 0).split('\n')

    i = 3  # first line containing nuc sequences
    pos = 0

    while i < len(res):
        incr = len(res[i].replace('.', '').replace(' ', ''))         # nt on this line
        res[i] = apply_annots(res[i], pos, ra, True)
        pos += incr
        i += 5              # gap between lines carrying nt sequence

    return '\n'.join(res)

def format_translated_fasta(name, seq, width):
    tr_seq = ''

    for cd in chunks(seq, 3):
        if '.' in cd or '-' in cd or len(cd) < 3:
            tr_seq += '.'
        else:
            try:
                tr_seq += str(Seq(cd).translate())
            except:
                tr_seq += 'X'

    return format_fasta_sequence(name, tr_seq, width)

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


# Style a button for the sequence_popup script

def popup_seq_button(sequence_id, sequence, gapped, seq, annots=[]):
    # Re-form annotations into a single string for each position
    ra = {}

    for (pos, len, text) in annots:
        for i in range(len):
           ind = pos + i
           if ind in ra:
               ra[ind] += '\n' + text
           else:
               ra[ind] = text

    return (
        ('<button type="button" id="btn_view_seq" class="btn btn-xs text-ogrdb-info icon_back" data-bs-toggle="modal" data-bs-target="#seqModal" data-bs-toggle="tooltip" title="View Sequence"' 
         ' data-sequence="%s"' 
         ' data-gapped-sequence="%s"' 
         ' data-name="%s"' 
         ' data-fa="%s"' 
         ' data-gapped-fa="%s"' 
         ' data-trans="%s"'
         ' data-trans-fa="%s"'
         '><i class="bi bi-search"></i>&nbsp;</button>'
        ) %
        (format_nuc_sequence(sequence, 50, ra=ra, gapped=False),
         format_nuc_sequence(gapped, 50, ra=ra, gapped=True),
         sequence_id,
         format_fasta_sequence(sequence_id, sequence, 50),
         format_fasta_sequence(sequence_id, gapped, 50),
         format_annot_v(seq, 52, ra=ra) if gapped else '',
         format_translated_fasta(sequence_id, gapped, 50) if gapped else ''
         )
    )

