import fs from 'node:fs';
import crypto from 'node:crypto';

// Store bounded, original screenshots. Never synthesize a passing screen.
export function saveVisualBuffer(buffer, name, details = {}) {
  if (!/^[a-z0-9-]+$/.test(name)) throw new Error('Invalid visual evidence name');
  const path = `ui/results/screenshots/${name}.png`;
  fs.mkdirSync('ui/results/screenshots', {recursive:true});
  fs.writeFileSync(path, buffer, {mode:0o600});
  return {...details, path, capturedAt:Date.now(), runId:process.env.UI_BUSINESS_RUN_ID,
    sha256:crypto.createHash('sha256').update(buffer).digest('hex')};
}
export async function captureVisual(target, name, details = {}, options = {}) {
  return saveVisualBuffer(await target.screenshot(options), name, details);
}
export async function captureSafeStatus(page, name, patterns, details = {}) {
  for (const pattern of patterns) {
    const label = page.getByText(new RegExp(pattern), {exact:true}).first();
    if (!(await label.isVisible().catch(()=>false))) continue;
    // Only capture a static status label, never a form or identity document.
    if (await label.locator('input,textarea,img,canvas,iframe,video').count()) continue;
    const box = await label.evaluate(node => {
      const range=document.createRange(); range.selectNodeContents(node);
      const r=range.getBoundingClientRect();
      return {x:r.x,y:r.y,width:r.width,height:r.height};
    });
    if (box.width <= 0 || box.height <= 0 || box.x < 0 || box.y < 0) continue;
    return captureVisual(page, name, {...details, privacy:'status_label_only', kind:'DOM assertion screenshot'}, {clip:box});
  }
  return {...details, status:'NOT_CAPTURED', reason:'Safe status label not found', runId:process.env.UI_BUSINESS_RUN_ID};
}
