// Browser fixture for the local status editor. Uses an isolated test database.
import { chromium } from 'playwright';
const browser = await chromium.launch({headless: true});
try {
  const page = await browser.newPage();
  await page.goto(process.env.QA_STATUS_URL);
  await page.getByText('本地状态已载入。', {exact: false}).waitFor();
  const row = page.locator('tr').filter({has: page.getByText('ISOP-2028 合规统计调整', {exact: true})});
  await row.locator('[data-channel="ui"]').click();
  await page.locator('#status').fill('FAT人工通过');
  await page.locator('#author').fill('浏览器夹具测试人');
  await page.locator('#source').fill('离线功能夹具');
  await page.locator('#reason').fill('测试保存与页面刷新');
  await page.locator('#save').click();
  await page.locator('#editor').waitFor({state: 'hidden'});
  await page.reload();
  await row.locator('td').nth(2).getByText('FAT人工通过', {exact: true}).waitFor();
  if (!(await row.textContent()).includes('FAIL')) throw new Error('Manual save erased API failure');
  await page.locator('#search').fill('ISOP-2028');
  if (await page.locator('tbody tr').count() !== 1) throw new Error('Search failed');
  await page.setViewportSize({width: 390, height: 844});
  if (!(await page.locator('#rows').isVisible())) throw new Error('Mobile status table unavailable');
  console.log('status browser fixture PASS');
} finally {
  await browser.close();
}
