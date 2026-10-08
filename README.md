# Room Reset

A daily "is my room clean" checklist with a photo wall, for **Oct 7 – Dec 31, 2026** (86 days).
Tick the boxes, snap as many photos a day as you like, watch the wall fill up with polaroids.

Plain HTML, CSS and JavaScript. No build step, no npm, no framework — open `index.html` and it works.

## What's in here

| File | What it does |
| --- | --- |
| `index.html` | The whole app: markup, styles and script in one file |
| `manifest.json` | Makes it installable as a phone app ("Add to Home Screen") |
| `sw.js` | Service worker — lets the app open with no internet |
| `icons/` | App icons (the cat) |
| `tools/make_icons.py` | Redraws those icons from scratch: `python3 tools/make_icons.py` |

## Where my stuff is saved

Everything stays **on this phone/computer**. Nothing is uploaded anywhere.

- **Checklists and settings** → `localStorage`, under keys like `rr:day-2026-10-09` and `rr:settings`. A day looks like `{done:{taskId:true}, photos:["id","id"]}`.
- **Photos** → `IndexedDB` (database `room-reset`, store `photos`). A day can hold as many as you want; the wall tile shows the first one with a little badge for the rest. localStorage only holds about 5 MB of text, which is nowhere near enough for photos, so the shrunk JPEGs live here instead.
- Photos get resized to max 1400px and saved as JPEG before storing, so a 4 MB camera photo ends up more like 200 KB.
- On first load the app asks the browser for **persistent storage** so it doesn't quietly throw the photos away when space gets tight.

Because it's all local: **use the Backup button.** It saves one `.json` file with every checklist *and* every photo inside it. Restore loads it back. Do this before switching phones or clearing your browser.

## Running it locally

```bash
python3 -m http.server 8123
```

Then open <http://localhost:8123>. (Open the file directly and the service worker won't register — it needs `http://` or `https://`.)

## Changing it

- **Different dates?** `START` and `END` at the top of the `<script>`.
- **Different default tasks?** `DEFAULT_TASKS`, just below that. (Tasks you've already edited in the app win — they're saved in `rr:settings`.)
- **Changed the app and the phone keeps showing the old one?** Bump `CACHE` in `sw.js` (`room-reset-v1` → `v2`). That's the service worker's way of being told "throw out what you cached."

## Later

If I ever want my data on both my phone *and* my laptop, that needs a real backend with a login (Supabase or similar). Not built yet — on purpose.
