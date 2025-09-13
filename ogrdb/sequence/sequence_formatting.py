# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from markupsafe import Markup
from sequence_format import popup_seq_button, format_unrearranged_sequence, format_fasta_sequence


def safe_textile(text):
    """Safe import and use of textile filter"""
    try:
        from textile_filter import safe_textile as _safe_textile
        return _safe_textile(text)
    except ImportError:
        return text


def pretty_sequence_item(fn, value, seq, trailer_text, gv_items, coordinate_offset=0):
    """
    Format sequence-related items for display with optional coordinate adjustment.
    
    Args:
        fn: field name
        value: field value
        seq: sequence object (GeneDescription or GenomicSupport)
        trailer_text: additional text to append
        gv_items: dictionary of view items with coordinate information
        coordinate_offset: offset to subtract from coordinates (for GenomicSupport)
    
    Returns:
        Formatted value with markup for display
    """
    if fn == 'sequence':
        if value is not None and len(value) > 0:
            # Adjust coordinates in gv_items if offset is provided
            display_gv_items = gv_items
            if coordinate_offset != 0:
                display_gv_items = adjust_coordinates_for_display(gv_items, coordinate_offset)
            
            # Get sequence name - handle both GeneDescription and GenomicSupport
            if hasattr(seq, 'sequence_name'):
                sequence_name = seq.sequence_name
                sequence_value = seq.sequence
            else:
                # For GenomicSupport, use accession as name and the sequence field
                sequence_name = getattr(seq, 'accession', 'sequence')
                sequence_value = value  # The sequence passed as value parameter
            
            value = Markup('<button id="seq_view" name="seq_view" type="button" class="btn btn-xs text-ogrdb-info icon_back" data-bs-toggle="modal" data-bs-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-bs-toggle="tooltip" title="View"><i class="bi bi-search"></i>&nbsp;</button>'
                           % (format_unrearranged_sequence(value, 50, display_gv_items) + trailer_text, sequence_name, format_fasta_sequence(sequence_name, sequence_value, 50)))
        else:
            value = 'None'
    elif fn == 'coding_seq_imgt' or fn == 'genomic_coding_seq':
        if value is not None and len(value) > 0:
            sequence_name = getattr(seq, 'sequence_name', None) or getattr(seq, 'accession', 'sequence')
            if fn == 'coding_seq_imgt' and seq.sequence_type == 'V' and '.' in value:
                value = Markup(popup_seq_button(sequence_name, value.replace('.', ''), value, seq).replace('btn_view_seq', 'seq_coding_view'))
            else:
                value = Markup(popup_seq_button(sequence_name, value, '', seq).replace('btn_view_seq', 'seq_coding_view'))
        else:
            value = 'None'
    elif fn == 'release_description':
        if value is not None and len(value) > 0:
            value = Markup(safe_textile(value))
    elif fn == 'release_date':
        if value is not None:
            value = value.strftime('%Y-%m-%d')
    
    return value


def adjust_coordinates_for_display(gv_items, coordinate_offset):
    """
    Adjust coordinate values in gv_items by subtracting the coordinate_offset and adding 1
    to convert from genomic coordinates to 1-based sequence coordinates.
    
    Args:
        gv_items: dictionary of view items
        coordinate_offset: the GenomicSupport.start value to subtract
    
    Returns:
        Dictionary with adjusted coordinates
    """
    adjusted_items = {}
    
    # Fields that contain coordinate information that need adjustment
    coordinate_fields = [
        'utr_5_prime_start', 'utr_5_prime_end',
        'leader_1_start', 'leader_1_end',
        'leader_2_start', 'leader_2_end',
        'v_rs_start', 'v_rs_end',
        'd_rs_3_prime_start', 'd_rs_3_prime_end',
        'd_rs_5_prime_start', 'd_rs_5_prime_end',
        'j_rs_start', 'j_rs_end',
        'gene_start', 'gene_end',
        'j_cdr3_end',
        'cdr1_start', 'cdr1_end',
        'cdr2_start', 'cdr2_end',
        'cdr3_start'
    ]
    
    for field_name, item in gv_items.items():
        adjusted_items[field_name] = item.copy()
        
        # Adjust coordinate values
        if field_name in coordinate_fields and item['value'] is not None:
            try:
                # Convert genomic coordinate to 1-based sequence coordinate
                adjusted_value = int(item['value']) - coordinate_offset + 1
                adjusted_items[field_name]['value'] = adjusted_value
            except (ValueError, TypeError):
                # Keep original value if conversion fails
                pass
    
    return adjusted_items


def create_genomic_support_view_items(genomic_support):
    """
    Create view items dictionary for GenomicSupport object, similar to gv_items for GeneDescription.
    
    Args:
        genomic_support: GenomicSupport object
    
    Returns:
        Dictionary of view items with coordinate information
    """
    gv_items = {}
    
    # Map GenomicSupport fields to view items
    coordinate_fields = {
        'gene_start': 'gene_start',
        'gene_end': 'gene_end',
        'utr_5_prime_start': 'utr_5_prime_start',
        'utr_5_prime_end': 'utr_5_prime_end',
        'leader_1_start': 'leader_1_start',
        'leader_1_end': 'leader_1_end',
        'leader_2_start': 'leader_2_start',
        'leader_2_end': 'leader_2_end',
        'v_rs_start': 'v_rs_start',
        'v_rs_end': 'v_rs_end',
        'd_rs_3_prime_start': 'd_rs_3_prime_start',
        'd_rs_3_prime_end': 'd_rs_3_prime_end',
        'd_rs_5_prime_start': 'd_rs_5_prime_start',
        'd_rs_5_prime_end': 'd_rs_5_prime_end',
        'j_rs_start': 'j_rs_start',
        'j_rs_end': 'j_rs_end',
        'j_cdr3_end': 'j_cdr3_end'
    }
    
    for field_name, attr_name in coordinate_fields.items():
        value = getattr(genomic_support, attr_name, None)
        gv_items[field_name] = {
            'field': field_name,
            'value': value,
            'item': field_name.replace('_', ' ').title(),
            'tooltip': ''
        }
    
    return gv_items
