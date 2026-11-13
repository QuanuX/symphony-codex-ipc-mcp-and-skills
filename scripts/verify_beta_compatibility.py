#!/usr/bin/env python3
"""Verify a private, two-source W13 evidence packet; never execute or publish it.

Requirements are independently selected review inputs, not inferred from results.
Exit 0: engineering review ready; 1: invalid; 2: valid but incomplete.
This is consistency/integrity verification, not signer or human authentication.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

JSON_LIMIT = 8 * 1024 * 1024
FILE_LIMIT = 256 * 1024 * 1024
CASES = ('catalog_census', 'native_read', 'default_deny', 'prepare_no_effect',
         'apply_inspect', 'consumed_preview', 'changed_input', 'native_failure',
         'lost_response_recovery', 'restart_preview_refused', 'cleanup')
ARTIFACTS = {'qxctl', 'qxctl_version', 'expected_registry', 'observed_registry',
             'catalog', 'bridge', 'package', 'package_inventory', 'source_inventory'}
BINDINGS = {'qxctl_sha256', 'catalog_sha256', 'bridge_sha256', 'package_sha256',
            'expected_registry_digest', 'observed_registry_digest'}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), 'Invalid fields: ' + label)


def text(value):
    need(type(value) is str and 0 < len(value) <= 1024 and all(ord(c) >= 32 for c in value), 'Invalid text')
    return value


def digest(value):
    need(type(value) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', value), 'Invalid SHA256')
    return value


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def strict_json(data):
    need(len(data) <= JSON_LIMIT, 'JSON size limit')
    value = json.loads(data, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    def bounded(node, depth=0):
        need(depth <= 32, 'JSON depth limit')
        if isinstance(node, dict):
            need(len(node) <= 20000, 'Object size limit')
            for child in node.values(): bounded(child, depth + 1)
        elif isinstance(node, list):
            need(len(node) <= 20000, 'Array size limit')
            for child in node: bounded(child, depth + 1)
        elif isinstance(node, str): need(len(node) <= 1024 * 1024, 'String size limit')
    bounded(value)
    return value


def regular(path, limit=FILE_LIMIT):
    # O_NONBLOCK prevents FIFO hangs; O_NOFOLLOW rejects final symlinks.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        need(stat.S_ISREG(st.st_mode) and st.st_size <= limit, 'Not a bounded regular file')
        data = stream.read(limit + 1)
        need(len(data) <= limit, 'File size limit')
        return data


def sha(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def relative(name):
    text(name)
    p = PurePosixPath(name)
    need(not p.is_absolute() and '..' not in p.parts and str(p) == name and '\\' not in name and name != '.', 'Unsafe relative path')
    return p


def attachment(root, name):
    p = root
    for part in relative(name).parts:
        p = p / part
        need(not p.is_symlink(), 'Symlink attachment')
    return p


def sources(value):
    fields(value, ('core', 'plugin'), 'sources')
    for role, repo in [('core', 'QuanuX/Symphony'), ('plugin', 'QuanuX/symphony-codex-ipc-mcp-and-skills')]:
        item = value[role]
        fields(item, ('repository', 'commit', 'tree'), role)
        need(item['repository'] == repo, 'Wrong repository')
        for key in ('commit', 'tree'):
            need(type(item[key]) is str and re.fullmatch(r'[0-9a-f]{40}', item[key]), 'Invalid Git identity')


def client(value):
    fields(value, ('id', 'name', 'version', 'os', 'architecture', 'mode', 'config_sha256'), 'client')
    for key in ('id', 'name', 'version', 'os', 'architecture'): text(value[key])
    need(value['name'] == 'Codex' and value['mode'] in ('stdio', 'same_user_ipc'), 'Unsupported primary client scope')
    digest(value['config_sha256'])


def requirements(value):
    fields(value, ('schema', 'sources', 'bindings', 'artifacts', 'clients'), 'requirements')
    need(value['schema'] == 'symphony.beta-compatibility.requirements.v1', 'Wrong requirements schema')
    sources(value['sources'])
    fields(value['bindings'], BINDINGS, 'bindings')
    for v in value['bindings'].values(): digest(v)
    need(type(value['artifacts']) is dict and ARTIFACTS <= value['artifacts'].keys() and len(value['artifacts']) <= 256, 'Missing artifact requirements')
    paths = set()
    for key, a in value['artifacts'].items():
        text(key); fields(a, ('path', 'sha256'), 'artifact'); relative(a['path']); digest(a['sha256'])
        need(a['path'] not in paths, 'Duplicate artifact path'); paths.add(a['path'])
    need(type(value['clients']) is list and 1 <= len(value['clients']) <= 16, 'Missing client requirements')
    ids = set()
    for c in value['clients']:
        client(c); need(c['id'] not in ids, 'Duplicate client'); ids.add(c['id'])
    need({c['mode'] for c in value['clients']} == {'stdio', 'same_user_ipc'}, 'Require both connection modes')


def catalog_check(expected, observed, catalog):
    need(expected['registry_kind'] == 'expected' and observed['registry_kind'] == 'observed', 'Wrong registry kinds')
    records = {r['command_id']: r for r in expected['commands']}
    need(len(records) == len(expected['commands']) and expected['commands'] == observed['commands'], 'Registry records differ or duplicate')
    need(catalog['schema'] == 'symphony.public-tool-catalog.v1' and catalog['source_registry_digest'] == observed['registry_digest'], 'Catalog registry mismatch')
    names, covered = set(), {}
    for entry in catalog['entries']:
        binding, tool = entry['binding'], entry['tool']
        ident, kind = binding['command_id'], binding['kind']
        need(ident in records and binding['record'] == records[ident], 'Catalog native record mismatch')
        need(tool['name'] not in names, 'Duplicate tool'); names.add(tool['name'])
        phases = covered.setdefault(ident, set()); need(kind not in phases, 'Duplicate phase'); phases.add(kind)
        annotations = tool['annotations']
        need(annotations['readOnlyHint'] is (kind != 'apply') and annotations['destructiveHint'] is (kind == 'apply') and annotations['idempotentHint'] is False, 'Unsafe annotations')
    for ident, phases in covered.items():
        need(phases == ({'read'} if records[ident]['mutability'] == 'read_only' else {'preview', 'apply'}), 'Missing or invalid phase')
    excluded = {r['command_id']: r['reason'] for r in catalog['excluded_commands']}
    need(len(excluded) == len(catalog['excluded_commands']) and not (covered.keys() & excluded.keys()) and covered.keys() | excluded.keys() == records.keys(), 'Incomplete catalog census')
    need(set(excluded) == {'qxcmd:symphony:sov.target.invoke', 'qxcmd:symphony:stav.append'}, 'Unreviewed exclusion')
    need(not catalog.get('native_help_unavailable'), 'Unresolved native help')
    return len(records), len(names)


def package_check(data, inventory, source, bindings):
    import io
    need(type(inventory) is dict and 1 <= len(inventory) <= 5000, 'Invalid package inventory')
    fields(source, ('source', 'files'), 'source inventory')
    need(type(source['files']) is dict and len(source['files']) <= 5000, 'Invalid source inventory')
    actual, total = {}, 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        need(len(archive.infolist()) <= 5000, 'Package member limit')
        for entry in archive.infolist():
            relative(entry.filename)
            need(entry.filename not in actual and stat.S_ISREG(entry.external_attr >> 16), 'Duplicate or nonregular package entry')
            total += entry.file_size
            need(entry.file_size <= FILE_LIMIT and total <= 512 * 1024 * 1024, 'Package expanded size limit')
            with archive.open(entry) as stream:
                content = stream.read(FILE_LIMIT + 1)
            need(len(content) == entry.file_size, 'Package size mismatch')
            actual[entry.filename] = sha(content)
    need(actual == inventory, 'Package inventory mismatch')
    for name, expected in source['files'].items():
        relative(name); digest(expected)
        need(actual.get(name) == expected, 'Packaged source drift: ' + name)
    need(set(actual) == set(source['files']) | {'bin/symphony-mcp'}, 'Unaccounted package source')
    need(actual.get('bin/symphony-mcp') == bindings['bridge_sha256'] and actual.get('catalog/tools.json') == bindings['catalog_sha256'], 'Packaged bridge/catalog mismatch')
    for required in ('schemas/beta-compatibility-v1.schema.json', 'scripts/verify_beta_compatibility.py', 'src/main.cpp'):
        need(required in actual, 'Missing required package member')


def verify(req, obs, root):
    requirements(req)
    fields(obs, ('schema', 'sources', 'bindings', 'clients', 'distribution', 'release_acceptance_complete', 'publication_authorized'), 'observations')
    need(obs['schema'] == 'symphony.beta-compatibility.observations.v1', 'Wrong observations schema')
    need(obs['sources'] == req['sources'] and obs['bindings'] == req['bindings'], 'Source pair or binding mismatch')
    need(obs['release_acceptance_complete'] is False and obs['publication_authorized'] is False, 'Unauthorized acceptance claim')
    need(obs['distribution'] == 'pending', 'Final channel acceptance is outside W13')
    need(type(obs['clients']) is dict and obs['clients'].keys() <= {c['id'] for c in req['clients']}, 'Unselected client')
    pending, data = [], {}
    for ident, a in req['artifacts'].items():
        p = attachment(root, a['path'])
        if not p.exists(): pending.append('missing artifact: ' + ident); continue
        content = regular(p)
        need(sha(content) == a['sha256'], 'Attachment digest mismatch: ' + ident)
        data[ident] = content
    for key in ('qxctl', 'bridge', 'catalog', 'package'):
        need(req['artifacts'][key]['sha256'] == req['bindings'][key + '_sha256'], 'Artifact binding mismatch: ' + key)
    if ARTIFACTS <= data.keys():
        decoded = {k: strict_json(data[k]) for k in ARTIFACTS - {'qxctl', 'bridge', 'package'}}
        version, b = decoded['qxctl_version'], req['bindings']
        need(version['protocol'] == 'symphony.qxctl.build-info.v1' and version['source_state'] == 'stamped' and version['build_recipe'] == 'symphony.qxctl.reproducible-build.v1', 'Unstamped owner build')
        need(version['source_commit'] == req['sources']['core']['commit'] and version['source_tree'] == req['sources']['core']['tree'] and 'sha256:' + version['executable_sha256'] == b['qxctl_sha256'], 'Owner source/executable mismatch')
        for kind in ('expected', 'observed'):
            need(decoded[kind + '_registry']['registry_digest'] == b[kind + '_registry_digest'], 'Registry digest mismatch')
        need(decoded['observed_registry']['executable_digest'] == b['qxctl_sha256'], 'Observed executable mismatch')
        catalog_check(decoded['expected_registry'], decoded['observed_registry'], decoded['catalog'])
        need(decoded['source_inventory']['source'] == req['sources']['plugin'], 'Packaged source identity mismatch')
        package_check(data['package'], decoded['package_inventory'], decoded['source_inventory'], b)
    for target in req['clients']:
        key = obs['clients'].get(target['id'])
        if key is None: pending.append('missing client: ' + target['id']); continue
        need(type(key) is str and key in req['artifacts'], 'Unbound client evidence')
        if key not in data: continue
        config_key = target['id'] + '-config'
        need(config_key in req['artifacts'] and req['artifacts'][config_key]['sha256'] == target['config_sha256'], 'Unbound client configuration')
        need(config_key in data, 'Client configuration evidence is missing')
        report = strict_json(data[key])
        fields(report, ('schema', 'sources', 'bindings', 'client', 'cases', 'scope', 'transcripts'), 'client report')
        need(report['schema'] == 'symphony.beta-client-evidence.v1' and report['scope'] == 'deterministic_app_server_native_owner', 'Fixture is not real client evidence')
        need(report['sources'] == req['sources'] and report['bindings'] == req['bindings'] and report['client'] == target, 'Client evidence identity mismatch')
        transcripts = report['transcripts']
        need(type(transcripts) is list and len(transcripts) == 3 and len(set(transcripts)) == 3 and all(t in data and t not in ARTIFACTS and t != key for t in transcripts), 'Missing session transcripts')
        need(type(report['cases']) is list and len(report['cases']) <= 128, 'Invalid cases')
        seen = set()
        for case in report['cases']:
            fields(case, ('id', 'status', 'evidence'), 'case'); text(case['id'])
            need(case['id'] not in seen and case['id'] in CASES, 'Duplicate or unexpected case'); seen.add(case['id'])
            need(case['status'] in ('passed', 'failed', 'pending'), 'Invalid case status')
            need(type(case['evidence']) is list and len(case['evidence']) <= 32 and len(case['evidence']) == len(set(case['evidence'])), 'Invalid evidence references')
            if case['status'] != 'passed': pending.append(target['id'] + ': ' + case['id']); continue
            need(case['evidence'] and all(e in data and e not in ARTIFACTS and e != key for e in case['evidence']), 'Passed case missing bound observations')
            for evidence in case['evidence']:
                assertions = strict_json(data[evidence])
                need(type(assertions) is list and len(assertions) <= 128, 'Invalid assertion ledger')
                matches = [a for a in assertions if type(a) is dict and a.get('id') == case['id']]
                need(len(matches) == 1 and matches[0].get('status') == case['status'], 'Contradictory or omitted assertion')
        pending.extend(target['id'] + ': missing case ' + k for k in CASES if k not in seen)
    return {'schema': 'symphony.beta-compatibility.report.v1', 'status': 'incomplete' if pending else 'engineering_review_ready',
            'sources': req['sources'], 'bindings': req['bindings'], 'acceptance_mapping': ['C02.4', 'MCP-CHANNELS'],
            'pending': pending, 'distribution': 'pending', 'release_acceptance_complete': False, 'publication_authorized': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--requirements', type=Path, required=True)
    p.add_argument('--observations', type=Path, required=True)
    p.add_argument('--evidence-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        req_data, obs_data = regular(args.requirements, JSON_LIMIT), regular(args.observations, JSON_LIMIT)
        result = verify(strict_json(req_data), strict_json(obs_data), args.evidence_root.resolve(strict=True))
        result.update(requirements_sha256=sha(req_data), observations_sha256=sha(obs_data))
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream: json.dump(result, stream, indent=2); stream.write('\n')
        return 2 if result['pending'] else 0
    except (ValueError, KeyError, TypeError, OSError, RecursionError, zipfile.BadZipFile) as error:
        print('Invalid compatibility evidence: ' + str(error), file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
