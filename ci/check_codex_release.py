#!/usr/bin/env python3
"""Exercise the public Symphony installer, plugin manager, and native read on this host."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile


VERSION = '0.2.0-beta.2.1'
DIST_INSTALLER = ('https://raw.githubusercontent.com/QuanuX/symphony-distribution/'
                  '254f1d5c20913dab8fd97bb36e0a8e5f32053299/install/install-symphony.py')
DIST_SHA256 = 'dfa0e60daa52f38a7720fced44c5a0c17488c2f4f139ad0a157f71bb6bbc52b4'
CODEX_VERSION = '0.172.0'
CODEX_ARTIFACTS = {
    'macos15-arm64': ('aarch64-apple-darwin', 'bd121f8abd6b28b3fc476da04a348e25a83e89eda19d39107f68f8e966053092'),
    'ubuntu24.04-arm64': ('aarch64-unknown-linux-musl', '0b99526c185a4425fe96a2214fb7b6a6a7f7c1471883b7afbebe97e15e83e79e'),
    'ubuntu24.04-amd64': ('x86_64-unknown-linux-musl', 'a2342a8f7f68f088be30620ccfe9cb84162c93a6b56177855961cda3ed6be392'),
    'ubuntu26.04-amd64': ('x86_64-unknown-linux-musl', 'a2342a8f7f68f088be30620ccfe9cb84162c93a6b56177855961cda3ed6be392'),
}


def download(url, path, sha256):
    subprocess.run(['curl', '--disable', '--fail', '--silent', '--show-error', '--location',
                    '--proto', '=https', '--proto-redir', '=https', '--retry', '2',
                    '--max-filesize', '180000000', '-o', str(path), url], check=True)
    with path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == sha256, path.name


def check_chat(cli, home, environment, profile):
    seq = 0
    proc = subprocess.Popen([cli, 'app-server', '--listen', 'stdio://'], cwd=home, env=environment,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def send(obj):
        proc.stdin.write(json.dumps(obj) + '\n')
        proc.stdin.flush()

    def rpc(method, params):
        nonlocal seq
        seq += 1
        send({'id': seq, 'method': method, 'params': params})
        for line in proc.stdout:
            msg = json.loads(line)
            if msg.get('id') == seq:
                if 'error' in msg:
                    raise RuntimeError(f'{method}: {msg["error"]}')
                return msg['result']
        raise RuntimeError('App server closed during ' + method)

    try:
        rpc('initialize', {'clientInfo': {'name': 'symphony-release-check', 'version': '1'},
                           'capabilities': {'experimentalApi': True}})
        send({'method': 'initialized', 'params': {}})
        thread = rpc('thread/start', {'ephemeral': True, 'cwd': str(home), 'sandbox': 'workspace-write',
                                     'approvalPolicy': 'on-request'})['thread']['id']
        states = rpc('mcpServerStatus/list', {'threadId': thread, 'limit': 100})['data']
        server, = [s for s in states if s.get('pluginId') == 'symphony@quanux-symphony-beta']
        assert server['runtimeStatus'] == 'connected'
        package = home / f'.codex/plugins/cache/quanux-symphony-beta/symphony/{VERSION}'
        receipt = json.loads((package / 'package-profile.json').read_bytes())
        assert receipt['profile'] == profile and receipt['package_version'] == VERSION
        catalog = json.loads((package / 'catalog/tools.json').read_bytes())
        names = {x['tool']['name'] for x in catalog['entries']} | {'symphony_connection'}
        assert len(names) == 744 and names == set(server['tools'])
        for skill in ['symphony-setup', 'symphony-admin']:
            assert (package / 'skills' / skill / 'SKILL.md').is_file()

        def tool(name, arguments):
            result = rpc('mcpServer/tool/call', {'threadId': thread, 'server': server['name'],
                                                 'tool': name, 'arguments': arguments})
            assert not result.get('isError'), name
            return result['structuredContent']

        connected = tool('symphony_connection', {})
        assert connected['qxctl_sha256'] == receipt['released_inputs']['bindings']['qxctl_sha256']
        assert connected['bridge_version'] == VERSION and connected['enabled_nonread_commands'] == []
        native = tool('symphony_sov_remote_template', {'operation': 'target_configure'})
        assert native['exit_code'] == 0 and native['parsed_stdout']['protocol'] == 'symphony.sov.remote-template.v1'
        print(json.dumps({'profile': profile, 'codex': CODEX_VERSION, 'plugin': server['pluginId'],
                          'bridge': connected['bridge_version'], 'bridge_sha256': receipt['bridge_build']['sha256'],
                          'qxctl_sha256': connected['qxctl_sha256'], 'tools': len(names),
                          'native_protocol': native['parsed_stdout']['protocol'], 'native_exit': 0}, indent=2))
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=10)


def main(profile):
    arch, sha256 = CODEX_ARTIFACTS[profile]
    with tempfile.TemporaryDirectory(prefix='symphony-hosted-') as tmp:
        root = Path(tmp)
        home = root / 'home'
        home.mkdir(mode=0o700)
        (home / '.codex').mkdir(mode=0o700)
        archive = root / 'codex.tar.gz'
        stem = f'codex-{arch}'
        download(f'https://github.com/openai/codex/releases/download/rust-v{CODEX_VERSION}/{stem}.tar.gz', archive, sha256)
        cli = root / 'codex'
        with tarfile.open(archive) as bundle:
            executable, = [m for m in bundle.getmembers() if m.isfile() and Path(m.name).name == stem]
            with bundle.extractfile(executable) as source, cli.open('xb') as target:
                shutil.copyfileobj(source, target)
        cli.chmod(0o700)
        environment = dict(os.environ, HOME=str(home), CODEX_HOME=str(home / '.codex'), PATH=str(root) + ':' + os.environ['PATH'])
        assert CODEX_VERSION in subprocess.check_output([cli, '--version'], env=environment, text=True)
        installer = root / 'install-symphony.py'
        download(DIST_INSTALLER, installer, DIST_SHA256)
        subprocess.run([sys.executable, '-I', str(installer), '--codex'], env=environment, check=True)
        signal.alarm(180)
        check_chat(cli, home, environment, profile)
        signal.alarm(0)


if __name__ == '__main__':
    main(sys.argv[1])
