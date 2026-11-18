// Capture presentation-resolution screenshots of the real MLflow 3 UI.
//
// Prerequisites:
//   1. python -m pip install mlflow  (or use the repo's .venv)
//   2. .venv/bin/python docs/demo/copy_traces.py
//   3. mlflow ui --backend-store-uri sqlite:///<tmp>/mlflowtest-demo-shots/mlflow.db \
//        --host 127.0.0.1 --port 5123
//   4. PLAYWRIGHT_MODULE=/path/to/node_modules/playwright node docs/demo/shoot.js
//
// The local store gets fresh trace IDs on every copy. Targets below name the
// ORIGINAL Databricks trace (short prefix); the script resolves the current
// local ID from trace_map.json. Falls back to the IDs used for the committed
// screenshots if the map is absent.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/Users/yourbabes/dev/handy-dandy/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const OUT = path.join(HERE, 'screenshots');
fs.mkdirSync(OUT, { recursive: true });

const BASE = process.env.MLFLOW_UI_URL || 'http://127.0.0.1:5123';
const EXP = process.env.MLFLOW_EXPERIMENT_ID || '1';

// trace = short prefix of the original Databricks trace ID (see LAB_BOOK.md).
const targets = [
  { file: '01-traces-list.png',       url: `#/experiments/${EXP}/traces`, note: 'traces list' },
  { file: '02-baseline-waterfall.png', trace: '054cbbc9', note: 'baseline 7 spans' },
  { file: '03-manual-spans.png',       trace: '0cb5f6d2', note: 'manual spans 10 spans' },
  { file: '04-multiturn-turn3.png',    trace: '6f99921d', note: 'turn 3 recall' },
  { file: '05-tool-error.png',         trace: 'cbd09f84', note: 'tool error' },
  { file: '06-unhandled-error.png',    trace: '3dbea41e', note: 'unhandled error' },
  { file: '07-handled-error.png',      trace: '193c937a', note: 'handled error' },
  { file: '08-error-rows.png',         url: `#/experiments/${EXP}/traces`, note: 'error + session rows', scrollTo: 380 },
];

// Fallback IDs are the ones visible in the committed screenshots.
const FALLBACK = {
  '054cbbc9': 'tr-ee8cf68fbe82ea628f5bc5599b2526d1',
  '0cb5f6d2': 'tr-c2c963345996b3b8829870f55e0c48d9',
  '6f99921d': 'tr-30fe163b1895fbf03ffc30ee189fd380',
  'cbd09f84': 'tr-651bee5671295a29be3a4c6b2ec8729f',
  '3dbea41e': 'tr-f53de5648d3b7f9ceed011b4c70b702e',
  '193c937a': 'tr-1c0d8c12605f1c535f474129f66387cb',
};

function localId(prefix) {
  if (FALLBACK[prefix] && !fs.existsSync(path.join(HERE, 'trace_map.json'))) return FALLBACK[prefix];
  try {
    const map = JSON.parse(fs.readFileSync(path.join(HERE, 'trace_map.json'), 'utf8'));
    const hit = map.find(r => r.old_id.includes(prefix));
    if (hit) return hit.new_id;
  } catch (e) { /* fall through */ }
  if (FALLBACK[prefix]) return FALLBACK[prefix];
  throw new Error(`no local trace ID for ${prefix}; run copy_traces.py first`);
}

for (const t of targets) {
  if (t.trace) t.url = `#/experiments/${EXP}/traces?traceId=${localId(t.trace)}`;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1600, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();
  for (const t of targets) {
    await page.goto(BASE + '/' + t.url, { waitUntil: 'domcontentloaded' });
    // The guidance popover renders after load; dismiss it before capturing.
    await page.waitForTimeout(1200);
    for (let attempt = 0; attempt < 6; attempt++) {
      const clicked = await page.evaluate(() => {
        const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim() === 'Got it');
        if (b) { b.click(); return true; }
        return false;
      });
      if (clicked) await page.waitForTimeout(300);
      const stillThere = await page.evaluate(() =>
        Array.from(document.querySelectorAll('button')).some(x => x.textContent.trim() === 'Got it')
      );
      if (!stillThere) break;
      await page.waitForTimeout(500);
    }
    await page.waitForTimeout(1500);
    if (t.scrollTo) {
      await page.evaluate(y => {
        const el = Array.from(document.querySelectorAll('*')).find(
          e => e.scrollHeight > e.clientHeight + 100 && e.clientHeight > 200
        );
        if (el) el.scrollTop = y;
      }, t.scrollTo);
      await page.waitForTimeout(600);
    }
    const file = path.join(OUT, t.file);
    await page.screenshot({ path: file, fullPage: false });
    console.log(`${t.file}  ${t.note}  ${Math.round(fs.statSync(file).size / 1024)}KB`);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
