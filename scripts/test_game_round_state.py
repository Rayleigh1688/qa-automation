import subprocess
import unittest


class GameRoundGuards(unittest.TestCase):
    def test_visual_and_paid_evidence_fail_closed(self):
        result = subprocess.run(['node', '--input-type=module', '-e', r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {classifyRound,GameRoundState} from './ui/framework/game-round-state.mjs';
import {verifyPaidDelta} from './ui/framework/game-paid-bets.mjs';
const c=JSON.parse(fs.readFileSync('ui/data/client-game-actions.json')).games[0].roundState;
const observation={mask:c.readyMasks[0],buttonText:'HOLD FOR TURBO',stable:true,freeBackground:false};
assert.equal(classifyRound(observation,c),'ready');
for (const patch of [{buttonText:'8 FREESPINS'},{freeBackground:true}]) assert.equal(classifyRound({...observation,...patch},c),'free');
for (const patch of [{stable:false},{mask:'.'.repeat(1024)}]) assert.equal(classifyRound({...observation,...patch},c),'busy');
let shots=0;
const monitor=new GameRoundState({waitForTimeout:async()=>{},screenshot:async()=>{shots++;}},{...c,waitTimeoutMs:1});
monitor.observe=async()=> 'free';
await assert.rejects(monitor.waitReady(),/Free spins timeout/);assert.equal(shots,1);
const old=[{id:'old',bet_amount:100,status:1}];
const paid={id:'new',bet_amount:100,status:1};
assert.equal(verifyPaidDelta([...old,paid,{id:'payout',bet_amount:0,status:1}],old,1,100).accepted,true);
assert.equal(verifyPaidDelta(old,old,1,100).accepted,false);
assert.equal(verifyPaidDelta([...old,{...paid,status:0}],old,1,100).accepted,false);
assert.throws(()=>verifyPaidDelta([paid,{...paid,id:'extra'}],[],1,100),/Unexpected/);
assert.throws(()=>verifyPaidDelta([{...paid,bet_amount:1000}],[],1,100),/Unexpected/);
'''], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
