#!/bin/bash

bibtool -d economics.bib -o economics_deduped_$(date +%Y%m%d).bib
