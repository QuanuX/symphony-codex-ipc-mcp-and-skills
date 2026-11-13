#!/usr/bin/env python3
"""Qualify an explicitly selected Codex app-server with disposable SOV state.

Runs deterministic calls, never a model turn. Uses new private profiles and only
local target configure/inspect/remove. Synthetic target/job references MUST NOT
be invoked. Does not edit user configuration, grant authority or publish.
"""
import argparse
import hashlib
import stat
import json
import os
from pathlib import Path
import platform
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import time

from configure_clients import render
from verify_beta_compatibility import regular, strict_json, sha, need, sources, BINDINGS


class Codex:
    def __init__(self, executable, directory, fragment, log_prefix):
        directory.mkdir(mode=0o700)
        (directory / 'config.toml').write_text(fragment)
        (directory / 'config.toml').chmod(0o600)
        self.log = log_prefix.with_suffix('.jsonl').open('x')
        self.err = log_prefix.with_suffix('.stderr').open('x')
        self.sequence, self.queue = 0, queue.Queue(maxsize=1024)
        env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'LANG') if k in os.environ}
        env['CODEX_HOME'] = str(directory)
        self.p = subprocess.Popen([str(executable), 'app-server', '--stdio'], cwd=directory,
                                  env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=self.err, text=True, bufsize=1)
        def reader():
            try:
                while True:
                    line = self.p.stdout.readline(8 * 1024 * 1024 + 1)
                    if not line: break
                    if len(line) > 8 * 1024 * 1024: raise ValueError('Codex response size limit')
                    self.queue.put(json.loads(line), timeout=5)
            except Exception as e: self.queue.put({'reader_error': str(e)}, timeout=5)
            finally:
                try: self.queue.put({'eof': True}, timeout=5)
                except queue.Full: pass
        self.reader = threading.Thread(target=reader, daemon=True); self.reader.start()
        try:
            self.rpc('initialize', {'clientInfo': {'name': 'symphony-w13', 'version': '1'}, 'capabilities': {'experimentalApi': True}})
            self.send({'method': 'initialized', 'params': {}})
            response = self.rpc('thread/start', {'cwd': str(directory), 'ephemeral': True, 'sandbox': 'workspace-write', 'approvalPolicy': 'on-request'})
            self.thread = response['thread']['id']
        except Exception:
            self.close(); raise

    def send(self, item):
        self.log.write(json.dumps({'direction': 'send', 'message': item}) + '\n'); self.log.flush()
        self.p.stdin.write(json.dumps(item) + '\n'); self.p.stdin.flush()

    def rpc(self, method, params):
        self.sequence += 1; ident = self.sequence
        self.send({'id': ident, 'method': method, 'params': params})
        end = time.monotonic() + 75
        while time.monotonic() < end:
            item = self.queue.get(timeout=max(.01, end - time.monotonic()))
            self.log.write(json.dumps({'direction': 'receive', 'message': item}) + '\n'); self.log.flush()
            need(not item.get('eof') and not item.get('reader_error'), 'Codex closed or malformed output')
            if item.get('id') == ident:
                need('error' not in item, 'Codex RPC error: ' + str(item.get('error')))
                return item['result']
        raise TimeoutError(method)

    def inventory(self):
        return self.rpc('mcpServerStatus/list', {'threadId': self.thread, 'serverName': 'symphony', 'limit': 100})

    def tool(self, name, args=None):
        return self.rpc('mcpServer/tool/call', {'threadId': self.thread, 'server': 'symphony', 'tool': name, 'arguments': args or {}})

    def discard_apply_response(self, name, plan):
        self.sequence += 1
        self.send({'id': self.sequence, 'method': 'mcpServer/tool/call', 'params': {'threadId': self.thread, 'server': 'symphony', 'tool': name, 'arguments': {'plan_id': plan}}})
        # Reader may buffer the reply, but it is never consumed by the caller.

    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
            try: self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.p.terminate()
                try: self.p.wait(timeout=5)
                except subprocess.TimeoutExpired: self.p.kill(); self.p.wait(timeout=5)
        self.reader.join(timeout=2)
        self.p.stdout.close()
        self.log.close(); self.err.close()


def content(result):
    need(result.get('isError') is not True, 'Native call failed: ' + str(result))
    return result['structuredContent']


