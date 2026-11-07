// Bấm phím thật trong Chrome không giao diện, qua giao thức gỡ lỗi của Chrome. Dùng bởi tests/test_fast_review.py.
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [chrome, url, debugPort, script] = process.argv.slice(2);
const profile = mkdtempSync(join(tmpdir(), "fast-review-"));
const proc = spawn(chrome, ["--headless=new", "--disable-gpu", "--no-first-run", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,800", "about:blank"], { stdio: "ignore" });
const wait = ms => new Promise(r => setTimeout(r, ms));
let target = null;
for (let i = 0; i < 60 && !target; i++) {
  await wait(250);
  try { target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(t => t.type === "page"); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => { ws.onopen = r; });
let seq = 0; const waiting = new Map();
ws.onmessage = e => { const d = JSON.parse(e.data); if (waiting.has(d.id)) { waiting.get(d.id)(d.result); waiting.delete(d.id); } };
const send = (method, params = {}) => new Promise(r => { const id = ++seq; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const value = async expression => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result.value;
async function ready() { for (let i = 0; i < 80; i++) { if (await value("window.__ready === true")) return; await wait(100); } throw new Error("không tải được trang"); }
async function idle() { await value("queue.then(() => 1)"); }
const CODES = { ArrowLeft: 37, ArrowRight: 39, Delete: 46 };
async function key(k) {
  const code = CODES[k] || k.toUpperCase().charCodeAt(0);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: k, windowsVirtualKeyCode: code, text: k.length === 1 ? k : undefined });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: k, windowsVirtualKeyCode: code });
  await idle();
}
const out = [];
await send("Page.enable"); await send("Runtime.enable");
await send("Page.navigate", { url }); await ready();
for (const a of JSON.parse(script)) {
  if (a.key) await key(a.key);
  if (a.reload) { await send("Page.reload"); await wait(300); await ready(); }
  if (a.shot) { await wait(400); const r = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(a.shot, Buffer.from(r.data, "base64")); }
  if (a.finish) { await value("document.getElementById('finish').click()"); await wait(300); }
  if (a.read) out.push(await value(`({cursor:S.cursor, pos:document.getElementById('pos').textContent, count:document.getElementById('count').textContent, msg:document.getElementById('msg').textContent, text:document.body.innerText, on:[...document.querySelectorAll('button.on')].map(b=>b.dataset.k), full:document.getElementById('full').width})`));
}
console.log(JSON.stringify(out));
ws.close(); proc.kill(); await wait(400);
try { rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(0);
