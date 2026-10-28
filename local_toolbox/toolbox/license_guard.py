"""Local trial/export policy, compatible with two offline key formats."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import re
import uuid

TRIAL_ROWS = 10


def clean_machine(value):
    value = str(value).strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{8}', value):
        raise ValueError('机器码必须为 8 位英文字母或数字')
    return value


def machine_code():
    identity = ''
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0,
                               winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                identity = str(winreg.QueryValueEx(key, 'MachineGuid')[0])
        except OSError:
            pass
    if not identity:
        identity = platform.node() + ':' + str(uuid.getnode())
    return hashlib.sha256(('DRJ-MACHINE-14|' + identity).encode()).hexdigest()[:8].upper()


def _format(raw):
    return 'VIP-' + '-'.join(raw[i:i+4] for i in (0, 4, 8))


def _web_digest(clean):
    parts = []
    for salt in ('DRJ', 'LOCAL', 'PRO'):
        h = 2166136261
        for char in salt + '|' + clean + '|2026':
            h = ((h ^ ord(char)) * 16777619) & 0xffffffff
        parts.append(f'{h & 0xffff:04X}')
    return ''.join(parts)


def validate_key(machine, code):
    try:
        clean = clean_machine(machine)
    except ValueError:
        return False
    code = str(code).strip().upper()
    if not re.fullmatch(r'VIP-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}', code):
        return False
    sha = hashlib.sha256(('DRJ-2026-PRO-' + clean).encode()).hexdigest()[:12].upper()
    return hmac.compare_digest(code, _format(sha)) or hmac.compare_digest(code, _format(_web_digest(clean)))


class LicenseGuard:
    def __init__(self, machine=None, path=None):
        self.machine = clean_machine(machine) if machine else machine_code()
        home = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share')))
        self.path = Path(path) if path is not None else home / 'CNBusinessToolbox/license.json'

    @property
    def activated(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return data.get('machine') == self.machine and validate_key(self.machine, data.get('key', ''))
        except (OSError, ValueError, AttributeError):
            return False

    def activate(self, code):
        if not validate_key(self.machine, code):
            raise ValueError('激活码不匹配，请核对本机机器码和激活码')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(machine=self.machine, key=str(code).strip().upper())), encoding='utf-8')
        temporary.replace(self.path)

    def export_rows(self, rows):
        return list(rows) if self.activated else list(rows)[:TRIAL_ROWS]
