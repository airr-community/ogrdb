# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for Genotype
from db.gene_description_db import *
from sequence_format import check_duplicate


class GenotypeMixin:
    # Find any gene descriptions out there that refer to this sequence

    def build_duplicate_list(self, db, new_status):
        self.published_duplicates = list()
        if new_status in ['reviewing', 'complete']:
            genes = db.session.query(GeneDescription).filter(GeneDescription.status.in_(['draft', 'published']), GeneDescription.species == self.genotype_description.submission.species).all()

            for gene in genes:
                if gene.sequence_type == self.genotype_description.sequence_type and check_duplicate(self.nt_sequence, self.sequence.replace('.', ''), self.genotype_description.sequence_type):
                    # gene.duplicate_sequences.append(self)
                    self.published_duplicates.append(gene)

        db.session.commit()
