"""CI-only Chromium flow at a project subpath; fixtures are clearly test-only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,shutil,tempfile,threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def fixture():
 rows=[]
 for num,coast in [(1,'pacific'),(2,'atlantic'),(3,'pacific')]:
  rows.append({'id':f'XC{num}','species':'Turdus migratorius','common_name':'American Robin','coast':coast,'province':'British Columbia' if coast=='pacific' else 'Nova Scotia','location':'TEST FIXTURE <img src=x onerror=alert(1)>','recordist':'Test fixture recordist','recorded_at':'2024-05-17','recorded_time':'06:15','uploaded_at':'2024-06-01','quality':'A' if num==3 else 'B','sound_type':'call' if num==3 else 'song','length':'0:20','source_url':f'https://xeno-canto.org/{num}','licence_url':'https://creativecommons.org/licenses/by-nc-sa/4.0/','audio_url':f'https://xeno-canto.org/{num}/download','remarks':'TEST FIXTURE — not a published observation'})
 return {'schema':1,'tool':'dawnchorus','status':'ready','records':rows,'captured_at':'2026-01-01T00:00:00Z','checked_at':'2026-01-02T00:00:00Z','coverage':'CI TEST FIXTURE','sources':[],'warnings':[]}

def main():
 shots=ROOT/'browser-checks';shots.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as temp:
  shutil.copytree(ROOT/'dist',Path(temp)/'example-tool')
  server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temp));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/assets/tool-metrics.js',lambda route:route.fulfill(status=200,body=''))
    page.route('https://xeno-canto.org/**',lambda route:route.abort())
    page.goto(f'http://127.0.0.1:{server.server_port}/example-tool/');page.wait_for_function("document.querySelector('#notice').textContent !== 'Loading the saved recording collection…'")
    assert page.locator('h1').inner_text().replace('\n',' ').strip()=='Dawn Chorus.'
    page.locator('#import-file').set_input_files({'name':'ci-fixture.json','mimeType':'application/json','buffer':json.dumps(fixture()).encode()})
    page.wait_for_function("document.querySelectorAll('.recording-card').length === 2")
    assert page.locator('#selected-name').inner_text()=='American Robin';assert page.locator('img').count()==0
    assert page.locator('audio').count()==2;assert page.locator('audio').first.get_attribute('preload')=='none'
    assert page.locator('audio').first.get_attribute('src')=='https://xeno-canto.org/3/download'
    page.get_by_label('Choose pacific recording').select_option('XC1');assert page.locator('audio').first.get_attribute('src')=='https://xeno-canto.org/1/download'
    page.locator('#sound').select_option('call');assert page.locator('#empty').is_visible();page.locator('#paired').uncheck();assert page.locator('.recording-card').count()==2;assert 'No matching recording' in page.locator('.recording-card.atlantic').inner_text()
    page.locator('#reset').click();page.locator('#quality').select_option('a');assert page.locator('#empty').is_visible();page.locator('#reset').click();page.locator('#search').fill('not-a-bird');assert page.locator('#empty').is_visible();page.locator('#reset').click()
    with page.expect_download() as event:page.locator('#export-csv').click()
    assert event.value.suggested_filename=='dawnchorus-recordings.csv'
    with page.expect_download() as event:page.locator('#export-json').click()
    assert event.value.suggested_filename=='dawnchorus-snapshot.json'
    page.locator('#import-file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{"schema":2}'})
    page.wait_for_function("document.querySelector('#import-status').textContent.includes('Choose a Dawn Chorus')")
    assert 'Choose a Dawn Chorus' in page.locator('#import-status').inner_text();assert page.locator('#selected-name').inner_text()=='American Robin'
    page.screenshot(path=str(shots/'desktop.png'),full_page=True);page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth');page.locator('#month').select_option('06');assert page.locator('#empty').is_visible();page.locator('#reset').click();page.screenshot(path=str(shots/'mobile.png'),full_page=True)
    page.locator('#restore').click();assert page.locator('#restore').is_hidden();assert not errors,errors;browser.close()
   print('Browser checks passed: local import, pair selection, safe source text, filtering, export, reset and mobile layout')
  finally:server.shutdown()
if __name__=='__main__':main()
