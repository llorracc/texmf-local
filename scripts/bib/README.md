# economics.bib: the single source for references

`bibtex/bib/economics.bib` is the one place references are corrected (`system.bib` is a link to it). A document's
bibliography is derived from this file and is never edited by hand. The reasons for individual corrections are in the
commit messages.

## Rules for the file

- **Keys are permanent.** Papers cite them, so a key is never renamed or removed. A work already in the file does not
  get a second key.
- **A superseded version keeps its own key.** The plain key holds the published or current version; the older one gets
  a suffix, such as `rameyFrancisLeisureNBERWP`, `stock&watson:handbookWP` or `romer:textEd4`.
- **Check a correction against a record of the work,** Crossref first, and OpenAlex or RePEc where Crossref has
  nothing. A match on title alone can be another edition or a reprint.
- **Every entry must render in both BibTeX and MyST:**
  - a `doi` is bare (`10.xxxx/suffix`), never a URL and never prefixed with `doi:`;
  - a `year` is a year, or a negative year for an ancient work (`-350`);
  - a `journal` is not a file path;
  - an accent encloses its letter: `{\'e}`, never `{\'}e`;
  - names and titles carry no `{\-}` hyphenation hints, which MyST prints literally;
  - a chapter in an edited volume is `@incollection`. An `@inbook` whose `crossref` parent has no `author` stops MyST.

  One unreadable entry stops MyST loading the whole `.bib`, not just that entry.

## The lint

```bash
scripts/bib/lint-economics-bib.py [path-to-bib]
```

It prints one line per problem and exits 1 if there are any errors. It needs only the Python standard library. Its
docstring lists the checks.

A few entries have no real date, such as periodic publications and work in progress. They are left that way on
purpose and are reported as `year` errors, so the lint currently exits 1. Any other error is a real problem.

## Deriving a document's bibliography

Pull this repository first, then copy each cited entry verbatim and record the commit it came from.

MyST follows a `crossref` only when the parent is in the same file, so the derivation must copy each entry's parent
as well.

## Testing a change to the whole file

```bash
# BibTeX: in a scratch directory holding a copy of the file as econ.bib
printf '\\citation{*}\n\\bibstyle{plain}\n\\bibdata{econ}\n' > t.aux
BIBINPUTS=. bibtex -min-crossrefs=999 t
```

For MyST, cite a few keys from a one-page project that lists the file under `project.bibliography`, run
`myst build --html`, and look for `Error reading file`. Test the whole file this way, because some failures appear only
when entries are read together.
