import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('producer002',Path(__file__).parent/'producer.py')
producer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class DirectUrlTests(unittest.TestCase):
    source={'record':{'path':'/tmp/approved pinned archive.tar.gz','sha256':'a'*64,'bytes':42}}

    def direct(self,archive):
        return {'url':Path(self.source['record']['path']).as_uri(),'archive_info':archive}

    def test_exact_verified_local_uri_without_optional_hash_passes(self):
        producer.validate_offline_direct_url(self.direct({}),self.source)
        producer.validate_offline_direct_url(self.direct({'hashes':{}}),self.source)

    def test_exact_supplied_sha256_and_legacy_hash_pass(self):
        producer.validate_offline_direct_url(self.direct({'hashes':{'sha256':'a'*64},'hash':'sha256='+'a'*64}),self.source)

    def test_wrong_supplied_hash_rejected_even_with_exact_uri(self):
        for archive in ({'hashes':{'sha256':'b'*64}},{'hash':'sha256='+'b'*64},
                        {'hashes':{'sha256':'a'*64},'hash':'sha256='+'b'*64},
                        {'hashes':None},{'hashes':{'sha512':'unsupported'}}):
            with self.subTest(archive=archive),self.assertRaises(ValueError):
                producer.validate_offline_direct_url(self.direct(archive),self.source)

    def test_wrong_nonlocal_or_fragment_url_rejected(self):
        for url in ('file:///tmp/other.tar.gz','https://example.invalid/archive.tar.gz',
                    Path(self.source['record']['path']).as_uri()+'#sha256='+'a'*64):
            direct=self.direct({});direct['url']=url
            with self.subTest(url=url),self.assertRaises(ValueError):
                producer.validate_offline_direct_url(direct,self.source)

    def test_vcs_directory_editable_and_subdirectory_rejected(self):
        for extra in ({'vcs_info':{'vcs':'git'}},{'dir_info':{'editable':True}},
                      {'dir_info':{'editable':False}},{'subdirectory':'src'}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                producer.validate_offline_direct_url(dict(self.direct({}),**extra),self.source)

    def test_missing_or_malformed_archive_metadata_rejected(self):
        for direct in (None, {}, {'url':self.direct({})['url']}, self.direct(None), self.direct({'unexpected':'metadata'})):
            with self.subTest(direct=direct),self.assertRaises(ValueError):
                producer.validate_offline_direct_url(direct,self.source)


if __name__=='__main__':
    unittest.main()
