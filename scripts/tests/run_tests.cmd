cd D:/Research/ogre/scripts
Rscript D:/Research/ogre/scripts/genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens TWO01A_naive_novel_ungapped.fasta TWO01A_naive_genotyped.tsv VH IGHJ6

cd D:/Research/ogre/scripts/tests/V_tigger_truncated
Rscript D:/Research/ogre/scripts/genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens TWO01A_naive_novel_ungapped.fasta TWO01A_naive_genotyped.tsv VH IGHJ6

cd D:/Research/ogre/scripts/tests/JH_tigger
Rscript D:/Research/ogre/scripts/genotype_statistics.R IMGT_REF_GAPPED_J_CHANGES.fasta Homosapiens TWO01A_naive_novel.fasta TWO01A_naive.airr.tab JH IGHV2-5

cd D:/Research/ogre/scripts/tests/D_tigger
Rscript D:/Research/ogre/scripts/genotype_statistics.R IMGT_REF_GAPPED_D_1_26_01_removed.fasta Homosapiens TWO01A_naive_novel.fasta TWO01A_naive.airr.tab DH IGHJ6

cd D:/Research/ogre/scripts/tests/JH_igdiscover
Rscript D:/Research/ogre/scripts/genotype_statistics.R IMGT_REF_GAPPED_fake_j.fasta Homosapiens J.fasta filtered.tab JH IGHV2-5

cd D:/Research/ogre/scripts/tests/JL_igdiscover
Rscript D:/Research/ogre/scripts/genotype_statistics.R IMGT_REF_GAPPED_fake_j_fake_JK.fasta Homosapiens J.fasta filtered.tab JH IGHV2-5

cd D:/Research/ogre/scripts/tests/VH_partis
Rscript D:/Research/ogre/scripts/genotype_statistics.R IMGT_REF_GAPPED.fasta Homosapiens TW02A_V_OGRDB.fasta TW02A_OGRDB.tsv VH IGHJ6
