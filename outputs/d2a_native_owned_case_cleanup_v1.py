"""Windows native inline cleanup of one verified, newly owned scratch case.

No machine/user execution-policy or global-environment changes. The exact
target/root/name/reparse guards run both before launch and inside PowerShell.
"""
from pathlib import Path
import os
import re
import subprocess

GUARD=r'''$ErrorActionPreference = 'Stop'
$Target = $env:D2A_OWNED_CASE_TARGET
$AllowedRoot = $env:D2A_OWNED_CASE_ROOT
$t = (Resolve-Path -LiteralPath $Target -ErrorAction Stop).ProviderPath
$a = (Resolve-Path -LiteralPath $AllowedRoot -ErrorAction Stop).ProviderPath
$i = Get-Item -LiteralPath $t -ErrorAction Stop
if ($i.Parent.FullName.TrimEnd('\') -ne $a.TrimEnd('\')) { throw 'Outside exact owned scratch root' }
if ($i.Name -notmatch '^d2a_cert_h[0-9]+_[A-Za-z0-9_]+$') { throw 'Unexpected scratch case name' }
if ($i.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point forbidden' }
Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction Stop
'''

def decode_native(raw):
    try:return raw.decode('utf-8')
    except UnicodeDecodeError:return raw.decode('cp936',errors='replace')

def cleanup_owned_case(case_path,scratch):
    if os.name!='nt':raise ValueError('THIS_REVIEWED_CLEANUP_IS_WINDOWS_NATIVE_ONLY')
    case_path=Path(case_path);scratch=Path(scratch)
    actual=case_path.resolve();allowed=(scratch/'work').resolve()
    if actual.parent!=allowed or not re.fullmatch(r'd2a_cert_h\d+_[A-Za-z0-9_]+',actual.name):
        raise ValueError('Unsafe scratch cleanup target')
    if case_path.is_symlink() or case_path.stat().st_file_attributes & 0x400:
        raise ValueError('No reparse point cleanup')
    native=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    if not native.is_file():raise ValueError('NATIVE_WINDOWS_POWERSHELL_UNAVAILABLE')
    env=dict(os.environ)
    env['PSModulePath']=str(native.parent/'Modules')
    env.pop('PSModuleAnalysisCachePath',None)
    env['D2A_OWNED_CASE_TARGET']=str(actual);env['D2A_OWNED_CASE_ROOT']=str(allowed)
    result=subprocess.run([str(native),'-NoProfile','-NonInteractive','-Command',GUARD],
                          env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    report={'status':'PASS_GUARDED_OWNED_SCRATCH_CASE_CLEANUP' if result.returncode==0 else 'FAILED_PRESERVE_OWNED_CASE',
            'returncode':result.returncode,'target':str(actual),'allowed_root':str(allowed),
            'native_powershell':str(native),'process_PSModulePath':env['PSModulePath'],
            'invocation':'Inline -Command, same native LiteralPath/path/name/reparse guards.',
            'machine_or_user_execution_policy_changed':False,'global_environment_changed':False,
            'stdout':decode_native(result.stdout),'stderr':decode_native(result.stderr)}
    if result.returncode:raise RuntimeError(str(report))
    if actual.exists():raise RuntimeError('Successful native cleanup left target present')
    return report