def private_json(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(value, f, indent=2); f.write('\n')


def run_mode(args, identity, root, mode, version):
    work = root / mode; work.mkdir(mode=0o700)
    owner = work / 'configuration.json'; inp = work / 'create.json'
    sentinel = work / 'untouched'; sentinel.write_text('preserve')
    profile = work / 'connection.json'
    subprocess.run([sys.executable, str(Path(__file__).with_name('configure_connection.py')), '--qxctl', str(args.qxctl), '--working-directory', str(work), '--output', str(profile)], check=True, stdout=subprocess.DEVNULL, timeout=40)
    config = strict_json(regular(profile)); config['inherit_environment'] = []
    # A private native home prevents accidental access to the user's enrollment.
    native_home = work / 'native-home'; native_home.mkdir(mode=0o700)
    config['environment'] = {'HOME': str(native_home), 'TMPDIR': str(work)}
    profile.write_text(json.dumps(config)); profile.chmod(0o600)
    expected = strict_json(regular(args.catalog))
    expected_names = {e['tool']['name'] for e in expected['entries']} | {'symphony_connection'}
    cases, assertions = [], []
    listener = c = None
    socket_temp = tempfile.TemporaryDirectory(prefix='w13-', dir='/private/tmp' if Path('/private/tmp').is_dir() else '/tmp')
    sock = Path(socket_temp.name).resolve() / 'mcp.sock'
    Path(socket_temp.name).chmod(0o700)
    listener_log = (work / 'listener.stderr').open('x')
    def connect(label):
        nonlocal listener
        if mode == 'same_user_ipc':
            if listener is None:
                listener = subprocess.Popen([str(args.bridge), '--config', str(profile), '--tool-catalog', str(args.catalog), '--listen', str(sock)], stdout=subprocess.DEVNULL, stderr=listener_log)
                end = time.monotonic() + 15
                ready = False
                while time.monotonic() < end and listener.poll() is None:
                    if sock.exists() and sock.stat().st_mode & 0o777 == 0o600:
                        try:
                            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                                probe.settimeout(.1); probe.connect(str(sock))
                            ready = True; break
                        except OSError: pass
                    time.sleep(.02)
                need(ready, 'Private IPC listener unavailable')
            fragment = render('codex', str(args.bridge), '--connect-socket', str(sock))
        else:
            fragment = render('codex', str(args.bridge), '--config', str(profile), str(args.catalog))
        session = Codex(args.codex, work / ('codex-' + label), fragment, work / label)
        try:
            server = next(s for s in session.inventory()['data'] if s['name'] == 'symphony')
            need(server['runtimeStatus'] == 'connected' and set(server['tools']) == expected_names, 'Incomplete actual client tool census')
        except Exception: session.close(); raise
        return session
    def passed(case, condition=True):
        need(condition, 'Failed case: ' + case)
        assertions.append({'id': case, 'status': 'passed'})
        cases.append({'id': case, 'status': 'passed', 'evidence': [mode + '-assertions']})
        print('PASS', mode, case, flush=True)
    configure, inspect, remove = 'symphony_sov_target_configure_', 'symphony_sov_target_inspect', 'symphony_sov_target_remove_'
    try:
        c = connect('readonly'); passed('catalog_census')
        conn = content(c.tool('symphony_connection'))
        need(conn['qxctl_sha256'] == identity['bindings']['qxctl_sha256'] and conn['service_health'] == 'not_probed', 'Wrong owner or health claim')
        template = content(c.tool('symphony_sov_remote_template', {'operation': 'target_configure'}))['parsed_stdout']
        passed('native_read', template['protocol'] == 'symphony.sov.remote-template.v1')
        request = template['template']; request['path'] = str(owner)
        private_json(inp, request)
        passed('default_deny', c.tool(configure + 'preview', {'input': str(inp)}).get('isError') is True and not owner.exists())
        c.close(); c = None
        config['enabled_nonread_commands'] = ['qxcmd:symphony:sov.target.configure', 'qxcmd:symphony:sov.target.remove']
        profile.write_text(json.dumps(config)); profile.chmod(0o600)
        c = connect('enabled')
        plan = content(c.tool(configure + 'preview', {'input': str(inp)}))['plan_id']
        passed('prepare_no_effect', not owner.exists())
        result = content(c.tool(configure + 'apply', {'plan_id': plan}))
        observed = content(c.tool(inspect, {'configuration': str(owner)}))['parsed_stdout']
        passed('apply_inspect', result['exit_code'] == 0 and observed['configuration'] == request['configuration'] and observed['sha256'] == sha(regular(owner))[7:])
        passed('consumed_preview', c.tool(configure + 'apply', {'plan_id': plan}).get('isError') is True)
        before = regular(owner)
        plan = content(c.tool(configure + 'preview', {'input': str(inp)}))['plan_id']
        refused = c.tool(configure + 'apply', {'plan_id': plan})
        detail = refused.get('structuredContent', {})
        passed('native_failure', refused.get('isError') is True and detail.get('exit_code') not in (0, None) and detail.get('retry_automatically') is False and detail.get('recovery_command_id') == 'qxcmd:symphony:sov.target.inspect' and regular(owner) == before)
        request['expected_sha256'] = sha(before)[7:]
        request['configuration']['target']['node_id'] = 'w13-disposable-recovery'
        inp.write_text(json.dumps(request))
        plan = content(c.tool(configure + 'preview', {'input': str(inp)}))['plan_id']
        inp.write_text(json.dumps(request) + '\n')
        passed('changed_input', c.tool(configure + 'apply', {'plan_id': plan}).get('isError') is True and regular(owner) == before)
        plan = content(c.tool(configure + 'preview', {'input': str(inp)}))['plan_id']
        c.discard_apply_response(configure + 'apply', plan)
        end = time.monotonic() + 15
        while regular(owner) == before and time.monotonic() < end: time.sleep(.02)
        need(regular(owner) != before, 'Lost reply test did not reach durable owner effect')
        c.p.terminate(); c.p.wait(timeout=5); c.close(); c = None
        c = connect('restarted')
        passed('restart_preview_refused', c.tool(configure + 'apply', {'plan_id': plan}).get('isError') is True)
        recovered = content(c.tool(inspect, {'configuration': str(owner)}))['parsed_stdout']
        passed('lost_response_recovery', recovered['configuration'] == request['configuration'] and recovered['sha256'] == sha(regular(owner))[7:])
        cleanup = content(c.tool(remove + 'preview', {'configuration': str(owner), 'configuration-sha256': recovered['sha256']}))['plan_id']
        result = content(c.tool(remove + 'apply', {'plan_id': cleanup}))
        passed('cleanup', result['exit_code'] == 0 and not owner.exists() and sentinel.read_text() == 'preserve')
        target = dict(id=mode, name='Codex', version=version, os=platform.system() + ' ' + platform.release(), architecture=platform.machine(), mode=mode,
                      config_sha256=sha(regular(profile)))
        private_json(work / 'RESULTS.json', dict(schema='symphony.beta-client-evidence.v1', sources=identity['sources'], bindings=identity['bindings'], client=target,
                                               cases=cases, scope='deterministic_app_server_native_owner', transcripts=[mode + '-' + phase for phase in ('readonly', 'enabled', 'restarted')]))
    finally:
        if c: c.close()
        if listener is not None:
            listener.terminate()
            try: listener.wait(timeout=5)
            except subprocess.TimeoutExpired: listener.kill(); listener.wait(timeout=5)
        listener_log.close(); socket_temp.cleanup()
        private_json(work / 'ASSERTIONS.json', assertions)
        # Failure preserves disposable owner state for reconciliation, never retries.


def client_digest(path):
    # Bundled Codex executables may exceed the packet's per-attachment limit.
    # Hash the selected native client in bounded chunks without retaining it.
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_size <= 512 * 1024 * 1024, 'Client executable size/type')
        digest = hashlib.sha256(); total = 0
        while chunk := stream.read(1024 * 1024):
            total += len(chunk); need(total <= 512 * 1024 * 1024, 'Client grew beyond bound')
            digest.update(chunk)
        return 'sha256:' + digest.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('codex', 'qxctl', 'bridge', 'catalog', 'identities', 'out'):
        p.add_argument('--' + key, type=Path, required=True)
    args = p.parse_args()
    for key in ('codex', 'qxctl', 'bridge', 'catalog', 'identities'):
        setattr(args, key, getattr(args, key).resolve(strict=True))
    identity = strict_json(regular(args.identities)); sources(identity['sources'])
    need(set(identity['bindings']) == BINDINGS, 'Incomplete selected bindings')
    for key in ('qxctl', 'bridge', 'catalog'):
        need(sha(regular(getattr(args, key))) == identity['bindings'][key + '_sha256'], 'Selected bytes differ: ' + key)
    args.out.mkdir(mode=0o700, parents=False, exist_ok=False); args.out = args.out.resolve()
    version = subprocess.check_output([str(args.codex), '--version'], text=True, timeout=10).strip()
    private_json(args.out / 'CLIENT.json', {'version': version, 'executable_sha256': client_digest(args.codex), 'os': platform.platform(), 'mode': 'deterministic app-server; no model or GUI qualification'})
    for mode in ('stdio', 'same_user_ipc'): run_mode(args, identity, args.out, mode, version)


if __name__ == '__main__': main()
