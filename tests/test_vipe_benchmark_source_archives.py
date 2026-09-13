"""Synthetic pinned source archives only; no real setup or source extraction."""
import hashlib
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from scripts.vipe_benchmark import runtime


class SourceArchiveTests(unittest.TestCase):
    REVISION = 'a' * 40

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.counter = 0

    def member(self, name, kind='file', value=b'fixture bytes', *, mode=None, prefix=None):
        prefix = 'sam2-' + self.REVISION if prefix is None else prefix
        info = tarfile.TarInfo(prefix + '/' + name if prefix else name)
        info.mode = (0o777 if kind == 'symlink' else 0o755 if kind == 'directory' else 0o644) if mode is None else mode
        info.type = {'file': tarfile.REGTYPE, 'directory': tarfile.DIRTYPE,
                     'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE,
                     'fifo': tarfile.FIFOTYPE, 'character': tarfile.CHRTYPE, 'block': tarfile.BLKTYPE}[kind]
        if kind in ('symlink', 'hardlink'):
            info.linkname = value
        if kind == 'file':
            info.size = len(value)
            return info, value
        return info, None

    def archive(self, entries):
        self.counter += 1
        archive = self.root / f'fixture-{self.counter}.tar'
        output = self.root / f'extracted-{self.counter}'
        with tarfile.open(archive, 'w') as stream:
            for member, value in entries:
                stream.addfile(member, io.BytesIO(value) if value is not None else None)
        return archive, output

    def reject_before_payload(self, entries):
        archive, output = self.archive(entries)
        with mock.patch.object(tarfile.TarFile, 'extractfile', side_effect=AssertionError('payload was read before rejection')):
            with self.assertRaises(ValueError):
                runtime.extract_source(archive, output, self.REVISION)
        self.assertEqual(list(output.iterdir()), [])

    def test_pinned_sam2_layout_allows_forward_file_alias_and_records_exact_text(self):
        text = 'configs/sam2/sam2_hiera_l.yaml'
        archive, output = self.archive([
            self.member('sam2/sam2_hiera_l.yaml', 'symlink', text),
            self.member('sam2/configs/sam2/sam2_hiera_l.yaml', value=b'model: fixture\n'),
        ])
        before = hashlib.sha256(archive.read_bytes()).hexdigest()
        record = runtime.extract_source(archive, output, self.REVISION)
        alias = output / 'sam2/sam2_hiera_l.yaml'
        target = output / 'sam2/configs/sam2/sam2_hiera_l.yaml'
        self.assertTrue(alias.is_symlink())
        self.assertEqual(os.readlink(alias), text)
        self.assertEqual(alias.read_bytes(), b'model: fixture\n')
        rows = {item['path']: item for item in record['files']}
        self.assertEqual(rows[str(alias)]['sha256'], rows[str(target)]['sha256'])
        self.assertEqual(rows[str(alias)]['symlink_target'], text)
        self.assertEqual(record['archive_root'], 'sam2-' + self.REVISION)
        self.assertEqual(record['archive_symlinks'], [dict(
            member='sam2-' + self.REVISION + '/sam2/sam2_hiera_l.yaml', target=text,
            target_member='sam2-' + self.REVISION + '/sam2/configs/sam2/sam2_hiera_l.yaml')])
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), before)

    def test_safe_parent_relative_target_preserves_original_link_text_and_mode(self):
        text = '.././script.sh'
        archive, output = self.archive([
            self.member('package/aliases/tool', 'symlink', text),
            self.member('package/script.sh', value=b'#!/bin/sh\n', mode=0o755),
        ])
        record = runtime.extract_source(archive, output, self.REVISION)
        row = next(item for item in record['files'] if item['path'].endswith('/aliases/tool'))
        self.assertEqual(row['symlink_target'], text)
        self.assertEqual(row['mode'], 0o755)
        self.assertEqual((output / 'package/aliases/tool').read_bytes(), b'#!/bin/sh\n')

    def test_links_are_created_only_after_all_regular_members_exist(self):
        archive, output = self.archive([
            self.member('alias', 'symlink', 'target'),
            self.member('target'), self.member('last-file'),
        ])
        original = Path.symlink_to
        created = []
        def observe(path, target, **kwargs):
            self.assertTrue((output / 'target').is_file())
            self.assertTrue((output / 'last-file').is_file())
            created.append(path)
            return original(path, target, **kwargs)
        with mock.patch.object(Path, 'symlink_to', new=observe):
            runtime.extract_source(archive, output, self.REVISION)
        self.assertEqual(created, [output / 'alias'])

    def test_link_provenance_detects_retargeting_between_identical_files(self):
        archive, output = self.archive([
            self.member('first', value=b'identical'), self.member('second', value=b'identical'),
            self.member('alias', 'symlink', 'first'),
        ])
        original = runtime.extract_source(archive, output, self.REVISION)
        (output / 'alias').unlink()
        (output / 'alias').symlink_to('second')
        changed = runtime.tree_record(output, self.REVISION)
        old = next(item for item in original['files'] if item['path'].endswith('/alias'))
        new = next(item for item in changed['files'] if item['path'].endswith('/alias'))
        self.assertEqual(old['sha256'], new['sha256'])
        self.assertNotEqual(old['symlink_target'], new['symlink_target'])

    def test_absolute_external_and_escaping_alias_targets_are_rejected(self):
        for target in ('/etc/passwd', '../../outside', '../../../sam2-' + self.REVISION + '/file',
                       'C:/outside', '..\\outside'):
            with self.subTest(target=target):
                self.reject_before_payload([self.member('regular'), self.member('nested/alias', 'symlink', target)])

    def test_dangling_and_empty_alias_targets_are_rejected(self):
        for target in ('missing-file', '', '.'):
            with self.subTest(target=target):
                self.reject_before_payload([self.member('regular'), self.member('alias', 'symlink', target)])

    def test_directory_targets_are_rejected_including_implicit_directories(self):
        for explicit in (False, True):
            with self.subTest(explicit=explicit):
                entries = [self.member('configs/file'), self.member('alias', 'symlink', 'configs')]
                if explicit:
                    entries.insert(0, self.member('configs', 'directory'))
                self.reject_before_payload(entries)

    def test_link_chains_cycles_and_self_links_are_rejected(self):
        cases = (
            [self.member('regular'), self.member('first', 'symlink', 'second'), self.member('second', 'symlink', 'regular')],
            [self.member('regular'), self.member('first', 'symlink', 'second'), self.member('second', 'symlink', 'first')],
            [self.member('regular'), self.member('alias', 'symlink', 'alias')],
        )
        for index, entries in enumerate(cases):
            with self.subTest(index=index):
                self.reject_before_payload(entries)

    def test_hardlinks_are_rejected_even_to_regular_members(self):
        self.reject_before_payload([
            self.member('regular'), self.member('alias', 'hardlink', 'sam2-' + self.REVISION + '/regular'),
        ])

    def test_duplicate_file_directory_and_alias_paths_are_rejected(self):
        for first, second in (('file', 'file'), ('directory', 'directory'), ('file', 'directory'),
                              ('symlink', 'file'), ('file', 'symlink')):
            with self.subTest(first=first, second=second):
                def entry(kind):
                    return self.member('collision', kind, 'regular' if kind == 'symlink' else b'fixture')
                self.reject_before_payload([self.member('regular'), entry(first), entry(second)])

    def test_file_and_alias_ancestor_collisions_are_rejected_in_either_order(self):
        for kind in ('file', 'symlink'):
            for reverse in (False, True):
                with self.subTest(kind=kind, reverse=reverse):
                    entries = [self.member('prefix', kind, 'regular' if kind == 'symlink' else b'fixture'),
                               self.member('prefix/nested-file')]
                    if reverse:
                        entries.reverse()
                    self.reject_before_payload([self.member('regular'), *entries])

    def test_traversal_and_ambiguous_member_paths_are_rejected(self):
        for name in ('../escape', 'safe/../escape', 'safe/./file', 'safe//file', 'safe\\file'):
            with self.subTest(name=name):
                self.reject_before_payload([self.member('regular'), self.member(name)])
        self.reject_before_payload([self.member('regular'), self.member('/absolute/file', prefix='')])

    def test_set_id_and_special_files_are_rejected_before_payload(self):
        for kind, mode in (('file', 0o4755), ('directory', 0o2755), ('symlink', 0o4777),
                           ('fifo', 0o644), ('character', 0o644), ('block', 0o644)):
            with self.subTest(kind=kind, mode=mode):
                self.reject_before_payload([self.member('regular'),
                    self.member('unsafe', kind, 'regular' if kind == 'symlink' else b'', mode=mode)])

    def test_prompts_alias_names_are_rejected_before_any_payload(self):
        for name in ('prompts', 'prompts/alias', 'nested/prompts/alias'):
            with self.subTest(name=name):
                self.reject_before_payload([self.member('regular'), self.member(name, 'symlink', 'regular')])

    def test_prompts_targets_are_rejected_even_when_normalization_would_remove_name(self):
        for target in ('prompts/file', '../prompts/file', 'prompts/../regular', './prompts/file'):
            with self.subTest(target=target):
                self.reject_before_payload([self.member('regular'), self.member('nested/alias', 'symlink', target)])

    def test_plain_prompts_payload_is_skipped_without_extractfile_access(self):
        archive, output = self.archive([
            self.member('prompts/skipped', value=b'never read as a member'),
            self.member('safe.py', value=b'allowed fixture'),
        ])
        opened = []
        original = tarfile.TarFile.extractfile
        def guarded(source, member):
            self.assertNotIn('prompts', member.name.split('/'))
            opened.append(member.name)
            return original(source, member)
        with mock.patch.object(tarfile.TarFile, 'extractfile', new=guarded):
            record = runtime.extract_source(archive, output, self.REVISION)
        self.assertEqual(opened, ['sam2-' + self.REVISION + '/safe.py'])
        self.assertFalse((output / 'prompts').exists())
        self.assertEqual(record['archive_symlinks'], [])

    def test_other_pins_and_multiple_archive_roots_are_rejected(self):
        self.reject_before_payload([self.member('regular'), self.member('other', prefix='sam2-' + 'b' * 40)])
        self.reject_before_payload([self.member('regular'), self.member('other', prefix='other-' + self.REVISION)])

    def test_archive_root_must_be_directory(self):
        self.reject_before_payload([self.member('sam2-' + self.REVISION, prefix='')])

    def test_existing_output_is_never_overwritten_or_reused(self):
        archive, output = self.archive([self.member('file')])
        output.mkdir()
        marker = output / 'existing'
        marker.write_bytes(b'preserve')
        with self.assertRaises(FileExistsError):
            runtime.extract_source(archive, output, self.REVISION)
        self.assertEqual(marker.read_bytes(), b'preserve')
        self.assertFalse((output / 'file').exists())

    def test_prompts_archive_path_is_rejected_without_opening_archive(self):
        with mock.patch.object(tarfile, 'open', side_effect=AssertionError('forbidden archive opened')):
            with self.assertRaisesRegex(ValueError, 'prompts'):
                runtime.extract_source(self.root / 'prompts/archive.tar', self.root / 'output', self.REVISION)


if __name__ == '__main__':
    unittest.main()
