#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from aggie.generater import Generater


def main():
    parser = ArgumentParser()
    parser.add_argument("prog")
    parser.add_argument("-o", "--output", dest = "output_file", nargs = "?")
    parser.add_argument("-O", "--optimize", type = int, default = 0)
    args = parser.parse_args()
    input_filepath = args.prog
    if args.output_file:
        output_filepath = args.output_file
    else:
        output_filepath = os.path.splitext(input_filepath)[0]
        if os.name == "nt":
            output_filepath += ".exe"

    generater = Generater()

    generater.generate(input_filepath, output_filepath, args.optimize)



if __name__ == "__main__":
    main()
