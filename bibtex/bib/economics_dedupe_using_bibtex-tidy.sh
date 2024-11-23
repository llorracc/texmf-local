#!/bin/bash

# bibtex-tidy --no-align --duplicates=key --no-escape --no-tidy-comments --no-remove-dupe-fields --no-lowercase economics.bib

nameLast=economics
nameNext=economics-before_bibtex-tidy_clean-only-20241117
bibtex-tidy --v2 --align=14                                  --no-escape --no-tidy-comments --no-remove-dupe-fields --no-lowercase $nameLast.bib > $nameNext.bib
# This looked fine

nameLast=$nameNext
nameNext=economics-before_bibtex-tidy_dedupe-and-merge-by-key-20241117
merged=$nameNext
bibtex-tidy --v2 --align=14 --duplicates=key --merge=combine --no-escape --no-tidy-comments --no-remove-dupe-fields --no-lowercase $nameLast.bib > $nameNext.bib

nameLast=$nameNext
nameNext=economics-before_bibtex-tidy_dedupe-and-merge-by-key-20241117_remove-files
# Remove all lines with 'file' that are not CDC files
# Keep non-file lines and file lines with desired patterns
# First, keep non-file lines and file lines with desired patterns
# First, handle the file patterns
awk '
    !/^[ \t]*file / {print}  # print all lines not containing file
    /^[ \t]*file / && /file .*(All Papers|All-Papers|\/Volumes|ByCiteKey|pdf:PDF)/ {print}  # print file lines with patterns
' "$nameLast.bib" > temp1.bib

# Then remove file lines containing alujan
awk '
    !/^[ \t]*file / {print}  # print all lines not containing file
    /^[ \t]*file / && !/alujan/ {print}  # print file lines without alujan
' temp1.bib > "$nameNext.bib"

# Clean up
rm temp1.bib

#diff $nameLast.bib $nameNext.bib

ditto $nameNext.bib economics.bib
