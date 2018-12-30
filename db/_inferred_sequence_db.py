# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Mixin methods for InferredSequence

from db.gene_description_db import *

class InferredSequenceMixin:
    # Find any gene descriptions out there that refer to this sequence

    def build_duplicate_list(self, db):
        self.published_duplicates = list()
        if self.submission.submission_status in ['reviewing', 'complete']:
            genes = db.session.query(GeneDescription).filter(GeneDescription.status.in_(['draft', 'published']), GeneDescription.organism == self.submission.species).all()

            for gene in genes:
                try:
                    if len(gene.sequence) > 0 and len(self.sequence_details.nt_sequence) > 0:
                        if(gene.sequence in self.sequence_details.nt_sequence or self.sequence_details.nt_sequence in gene.sequence):
                            self.published_duplicates.append(gene)
                except:
                    continue

        db.session.commit()

