"""Stable, portable TR-DOS game bundles (seven base-36 characters + part).

Only generated BASIC filename literals are rewritten. Compressed CODE data
is never patched. The identity includes the tape, options and packed bytes,
but excludes source paths, menu labels and a game's position on the disk.
"""
from dataclasses import replace
import hashlib
import json
import re
import struct


NAMING_VERSION = 1
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
NAME_SPACE = 36 ** 7


def bundle_id(files, tape_sha256, item):
    options = {"version": NAMING_VERSION, "tape": tape_sha256,
               "machine": str(item.get("machine", "auto")),
               "transfer_mode": str(item.get("transfer_mode", "auto")),
               "start": str(item.get("start", "")).strip()}
    digest = hashlib.sha256(json.dumps(options, sort_keys=True).encode("ascii"))
    for f in files:
        # Include the BASIC autostart trailer, but not sector padding.
        data = f.data[:f.length + (4 if f.kind == "B" else 0)]
        header = json.dumps([f.name, f.kind, f.parameter, f.length]).encode("ascii")
        digest.update(struct.pack("<II", len(header), len(data)))
        digest.update(header)
        digest.update(data)
    return digest.hexdigest()


def short_name(identity, collision=0):
    value = (int(identity, 16) + collision) % NAME_SPACE
    result = ""
    for _ in range(7):
        value, digit = divmod(value, 36)
        result = ALPHABET[digit] + result
    return result


def rename_bundle(files, old_prefix, stem):
    """Rename a generated bundle, rebuilding BASIC lengths and its trailer."""
    if not re.fullmatch(r"[0-9A-Z]{7}", stem):
        raise ValueError("Invalid TR-DOS game identifier")
    loaders = [f for f in files if f.kind == "B"]
    parts = [f for f in files if f.kind == "C"]
    if len(loaders) != 1 or not parts or len(files) != len(parts) + 1:
        raise ValueError("Unexpected TR-DOS game bundle")
    suffixes = set()
    for f in parts:
        suffix = f.name.removeprefix(old_prefix)
        if not f.name.startswith(old_prefix) or not re.fullmatch(r"[0-9A-Z]", suffix) or suffix in suffixes:
            raise ValueError("Unexpected TR-DOS part name: " + f.name)
        suffixes.add(suffix)
    loader = loaders[0]
    trailer = loader.data[loader.length:loader.length + 4]
    if loader.parameter != loader.length or len(trailer) != 4 or trailer[:2] != b"\x80\xaa":
        raise ValueError("Unexpected TR-DOS BASIC trailer or variables")
    literal = re.compile(rb'"' + re.escape(old_prefix.encode("ascii")) + rb'([0-9A-Z]?)"')
    references = set()

    def substitute(match):
        suffix = match[1].decode("ascii")
        if suffix and suffix not in suffixes:
            raise ValueError("BASIC references a missing TR-DOS part")
        references.add(suffix)
        return b'"' + stem.encode("ascii") + match[1] + b'"'

    program = bytearray()
    pos = 0
    while pos < loader.length:
        if pos + 4 > loader.length:
            raise ValueError("Truncated BASIC line header")
        size = int.from_bytes(loader.data[pos + 2:pos + 4], "little")
        end = pos + 4 + size
        if not size or end > loader.length or loader.data[end - 1] != 13:
            raise ValueError("Invalid BASIC line length")
        body = literal.sub(substitute, loader.data[pos + 4:end])
        program.extend(loader.data[pos:pos + 2] + struct.pack("<H", len(body)) + body)
        pos = end
    if not references or ("" not in references and references != suffixes):
        raise ValueError("BASIC does not reference all TR-DOS parts")
    return [replace(f, name=stem, parameter=len(program), length=len(program), data=bytes(program) + trailer)
            if f.kind == "B" else replace(f, name=stem + f.name[len(old_prefix):])
            for f in files]


def manifest(files):
    return [{"name": f.name, "type": f.kind, "bytes": f.sectors * 256} for f in files]
