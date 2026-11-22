# Dawn Chorus

A quiet listening room for comparing the **same bird species** in Pacific and Atlantic Canada. Built as a static CoolCode tool at [coolcode.ca/dawnchorus/](https://coolcode.ca/dawnchorus/).

<!-- coolcode:guide -->
Choose a species to compare original xeno-canto recordings from British Columbia and Atlantic Canada. Filter by sound, recording month or quality, switch between source recordings, and export attributed metadata. Six focal species and the first 100 records per species/province query form a bounded sample; different individuals, dates, equipment and habitats mean these examples do not establish regional dialects. Cards show recording dates separately from upload dates, plus recordist, source and individual licence. The initial page honestly shows a pending state until its first authenticated collection; a previously saved Dawn Chorus JSON snapshot can also be opened locally.
<!-- /coolcode:guide -->

## Coverage and interpretation

The collector uses xeno-canto **API v3**, not the retired v2 endpoint. It queries six scientific names separately: *Turdus migratorius* (American Robin), *Melospiza melodia* (Song Sparrow), *Poecile atricapillus* (Black-capped Chickadee), *Corvus corax* (Common Raven), *Agelaius phoeniceus* (Red-winged Blackbird), and *Zonotrichia leucophrys* (White-crowned Sparrow).

For each species it requests `cnt:Canada grp:birds id?:no` and a quoted locality match for British Columbia, Nova Scotia, New Brunswick, Prince Edward Island or Newfoundland. Pacific means British Columbia, including inland locations. Atlantic combines the other four province queries. The Newfoundland locality match includes the wording “Newfoundland and Labrador” but can miss recordings labelled only “Labrador.” Free-text locality matching is imperfect; this is a documented sample, not a provincial boundary inventory. No coordinates or restricted-species records are published.

There are **30 first-page metadata queries per weekly refresh**, each with `per_page=100`. At most 3,000 metadata rows are considered; duplicates are removed by XC catalogue number. Every query retains received, retained and source-reported total counts, query text, truncation flag and SHA-256 of the response. If a query reports additional pages, the UI says so. There is a one-second pause between queries and at most three attempts for transient failures. The official v3 documentation says the previous strict rate limiter was lifted; the terms still discourage indiscriminate automated downloads. This collector does not download audio in bulk.

Only recordings identified by the source, with an explicit supported Creative Commons licence and matching Canadian locality are retained. Source-redacted records are skipped. Original source audio is requested only when the visitor uses the audio control (`preload="none"`). Playback pauses the other coast's player. If playback is blocked by the source or the recording disappears, a source link remains and an error message directs the visitor to it.

Quality is the source's A–E rating, with A highest. Quality, then recording date, orders choices; it is not a claim that a selected bird is representative. Shared species are grouped by scientific name, never common name alone. A filter can remove one coast's recordings; an empty match does not establish species absence. “Recorded month” uses the recording date, not upload or collection date. Please avoid playing calls near wild birds.

## Sources and reuse

Primary source documentation checked 2026-11-22:

- [API v3](https://xeno-canto.org/explore/api): endpoint, credentials, tagged queries, page sizes, source fields and restricted-species redactions.
- [Search tips](https://xeno-canto.org/help/search): locality text matching, quality, sound types and recording versus upload dates.
- [Terms of use](https://xeno-canto.org/about/terms): per-recording Creative Commons licences, attribution, permitted embedding and considerate server use.
- [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/): one common licence, not a blanket licence for every recording.

The official pages were fetched directly over HTTPS during implementation; the web search renderer's copy was blocked. No account or key was used for documentation requests. An unauthenticated v3 request returned HTTP 401, so **no real recording inventory is claimed before the authenticated workflow runs**.

Every recording links to its exact source and licence and credits the recordist and XC number. Audio streams unchanged from xeno-canto; no clips are cropped, remixed or relicensed. Source remarks retain any recordist description of their own edits. Noncommercial and no-derivatives conditions apply where specified. Follow the individual licence when reusing or adapting a recording. Software licence terms do not apply to source audio or source data.

## Collection, retention and deployment

Set the repository Actions secret **`XENO_CANTO_API_KEY`** to a verified xeno-canto account's API key. The [official documentation](https://xeno-canto.org/explore/api) recommends an app key for apps. Keys are read only from the collector environment, never printed, saved, or sent to the browser. Query provenance deliberately omits the credential. The public UI never asks for a key.

The `Browser tool · Check and publish` workflow runs on pushes to `main`, PRs, manual dispatch and **Mondays at 08:23 UTC** (`23 8 * * 1`). A first push collects when `data/current.json` is pending; ordinary code pushes use an already collected snapshot. If the first push has no secret, the explicit pending state may deploy and visitors can use local snapshot import. Manual and scheduled runs attempt a fresh collection and fail clearly when credentials are missing or invalid. PRs test and build offline. A manual workflow dispatch after adding the secret starts the first collection immediately.

Any authenticated request failure or invalid response fails the workflow before deployment and before replacing the last successful dataset. A partially collected run is not saved. Empty result sets across the entire scope also fail. The last good Pages deployment remains available, showing its source check date. Schedules in inactive public GitHub repositories can stop after 60 days; source freshness remains visible.

`data/current.json` is the normalized current view. `data/index.json` is a compact status, count, coverage and timestamp manifest for the CoolCode hub. `data/history.json` lists immutable compressed snapshots in `archive/YYYY-MM/`. A changed recording set creates a new snapshot with SHA-256 and added/removed counts; an unchanged successful check updates only the current check timestamp and query provenance. Absence on a later bounded page is not treated as a deletion from xeno-canto or ecological disappearance. Nothing is pruned automatically. CI commits validated snapshots only after model, build and browser checks pass.

Build output includes source data, archive links and `data/build.json` with the build time. The build does not fetch source data. Source capture, last check, recording, upload and build dates have distinct meanings in the interface.

## Local use, export and privacy

The browser supports a JSON snapshot exported from this app (schema 1, up to 8 MB and 3,000 records). It validates identities, coast/species scope and allowed HTTPS source/licence/audio hosts. Imports and filters stay in the tab; no local storage is used. Use **Return to published collection** to restore the bundled view. Gzip archives can be decompressed and opened as JSON. CSV exports include every filtered recording, including single-coast recordings even while the species navigator is showing only shared species; spreadsheet formula-like strings are escaped.

Playing audio contacts xeno-canto. Opening links contacts the chosen source or Creative Commons. A CoolCode counter records aggregate page opens without filters or imported files. API credentials are never available to page JavaScript.

## Development and checks

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

Use `python3 scripts/collect.py` with the API key already present in the environment for an explicit refresh, or `--if-missing` to refresh only a pending state. No production dependencies are needed. CI installs the test-only Playwright requirement and exercises project-subpath loading, source selection, paired/unpaired filters, quality and recording-date behaviour, local imports, hostile source strings, exports, reset and the mobile layout. Test fixtures are labelled and never appear in published datasets. `dist/` and browser screenshots are not committed.
