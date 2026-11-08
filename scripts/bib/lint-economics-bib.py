#!/usr/bin/env python3
"""Fail on anything in economics.bib that would break a MyST or BibTeX build.

economics.bib is the single source for references: documents derive their .bib
from it, so a defect here reaches every document derived from it.

    scripts/bib/lint-economics-bib.py [path-to-bib]

Prints one line per problem and exits 1 if there is any, 0 if there is none.
Standard library only. Exit status 2 means the file could not be read.

Checks (each is an error):
  doi      must be bare, 10.xxxx/suffix. MyST turns a URL into a dead doi.org
           link; a "doi:" prefix or a TeX escape such as \\_ breaks it too.
  year     must be a year: four digits, or a negative year for an ancient work
           (Chris, 2026-10-27: ancient works print their own date, as -350).
  journal  must not be a file path.
  entry    a field must not swallow another entry (@article{...);
           a crossref must point to an entry that exists;
           a key must be unique, ignoring case, since BibTeX ignores case;
           the entry must parse.
  accent   must enclose its letter: {\\'e}, not {\\'}e. MyST's parser (citation-js)
           cannot read the second form, and one such entry stops MyST reading
           the whole .bib; LaTeX errors on it too.
           An @inbook whose crossref parent has no author stops MyST the same way.
  name     an author or editor may have at most two commas between "and"s.

Printed as warnings, and not failing:
  - a journal that is a URL;
  - an entry with only a crossref, which is empty unless its parent is copied
    into the same derived .bib;
  - {\\-} in an author or title, which MyST prints literally (Sla\\-calek);
  - a url containing a space, which breaks the link.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[2] / "bibtex" / "bib" / "economics.bib"

BARE_DOI = re.compile(r"10\.\d{4,9}/[^\s{}\\]+")
YEAR = re.compile(r"\d{4}|-\d{1,4}")
PATHLIKE = re.compile(r"(\.{0,2}/|~/)\S*|\S*/\S*\.(nb|m|py|ipynb|pdf|tex|zip|html?)")
URL = re.compile(r"https?://", re.I)
STRAY_ENTRY = re.compile(r"@[A-Za-z]+\s*\{")
SPLIT_ACCENT = re.compile(r"""\{\\(?:['"`^~=.]|[uvHckrbdt])\}""")
NAME_FIELDS = ("author", "editor")
HEAD = re.compile(r"^@([A-Za-z]+)\s*([{(])", re.M)
NON_ENTRIES = {"comment", "preamble", "string"}


def skip_space(text, i):
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def end_of_braces(text, i):
    depth = 0
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced braces")


def end_of_quotes(text, i):
    depth = 0
    i += 1
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char == '"' and depth == 0:
            return i + 1
        i += 1
    raise ValueError("unbalanced quotes")


def end_of_value(text, i):
    while True:
        i = skip_space(text, i)
        if text[i] == "{":
            i = end_of_braces(text, i)
        elif text[i] == '"':
            i = end_of_quotes(text, i)
        else:
            bare = re.compile(r"[^\s,}#]+").match(text, i)
            if not bare:
                raise ValueError("missing value")
            i = bare.end()
        after = skip_space(text, i)
        if after < len(text) and text[after] == "#":
            i = after + 1
            continue
        return i


def clean(raw):
    value = raw.strip()
    if len(value) > 1 and value[0] + value[-1] in ("{}", '""'):
        value = value[1:-1]
    return re.sub(r"\s+", " ", value).strip()


def entries(text):
    """Yield (key, fields, problem); fields maps lower-case names to raw values."""
    position = 0
    while True:
        head = HEAD.search(text, position)
        if not head:
            return
        if head.group(1).lower() in NON_ENTRIES:
            try:
                position = end_of_braces(text, head.end() - 1)
            except ValueError:
                position = head.end()
            continue
        i = skip_space(text, head.end())
        key_match = re.compile(r"[^\s,}]*").match(text, i)
        key = key_match.group(0)
        try:
            body_end = end_of_braces(text, head.end() - 1)
        except ValueError:
            yield key, {}, "unbalanced braces"
            position = head.end()
            continue
        fields, problem = {}, None
        i = skip_space(text, key_match.end())
        if text[i] == ",":
            i += 1
        while True:
            i = skip_space(text, i)
            if i >= body_end - 1:
                break
            name = re.compile(r"([A-Za-z_][\w:.+-]*)\s*=\s*").match(text, i)
            if not name:
                problem = "cannot parse near: " + text[i : i + 40].replace("\n", " ")
                break
            try:
                end = end_of_value(text, name.end())
            except (ValueError, IndexError) as error:
                problem = f"field {name.group(1)}: {error}"
                break
            fields[name.group(1).lower()] = text[name.end() : end]
            i = skip_space(text, end)
            if i < len(text) and text[i] == ",":
                i += 1
        yield key, fields, problem
        position = body_end


def entry_types(text):
    """Map lower-case keys to lower-case entry types."""
    found = re.findall(r"^@([A-Za-z]+)\s*[{(]\s*([^\s,}]+)", text, re.M)
    return {key.lower(): kind.lower() for kind, key in found}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"cannot read {path}: {error}", file=sys.stderr)
        return 2

    errors, warnings = [], []
    parsed = list(entries(text))
    keys = {key.lower() for key, _, _ in parsed}
    parents = {key.lower(): fields for key, fields, _ in parsed}
    types = entry_types(text)
    seen = defaultdict(list)

    for key, fields, problem in parsed:
        seen[key.lower()].append(key)
        if problem:
            errors.append(f"entry    {key}: {problem}")
        if "doi" in fields and not BARE_DOI.fullmatch(clean(fields["doi"])):
            errors.append(f"doi      {key}: {clean(fields['doi'])!r} is not a bare DOI")
        if "year" in fields and not YEAR.fullmatch(clean(fields["year"])):
            errors.append(f"year     {key}: {clean(fields['year'])[:60]!r} is not a year")
        if "journal" in fields:
            journal = clean(fields["journal"])
            if URL.match(journal):
                warnings.append(f"journal  {key}: is a URL: {journal[:70]}")
            elif PATHLIKE.fullmatch(journal):
                errors.append(f"journal  {key}: {journal[:70]!r} is a file path")
        for name, raw in fields.items():
            if STRAY_ENTRY.search(raw):
                errors.append(f"entry    {key}: field {name} contains another entry")
            if SPLIT_ACCENT.search(raw):
                errors.append(f"accent   {key}: field {name} has an accent split from its letter")
        for field in NAME_FIELDS:
            if field in fields:
                for person in re.split(r"\s+and\s+", clean(fields[field])):
                    if person.count(",") > 2:
                        errors.append(f"name     {key}: {field} has too many commas: {person[:50]}")
        if "crossref" in fields:
            if clean(fields["crossref"]).lower() not in keys:
                errors.append(f"entry    {key}: crossref {clean(fields['crossref'])!r} does not exist")
            elif len(fields) == 1:
                warnings.append(f"entry    {key}: only a crossref; empty unless its parent is derived too")
            if types[key.lower()] == "inbook" and "author" not in parents.get(clean(fields["crossref"]).lower(), {}):
                errors.append(f"entry    {key}: @inbook whose crossref parent has no author stops MyST")
        if " " in clean(fields.get("url", "")):
            warnings.append(f"url      {key}: contains a space, which breaks the link")
        if any(r"\-" in fields.get(field, "") for field in ("author", "title")):
            warnings.append(rf"hyphen   {key}: {{\-}} in author or title prints literally in MyST")

    for variants in seen.values():
        if len(variants) > 1:
            errors.append(f"entry    duplicate key: {', '.join(variants)}")

    for line in warnings:
        print("warning: " + line)
    for line in errors:
        print("error:   " + line)
    print(f"{path.name}: {len(parsed)} entries, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
