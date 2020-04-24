#!/usr/bin/env python

import argparse
from collections import defaultdict

import pysam

from ragoo2_utilities.utilities import reverse_complement


def main():
    parser = argparse.ArgumentParser(description="Build scaffolds from an 'orderings.bed' file")
    parser.add_argument("orderings", metavar="<orderings.bed>", type=str, help="'orderings.bed' file produced by 'ragoo2_scaffold.py'")
    parser.add_argument("query", metavar="<query.fasta>", type=str, help="query fasta file to be scaffolded. must not be gzipped")
    parser.add_argument("out_fasta_file", metavar="<ragoo.fasta>", type=str, help="output fasta file name")
    parser.add_argument("out_unplaced_file", metavar="<unplaced.txt>", type=str, help="file to write unplaced sequences")
    parser.add_argument("gap_size", metavar="100", default=100, type=int, help="gap size for chr0")
    parser.add_argument("-C", default=False, action='store_true', help="concatenate unplaced contigs and make 'chr0'")

    args = parser.parse_args()
    orderings_file = args.orderings
    query_file = args.query
    out_file = args.out_fasta_file
    out_unplaced_file = args.out_unplaced_file
    chr0_gap_size = args.gap_size
    make_chr0 = args.C

    # Organize the orderings
    orderings = defaultdict(list)
    with open(orderings_file, "r") as f:
        for line in f:
            l = line.rstrip().split()
            start, end, seq_type, header, strand = int(l[1]), int(l[2]), l[3], l[4], l[5]
            orderings[l[0]].append((start, end, seq_type, header, strand))

    # Sort the orderings and write the fasta output
    out_fasta = open(out_file, "w")
    x = pysam.FastaFile(query_file)
    placed_q_seqs = set()
    for i in orderings:
        out_fasta.write(">" + i + "\n")
        orderings[i] = sorted(orderings[i])

        # Iterate through each sequence of this scaffold
        for j in orderings[i]:
            q_header = j[3]
            if j[2] == "s":
                # This is a query sequence
                placed_q_seqs.add(q_header)
                if j[4] == "+":
                    out_fasta.write(x.fetch(q_header))
                else:
                    out_fasta.write(reverse_complement(x.fetch(q_header)))
            else:
                # This is a gap
                assert j[2] == "g"
                gap_len = j[1] - j[0]
                out_fasta.write("N" * gap_len)

        out_fasta.write("\n")

    # Take care of the unplaced sequences
    all_q_seqs = set(x.references)
    remaining_seqs = all_q_seqs - placed_q_seqs
    unplaced_out = open(out_unplaced_file, "w")
    unplaced_lines = []
    if remaining_seqs:
        # Output the unplaced contigs in sorted order
        remaining_seqs = sorted(list(remaining_seqs))
        if make_chr0:
            out_fasta.write(">Chr0_RaGOO\n")
            pad = "N" * chr0_gap_size
            curr_seq = []

            # Iterate through the unplaced contigs
            for i in remaining_seqs:
                unplaced_lines.append(i + "\t" + str(x.get_reference_length(i)))
                curr_seq.append(x.fetch(i))

            out_fasta.write(pad.join(curr_seq) + "\n")

        else:
            # Write unplaced contigs individually with original headers
            for i in remaining_seqs:
                unplaced_lines.append(i + "\t" + str(x.get_reference_length(i)))
                out_fasta.write(">" + i + "\n")
                out_fasta.write(x.fetch(i) + "\n")

    out_fasta.close()

    if unplaced_lines:
        unplaced_out.write("\n".join(unplaced_lines) + "\n")
    unplaced_out.close()


if __name__ == "__main__":
    main()
