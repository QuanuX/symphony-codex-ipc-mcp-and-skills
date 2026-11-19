#!/usr/bin/env python3
"""Create a deterministic local review ZIP; never upload or include profiles."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('README.md', 'INTENT.md', 'LICENSE', 'CMakeLists.txt', 'plugin.json', 'mcp.json', '.mcp.json', '.gitignore', '.gitattributes')
DIRS = ('src', 'include', 'third_party', 'scripts', 'tests', 'skills', 'docs', 'adapters', '.claude-plugin', '.codex-plugin', 'assets', 'catalog', 'schemas', 'ci', 'packaging')

def collect_members(root=ROOT, tracked_paths=None):
    """Select public package files; callers may restrict this to a committed tree."""
    if tracked_paths is not None:
        return {name: root / name for name in tracked_paths
                if name in FILES or (Path(name).parts and Path(name).parts[0] in DIRS)}
    selected = [root / name for name in FILES if (root / name).is_file()]
    for name in DIRS:
        directory = root / name
        if directory.exists():
            selected.extend(x for x in directory.rglob('*') if x.is_file()
                            and '__pycache__' not in x.parts and x.suffix != '.pyc')
    return {str(x.relative_to(root)): x for x in selected}


def read_entries(members, root=ROOT):
    if len(members) > 5000:
        raise ValueError('Too many archive members')
    total = 0
    entries = {}
    for name, source in sorted(members.items()):
        if source.is_symlink() or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe archive member')
        data = source.read_bytes()
        if name != 'bin/symphony-mcp':
            # Do not ship developer-machine paths, connection profiles or local evidence.
            if str(Path.home()).encode() in data or str(root.parent / 'symphony-agent-plugin-evidence').encode() in data:
                raise ValueError('Private local path/evidence found in '+name)
        total += len(data)
        if len(data)>100*1024*1024 or total>512*1024*1024:
            raise ValueError('Archive exceeds published size limits')
        entries[name] = data
    return entries


def write_archive(output, entries):
    """Write the same deterministic ZIP bytes for the same named byte contents."""
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids silently replacing an already-reviewed candidate.
    with open(output, 'xb') as stream, zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(entries.items()):
            info=zipfile.ZipInfo(name, (2026,10,22,0,0,0))
            info.create_system=3
            mode=0o755 if name=='bin/symphony-mcp' else 0o644
            info.external_attr=(stat.S_IFREG|mode)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
    if output.stat().st_size>100_000_000:
        output.unlink()
        raise ValueError('Compressed archive exceeds100MB')
    result={'artifact':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'files':len(entries),'expanded_bytes':sum(map(len, entries.values())),'compressed_bytes':output.stat().st_size,'includes_binary':'bin/symphony-mcp' in entries,'submitted':False}
    output.with_suffix(output.suffix+'.sha256').write_text(result['sha256']+'  '+output.name+'\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--binary', type=Path, help='Include an explicitly selected built binary as bin/symphony-mcp')
    args = p.parse_args()
    members = collect_members()
    if args.binary:
        if not args.binary.is_file() or args.binary.is_symlink():
            p.error('Select a regular compiled binary')
        members['bin/symphony-mcp'] = args.binary
    try:
        result = write_archive(args.output, read_entries(members))
    except (OSError, ValueError) as error:
        p.error(str(error))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
