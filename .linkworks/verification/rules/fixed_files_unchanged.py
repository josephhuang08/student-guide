import os
from jinja2 import Environment, BaseLoader
from lara.api.document import Document

FILES = [
    ("LICENSE", [(0, -1), (-1, 0)]),  # match completely
    ("LICENSES/MPL-2.0.txt", [(0, -1), (-1, 0)]),  # match completely
    ("CONTRIBUTING.md", [(0, -1), (-1, 0)]),  # match completely
    ("AUTHORS", [ (0, 6), ]), # match header
    ("DCO", [(0, -1), (-1, 0)]),  # match completely
]

rule_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(rule_dir, "data")

def load_document(filename):
    full_path = os.path.join(data_dir, filename)
    if not os.path.isfile(full_path):
        return None
    document = Document()
    document.load_file(full_path)
    return document

def verify(repository, template):
    errors = list()
    warnings = list()

    for fname, blklist in FILES:
        templatefile = load_document(fname)
        repofile = repository.load_document(fname)

        (tfixed, blkopts) = _blocklist2mask(len(templatefile), blklist)
        tendfixed = True if (blkopts & 0x01) else False

        templatefile = Environment(loader=BaseLoader()).from_string("".join(templatefile))
        templatefile = templatefile.render({**repository.environment}).splitlines(keepends=True)

        tid = 0
        for rid, rline in enumerate(repofile):
            if tid >= len(templatefile):
                break

            tline = templatefile[tid].strip()
            rline = rline.strip()
            # print("Checking line [{} {}-{}]: {}".format(tplfile, tid, rid, rline))

            if tline == rline:
                tid += 1
            else:
                if tfixed[tid] & 0x01:
                    # line changed or inserted in fixed block
                    errors.append("Template was modified in fixed line block: {}:{}.".format(fname, rid + 1))
        else:
            rid = len(repofile)

        if tid < len(templatefile):
            # unable to find line of the template
            errors.append("Template was modified in fixed line block: {}:{}.".format(fname, rid + 1))
        elif tendfixed:
            # disallow inserting lines after template EOF
            if tid != len(templatefile) or rid != len(repofile):
                errors.append("Template was modified in fixed line block: {}:{}.".format(fname, rid + 1))

    return errors, warnings


# takes a list of "blocks" (list of tuple "(start, end)" ) and turns it into a
# mask where all elements inside of blocks have a 1 and all others have a 0
def _blocklist2mask(masksize, blocks):
    options = 0x00

    tfixed = [0] * masksize
    for blk in blocks:
        if blk[0] == -1 and blk[1] == 0:
            # special command to verify \n of last line
            options |= 0x01
            continue

        bstart = blk[0] if blk[0] >= 0 else (masksize + blk[0])
        bend = blk[1] if blk[1] >= 0 else (masksize + blk[1])
        for tid in range(bstart, bend + 1):
            tfixed[tid] |= 0x01

    return (tfixed, options)
