import {validateDataset,filterRecords,groupSpecies,licenceName,dateLabel,csv} from './model.mjs';
const $=id=>document.getElementById(id);
let published=null,current=null,selected='',filtered=[],local=false,history=[];
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const link=(text,url)=>{const n=el('a',text);n.href=url;n.target='_blank';n.rel='noopener noreferrer';return n;};
function download(text,type,name){const url=URL.createObjectURL(new Blob([text],{type}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function stopAudio(){document.querySelectorAll('audio').forEach(a=>a.pause());}
function recordCard(coast,rows){
  const card=el('article',undefined,'recording-card '+coast);card.append(el('p',coast==='pacific'?'01 / Pacific Canada':'02 / Atlantic Canada','coast-tag'));
  if(!rows.length){card.append(el('h4','No matching recording'),el('p','Try widening your sound, month or quality filters. This does not mean the species is absent from this coast.','location'));return card;}
  let active=rows[0];const content=el('div');
  const chooseLabel=el('label','Choose a recording');const choose=el('select');choose.setAttribute('aria-label',`Choose ${coast} recording`);
  rows.forEach(r=>{const option=el('option',`${r.id} · ${r.quality} · ${dateLabel(r.recorded_at)} · ${r.length||'length unknown'}`);option.value=r.id;choose.append(option);});chooseLabel.append(choose);card.append(chooseLabel,content);
  function render(){
    content.replaceChildren();content.append(el('h4',active.province),el('p',active.location,'location'));
    if(active.audio_url){
      const audio=el('audio');audio.controls=true;audio.preload='none';audio.src=active.audio_url;audio.setAttribute('aria-label',`${active.common_name}, ${coast}, ${active.id}`);
      const status=el('p','Original audio · plays from xeno-canto','clip-status');
      audio.addEventListener('play',()=>{document.querySelectorAll('audio').forEach(other=>{if(other!==audio)other.pause();});status.textContent='Listening to '+active.id+' · original, unmodified audio';});
      audio.addEventListener('error',()=>{status.textContent='Audio could not load here. Open the source recording below to listen.';});content.append(audio,status);
    }else content.append(el('p','Audio is unavailable in the source metadata. Open the source recording below.','clip-status'));
    const dl=el('dl',undefined,'metadata');
    for(const [name,value] of [['Recorded',dateLabel(active.recorded_at)],['Sound',active.sound_type],['Quality / length',`${active.quality} / ${active.length||'not supplied'}`],['Uploaded',dateLabel(active.uploaded_at)]]){const box=el('div');box.append(el('dt',name),el('dd',value));dl.append(box);}
    content.append(dl);const credit=el('p',undefined,'credit');credit.append(el('span','© '+active.recordist),el('br'),link(active.id+' · source recording ↗',active.source_url),el('br'),link(licenceName(active.licence_url)+' ↗',active.licence_url));content.append(credit);
    if(active.remarks){const details=el('details');details.append(el('summary','Recordist’s notes'),el('p',active.remarks));content.append(details);}
  }
  choose.addEventListener('change',()=>{stopAudio();active=rows.find(r=>r.id===choose.value);render();});render();return card;
}
function render(){
  if(!current)return;stopAudio();
  const ready=current.status==='ready';const shared=groupSpecies(current.records).length;
  $('species-count').textContent=ready?shared.toLocaleString():'—';$('recording-count').textContent=ready?current.records.length.toLocaleString():'—';
  $('snapshot-date').textContent=ready?dateLabel(current.captured_at):'Awaiting collection';$('checked-date').textContent=ready?'Checked '+dateLabel(current.checked_at):'Weekly source checks';
  $('dataset-label').textContent=local?'Local snapshot':'xeno-canto · saved collection';$('restore').hidden=!local||!published;
  $('notice').hidden=false;$('notice').textContent=!ready?'The first source collection is pending. No recordings or counts have been invented. Once the scheduled collection succeeds, both coasts will appear here.':local?'You are viewing a local snapshot. It stays in this tab. Playing audio still contacts xeno-canto.':`Saved collection, checked ${dateLabel(current.checked_at)}. ${current.warnings?.length?current.warnings.join(' '):'Use the controls below to explore the source recordings.'}`;
  filtered=filterRecords(current.records,{search:$('search').value,sound:$('sound').value,quality:$('quality').value,month:$('month').value});
  const groups=groupSpecies(filtered,$('paired').checked);if(!groups.some(g=>g.name===selected))selected=groups[0]?.name||'';
  $('results-count').textContent=`${groups.length} species · ${filtered.length} filtered recordings`;$('species-list').replaceChildren();
  groups.forEach(g=>{const b=el('button',g.common,'species-choice');b.type='button';b.setAttribute('aria-pressed',String(g.name===selected));b.append(el('small',`${g.pacific.length} Pacific · ${g.atlantic.length} Atlantic`));b.addEventListener('click',()=>{selected=g.name;render();});$('species-list').append(b);});
  const group=groups.find(g=>g.name===selected);$('recording-pair').replaceChildren();$('empty').hidden=Boolean(group);$('comparison-heading').hidden=!group;
  if(group){$('selected-name').textContent=group.common;$('selected-scientific').textContent=group.name;$('recording-pair').append(recordCard('pacific',group.pacific),recordCard('atlantic',group.atlantic));}
  else {$('empty').querySelector('h3').textContent=ready?'No recordings match these filters.':'Your listening room is ready.';$('empty-detail').textContent=ready?'Clear the search or widen the sound, month and quality filters. Turn off “Available on both coasts” to explore one coast at a time.':'The first authenticated xeno-canto collection has not completed. You can open a previously saved Dawn Chorus snapshot below, or visit xeno-canto while the collection is prepared.';}
  $('export-csv').disabled=!filtered.length;$('export-json').disabled=!ready;
  $('coverage').textContent=current.coverage||'Coverage was not supplied by this snapshot.';
  $('coverage-detail').replaceChildren();
  for(const source of current.sources||[]){const p=el('p',`${source.species} / ${source.province}: ${source.received} received, ${source.retained} retained; ${source.reported_total} reported matches${source.truncated?' · first page only':''}.`,'coverage-row');$('coverage-detail').append(p);}
  if(!(current.sources||[]).length)$('coverage-detail').append(el('p','No completed source queries yet.'));
}
function reset(){for(const id of ['search','sound','quality','month'])$(id).value=id==='search'?'':'all';$('paired').checked=true;selected='';render();}
for(const id of ['search','sound','quality','month','paired'])$(id).addEventListener(id==='search'?'input':'change',render);
$('reset').addEventListener('click',reset);
$('export-csv').addEventListener('click',()=>download(csv(filtered),'text/csv;charset=utf-8','dawnchorus-recordings.csv'));
$('export-json').addEventListener('click',()=>download(JSON.stringify(current,null,2),'application/json','dawnchorus-snapshot.json'));
$('restore').addEventListener('click',()=>{current=published;local=false;$('import-status').textContent='Published collection restored.';reset();});
$('import-file').addEventListener('change',async event=>{const file=event.target.files[0];if(!file)return;try{if(file.size>8_000_000)throw Error('Choose a JSON snapshot smaller than 8 MB.');const parsed=validateDataset(JSON.parse(await file.text()));current=parsed;local=true;$('import-status').textContent=`Opened ${file.name} in this tab.`;reset();}catch(error){$('import-status').textContent=error instanceof SyntaxError?'This file is not valid JSON. The current collection is unchanged.':error.message;}finally{event.target.value='';}});
async function start(){
  try{const response=await fetch('./data/current.json');if(!response.ok)throw Error('Snapshot not available');published=validateDataset(await response.json());current=published;render();}
  catch{ $('notice').textContent='The saved collection could not load. Reload the page or open a saved Dawn Chorus JSON snapshot below.';$('empty').hidden=false;$('empty-detail').textContent='A source dataset is required before recording comparisons can be shown.';$('export-csv').disabled=true;$('export-json').disabled=true;}
  try{const response=await fetch('./data/history.json');history=await response.json();if(!Array.isArray(history))return;const recent=[...history].reverse().slice(0,12);$('history').append(el('h4',`${history.length} retained snapshots`));for(const item of recent){if(!/^archive\/\d{4}-\d{2}\/[A-Za-z0-9-]+\.json\.gz$/.test(item.file))continue;const a=link(`${dateLabel(item.captured_at)} · ${item.records} recordings · archived JSON (gzip)`,'./'+item.file);a.className='history-row';$('history').append(a);}}
  catch{$('history').textContent='Snapshot history is not available.';}
  try{const response=await fetch('./data/build.json');const build=await response.json();$('build-date').textContent='Site built '+dateLabel(build.built_at)+'. Source checks run weekly; the source date above may differ.';}catch{}
}
start();
