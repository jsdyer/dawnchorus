#!/usr/bin/env python3
"""Bounded xeno-canto v3 collector. Credentials are never serialized or logged."""
from datetime import datetime, timezone
import argparse, gzip, hashlib, json, os, re, time
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
ROOT = Path(__file__).resolve().parents[1]
API = 'https://xeno-canto.org/api/3/recordings'
SPECIES = ('Turdus migratorius', 'Melospiza melodia', 'Poecile atricapillus', 'Corvus corax', 'Agelaius phoeniceus', 'Zonotrichia leucophrys')
PLACES = {'British Columbia':'pacific','Nova Scotia':'atlantic','New Brunswick':'atlantic','Prince Edward Island':'atlantic','Newfoundland':'atlantic'}
PER_PAGE = 100
MAX_BYTES = 8_000_000
COVERAGE = 'Six focal species; locality-text matches for British Columbia and four Atlantic provinces; first 100 results per species/province query. Not a complete inventory or evidence of regional dialect.'

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def digest(data): return hashlib.sha256(data).hexdigest()
def encode(value): return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def safe_url(value, hosts):
    if not isinstance(value,str): return ''
    if value.startswith('//'): value='https:'+value
    if value.startswith('http://creativecommons.org/'): value='https:'+value[7:]
    p=urlsplit(value)
    return value if p.scheme=='https' and p.hostname in hosts and not p.query and not p.fragment and not p.username else ''
def duration(value):
    try:
        fields=str(value).split(':')
        if len(fields)!=2: return None
        minutes,seconds=map(float,fields)
        return round(minutes*60+seconds,2) if minutes>=0 and 0<=seconds<60 else None
    except (ValueError,TypeError): return None

def normalize(raw, province):
    if not isinstance(raw,dict) or not re.fullmatch(r'\d+',str(raw.get('id',''))): return None
    if str(raw.get('cnt','')).casefold()!='canada' or raw.get('status','identified')!='identified': return None
    if (raw.get('_meta') or {}).get('redacted_fields'): return None
    scientific=' '.join(str(raw.get(k) or '').strip() for k in ('gen','sp'))
    if scientific not in SPECIES: return None
    location=str(raw.get('loc') or '')
    if province.casefold() not in location.casefold(): return None
    licence=safe_url(raw.get('lic'),{'creativecommons.org','www.creativecommons.org'})
    if not re.fullmatch(r'https://(?:www\.)?creativecommons.org/(?:licenses/(?:by|by-sa|by-nc|by-nc-sa|by-nd|by-nc-nd)/(?:1\.0|2\.0|2\.5|3\.0|4\.0)/|publicdomain/zero/1\.0/)',licence): return None
    file=safe_url(raw.get('file'),{'xeno-canto.org','www.xeno-canto.org','www.xeno-canto.org','audio.xeno-canto.org'})
    # No unknown URLs, restricted locations, sensitive coordinates, or API credentials are persisted.
    return {'id':'XC'+str(raw['id']),'species':scientific,'common_name':str(raw.get('en') or scientific),'coast':PLACES[province],
      'province':province,'location':location,'recorded_at':str(raw.get('date') or ''),'recorded_time':str(raw.get('time') or ''),
      'uploaded_at':str(raw.get('uploaded') or ''),'recordist':str(raw.get('rec') or 'Recordist not supplied'),
      'licence_url':licence,'source_url':'https://xeno-canto.org/'+str(raw['id']),'audio_url':file,
      'quality':str(raw.get('q') or 'unrated'),'sound_type':str(raw.get('type') or 'Unspecified'),
      'length':str(raw.get('length') or ''),'duration_seconds':duration(raw.get('length')),
      'remarks':str(raw.get('rmk') or ''),'playback_used':str(raw.get('playback-used') or 'unknown'),
      'identification_status':'identified'}

def request_json(query,key):
    url=API+'?'+urlencode({'query':query,'key':key,'per_page':PER_PAGE,'page':1})
    for attempt in range(3):
        try:
            req=Request(url,headers={'User-Agent':'DawnChorus/1.0 (+https://coolcode.ca/dawnchorus/)','Accept':'application/json'})
            with urlopen(req,timeout=45) as response: raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES: raise ValueError('Source response exceeded 8 MB bound')
            result=json.loads(raw)
            if not isinstance(result,dict) or not isinstance(result.get('recordings'),list) or result.get('error'):
                raise ValueError('Source did not return a recording list')
            if len(result['recordings'])>PER_PAGE: raise ValueError('Source exceeded requested page bound')
            return result, digest(raw)
        except HTTPError as exc:
            code=exc.code
            if code in (401,403): raise RuntimeError('Source authentication failed; check the Actions secret and xeno-canto account access') from None
            if code!=429 and code<500: raise RuntimeError(f'Source request rejected (HTTP {code})') from None
            if code==429:
                retry=exc.headers.get('Retry-After','') if exc.headers else ''
                if retry.isdigit():
                    if int(retry)>60: raise RuntimeError('Source requested a longer pause; retry on the next scheduled run') from None
                    time.sleep(int(retry))
        except (URLError,TimeoutError,OSError): pass
        if attempt<2: time.sleep(2**(attempt+1))
    raise RuntimeError('Source unavailable after three attempts; last good snapshot retained') from None

