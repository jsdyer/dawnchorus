import gzip,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect
RAW={'id':'1','gen':'Turdus','sp':'migratorius','en':'American Robin','cnt':'Canada','loc':'Example location, British Columbia','status':'identified','rec':'Fixture recordist','lic':'https://creativecommons.org/licenses/by-nc-sa/4.0/','file':'https://xeno-canto.org/1/download','date':'2024-05-01','uploaded':'2024-06-01','length':'0:20','q':'A','type':'song'}
SOURCE={'url':collect.API,'truncated':False}
class CollectorTests(unittest.TestCase):
 def test_recording_dates_and_licence_are_retained(self):
  row=collect.normalize(RAW,'British Columbia');self.assertEqual(row['recorded_at'],'2024-05-01');self.assertEqual(row['uploaded_at'],'2024-06-01');self.assertEqual(row['coast'],'pacific');self.assertEqual(row['duration_seconds'],20);self.assertEqual(row['recordist'],'Fixture recordist')
 def test_redactions_and_ambiguous_locations_are_excluded(self):
  for change in [{'cnt':'United States'},{'loc':'British Columbia University, another country' ,'cnt':'France'},{'_meta':{'redacted_fields':{'loc':'restricted_species'}}},{'loc':None},{'status':'questioned'},{'lic':'https://unknown.test/license'}]:
   self.assertIsNone(collect.normalize({**RAW,**change},'British Columbia'))
 def test_older_cc_versions_supported_and_secrets_are_removed(self):
  self.assertIsNotNone(collect.normalize({**RAW,'lic':'https://creativecommons.org/licenses/by-nc-nd/2.5/'},'British Columbia'))
  self.assertEqual(collect.normalize({**RAW,'file':'https://xeno-canto.org/1/download?key=never-publish'},'British Columbia')['audio_url'],'')
 def test_missing_secret_makes_no_network_requests(self):
  with patch.object(collect,'request_json') as request:
   with self.assertRaisesRegex(ValueError,'required'):collect.collect('')
   request.assert_not_called()
 def test_all_queries_are_bounded_and_only_safe_metadata_is_saved(self):
  response={'numRecordings':'200','numPages':2,'recordings':[RAW]}
  with patch.object(collect,'request_json',return_value=(response,'abc')) as fetch,patch.object(collect.time,'sleep'):
   rows,sources=collect.collect('test-only-credential')
  self.assertEqual(fetch.call_count,30);self.assertEqual(len(sources),30);self.assertTrue(all(s['truncated'] for s in sources));self.assertNotIn('test-only-credential',json.dumps([rows,sources]));self.assertEqual(len(rows),1)
 def test_empty_collection_and_auth_failure_preserve_saved_data(self):
  with patch.object(collect,'request_json',return_value=({'numRecordings':0,'numPages':0,'recordings':[]},'abc')),patch.object(collect.time,'sleep'):
   with self.assertRaisesRegex(ValueError,'No usable'):collect.collect('test')
 def test_archives_append_and_unchanged_checks_keep_the_first_snapshot(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);row=collect.normalize(RAW,'British Columbia')
   with patch.object(collect,'now',return_value='2026-01-01T00:00:00Z'):first=collect.save([row],[SOURCE],root)
   files=list(root.glob('archive/*/*'));before=files[0].read_bytes()
   with patch.object(collect,'now',return_value='2026-01-02T00:00:00Z'):second=collect.save([row],[SOURCE],root)
   self.assertEqual(first['captured_at'],second['captured_at']);self.assertNotEqual(first['checked_at'],second['checked_at']);self.assertEqual(len(list(root.glob('archive/*/*'))),1);self.assertEqual(files[0].read_bytes(),before)
   with patch.object(collect,'now',return_value='2026-01-03T00:00:00Z'):collect.save([{**row,'quality':'B'}],[SOURCE],root)
   self.assertEqual(len(list(root.glob('archive/*/*'))),2);self.assertEqual(json.loads(gzip.decompress(before))['records'][0]['quality'],'A')
 def test_validation_prevents_empty_ready_or_duplicate_data(self):
  payload={'schema':1,'tool':'dawnchorus','status':'ready','records':[]}
  with self.assertRaises(ValueError):collect.validate(payload)
  row=collect.normalize(RAW,'British Columbia')
  with self.assertRaises(ValueError):collect.validate({**payload,'records':[row,row]})
