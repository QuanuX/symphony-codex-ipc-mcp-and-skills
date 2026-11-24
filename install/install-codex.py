#!/usr/bin/env python3
"""Install the released Symphony plugin in this user's local Codex marketplace."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile


VERSION = '0.2.0-beta.2.1'
MARKET = 'quanux-symphony-beta'
PLUGIN = 'symphony'
RELEASE_URL = f'https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/download/v{VERSION}'
ZIP_HASHES = {
    'macos15-arm64': 'b36023b66d1dc2bebfa30d653497ddd310e999b0d98311fef28dbf285c8efc08',
    'ubuntu24.04-amd64': '3f41de5afe4905637071ac4e9303e3e1be7b193df2abcda836d66c2d4231ab6e',
    'ubuntu24.04-arm64': 'cd446fd2124df6fc3e67bc70df0c2c1202c85fc511a30536859dbf80334dfc44',
    'ubuntu26.04-amd64': 'df4293c8579d951c2791fac69e69878e726d856956844d9ec35165d6219c4b4f',
}
MARKETPLACE = {'name': MARKET, 'interface': {'displayName': 'QuanuX Symphony'}, 'plugins': [
    {'name': PLUGIN, 'source': {'source': 'local', 'path': './plugin'},
     'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Developer Tools'}]}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def host_profile():
    arch = {'aarch64': 'arm64', 'x86_64': 'amd64'}.get(platform.machine().lower(), platform.machine().lower())
    if sys.platform == 'darwin':
        name = 'macos' + platform.mac_ver()[0].split('.')[0] + '-' + arch
    elif sys.platform == 'linux':
        info = platform.freedesktop_os_release()
        name = info['ID'] + info['VERSION_ID'] + '-' + arch
    else:
        name = platform.system() + '-' + arch
    if name not in ZIP_HASHES:
        raise ValueError(f'No matching Symphony beta.2.1 package for {name}. See https://quanux.org/downloads#codex.')
    return name


def select_codex(explicit):
    candidates = [explicit] if explicit else [shutil.which('codex'),
        '/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex',
        '/Applications/Codex.app/Contents/Resources/codex']
    for candidate in filter(None, candidates):
        if os.access(candidate, os.X_OK) and subprocess.run(
                [candidate, 'plugin', 'add', '--help'], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL).returncode == 0:
            return candidate
    raise ValueError('Install a Codex version with local plugin support or select its executable with --codex-bin.')


def codex_json(cli, *arguments):
    return json.loads(subprocess.check_output([cli, 'plugin', *arguments, '--json'], text=True))


def prepare_marketplace(archive, profile, root):
    if digest(archive) != ZIP_HASHES[profile]:
        raise ValueError(f'Plugin ZIP SHA-256 differs from the published {profile} package.')
    with zipfile.ZipFile(archive) as zipped:
        receipt = json.loads(zipped.read('package-profile.json'))
        if (receipt['profile'] != profile or receipt['package_version'] != VERSION
                or receipt['bridge_runtime_version'] != VERSION):
            raise ValueError('Plugin receipt does not match the selected release and profile.')
        # The pinned archive has one plugin root. Retain its executable permissions.
        plugin = root / 'plugin'
        for info in zipped.infolist():
            member = Path(info.filename)
            mode = info.external_attr >> 16
            if member.is_absolute() or '..' in member.parts or not stat.S_ISREG(mode):
                raise ValueError(f'Unexpected ZIP member: {info.filename}')
            target = plugin / member
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as dst, zipped.open(info) as src:
                shutil.copyfileobj(src, dst)
            target.chmod(0o700 if mode & 0o111 else 0o600)
    meta = root / '.agents/plugins/marketplace.json'
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps(MARKETPLACE) + '\n')
    return receipt


def verify_existing_market(source, installed):
    expected = {p.relative_to(source) for p in source.rglob('*')}
    if installed.is_symlink() or {p.relative_to(installed) for p in installed.rglob('*')} != expected:
        raise ValueError(f'Existing local marketplace differs from the signed-off ZIP: {installed}')
    for rel in expected:
        a, b = source / rel, installed / rel
        if b.is_symlink() or (a.is_dir() and not b.is_dir()) or (a.is_file() and
                (not b.is_file() or digest(a) != digest(b) or os.access(a, os.X_OK) != os.access(b, os.X_OK))):
            raise ValueError(f'Existing local marketplace member differs: {b}')


def private_profile(data, expected):
    data.mkdir(parents=True, mode=0o700, exist_ok=True)
    if data.is_symlink() or data.stat().st_uid != os.getuid() or data.stat().st_mode & 0o077:
        raise ValueError(f'Codex plugin data must be private and owned by your account: {data}')
    dest = data / 'connection.json'
    # A link publishes a completely written file atomically and refuses overwrite.
    with tempfile.NamedTemporaryFile(dir=data) as temp:
        temp.write(expected.read_bytes())
        temp.flush()
        try:
            os.link(temp.name, dest)
        except FileExistsError:
            if (dest.is_symlink() or not dest.is_file() or dest.stat().st_uid != os.getuid()
                    or dest.stat().st_mode & 0o077 or json.loads(dest.read_bytes()) != json.loads(expected.read_bytes())):
                raise ValueError(f'An existing connection differs. Review your selection in {dest}.') from None
    return dest


def install(args):
    profile = host_profile()
    cli = select_codex(args.codex_bin)
    qxctl = args.qxctl.expanduser().resolve(strict=True)
    cwd = args.working_directory.expanduser().resolve(strict=True)
    storage = Path.home() / '.local/share/quanux/symphony/codex'
    storage.mkdir(parents=True, mode=0o700, exist_ok=True)
    root = storage / (VERSION + '-' + profile)
    with (storage / '.install.lock').open('a') as lock, tempfile.TemporaryDirectory(dir=storage) as tmp:
        fcntl.flock(lock, fcntl.LOCK_EX)
        work = Path(tmp)
        archive = args.archive
        if archive is None:
            suffix = '-candidate' if profile == 'ubuntu24.04-arm64' else ''
            filename = f'symphony-{VERSION}-{profile}{suffix}.zip'
            archive = work / filename
            subprocess.run(['curl', '--disable', '--fail', '--silent', '--show-error', '--location',
                            '--proto', '=https', '--proto-redir', '=https', '--retry', '2',
                            '--max-filesize', '2000000', '--output', str(archive), f'{RELEASE_URL}/{filename}'], check=True)
        staged = work / 'marketplace'
        receipt = prepare_marketplace(archive, profile, staged)
        bindings = receipt['released_inputs']['bindings']
        if 'sha256:' + digest(qxctl) != bindings['qxctl_sha256']:
            raise ValueError('Selected qxctl does not match this signed Symphony beta.2.1 platform release.')
        expected = work / 'connection.json'
        subprocess.run([sys.executable, '-I', str(staged / 'plugin/scripts/configure_connection.py'),
                        '--qxctl', str(qxctl), '--working-directory', str(cwd), '--output', str(expected)],
                       stdout=subprocess.DEVNULL, check=True)
        if json.loads(expected.read_bytes())['registry_digest'] != bindings['observed_registry_digest']:
            raise ValueError('The selected qxctl registry differs from the released catalogue.')
        if root.exists() or root.is_symlink():
            verify_existing_market(staged, root)
        else:
            staged.rename(root)
        for market in codex_json(cli, 'marketplace', 'list')['marketplaces']:
            if market.get('name') == MARKET and Path(market['root']).resolve() != root.resolve():
                raise ValueError(f'Codex already has another {MARKET} marketplace at {market["root"]}.')
        added = codex_json(cli, 'marketplace', 'add', str(root))
        if added['marketplaceName'] != MARKET or Path(added['installedRoot']).resolve() != root.resolve():
            raise ValueError('Codex returned a different local marketplace.')
        installed = codex_json(cli, 'add', f'{PLUGIN}@{MARKET}')
        package = Path(installed['installedPath'])
        if (installed['pluginId'] != f'{PLUGIN}@{MARKET}' or installed['version'] != VERSION or
                package.parts[-5:] != ('plugins', 'cache', MARKET, PLUGIN, VERSION)):
            raise ValueError('Codex returned an unrecognized installation path or plugin identity.')
        binary = package / 'bin/symphony-mcp'
        if ('sha256:' + digest(binary) != receipt['bridge_build']['sha256'] or
                'sha256:' + digest(package / 'catalog/tools.json') != bindings['catalog_sha256'] or
                subprocess.check_output([str(binary), '--version'], text=True).strip() != 'symphony-mcp ' + VERSION):
            raise ValueError('Codex-installed runtime or catalogue differs from the verified ZIP.')
        # Codex PluginStore::agent_plugin_data_root keys data by marketplace NUL name.
        namespace = hashlib.sha256((MARKET + '\0' + PLUGIN).encode()).hexdigest()
        data = package.parents[3] / 'data/agent-plugins' / namespace
        selected = private_profile(data, expected)
    print(f'Symphony Codex plugin {VERSION} is installed for {profile}.\n'
          f'Read-only connection: {selected}\nOpen a new Codex chat and ask: '
          '“Use symphony_connection to report the bridge version and read the SOV target configuration template.”')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qxctl', type=Path, default=Path.home() / f'symphony-{VERSION}/bin/qxctl',
                        help='Retained qxctl from this platform’s signed beta.2.1 installation')
    parser.add_argument('--working-directory', type=Path, default=Path.home(), help='Symphony working directory')
    parser.add_argument('--codex-bin', help='Path to the Codex CLI with plugin support')
    parser.add_argument('--archive', type=Path, help='Use an already-downloaded profile ZIP and verify its pinned digest')
    args = parser.parse_args()
    if sys.version_info < (3, 11) or os.geteuid() == 0:
        parser.error('Run as your normal user with Python 3.11 or newer.')
    os.umask(0o077)
    try:
        install(args)
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        parser.exit(1, f'Could not finish Symphony Codex setup: {exc}\n')


if __name__ == '__main__':
    main()