def collect(key):
    if not key: raise ValueError('XENO_CANTO_API_KEY is required for refresh; existing data is unchanged')
    rows={}; sources=[]
    for species in SPECIES:
        for province in PLACES:
            query=f'grp:birds cnt:Canada sp:"{species}" loc:"{province}" id?:no'
            result,sha=request_json(query,key)
            try: total=int(result['numRecordings']); pages=int(result['numPages'])
            except (KeyError,ValueError,TypeError): raise ValueError('Source totals are missing or invalid') from None
            if total<0 or pages<0: raise ValueError('Invalid source coverage totals')
            kept=0
            for raw in result['recordings']:
                row=normalize(raw,province)
                if row and row['species']==species: rows[row['id']]=row; kept+=1
            sources.append({'url':API,'query':query,'province':province,'species':species,'page':1,'per_page':PER_PAGE,
                'reported_total':total,'reported_pages':pages,'received':len(result['recordings']),'retained':kept,
                'truncated':pages>1,'response_sha256':sha})
            time.sleep(1)
    if not rows: raise ValueError('No usable recordings returned; existing data is unchanged')
    return sorted(rows.values(),key=lambda r:r['id']),sources

def validate(payload):
    if payload.get('schema')!=1 or payload.get('tool')!='dawnchorus' or payload.get('status') not in ('ready','pending'): raise ValueError('Invalid Dawn Chorus dataset')
    rows=payload.get('records')
    if not isinstance(rows,list) or len(rows)>3000: raise ValueError('Invalid record bound')
    if payload['status']=='ready' and not rows: raise ValueError('Ready data must have records')
    if payload['status']=='pending' and rows: raise ValueError('Pending data cannot have records')
    ids=set()
    for r in rows:
        if r['id'] in ids or not re.fullmatch(r'XC\d+',r['id']): raise ValueError('Invalid or duplicate recording identity')
        ids.add(r['id'])
        if r.get('coast') not in ('atlantic','pacific') or r.get('species') not in SPECIES: raise ValueError('Outside documented scope')
        if not safe_url(r.get('source_url'),{'xeno-canto.org'}) or not safe_url(r.get('licence_url'),{'creativecommons.org','www.creativecommons.org'}): raise ValueError('Invalid attribution URL')
        if r.get('audio_url') and not safe_url(r['audio_url'],{'xeno-canto.org','www.xeno-canto.org','audio.xeno-canto.org'}): raise ValueError('Invalid audio URL')
    encode(payload)
    return payload

def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_bytes(encode(value));tmp.replace(path)
def save(records,sources,root=ROOT):
    stamp=now();folder=root/'data';folder.mkdir(exist_ok=True)
    old=json.loads((folder/'current.json').read_text()) if (folder/'current.json').exists() else {'records':[]}
    history=json.loads((folder/'history.json').read_text()) if (folder/'history.json').exists() else []
    records_sha=digest(encode(records));payload=validate({'schema':1,'tool':'dawnchorus','status':'ready','captured_at':stamp,'checked_at':stamp,
      'coverage':COVERAGE,'records':records,'sources':sources,'records_sha256':records_sha,'warnings':['Some source queries exceed the first 100 records; see coverage.'] if any(s['truncated'] for s in sources) else []})
    if old.get('records_sha256')==records_sha:
        payload['captured_at']=old['captured_at'];payload['snapshot']=old['snapshot']
    else:
        name=stamp.replace(':','').replace('-','')+'-'+records_sha[:12]+'.json.gz';path=root/'archive'/stamp[:7]/name
        payload['snapshot']='archive/'+stamp[:7]+'/'+name
        raw=encode(payload);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(gzip.compress(raw,mtime=0))
        old_ids={r['id'] for r in old['records']};new_ids={r['id'] for r in records}
        history.append({'captured_at':stamp,'file':payload['snapshot'],'records':len(records),'sha256':digest(raw),'added':len(new_ids-old_ids),'removed':len(old_ids-new_ids)})
    atomic(folder/'current.json',payload);atomic(folder/'history.json',history)
    atomic(folder/'index.json',{'schema':1,'tool':'dawnchorus','status':'ready','source':'xeno-canto API v3','source_url':'https://xeno-canto.org/explore/api',
      'captured_at':payload['captured_at'],'checked_at':stamp,'record_count':len(records),'species_count':len({r['species'] for r in records}),
      'snapshot_count':len(history),'coverage':COVERAGE,'latest':'current.json','history':'history.json','warnings':payload['warnings']})
    print(f'Saved {len(records)} recordings and {len(history)} immutable snapshots')
    return payload

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--if-missing',action='store_true');args=parser.parse_args()
    if args.if_missing and (ROOT/'data/current.json').exists():
        existing=validate(json.loads((ROOT/'data/current.json').read_text()))
        if existing['status']=='ready': print('Using saved source data');return
    key=os.environ.get('XENO_CANTO_API_KEY','').strip()
    if args.if_missing and not key and (ROOT/'data/current.json').exists():
        baseline=validate(json.loads((ROOT/'data/current.json').read_text()))
        if baseline['status']=='pending':
            print('No Actions credential is configured yet; retaining explicit pending collection state')
            return
    rows,sources=collect(key);save(rows,sources)
if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError) as exc: raise SystemExit(str(exc)) from None
