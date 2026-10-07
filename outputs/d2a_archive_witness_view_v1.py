"""Read-only witness availability backends; never hashes/opens witness payloads."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import stat
import zipfile

HEX = re.compile(r'^[0-9a-f]{64}$')
CASE = re.compile(r'^d2a_cert_h[0-9]+_[A-Za-z0-9_]+$')

class WitnessViewError(ValueError):
    pass

def archive_relative(value):
    value = str(value)
    if '\\' in value or ':' in value or value.startswith('/'):
        raise WitnessViewError('UNSAFE_ARCHIVE_NAMESPACE')
    parts = value.split('/')
    if not parts or any(p in ('','.', '..') for p in parts):
        raise WitnessViewError('UNSAFE_ARCHIVE_NAMESPACE')
    for part in parts:
        base=part.split('.')[0].upper()
        if (part.endswith(('.', ' ')) or any(ord(c)<32 or c in '<>:"|?*' for c in part)
                or base in {'CON','PRN','AUX','NUL'}
                or re.fullmatch(r'(COM|LPT)[1-9]',base)):
            raise WitnessViewError('UNSAFE_WINDOWS_ARCHIVE_NAMESPACE')
    return PurePosixPath(value).as_posix()

def witness_relative(value):
    value = archive_relative(str(value).replace('\\','/'))
    parts = PurePosixPath(value).parts
    if len(parts)!=4 or parts[0]!='work' or not CASE.fullmatch(parts[1]) or parts[2]!='audit':
        raise WitnessViewError('MALFORMED_WITNESS_NAMESPACE')
    expected = ('D2A_'+parts[1][len('d2a_cert_'):]).upper()+'_ADJOINT_JET.json.gz'
    if parts[3]!=expected:
        raise WitnessViewError('CASE_WITNESS_NAME_MISMATCH')
    return value

class FilesystemWitnessView:
    """Exactly the old contained-Path.is_file check; no content or size claim."""
    def __init__(self, root):
        self.root=Path(root).resolve()
        self.checked=0

    def available(self, value, expected_sha256=None, expected_bytes=None):
        candidate=(self.root/str(value).replace('\\','/')).resolve()
        if not candidate.is_relative_to(self.root):
            raise WitnessViewError('OUTSIDE_METADATA_ROOT')
        self.checked+=1
        return candidate.is_file()

    def scope_info(self):
        return {'backend':'filesystem','availability_checks':self.checked,
                'scope':'Contained filesystem presence only; original v1 behavior.',
                'witness_payload_bytes_read':0,'witness_payload_hash_verified':False}

class ZipWitnessView:
    """Actual central directory + independently supplied manifest SHA mapping.

    The SHA in each file entry is compared with the caller's bound receipt SHA.
    This is a metadata binding, NOT verification of the large payload bytes.
    """
    def __init__(self, archive_path, expected_manifest_sha256):
        if not HEX.fullmatch(str(expected_manifest_sha256)):
            raise WitnessViewError('EXPECTED_MANIFEST_SHA_REQUIRED')
        self.archive_path=Path(archive_path).resolve()
        self.identity=self._identity()
        self.checked=0
        self.manifest_sha256=expected_manifest_sha256
        self.members={}
        with zipfile.ZipFile(self.archive_path) as archive:
            folded=set()
            for item in archive.infolist():
                name=archive_relative(item.filename.rstrip('/') if item.is_dir() else item.filename)
                if name.casefold() in folded:
                    raise WitnessViewError('DUPLICATE_CASEFOLD_ARCHIVE_NAMESPACE')
                folded.add(name.casefold())
                if stat.S_ISLNK(item.external_attr>>16) or item.flag_bits&1:
                    raise WitnessViewError('SYMLINK_OR_ENCRYPTED_MEMBER_FORBIDDEN')
                if not item.is_dir():self.members[name]=item.file_size
            info=archive.getinfo('MANIFEST.json')
            if info.file_size>16*1024**2:
                raise WitnessViewError('MANIFEST_METADATA_SIZE_CAP')
            raw=archive.read('MANIFEST.json')
            side=archive.getinfo('MANIFEST.sha256')
            if side.file_size>1024:raise WitnessViewError('MANIFEST_SIDECAR_SIZE_CAP')
            declared=archive.read('MANIFEST.sha256').decode('ascii').split()[0]
        if hashlib.sha256(raw).hexdigest()!=expected_manifest_sha256 or declared!=expected_manifest_sha256:
            raise WitnessViewError('MANIFEST_SHA_BINDING_MISMATCH')
        doc=json.loads(raw)
        self.files={}
        folded=set()
        for item in doc['files']:
            name=archive_relative(item['path'])
            if name.casefold() in folded:raise WitnessViewError('DUPLICATE_MANIFEST_NAMESPACE')
            folded.add(name.casefold())
            if not HEX.fullmatch(str(item['sha256'])) or type(item['bytes']) is not int or item['bytes']<0:
                raise WitnessViewError('INVALID_MANIFEST_FILE_BINDING')
            self.files[name]={'sha256':item['sha256'],'bytes':item['bytes']}
        if self.identity!=self._identity():raise WitnessViewError('ARCHIVE_CHANGED_DURING_INDEX')

    def _identity(self):
        s=self.archive_path.stat()
        return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)

    def available(self, value, expected_sha256, expected_bytes):
        if self.identity!=self._identity():raise WitnessViewError('ARCHIVE_INDEX_STALE')
        name=witness_relative(value)
        if not HEX.fullmatch(str(expected_sha256)) or type(expected_bytes) is not int or expected_bytes<0:
            raise WitnessViewError('EXPECTED_WITNESS_BINDING_REQUIRED')
        self.checked+=1
        if name not in self.members or name not in self.files:
            return False
        item=self.files[name]
        if item['sha256']!=expected_sha256:
            raise WitnessViewError('WITNESS_MANIFEST_SHA_MAPPING_MISMATCH')
        if item['bytes']!=expected_bytes or self.members[name]!=expected_bytes:
            raise WitnessViewError('WITNESS_MEMBER_SIZE_MISMATCH')
        return True

    def scope_info(self):
        return {'backend':'actual_zip_manifest_index','archive':str(self.archive_path),
                'manifest_sha256':self.manifest_sha256,'availability_checks':self.checked,
                'scope':'Actual ZIP member presence, uncompressed size and manifest-to-receipt SHA mapping only.',
                'witness_payload_bytes_read':0,'witness_payload_hash_verified':False,
                'scientific_arithmetic_verified':False}
