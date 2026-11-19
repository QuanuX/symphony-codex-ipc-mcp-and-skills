#!/usr/bin/env python3
"""Build one beta.2 review ZIP from clean source and an exact released client.

This performs no download, installation, upload or submission. First verify the
beta publisher signature and extract the selected client using the release guide.
The checked-in pins then bind the binary/catalog inputs to that published cohort.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

import package_release

ROOT = Path(__file__).resolve().parents[1]
INPUTS = 'packaging/beta2/release-inputs.json'
REPLACED = ('bin/symphony-mcp', 'catalog/tools.json', 'catalog/beta-source.json',
            'catalog/stamped-owner-delta.json')
NATIVE_DIRS = ('src', 'include', 'third_party')


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def regular_bytes(root, name):
    path = root / name
    # Inspect the selected root and descendants. System ancestors such as macOS
    # /var may legitimately be symlinks and are not package members.
    components = Path(name).parts
    if (Path(name).is_absolute() or '..' in Path(name).parts
            or any((root / Path(*components[:n])).is_symlink()
                   for n in range(len(components) + 1))
            or not path.is_file()):
        raise ValueError('Expected a regular, non-symlink input: ' + name)
    return path.read_bytes()


def verify_inputs(root, released_client, profile, inputs):
    if profile not in inputs['profiles']:
        raise ValueError('Unsupported beta profile: ' + profile)
    pins = inputs['profiles'][profile]
    version = json.loads(regular_bytes(root, 'plugin.json'))['version']
    if version != inputs['package_version']:
        raise ValueError('Plugin version differs from the pinned review package version')
    replacements = {}
    for name in REPLACED:
        data = regular_bytes(released_client, name)
        if digest(data) != pins['files'][name]:
            raise ValueError('Released input hash/profile mismatch: ' + name)
        replacements[name] = data
    native_names = {p.relative_to(root).as_posix() for directory in NATIVE_DIRS
                    for p in (root / directory).rglob('*') if p.is_file() or p.is_symlink()}
    if native_names != set(inputs['native_files']):
        raise ValueError('Native source file set differs from the released bridge')
    for name, expected in inputs['native_files'].items():
        if digest(regular_bytes(root, name)) != expected:
            raise ValueError('Native source differs from the released bridge: ' + name)
    source = json.loads(replacements['catalog/beta-source.json'])
    catalog = json.loads(replacements['catalog/tools.json'])
    if (source['core'] != inputs['native_source']
            or source['client_dependency'] != inputs['released_client_source']
            or source['catalog_sha256'] != digest(replacements['catalog/tools.json'])
            or source['observed_registry_digest'] != catalog['source_registry_digest']
            or source['observed_registry_digest'] != pins['bindings']['observed_registry_digest']
            or 'sha256:' + source['qxctl_build']['executable_sha256'] != pins['bindings']['qxctl_sha256']):
        raise ValueError('Released source, catalog and executable bindings disagree')
    counts = Counter(entry['binding']['kind'] for entry in catalog['entries'])
    contracts = {entry['binding']['command_id'] for entry in catalog['entries']}
    if counts != {'read': 303, 'preview': 220, 'apply': 220} or len(contracts) != 523:
        raise ValueError('Unexpected beta.2 tool/contract census')
    return replacements, source


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def source_identity(root, require_clean=True):
    dirty = bool(git(root, 'status', '--porcelain', '--untracked-files=all'))
    if require_clean and dirty:
        raise ValueError('Commit the review source before creating final packages; use --validate-only for precommit input checks')
    return {'repository': 'QuanuX/symphony-codex-ipc-mcp-and-skills',
            'commit': git(root, 'rev-parse', 'HEAD'),
            'tree': git(root, 'rev-parse', 'HEAD^{tree}'),
            'clean': not dirty}


def build_entries(root, released_client, profile, inputs, identity):
    replacements, source = verify_inputs(root, released_client, profile, inputs)
    if not identity.get('clean'):
        raise ValueError('Final packages require clean review source')
    paths = git(root, 'ls-files', '-z').split('\0')
    members = package_release.collect_members(root, tracked_paths=paths)
    members[INPUTS] = root / INPUTS
    for name in members:
        parts = Path(name).parts
        if (Path(name).name in ('connection.json', 'credentials.json', '.env')
                or any(part in ('profiles', 'retention', 'transcripts', '.git') for part in parts)
                or Path(name).suffix in ('.key', '.pem')
                or (name.endswith('/plugin.json') and name not in
                    ('.claude-plugin/plugin.json', '.codex-plugin/plugin.json'))):
            raise ValueError('Private state or additional plugin root is not a package input: ' + name)
        regular_bytes(root, name)
    entries = package_release.read_entries(members, root)
    entries.update(replacements)
    for required in ('plugin.json', 'mcp.json', 'INTENT.md', 'skills/symphony-admin/SKILL.md',
                     'skills/symphony-setup/SKILL.md'):
        if required not in entries:
            raise ValueError('Missing required review package file: ' + required)
    pins = inputs['profiles'][profile]
    metadata = {
        'schema': 'symphony.beta-review-package.v1',
        'profile': profile,
        'package_version': inputs['package_version'],
        'bridge_runtime_version': inputs['bridge_runtime_version'],
        'release': inputs['release'],
        'review_source': identity,
        'native_source': inputs['native_source'],
        'released_client_source': inputs['released_client_source'],
        'released_inputs': pins,
        'qxctl_build': source['qxctl_build'],
        'tool_counts': {'native_contracts': 523, 'read': 303, 'preview': 220,
                        'apply': 220, 'connection': 1, 'total': 744},
        'constraints': {'fresh_beta2_prefix_required': True,
                        'beta1_in_place_upgrade_qualified': False,
                        'runtime_binary_rebuilt_for_this_refresh': False,
                        'native_sources_identical_to_released_bridge': True,
                        'openai_submission_or_approval_claimed': False},
        'files': {name: digest(data) for name, data in sorted(entries.items())},
    }
    entries['package-profile.json'] = json_bytes(metadata)
    if len(entries) > 5000 or sum(map(len, entries.values())) > 512 * 1024 * 1024:
        raise ValueError('Archive exceeds package size limits')
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--released-client', required=True, type=Path,
                        help='Extracted verified client root containing bin/ and catalog/')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--validate-only', action='store_true',
                        help='Check released inputs/native sources without writing a package; permits uncommitted review edits')
    args = parser.parse_args()
    try:
        inputs = json.loads(regular_bytes(ROOT, INPUTS))
        verify_inputs(ROOT, args.released_client, args.profile, inputs)
        identity = source_identity(ROOT, require_clean=not args.validate_only)
        if args.validate_only:
            print(json.dumps({'profile': args.profile, 'inputs_verified': True,
                              'source_clean': identity['clean'], 'package_created': False}, indent=2))
            return
        if args.output is None:
            parser.error('--output is required when creating a package')
        entries = build_entries(ROOT, args.released_client, args.profile, inputs, identity)
        result = package_release.write_archive(args.output, entries)
        result.update({'profile': args.profile, 'package_version': inputs['package_version'],
                       'bridge_runtime_version': inputs['bridge_runtime_version'],
                       'review_source': identity})
        print(json.dumps(result, indent=2))
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
