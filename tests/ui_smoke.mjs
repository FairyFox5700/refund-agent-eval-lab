import fs from 'node:fs';

const debugPort = process.env.CHROME_DEBUG_PORT || '9223';
const pages = await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json();
const page = pages.find(p => p.type === 'page' && p.url.includes('127.0.0.1:8765'));
if (!page) throw new Error('Dashboard tab not found');

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
let nextId = 0;
const pending = new Map();
ws.onmessage = event => {
  const message = JSON.parse(event.data);
  if (!message.id) return;
  const item = pending.get(message.id);
  if (!item) return;
  pending.delete(message.id);
  message.error ? item.reject(new Error(JSON.stringify(message.error))) : item.resolve(message.result);
};
function cdp(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await cdp('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function ready() {
  for (let i = 0; i < 30; i++) {
    const count = await evaluate("document.querySelectorAll('.scenario-item').length");
    if (count === 8) return;
    await wait(100);
  }
  throw new Error('Scenario catalog did not render');
}
async function runAndInspect() {
  await evaluate("document.querySelector('#run').click()");
  for (let i = 0; i < 30; i++) {
    const status = await evaluate("document.querySelector('#run-status').textContent");
    if (status === 'passed') break;
    await wait(100);
  }
  return evaluate(`(() => ({
    title: document.title,
    scenarios: document.querySelectorAll('.scenario-item').length,
    status: document.querySelector('#run-status').textContent,
    score: document.querySelector('#overall-score').textContent,
    traceEvents: document.querySelectorAll('.trace-event').length,
    metrics: document.querySelectorAll('.metric-card').length,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    response: document.querySelector('#agent-response').textContent
  }))()`);
}
async function screenshot(path) {
  const shot = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  fs.writeFileSync(path, Buffer.from(shot.data, 'base64'));
}

await cdp('Page.enable');
await cdp('Runtime.enable');
await ready();
const desktop = await runAndInspect();
await wait(2800); // Let the transient success toast clear before visual capture.
await screenshot('artifacts/dashboard-desktop.png');

await cdp('Emulation.setDeviceMetricsOverride', { width: 320, height: 900, deviceScaleFactor: 1, mobile: true });
await cdp('Page.reload', { ignoreCache: true });
await wait(500);
await ready();
const mobile = await runAndInspect();
await wait(2800);
await screenshot('artifacts/dashboard-mobile.png');

for (const result of [desktop, mobile]) {
  if (result.scenarios !== 8 || result.status !== 'passed' || result.score !== '100%' || result.metrics !== 4 || result.traceEvents < 6 || result.overflow !== 0) {
    throw new Error(`UI assertion failed: ${JSON.stringify(result)}`);
  }
  if (!result.response.includes('no refund has been executed')) throw new Error('Safety boundary copy missing');
}
console.log(JSON.stringify({ desktop, mobile }, null, 2));
ws.close();
