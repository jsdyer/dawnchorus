import test from 'node:test';
import assert from 'node:assert/strict';
import {validateDataset,filterRecords,groupSpecies,rank,safeURL,csv,licenceName} from '../web/model.mjs';
const record=(id,coast,extra={})=>({id,species:'Turdus migratorius',common_name:'American Robin',coast,province:coast==='pacific'?'British Columbia':'Nova Scotia',location:'Test fixture location',recordist:'Test fixture recordist',recorded_at:'2024-05-17',uploaded_at:'2024-06-01',quality:'B',sound_type:'song',length:'0:20',source_url:'https://xeno-canto.org/'+id.slice(2),licence_url:'https://creativecommons.org/licenses/by-nc-sa/4.0/',audio_url:'https://xeno-canto.org/'+id.slice(2)+'/download',...extra});
const rows=[record('XC1','pacific'),record('XC2','atlantic'),record('XC3','pacific',{quality:'A',sound_type:'call',recorded_at:'2023-10-10'})];
test('pairs exact scientific names and does not create missing-coast matches',()=>{
 assert.equal(groupSpecies(rows).length,1);assert.equal(groupSpecies(rows.slice(0,1)).length,0);assert.equal(groupSpecies(rows.slice(0,1),false)[0].atlantic.length,0);
});
test('filters on recording month, sound and quality rather than upload date',()=>{
 assert.deepEqual(filterRecords(rows,{month:'05',sound:'song',quality:'ab'}).map(r=>r.id),['XC1','XC2']);assert.equal(filterRecords(rows,{month:'06'}).length,0);assert.equal(filterRecords(rows,{search:'xc3'})[0].id,'XC3');
});
test('ranks quality first and then date, preserving source arrays',()=>{
 assert.equal(rank(rows)[0].id,'XC3');assert.equal(rows[0].id,'XC1');
});
test('imports reject duplicate identities, arbitrary audio URLs and mismatched scope',()=>{
 const data={schema:1,tool:'dawnchorus',status:'ready',records:rows};assert.equal(validateDataset(data).records.length,3);
 for(const records of [[rows[0],rows[0]],[{...rows[0],audio_url:'https://attacker.test/audio.mp3'}],[{...rows[0],source_url:'https://xeno-canto.org/1?key=secret'}],[{...rows[0],coast:'central'}]])assert.throws(()=>validateDataset({...data,records}));
 assert.throws(()=>validateDataset({...data,status:'pending'}));
});
test('links cannot transmit credentials and licence names preserve version',()=>{
 assert.equal(safeURL('javascript:alert(1)'), '');assert.equal(safeURL('https://user:pass@xeno-canto.org/1'),'');assert.equal(licenceName(rows[0].licence_url),'CC BY-NC-SA 4.0');
});
test('CSV preserves attribution and protects formula-like source strings',()=>{
 const text=csv([record('XC1','pacific',{recordist:'=SUM(A1:A2)',location:'A "quoted", place'})]);assert.match(text,/'=SUM/);assert.match(text,/A ""quoted"", place/);assert.match(text,/licence_url/);
});
