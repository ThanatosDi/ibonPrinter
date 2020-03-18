#!/usr/bin/env python3

import argparse
import sys
import os

from ibonPrinter import IBON


def main():
    parser = argparse.ArgumentParser(
        prog='ibonprinter-cli',
        description='7-11 iBon printer uploader.'
    )
    parser.add_argument(
        '--name',
        type=str,
        default=' ',
        help='User name'
    )
    parser.add_argument(
        '--email',
        type=str,
        default=' ',
        help='User email'
    )
    parser.add_argument(
        'file',
        type=str,
        help='Upload file'
    )

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        return f'File is not existed, {args.file}'

    # TODO: check file ext
    # doc、docx、ppt、pptx、xls、xlsx、txt、ini、pdf、jpg、gif、bmp

    # TODO: check file size < 10M

    printer = IBON()
    r = printer.upload(
        args.file,
        user=args.name,
        email=args.email,
    )


if __name__ == "__main__":
    sys.exit(main())
