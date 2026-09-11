// Fixed asset execution. No discovery, generated code, force clicks or action retries.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
import { decodeBusinessBody, readBusinessRequest } from './business-response.mjs';

export function locate(root, spec) {
  if (spec.scope) root = locate(root, spec.scope);
  let target;
  if (spec.testId) target = root.getByTestId(spec.testId);
  else if (spec.role) target = root.getByRole(spec.role, { name: spec.name, exact: true });
  else if (spec.label) target = root.getByLabel(spec.label, { exact: true });
  else if (spec.text !== undefined && !spec.css) target = root.getByText(spec.text, { exact: true });
  else if (spec.css) target = root.locator(spec.css);
  else throw new Error('unknown locator');
  if (spec.hasText !== undefined) target = target.filter({ hasText: spec.hasText });
  if (spec.exactText !== undefined) target = target.filter({hasText:new RegExp('^\\s*'+spec.exactText.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\s*$')});
  if (spec.index !== undefined) target = target.nth(spec.index);
  return target;
}
function safeNumbers(value) {
  if (typeof value === 'number' && Number.isInteger(value) && !Number.isSafeInteger(value)) throw new Error('unsafe integer identity');
  if (value && typeof value === 'object') Object.values(value).forEach(safeNumbers);
  return value;
}
const get = (value, key) => key.split('.').reduce((v,k) => v?.[k], value);
export function matches(request, origin, route, match = {}) {
  const url = new URL(request.url());
  if (url.origin !== origin || url.pathname !== route.path || request.method() !== route.method) return false;
  if (!Object.keys(match).length) return true;
  try {
    const body = safeNumbers(readBusinessRequest(request));
    return Object.entries(match).every(([key, value]) => String(get(body,key)) === String(value));
  } catch { return false; }
}
export class RequirementUI {
  constructor(config) { this.config = config; this.sessions = new Map(); }
  async session(actor, auth) {
    if (this.sessions.has(actor)) return this.sessions.get(actor);
    this.browser ||= await chromium.launch({ headless: true });
    const context = await this.browser.newContext({ viewport: { width: 1365, height: 900 }, serviceWorkers: 'block', ignoreHTTPSErrors: this.config.insecure });
    const page = await context.newPage();
    page.setDefaultTimeout(this.config.timeout_ms);
    page.setDefaultNavigationTimeout(30000);
    const s = { context, page, actor, denied: [], privateHeaders: {}, owned: {}, active: null };
    this.sessions.set(actor,s);
    await context.route('**/*', async route => {
      const req = route.request(), url = new URL(req.url());
      const origin = this.config.origin;
      const contract = Object.values(this.config.contracts).find(r => r.service === 'admin' && r.path === url.pathname && r.method === req.method());
      if (url.origin === origin && contract?.write) {
        const key = contract.ownership;
        const own = !key || (s.owned[key] || []).includes(String(readBusinessRequest(req)?.[key]));
        const allowed = !s.sent && s.active?.contract && this.config.contracts[s.active.contract] === contract && own && this.config.scopes.includes(contract.scope);
        if (!allowed) { s.denied.push({ path: contract.path, reason: 'write scope/ownership/active step' }); return route.abort(); }
        s.sent = true;
        // Intent is durable before the browser's business request leaves this process.
        fs.appendFileSync(path.join(this.config.folder,'private-ui-intents.jsonl'),JSON.stringify({case:s.caseId,step:s.stepId,actor,path:contract.path,phase:'INTENT'})+'\n',{mode:0o600});
      } else {
        const allowed = this.config.assets.requests.some(r => (r.service ? origin : r.origin) === url.origin && r.method === req.method() && new RegExp(r.path_pattern).test(url.pathname));
        if (!allowed) { s.denied.push({ path: url.pathname, reason: 'unregistered route' }); return route.abort(); }
      }
      if (url.origin === origin && url.pathname.startsWith('/admin/')) {
        const headers = req.headers();
        if (headers.t) s.privateHeaders = Object.fromEntries(['t','x-device-id','client-id','client-version','lang','d'].filter(k => headers[k]).map(k => [k,headers[k]]));
      }
      return route.continue();
    });
    await page.goto(this.config.origin + this.config.assets.auth.path);
    for (const step of this.config.assets.auth.steps) {
      const target = locate(page,step.target);
      if (step.op === 'fill') await target.fill(auth[step.key]);
      else await target.click();
    }
    await locate(page,this.config.assets.auth.ready).waitFor();
    return s;
  }
  async execute(input) {
    const { actor, step, auth, owned, caseId } = input;
    let s;
    try {
      s = await this.session(actor,auth);
      s.owned = owned; s.caseId = caseId; s.stepId = step.id;
      const page = s.page;
      const out = { checks: { completed: true, policy: true }, summary: 'UI动作和显式观测完成' };
      let target = step.target ? locate(page,step.target) : null;
      if (step.target?.index !== undefined) {
        const {index, ...base} = step.target;
        if (await locate(page,base).count() !== base.expectedCount) throw new Error('document slot count mismatch');
      }
      const rule = step.response && this.config.contracts[step.response.contract];
      const requests = [], responses = [];
      const onRequest = request => { if (matches(request,this.config.origin,rule,step.response.match)) requests.push(request); };
      const onResponse = response => { if (requests.includes(response.request())) responses.push(response); };
      if (rule) { page.on('request',onRequest); page.on('response',onResponse); }
      s.active = step.response; s.sent = false;
      try {
        switch (step.op) {
          case 'open': await page.goto(this.config.origin + step.path); await locate(page,step.ready).waitFor(); break;
          case 'click': await target.click(); break;
          case 'fill': await target.fill(String(step.value)); break;
          case 'select': await target.selectOption({label:String(step.value)}); break;
          case 'check': await target.setChecked(step.value); break;
          case 'upload': await target.setInputFiles({name:'qa.png',mimeType:'image/png',buffer:Buffer.from(input.png,'base64')}); break;
          case 'wait':
            await target.waitFor({state:step.property === 'value' ? 'visible' : step.value || 'visible'});
            if (step.property === 'value') await page.waitForFunction(({el,value}) => el.value === value,{el:await target.elementHandle(),value:step.value});
            break;
          case 'press': await page.keyboard.press(step.value); break;
          case 'scroll': await target.scrollIntoViewIfNeeded(); break;
          case 'observe':
            if (step.property === 'count') {
              if (step.expect?.some(c => c.path === 'value' && c.op === 'eq' && c.value > 0)) await target.waitFor({state:'visible'});
              out.value = await target.count();
            }
            else if (step.property === 'url') out.value = page.url();
            else {
              await target.waitFor({state:'visible'});
              if (step.property === 'disabled') out.value = await target.isDisabled();
              else if (step.property === 'text') out.value = (await target.innerText()).trim();
              else if (step.property === 'value') out.value = await target.inputValue();
              else if (step.property === 'loaded') {
                await page.waitForFunction(img => img.complete && img.naturalWidth > 0, await target.elementHandle());
                out.value = await target.evaluate(img => img.complete && img.naturalWidth > 0);
              } else out.value = await target.isVisible();
            }
            break;
          default: throw new Error('unknown operation');
        }
        if (rule) {
          const deadline = Date.now() + (step.response.none ? step.response.window_ms : this.config.timeout_ms);
          while ((step.response.none || responses.length === 0) && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve,20));
          out.request_count = requests.length;
          if (!step.response.none) {
            if (responses.length !== 1 || requests.length !== 1) throw new Error('missing or multiple correlated responses');
            out.http = responses[0].status(); out.body = safeNumbers(decodeBusinessBody(await responses[0].body()));
          }
        }
        if (s.denied.length) throw new Error('request-policy');
        out.checks.policy = true;
        out.privateHeaders = s.privateHeaders;
        return out;
      } finally {
        if (rule) { page.off('request',onRequest); page.off('response',onResponse); }
        s.active = null;
      }
    } catch (error) {
      const obstructed = /intercepts pointer events/.test(String(error.message));
      const result = { checks:{completed:false,policy:!s?.denied.length}, execution_error: !obstructed,
        summary: obstructed ? '真实点击被其他元素遮挡，未执行强制点击' : 'UI执行未完成；定位/登录/响应证据见本轮UI诊断',
        error_category: obstructed ? 'pointer-intercepted' : s?.denied.length ? 'request-policy' : error.name === 'TimeoutError' ? 'ui-timeout' : 'ui-execution',
        privateHeaders:s?.privateHeaders || {} };
      if (s) {
        const name = `${caseId}-${step.id}.png`;
        // Mask all personal-data-bearing surfaces; synthetic inputs/images are masked too.
        await s.page.screenshot({path:path.join(this.config.folder,name),mask:[s.page.locator('table:visible,header:visible,input:visible,textarea:visible,img:visible,.ant-descriptions:visible,aside:visible')]}).then(()=>{result.evidence=name;}).catch(()=>{});
        if (obstructed && step.target) {
          const target = locate(s.page,step.target);
          result.obstruction = await target.evaluate(el => {
            const r = el.getBoundingClientRect(), hit = document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
            return {target:{x:r.x,y:r.y,width:r.width,height:r.height},hitTag:hit?.tagName,hitClass:typeof hit?.className === 'string' ? hit.className : '',covered:!el.contains(hit)};
          }).catch(()=>null);
          const r = result.obstruction?.target;
          if (r && r.width>0 && r.height>0) {
            const clip = {x:Math.max(0,r.x-10),y:Math.max(0,r.y-10),width:Math.min(r.width+100,1365-Math.max(0,r.x-10)),height:Math.min(r.height+20,900-Math.max(0,r.y-10))};
            const crop = `${caseId}-${step.id}-target.png`;
            await s.page.screenshot({path:path.join(this.config.folder,crop),clip}).then(()=>{result.evidence=crop;}).catch(()=>{});
          }
        }
        fs.appendFileSync(path.join(this.config.folder,'ui-diagnostics.jsonl'),JSON.stringify({case:caseId,step:step.id,category:result.error_category,denied:s.denied,evidence:result.evidence,obstruction:result.obstruction})+'\n',{mode:0o600});
      }
      return result;
    }
  }
  async close() { await this.browser?.close(); this.sessions.clear(); }
}
