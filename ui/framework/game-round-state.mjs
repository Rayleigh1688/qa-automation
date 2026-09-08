import {saveVisualBuffer} from './visual-evidence.mjs';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
const execute = promisify(execFile);

export async function visualDependencies() {
  await execute('magick', ['-version']);
  await execute('tesseract', ['--version']);
}
function commandInput(command, args, input) {
  return new Promise((resolve, reject) => {
    const child = execFile(command, args, { encoding: 'buffer', timeout: 10000, maxBuffer: 8 * 1024 * 1024 }, (error, stdout) => error ? reject(new Error(`${command} visual check failed`)) : resolve(stdout));
    child.stdin.on('error', () => {});
    child.stdin.end(input);
  });
}
export async function imageMask(png) {
  const rgb = await commandInput('magick', ['png:-', '-resize', '32x32!', '-depth', '8', 'RGB:-'], png);
  return Array.from({length: 1024}, (_, i) => {
    const [r,g,b] = rgb.subarray(i*3,i*3+3);
    return r>210 && g>210 && b>210 ? 'W' : g>120 && g>r*1.3 && g>b*1.15 ? 'G' : '.';
  }).join('');
}
export function maskDistance(a,b) {
  if (a.length !== b.length || !a.length) return 1;
  return [...a].filter((c,i)=>c!==b[i]).length/a.length;
}
export function classifyRound({buttonText, mask, stable, freeBackground}, config) {
  if (new RegExp(config.freePattern, 'i').test(buttonText) || freeBackground) return 'free';
  const ready = config.readyMasks.some(reference => maskDistance(mask, reference) <= config.maxMaskDifference);
  return ready && stable ? 'ready' : 'busy';
}
function clip(page, ratios) {
  const {width,height}=page.viewportSize();
  return {x:width*ratios[0], y:height*ratios[1], width:width*ratios[2], height:height*ratios[3]};
}
async function ocr(png) {
  return String(await commandInput('tesseract', ['stdin','stdout','--psm','6'], png));
}
export class GameRoundState {
  constructor(page, config) { this.page=page; this.config=config; this.events=[]; this.visualEvidence={}; }
  async observe() {
    const c=this.config;
    const button=await this.page.screenshot({clip:clip(this.page,c.buttonRegion)});
    const reels1=await this.page.screenshot({clip:clip(this.page,c.reelsRegion)});
    await this.page.waitForTimeout(c.stabilityMs);
    const reels2=await this.page.screenshot({clip:clip(this.page,c.reelsRegion)});
    const background=await this.page.screenshot({clip:clip(this.page,c.backgroundRegion)});
    const rgb=await commandInput('magick',['png:-','-resize','1x1!','-depth','8','RGB:-'],background);
    const observations=await Promise.all([ocr(button),imageMask(button),commandInput('magick',['png:-','-resize','32x32!','-colorspace','gray','-depth','8','GRAY:-'],reels1),commandInput('magick',['png:-','-resize','32x32!','-colorspace','gray','-depth','8','GRAY:-'],reels2)]);
    const [buttonText,mask,a,b]=observations;
    const difference=Array.from(a).reduce((sum,value,i)=>sum+Math.abs(value-b[i]),0)/(a.length*255);
    const freeBackground=rgb[2]>rgb[1]+c.freeBlueMargin;
    const state=classifyRound({buttonText,mask,stable:difference<=c.maxReelsDifference,freeBackground},c);
    const maskDifference=Math.min(...c.readyMasks.map(reference=>maskDistance(mask,reference)));
    this.visualEvidence[state] = saveVisualBuffer(button, `game-button-${state}`, {title:`游戏按钮识别：${state}`, kind:'image assertion input', state, region:c.buttonRegion, maskDifference, maxMaskDifference:c.maxMaskDifference, reelsDifference:difference, maxReelsDifference:c.maxReelsDifference, assertion:`按钮特征差异 ${maskDifference.toFixed(4)} / 阈值 ${c.maxMaskDifference}；转轴差异 ${difference.toFixed(4)} / 阈值 ${c.maxReelsDifference}`});
    this.events.push({ts:Date.now(),state,maskDifference,reelsDifference:difference,freeText:new RegExp(c.freePattern,'i').test(buttonText),freeBackground});
    return state;
  }
  async enter(tap) {
    // Recognize the splash before tapping; never blindly tap a resumed round.
    const state=await this.observe();
    if(state==='ready'||state==='free') return;
    const splash=await this.page.screenshot();
    const text=await ocr(splash);
    if(new RegExp(this.config.startPattern,'i').test(text)) {this.visualEvidence.start=saveVisualBuffer(splash,'game-start-recognized',{title:'启动页识别后进入游戏',kind:'image assertion input',status:'PASS',assertion:'OCR 命中配置启动文字，随后点击进入'});await tap();this.events.push({ts:Date.now(),state:'start_tapped'});}
  }
  async waitReady() {
    const deadline=Date.now()+this.config.waitTimeoutMs;
    let freeSeen=false;
    while(Date.now()<deadline) {
      const state=await this.observe();
      freeSeen ||= state==='free';
      if(state==='ready' && Date.now()<=deadline) return;
      await this.page.waitForTimeout(Math.min(this.config.pollIntervalMs,Math.max(0,deadline-Date.now())));
    }
    const timeoutImage=await this.page.screenshot();
    if (timeoutImage) this.visualEvidence.timeout=saveVisualBuffer(timeoutImage,'game-state-timeout',{title:'游戏等待超时现场',kind:'failure screenshot',status:'FAIL',assertion:`等待 ${this.config.waitTimeoutMs}ms 未恢复；停止后续投注`});
    throw new Error(`${freeSeen?'Free spins':'Game readiness'} timeout after ${this.config.waitTimeoutMs}ms; no further bet`);
  }
  save() { fs.writeFileSync('ui/results/game-round-state.json',JSON.stringify({events:this.events,visualEvidence:this.visualEvidence,runId:process.env.UI_BUSINESS_RUN_ID},null,2)); }
}
