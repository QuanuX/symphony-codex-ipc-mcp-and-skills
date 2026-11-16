#!/usr/bin/env python3
"""Verify a D07 client packet against independently selected D06 owner evidence.

This separate protocol proves consistency of exact retained bytes and evidence.
It never manufactures an executable source stamp, authenticates a publisher, or
grants release approval. The existing W13 self-stamp verifier stays unchanged.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import zipfile

import verify_beta_compatibility as base

OWNER_FIELDS = ('kind', 'cohort_result_sha256', 'round_result_sha256', 'delivery_record_sha256',
                'derived_source_export_digest', 'round', 'qxctl_payload_path')
VERSION_FIELDS = ('protocol', 'component_id', 'version', 'source_state', 'source_commit', 'source_tree',
                  'source_date_epoch', 'dependency_map_sha256', 'build_recipe', 'go_version', 'goos',
                  'goarch', 'executable_sha256')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def requirements(value):
    base.fields(value, ('schema', 'compatibility', 'owner_build_evidence'), 'distribution requirements')
    base.need(value['schema'] == 'symphony.distribution-client.requirements.v1', 'Wrong distribution requirements schema')
    base.requirements(value['compatibility'])
    owner = value['owner_build_evidence']
    base.fields(owner, OWNER_FIELDS, 'external owner requirements')
    base.need(owner['kind'] == 'd06-external-cohort' and owner['round'] == 'round-1' and
              owner['qxctl_payload_path'] == 'go/qxctl/bin/qxctl', 'Unselected external owner scope')
    for name in OWNER_FIELDS[1:5]:
        base.digest(owner[name])


def hash_file(path, limit=base.FILE_LIMIT):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        base.need(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'Not a bounded regular input')
        h, size = hashlib.sha256(), 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(chunk)
            base.need(size <= limit, 'Input size limit')
            h.update(chunk)
        after = os.fstat(stream.fileno())
        base.need(size == before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
                  'Input changed during verification')
        return {'sha256': h.hexdigest(), 'size': size, 'mode': stat.S_IMODE(after.st_mode)}


def inventory(root, *, links):
    base.need(root.is_dir() and not root.is_symlink(), 'Selected input tree is absent or linked')
    root = root.resolve(strict=True)
    result = []
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix(); base.relative(name)
        if path.is_symlink():
            base.need(links and root in path.resolve(strict=True).parents, 'Escaping or unselected source link')
            result.append({'path': name, 'link': os.readlink(path)})
        elif path.is_dir():
            continue
        else:
            result.append({'path': name, **hash_file(path)})
        base.need(len(result) <= 20000, 'Input tree member limit')
    return result


def selected_json(path, expected, label, pending):
    if not path.exists():
        base.need(not path.is_symlink(), 'Linked evidence input')
        pending.append('missing owner evidence: ' + label)
        return None
    raw = base.regular(path, base.JSON_LIMIT)
    base.need(base.sha(raw) == expected, 'Owner evidence digest mismatch: ' + label)
    return base.strict_json(raw)


def no_approval(document, keys):
    for key in keys:
        base.need(document.get(key) is False, 'Owner evidence claims unselected approval: ' + key)


def unique(rows, key, label):
    base.need(type(rows) is list, 'Invalid ' + label)
    result = {row[key]: row for row in rows}
    base.need(len(result) == len(rows), 'Duplicate ' + label)
    return result


def owner_evidence(wrapper, cohort_root, delivery_path, export, pending):
    req, selected = wrapper['compatibility'], wrapper['owner_build_evidence']
    core = req['sources']['core']
    round_root = base.attachment(cohort_root, selected['round'])
    aggregate = selected_json(base.attachment(cohort_root, 'result.json'), selected['cohort_result_sha256'], 'aggregate', pending)
    completed = selected_json(base.attachment(round_root, 'result.json'), selected['round_result_sha256'], 'round', pending)
    delivery = selected_json(delivery_path, selected['delivery_record_sha256'], 'delivery', pending)
    # Present contradictory evidence remains invalid even when another selected
    # input is absent. Missing whole attachments alone remain incomplete.
    if aggregate is not None:
        base.need(aggregate['protocol'] == 'symphony.distribution.clean-cohort.v1' and
                  aggregate['state'] == 'built_and_sdk_checked', 'Owner aggregate is not a completed D06 cohort')
        base.need((aggregate['source_commit'], aggregate['source_tree']) == (core['commit'], core['tree']), 'Owner core source differs')
        no_approval(aggregate, ('acceptance_complete', 'publication_authorized'))
        source_input = aggregate['source_input']
        base.need(source_input['kind'] == 'verified_reviewed_derived_export' and source_input['verified'] is True and
                  'sha256:' + source_input['export_digest'] == selected['derived_source_export_digest'], 'Owner reviewed source binding differs')
    if completed is not None:
        base.need(completed['state'] == 'built_and_sdk_checked' and completed['native_count'] == 51 and
                  len(unique(completed['go_commands'], 'component_id', 'Go command')) == 6 and
                  len(unique(completed['native_receipts'], 'component_id', 'native receipt')) == 51,
                  'Completed owner round is not the 51-native/six-Go cohort')
        no_approval(completed, ('publication_authorized',))
        base.need(completed['sdk_audit']['status'] == completed['installed_owner_audit']['status'] ==
                  completed['loader_audit']['status'] == 'passed', 'Owner engineering gate is incomplete')
    if delivery is not None:
        base.need(delivery['protocol'] == 'symphony.distribution.d06-delivery-record.v1' and
                  delivery['state'] == 'inventory_complete_publisher_review_pending', 'Delivery inventory is incomplete')
        base.need(delivery['source_binding'] == {'commit': core['commit'], 'tree': core['tree']}, 'Delivery core binding differs')
        no_approval(delivery, ('publication_authorized', 'release_ready', 'fresh_host_accepted'))
        base.need('sha256:' + delivery['build_result_sha256'] == selected['cohort_result_sha256'] and
                  'sha256:' + delivery['round_result_sha256'] == selected['round_result_sha256'], 'Delivery cohort binding differs')
        source = delivery['source']
        base.need(source['mode'] == 'verified_derived_public_export' and source['matching_build_install_source_prepared'] is True and
                  (source['origin_commit'], source['origin_tree']) == (core['commit'], core['tree']) and
                  'sha256:' + source['derived_export_digest'] == selected['derived_source_export_digest'], 'Delivery reviewed source differs')
    if any(item is None for item in (aggregate, completed, delivery)):
        return None
    rounds = unique(aggregate['rounds'], 'directory', 'aggregate round')
    row = rounds.get(selected['round'])
    base.need(row is not None and 'sha256:' + row['result_sha256'] == selected['round_result_sha256'] and
              row['native_count'] == 51 and row['go_count'] == 6, 'Aggregate round binding differs')
    payload = base.attachment(round_root, 'relocated-prefix')
    actual = inventory(payload, links=True)
    base.need(actual == completed['payload_inventory'] == delivery['payload_files'], 'Final payload inventory differs')
    by_path = unique(actual, 'path', 'payload path')
    for receipt in completed['native_receipts']:
        path = 'share/symphony/receipts/' + receipt['component_id'] + '/' + receipt['version'] + '/install-receipt.json'
        base.relative(path)
        base.need(by_path.get(path, {}).get('sha256') == receipt['receipt_sha256'], 'Native receipt bytes differ')
    qxctl = by_path.get(selected['qxctl_payload_path'])
    commands = unique(completed['go_commands'], 'component_id', 'Go command')
    artifacts = unique(delivery['go_artifacts'], 'id', 'delivery Go artifact')
    go = artifacts.get('go:qxctl')
    base.need(qxctl is not None and go is not None and len(artifacts) == 6 and
              qxctl.get('mode', 0) & 0o111 and
              qxctl.get('sha256') == commands['qxctl']['sha256'] == go['sha256'] == req['bindings']['qxctl_sha256'][7:] and
              go['path'] == selected['qxctl_payload_path'] and go['version'] == commands['qxctl']['version'] and
              go['go_version'] == 'go1.26.5' and go['main_module']['Path'] == 'github.com/QuanuX/Symphony/tools/qxctl' and
              not go['main_module'].get('Replace'), 'D06 qxctl artifact differs')
    settings = unique(go['settings'], 'Key', 'Go build setting')
    base.need(settings['-trimpath']['Value'] == 'true' and settings['CGO_ENABLED']['Value'] == '0', 'Owner Go build policy differs')
    manifest_path = base.attachment(export, 'SOURCE-EXPORT.json')
    if not manifest_path.exists():
        base.need(not manifest_path.is_symlink(), 'Linked export manifest')
        pending.append('missing owner evidence: reviewed export manifest')
        return None
    manifest = base.strict_json(base.regular(manifest_path, base.JSON_LIMIT))
    base.need(manifest['protocol'] == 'symphony.public-source-export.v2' and manifest['is_original_git_tree'] is False and
              (manifest['origin_commit'], manifest['origin_tree']) == (core['commit'], core['tree']), 'Reviewed export origin differs')
    no_approval(manifest, ('release_acceptance_complete', 'publication_authorized'))
    rows = manifest['source_files']; unique(rows, 'path', 'exported source')
    expected, digest_rows = [], []
    for row in sorted(rows, key=lambda item: item['path']):
        base.relative(row['path']); base.digest('sha256:' + row['export_sha256'])
        base.need(row['mode'] in ('100644', '100755'), 'Unselected export file mode')
        expected.append({'path': row['path'], 'mode': int(row['mode'], 8) & 0o777,
                         'sha256': row['export_sha256'], 'size': row['export_size']})
        digest_rows.append({'path': row['path'], 'mode': row['mode'], 'sha256': row['export_sha256']})
    base.need(base.sha(canonical(digest_rows)) == selected['derived_source_export_digest'] ==
              'sha256:' + manifest['derived_export_digest'], 'Reviewed export inventory digest differs')
    # The source export orders POSIX strings; the native builder orders Path
    # components. Membership and exact file records are the invariant here.
    base.need(unique(inventory(base.attachment(export, 'source'), links=False), 'path', 'reviewed source') ==
              unique(expected, 'path', 'expected source') ==
              unique(inventory(base.attachment(cohort_root, 'source'), links=False), 'path', 'built source'),
              'Built source bytes or modes differ from reviewed export')
    archive = hash_file(base.attachment(export, 'symphony-source.tar'))
    base.need(archive['sha256'] == aggregate['source_input']['archive_sha256'] == delivery['source']['export_archive_sha256'],
              'Reviewed source archive differs from owner input')
    repair = aggregate.get('repair_provenance')
    if repair is not None:
        base.need(aggregate.get('fresh_whole_cohort_build') is False and completed.get('fresh_whole_cohort_build') is False and
                  delivery.get('fresh_whole_cohort_build') is False and aggregate.get('original_evidence_unchanged') is True and
                  aggregate.get('repeated_payload_bytes_equal') is False and delivery.get('repeated_payload_bytes_equal') is False,
                  'Retained repair is falsely labelled a fresh whole build')
        base.need(repair == delivery['repair_provenance'] and completed['native_unit_provenance'] == delivery['native_unit_provenance'] and
                  repair['source_inventory_sha256'] == manifest['derived_export_digest'], 'Repair source/provenance differs')
        provenance = unique(completed['native_unit_provenance'], 'component_id', 'native provenance')
        rebuilt = {key for key, item in provenance.items() if item['kind'] == 'rebuilt_from_exact_origin_source'}
        inherited = {key for key, item in provenance.items() if item['kind'] == 'inherited_native_receipt_and_bytes'}
        base.need(len(provenance) == 51 and len(rebuilt) == 8 and len(inherited) == 43 and rebuilt == set(repair['rebuild_ids']) and
                  completed['repaired_native_count'] == delivery['repaired_native_count'] == 8 and
                  completed['inherited_native_count'] == delivery['inherited_native_count'] == repair['inherited_native_count'] == 43 and
                  completed['inherited_go_count'] == delivery['inherited_go_count'] == repair['inherited_go_count'] == 6,
                  'Repair inheritance coverage differs')
        base.need(go['build_provenance'] == {'kind': 'inherited_exact_origin_bytes', 'origin_tool_commit': repair['origin_tool_commit'],
                  'origin_payload_inventory_sha256': repair['origin_payload_inventory_sha256']}, 'Inherited qxctl provenance differs')
    else:
        base.need(all(item.get('fresh_whole_cohort_build') is not False for item in (aggregate, completed, delivery)) and
                  delivery.get('repair_provenance') is None, 'Unbound inherited owner provenance')
    return {'kind': selected['kind'], 'selected_evidence': selected, 'verified_payload_entries': len(actual),
            'verified_source_files': len(expected), 'source_export_manifest_sha256': base.sha(base.regular(manifest_path, base.JSON_LIMIT)),
            'host': aggregate['host'], 'qxctl': go, 'repair_provenance': repair,
            'fresh_whole_cohort_build': aggregate.get('fresh_whole_cohort_build', True),
            'builder_sha256': aggregate['builder_sha256'], 'build_helpers': aggregate['build_helpers'],
            'imported_helpers': aggregate['imported_helpers'], 'repair_helpers': aggregate.get('repair_helpers', {}),
            'scope': 'exact retained evidence and byte consistency; no publisher authentication, source-stamp repair or new platform acceptance'}


def owner_version(version, proof, bindings):
    base.fields(version, VERSION_FIELDS, 'distribution qxctl version')
    base.need(version['protocol'] == 'symphony.qxctl.build-info.v1' and version['component_id'] == 'qxctl' and
              version['source_state'] == 'unavailable' and all(version[key] is None for key in
              ('source_commit', 'source_tree', 'source_date_epoch', 'dependency_map_sha256', 'build_recipe')),
              'Distribution verifier requires the actual unstamped owner response')
    base.need('sha256:' + version['executable_sha256'] == bindings['qxctl_sha256'], 'Owner version/executable mismatch')
    if proof:
        qxctl, host = proof['qxctl'], proof['host']
        base.need(version['version'] == qxctl['version'] and version['go_version'] == qxctl['go_version'] and
                  version['goos'] == {'macos': 'darwin', 'linux': 'linux'}[host['os']] and
                  version['goarch'] == host['architecture'], 'Owner version/build evidence differs')


def catalog_source(package, wrapper, version):
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        names = set(archive.namelist())
        base.need({'scripts/verify_distribution_compatibility.py', 'schemas/distribution-client-v1.schema.json',
                   'catalog/beta-source.json'} <= names, 'Distribution package lacks provenance verifier/source binding')
        value = base.strict_json(archive.read('catalog/beta-source.json'))
    req, selected = wrapper['compatibility'], wrapper['owner_build_evidence']
    base.need(value['schema'] == 'symphony.beta-catalog-source.v1' and value['core'] == req['sources']['core'] and
              value['qxctl_build'] == version and value['publication_authorized'] is False, 'Packaged catalog source differs')
    for key in ('expected_registry_digest', 'observed_registry_digest', 'catalog_sha256'):
        base.need(value[key] == req['bindings'][key], 'Packaged catalog identity differs')
    owner = value['distribution_source_binding']
    base.need(owner['kind'] == 'verified_d06_derived_source_and_exact_payload' and owner['self_stamp'] == 'unavailable' and
              owner['legacy_w13_source_stamp_gate'] == 'not_passed' and owner['release_acceptance_complete'] is False,
              'Packaged catalog misrepresents owner provenance')
    for key in ('cohort_result_sha256', 'round_result_sha256', 'delivery_record_sha256', 'qxctl_payload_path'):
        base.need(owner[key] == selected[key], 'Packaged catalog cohort binding differs')
    base.need('sha256:' + owner['derived_source_export_digest'] == selected['derived_source_export_digest'],
              'Packaged catalog reviewed export differs')


def client_evidence(req, obs, data, pending):
    """Retain W13 client/transcript/assertion rules without its owner-stamp gate."""
    for target in req['clients']:
        key = obs['clients'].get(target['id'])
        if key is None:
            pending.append('missing client: ' + target['id']); continue
        base.need(type(key) is str and key in req['artifacts'], 'Unbound client evidence')
        if key not in data:
            continue
        config_key = target['id'] + '-config'
        base.need(config_key in req['artifacts'] and req['artifacts'][config_key]['sha256'] == target['config_sha256'], 'Unbound client configuration')
        report = base.strict_json(data[key])
        base.fields(report, ('schema', 'sources', 'bindings', 'client', 'cases', 'scope', 'transcripts'), 'client report')
        base.need(report['schema'] == 'symphony.beta-client-evidence.v1' and report['scope'] == 'deterministic_app_server_native_owner', 'Fixture is not real client evidence')
        base.need(report['sources'] == req['sources'] and report['bindings'] == req['bindings'] and report['client'] == target, 'Client evidence identity mismatch')
        transcripts = report['transcripts']
        base.need(type(transcripts) is list and len(transcripts) == 3 and len(set(transcripts)) == 3 and
                  all(t in req['artifacts'] and t not in base.ARTIFACTS and t != key for t in transcripts), 'Unbound session transcripts')
        base.need(type(report['cases']) is list and len(report['cases']) <= 128, 'Invalid cases')
        seen = set()
        for case in report['cases']:
            base.fields(case, ('id', 'status', 'evidence'), 'case'); base.text(case['id'])
            base.need(case['id'] not in seen and case['id'] in base.CASES, 'Duplicate or unexpected case'); seen.add(case['id'])
            base.need(case['status'] in ('passed', 'failed', 'pending'), 'Invalid case status')
            base.need(type(case['evidence']) is list and len(case['evidence']) <= 32 and
                      len(case['evidence']) == len(set(case['evidence'])), 'Invalid evidence references')
            if case['status'] != 'passed':
                pending.append(target['id'] + ': ' + case['id']); continue
            base.need(case['evidence'] and all(e in req['artifacts'] and e not in base.ARTIFACTS and e != key for e in case['evidence']),
                      'Passed case missing bound observations')
            for evidence in case['evidence']:
                if evidence not in data:
                    continue
                assertions = base.strict_json(data[evidence])
                base.need(type(assertions) is list and len(assertions) <= 128, 'Invalid assertion ledger')
                matches = [a for a in assertions if type(a) is dict and a.get('id') == case['id']]
                base.need(len(matches) == 1 and matches[0].get('status') == case['status'], 'Contradictory or omitted assertion')
        pending.extend(target['id'] + ': missing case ' + key for key in base.CASES if key not in seen)


def verify(wrapper, obs, root, cohort_root, delivery_record, export):
    requirements(wrapper); req = wrapper['compatibility']
    base.fields(obs, ('schema', 'sources', 'bindings', 'clients', 'distribution', 'release_acceptance_complete', 'publication_authorized'), 'observations')
    base.need(obs['schema'] == 'symphony.beta-compatibility.observations.v1' and obs['sources'] == req['sources'] and
              obs['bindings'] == req['bindings'], 'Source pair or binding mismatch')
    base.need(obs['release_acceptance_complete'] is False and obs['publication_authorized'] is False and
              obs['distribution'] == 'pending', 'Unselected final acceptance claim')
    base.need(type(obs['clients']) is dict and obs['clients'].keys() <= {c['id'] for c in req['clients']}, 'Unselected client')
    pending, data = [], {}
    for ident, selected in req['artifacts'].items():
        path = base.attachment(root, selected['path'])
        if not path.exists():
            pending.append('missing artifact: ' + ident); continue
        raw = base.regular(path)
        base.need(base.sha(raw) == selected['sha256'], 'Attachment digest mismatch: ' + ident)
        data[ident] = raw
    for key in ('qxctl', 'bridge', 'catalog', 'package'):
        base.need(req['artifacts'][key]['sha256'] == req['bindings'][key + '_sha256'], 'Artifact binding mismatch: ' + key)
    proof = owner_evidence(wrapper, cohort_root, delivery_record, export, pending)
    if 'qxctl_version' in data:
        owner_version(base.strict_json(data['qxctl_version']), proof, req['bindings'])
    if base.ARTIFACTS <= data.keys():
        decoded = {key: base.strict_json(data[key]) for key in base.ARTIFACTS - {'qxctl', 'bridge', 'package'}}
        for kind in ('expected', 'observed'):
            base.need(decoded[kind + '_registry']['registry_digest'] == req['bindings'][kind + '_registry_digest'], 'Registry digest mismatch')
        base.need(decoded['observed_registry']['executable_digest'] == req['bindings']['qxctl_sha256'], 'Observed executable mismatch')
        base.catalog_check(decoded['expected_registry'], decoded['observed_registry'], decoded['catalog'])
        base.need(decoded['source_inventory']['source'] == req['sources']['plugin'], 'Packaged source identity mismatch')
        base.package_check(data['package'], decoded['package_inventory'], decoded['source_inventory'], req['bindings'])
        catalog_source(data['package'], wrapper, decoded['qxctl_version'])
    client_evidence(req, obs, data, pending)
    return {'schema': 'symphony.distribution-client.report.v1', 'status': 'incomplete' if pending else 'engineering_review_ready',
            'sources': req['sources'], 'bindings': req['bindings'], 'owner_build_evidence': proof,
            'legacy_w13_source_stamp_gate': 'unavailable_not_passed',
            'scope': 'independent distribution-bound integrity and selected real-client evidence; not a W13 stamp pass or publisher approval',
            'acceptance_mapping': ['C02.4', 'MCP-CHANNELS', 'D07'], 'pending': pending, 'distribution': 'pending',
            'publisher_authentication': 'not_established', 'fresh_host_accepted': False,
            'release_acceptance_complete': False, 'publication_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('requirements', 'observations', 'evidence-root', 'cohort-root', 'delivery-record', 'export', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        requirements_raw, observations_raw = base.regular(args.requirements, base.JSON_LIMIT), base.regular(args.observations, base.JSON_LIMIT)
        result = verify(base.strict_json(requirements_raw), base.strict_json(observations_raw), args.evidence_root.resolve(strict=True),
                        args.cohort_root, args.delivery_record, args.export)
        result.update(requirements_sha256=base.sha(requirements_raw), observations_sha256=base.sha(observations_raw),
                      verifier_sha256='sha256:' + hash_file(Path(__file__))['sha256'])
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(result, stream, indent=2); stream.write('\n')
        return 2 if result['pending'] else 0
    except (ValueError, KeyError, TypeError, OSError, RecursionError, RuntimeError, zipfile.BadZipFile) as error:
        print('Invalid distribution compatibility evidence: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
