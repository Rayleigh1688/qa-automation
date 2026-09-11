// Declarative UI discovery/execution. No generated JavaScript is evaluated.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
import { loadEnv, requiredEnv } from './env.mjs';
import { decodeBusinessBody } from './business-response.mjs';

export async function runLegacyUi(folderArg, mode) {
const folder = path.resolve(folderArg || '.');
const read = name => JSON.parse(fs.readFileSync(path.join(folder, name), 'utf8'));
const write = (name, data) => fs.writeFileSync(path.join(folder, name), JSON.stringify(data, null, 2));
const config = read('ui-config.json');
loadEnv(config.env_file);
if (!['scan', 'run'].includes(mode)) throw new Error('scan or run required');
if (!config.pages || !Object.keys(config.pages).length || !config.auth?.ready) throw new Error('pages and authenticated ready locator required');
if (!Array.isArray(config.requests) || !config.requests.length) throw new Error('request allowlist required');
const rules = config.requests.map(r => {
  if (!r.id || !r.path_pattern.startsWith('^') || !r.path_pattern.endsWith('$') || new URL(r.origin).protocol !== 'https:') throw new Error('invalid request rule');
  return { ...r, pattern: new RegExp(r.path_pattern) };
});
const match = request => {
  const u = new URL(request.url());
  return rules.find(r => r.origin === u.origin && r.method === request.method() && r.pattern.test(u.pathname));
};
function locator(page, spec) {
  if (spec.testId) return page.getByTestId(spec.testId);
  if (spec.role) return page.getByRole(spec.role, { name: spec.name, exact: true });
  if (spec.label) return page.getByLabel(spec.label, { exact: true });
  if (spec.css) {
    const target = page.locator(spec.css);
    return spec.text === undefined ? target : target.filter({ hasText: new RegExp('^\\s*' + spec.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*$') });
  }
  throw new Error('unknown locator');
}
const browser = await chromium.launch({ headless: true });
async function session(info) {
  const context = await browser.newContext({ viewport: config.viewport || { width: 1365, height: 900 }, serviceWorkers: 'block',
    ignoreHTTPSErrors: config.ignore_https_errors === true });
  const network = [], denied = [];
  await context.route('**/*', async route => {
    if (!match(route.request())) {
      denied.push({ method: route.request().method(), resource: route.request().resourceType() });
      return route.abort();
    }
    return route.continue();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(config.action_timeout_ms || 10000);
  page.setDefaultNavigationTimeout(30000);
  page.on('response', response => {
    const rule = match(response.request());
    if (!rule) return;
    const entry = { rule: rule.id, method: response.request().method(), status: response.status() };
    network.push(entry);
    if (rule.business_success === true) {
      void (async () => {
        try {
          const body = await response.body();
          const decoded = decodeBusinessBody(body);
          entry.business_success = decoded?.status === true;
        } catch { entry.business_success = null; entry.decode_error = true; }
      })();
    }
  });
  try {
    if (config.auth.url) {
      await page.goto(config.auth.url, { waitUntil: 'domcontentloaded' });
      for (const step of config.auth.steps || []) {
        const target = locator(page, step.target);
        if (step.op === 'fill') await target.fill(requiredEnv(step.value_env));
        else if (step.op === 'click') await target.click();
        else if (step.op === 'visible') await target.waitFor({ state: 'visible' });
        else throw new Error('unsupported authentication action');
      }
      await locator(page, config.auth.ready).waitFor({ state: 'visible' });
    }
    await page.goto(info.url, { waitUntil: 'domcontentloaded' });
    await locator(page, config.auth.ready).waitFor({ state: 'visible' });
    for (const step of info.steps || []) {
      if (step.op !== 'click') throw new Error('unsupported page setup action');
      await locator(page, step.target).click();
    }
    return { context, page, network, denied };
  } catch (error) {
    await context.close();
    throw new Error('fresh UI authentication/navigation failed');
  }
}
try {
  if (mode === 'scan') {
    const pages = {};
    for (const [key, info] of Object.entries(config.pages)) {
      const s = await session(info);
      try {
        await locator(s.page, info.ready).waitFor({ state: 'visible' });
        const elements = await s.page.locator('button, a, input:not([type=hidden]), select, textarea, [role=button], [role=tab], [data-testid]').evaluateAll(nodes => nodes.slice(0, 250).map((e, i) => {
          const tag = e.tagName.toLowerCase();
          const name = (e.getAttribute('aria-label') || e.labels?.[0]?.textContent || ((tag === 'button' || tag === 'a' || ['button', 'tab'].includes(e.getAttribute('role'))) ? e.textContent : '') || '').trim().slice(0, 100);
          const id = e.getAttribute('id'), testId = e.getAttribute('data-testid');
          let target = null;
          if (testId) target = { testId };
          else if (e.getAttribute('role') === 'tab' && /-tab-(pending|reviewed)$/.test(id || '')) target = { css: '[role="tab"][id$="' + id.match(/-tab-(pending|reviewed)$/)[0] + '"]' };
          else if (id) target = { css: '#' + CSS.escape(id) };
          else if (name && tag === 'button' && !e.getAttribute('aria-label') && e.querySelector('[role=img][aria-label], img[alt]')) target = { css: 'button', text: name };
          else if (name && ['button', 'a'].includes(tag)) target = { role: tag === 'a' ? 'link' : 'button', name };
          else if (e.labels?.length && name) target = { label: name };
          return { id: 'E' + (i + 1), tag, name, type: e.getAttribute('type'), target, disabled: Boolean(e.disabled) };
        }).filter(e => e.target));
        pages[key] = { elements, network: s.network, blocked_requests: s.denied.length };
      } finally { await s.context.close(); }
    }
    write('scan.json', { pages });
  } else {
    const plan = read('ui-plan.json'), scan = read('scan.json');
    const results = [];
    // Defense in depth: the Python validator runs first; reject unknown operations here too.
    for (const c of plan.cases) {
      const result = { id: c.id, case_ids: [c.case_id], status: 'BLOCKED', detail: c.blocked || '', assertions: [], network: [] };
      results.push(result);
      if (c.blocked) continue;
      let s, stepNumber = 0, lastActionOffset = 0;
      try {
        if (!config.pages[c.page] || !scan.pages[c.page]) throw new Error('unknown page');
        s = await session(config.pages[c.page]);
        await locator(s.page, config.pages[c.page].ready).waitFor({ state: 'visible' });
        for (const step of c.steps) {
          stepNumber += 1;
          if (step.op === 'assert_response') {
            const rule = rules.find(r => r.id === step.target);
            const check = () => s.network.slice(lastActionOffset).some(r => r.rule === step.target && r.status === Number(step.value) && (rule?.business_success !== true || r.business_success === true));
            const deadline = Date.now() + (config.action_timeout_ms || 10000);
            while (!check() && Date.now() < deadline) await s.page.waitForTimeout(50);
            if (!check()) {
              const observed = s.network.slice(lastActionOffset).filter(r => r.rule === step.target);
              if (!observed.length || observed.some(r => r.decode_error)) throw new Error('response unavailable for assertion');
              throw Object.assign(new Error('response assertion failed'), { assertionFailure: true });
            }
            result.assertions.push({ op: step.op, target: step.target, expected: step.value, matched: true });
            continue;
          }
          const element = scan.pages[c.page].elements.find(e => e.id === step.target);
          if (!element) throw new Error('unknown target');
          const target = locator(s.page, element.target);
          if (!step.op.startsWith('assert_')) lastActionOffset = s.network.length;
          switch (step.op) {
            case 'click': await target.click(); break;
            case 'fill': await target.fill(step.value); break;
            case 'select': await target.selectOption({ label: step.value }); break;
            case 'check': await target.check(); break;
            case 'uncheck': await target.uncheck(); break;
            case 'assert_visible': await target.waitFor({ state: 'visible' }); break;
            case 'assert_text': {
              await target.waitFor({ state: 'visible' });
              if ((await target.innerText()).trim() !== step.value) throw Object.assign(new Error('text mismatch'), { assertionFailure: true });
              break;
            }
            case 'assert_enabled': {
              await target.waitFor({ state: 'visible' });
              if (await target.isEnabled() !== (step.value === 'true')) throw Object.assign(new Error('enabled mismatch'), { assertionFailure: true });
              break;
            }
            case 'assert_count': if (await target.count() !== Number(step.value)) throw Object.assign(new Error('count mismatch'), { assertionFailure: true }); break;
            default: throw new Error('unsupported step');
          }
          if (step.op.startsWith('assert_')) result.assertions.push({ op: step.op, target: step.target, expected: step.value, matched: true });
        }
        if (!result.assertions.length) throw new Error('no assertions');
        result.status = s.denied.length ? 'BLOCKED' : 'PASS';
        result.detail = s.denied.length ? 'Request policy blocked traffic; inspect local configuration' : 'Declared assertions passed';
      } catch (error) {
        result.status = s?.denied.length ? 'BLOCKED' : error.assertionFailure ? 'FAIL' : 'ERROR';
        result.failed_step = stepNumber;
        if (error.assertionFailure && stepNumber && c.steps[stepNumber - 1]?.op.startsWith('assert_')) {
          const failed = c.steps[stepNumber - 1];
          result.assertions.push({ op: failed.op, target: failed.target, expected: failed.value, matched: false });
        }
        const operation = c.steps[stepNumber - 1]?.op || 'prepare';
        result.detail = `Step ${stepNumber} ${operation}: ${result.status === 'FAIL' ? 'assertion mismatch' : 'execution not completed'}; ${result.assertions.filter(a => a.matched).length} assertions passed`;
      } finally {
        if (s) {
          result.network = s.network;
          result.blocked_requests = s.denied.length;
          await s.context.close();
        }
        write('ui-result.json', { results });
      }
    }
    write('ui-result.json', { results });
    if (results.some(r => r.status !== 'PASS')) process.exitCode = 1;
  }
} catch {
  console.error('UI stage failed; raw error and page contents suppressed');
  process.exitCode = 1;
} finally {
  await browser.close();
}

}
