// Private stdin/stdout bridge; credentials never enter arguments or normal logs.
import readline from 'node:readline';
import { RequirementUI } from '../ui/framework/requirement-ui.mjs';
let runner;
try {
  for await (const line of readline.createInterface({input:process.stdin})) {
    try {
      const input = JSON.parse(line);
      if (input.op === 'init') { runner = new RequirementUI(input.config); process.stdout.write('{"ready":true}\n'); }
      else if (input.op === 'close') { await runner?.close(); process.stdout.write('{"closed":true}\n'); break; }
      else process.stdout.write(JSON.stringify(await runner.execute(input))+'\n');
    } catch { process.stdout.write('{"execution_error":true,"error_category":"worker-protocol"}\n'); }
  }
} finally { await runner?.close(); }
