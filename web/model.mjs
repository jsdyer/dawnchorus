export const SPECIES = ['Turdus migratorius','Melospiza melodia','Poecile atricapillus','Corvus corax','Agelaius phoeniceus','Zonotrichia leucophrys'];
export const COASTS = ['pacific','atlantic'];
export function safeURL(value, kind='source') {
  try { const u=new URL(value);const hosts=kind==='licence'?['creativecommons.org','www.creativecommons.org']:['xeno-canto.org','www.xeno-canto.org','audio.xeno-canto.org'];
    return u.protocol==='https:'&&hosts.includes(u.hostname)&&!u.username&&!u.password&&!u.search&&!u.hash?u.href:'';
  } catch {return '';}
}
export function validateDataset(data) {
  if (!data||data.schema!==1||data.tool!=='dawnchorus'||!['ready','pending'].includes(data.status)||!Array.isArray(data.records)||data.records.length>3000) throw Error('Choose a Dawn Chorus snapshot JSON file (schema 1, up to 3,000 records).');
  if (data.status==='ready'&&!data.records.length||data.status==='pending'&&data.records.length) throw Error('The snapshot status does not match its records.');
  const seen=new Set();
  const records=data.records.map(r=>{
    if (!r||!/^XC\d+$/.test(r.id)||seen.has(r.id)||!SPECIES.includes(r.species)||!COASTS.includes(r.coast)) throw Error('The snapshot contains invalid, duplicate or out-of-scope recordings.');
    seen.add(r.id);
    for (const key of ['common_name','location','province','recordist','recorded_at','uploaded_at','quality','sound_type','length']) if (typeof r[key]!=='string'||r[key].length>5000) throw Error('The snapshot has missing or oversized recording metadata.');
    const source=safeURL(r.source_url);const licence=safeURL(r.licence_url,'licence');const audio=safeURL(r.audio_url);
    if (!source||!licence||r.audio_url&&!audio) throw Error('Source, audio and licence links must be approved HTTPS hosts without credentials.');
    return {...r,source_url:source,licence_url:licence,audio_url:audio};
  });
  return {...data,records};
}
export function filterRecords(records,{search='',sound='all',quality='all',month='all'}={}) {
  const needle=search.toLocaleLowerCase().trim();
  return records.filter(r=>(!needle||[r.common_name,r.species,r.location,r.recordist,r.id].join(' ').toLocaleLowerCase().includes(needle))&&(sound==='all'||r.sound_type.toLowerCase().includes(sound))&&(quality==='all'||(quality==='ab'?['A','B'].includes(r.quality):r.quality==='A'))&&(month==='all'||r.recorded_at.slice(5,7)===month));
}
export function groupSpecies(records,pairedOnly=true) {
  const groups=new Map();
  for(const r of records){if(!groups.has(r.species)) groups.set(r.species,{name:r.species,common:r.common_name,pacific:[],atlantic:[]});groups.get(r.species)[r.coast].push(r);}
  return [...groups.values()].filter(g=>!pairedOnly||g.pacific.length&&g.atlantic.length).sort((a,b)=>a.common.localeCompare(b.common)).map(g=>({...g,pacific:rank(g.pacific),atlantic:rank(g.atlantic)}));
}
export function rank(records) {return [...records].sort((a,b)=>('ABCDE'.includes(a.quality)?'ABCDE'.indexOf(a.quality):9)-('ABCDE'.includes(b.quality)?'ABCDE'.indexOf(b.quality):9)||b.recorded_at.localeCompare(a.recorded_at)||a.id.localeCompare(b.id));}
export function licenceName(url) {try {const parts=new URL(url).pathname.split('/').filter(Boolean);return parts[0]==='publicdomain'?'CC0 1.0':`CC ${parts[1].toUpperCase()} ${parts[2]}`;}catch{return 'Licence';}}
export function dateLabel(value) {return /^\d{4}-\d{2}-\d{2}/.test(value||'')?value.slice(0,10):'Date not supplied';}
export function csv(records) {
  const columns=['id','common_name','species','coast','province','location','recorded_at','recorded_time','recordist','quality','sound_type','length','source_url','licence_url','audio_url'];
  const cell=v=>{let s=String(v??'');if(/^[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
  return [columns,...records.map(r=>columns.map(k=>r[k]))].map(row=>row.map(cell).join(',')).join('\r\n');
}
