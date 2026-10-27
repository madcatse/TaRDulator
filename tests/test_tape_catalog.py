"""Catalog recognition, safe routing and generated help must stay in sync."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import engine
import load_strategies
import tape_catalog
import tape_profiles
from generate_profile_help import render, updated


class TapeCatalogTests(unittest.TestCase):
    def test_duplicate_ids_hashes_and_invalid_checksums_are_rejected(self):
        first=tape_catalog.PROFILES[0]
        for entries in ((first,first), (first,replace(first,id='another')),
                        (replace(first,sha256='bad'),), (replace(first,format='TRD'),)):
            with self.assertRaises(ValueError):tape_catalog.validate(entries)

    def test_recognition_uses_full_hash_and_format_not_name(self):
        for entry in tape_catalog.PROFILES:
            with self.subTest(profile=entry.id):
                path=Path('any-renamed-game.'+entry.format.lower())
                self.assertEqual(tape_profiles.identify(path,entry.sha256),entry.id)
                changed=('0' if entry.sha256[0]!='0' else '1')+entry.sha256[1:]
                self.assertIsNone(tape_profiles.identify(path,changed))
                other='.tzx' if entry.format=='TAP' else '.tap'
                self.assertIsNone(tape_profiles.identify(path.with_suffix(other),entry.sha256))

    def test_every_catalog_record_has_real_handling_or_explicit_rejection(self):
        implemented=set(load_strategies.SNAPSHOTS)|set(load_strategies.CHAINS)|{'wec-le-mans-128'}
        for entry in tape_catalog.PROFILES:
            if entry.status=='unsupported':
                with self.assertRaises(tape_profiles.UnsupportedTape):tape_profiles.require_supported(entry.id)
            else:
                tape_profiles.require_supported(entry.id)
                self.assertIn(entry.id,implemented)
                self.assertNotEqual(load_strategies.describe(entry.id)['strategy'],'snapshot')
        self.assertTrue(implemented<=set(tape_catalog.BY_ID))

    def test_help_is_current_and_contains_every_exact_checksum(self):
        for language in ('ru','en'):
            content=(ROOT/'help'/f'index.{language}.html').read_text(encoding='utf-8-sig')
            self.assertEqual(content,updated(content,language))
            table=render(language)
            self.assertIn('href="#profiles"',content)
            for entry in tape_catalog.PROFILES:
                self.assertEqual(table.count(entry.sha256),1)
                self.assertIn('data-profile="'+entry.id+'"',table)

    def test_inspection_exposes_matching_profile(self):
        path=ROOT/'taps/escape_trilogy/Castle Escape.tap'
        if not path.exists():self.skipTest('Local Escape tape not shipped')
        result=engine.inspect_tap(path)
        self.assertEqual(result['tape_profile'],'escape-castle-no-floating-bus')
        self.assertEqual(result['profile_title'],'Castle Escape')
        self.assertEqual(result['profile_status'],'hardware-test')
        self.assertIn('floating bus',result['profile_description'])


if __name__=='__main__':unittest.main()
