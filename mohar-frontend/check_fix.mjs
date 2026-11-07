import { canApplyFix, applyFixToText } from './src/utils/fixes.js';

const a = applyFixToText('Start investing today. Follow us!', 'Start investing today.', 'Start investing today. Investments are subject to market risks.');
console.log('CHECK 1 sentence is kept          :', a === 'Start investing today. Investments are subject to market risks. Follow us!' ? 'PASS' : 'FAIL', '->', a);
console.log('CHECK 2 refuses when text is gone :', canApplyFix('already rewritten text', 'old sentence') === false ? 'PASS' : 'FAIL');
console.log('CHECK 3 short fix is not skipped  :', applyFixToText('Hey bro, great news', 'bro', 'friends') === 'Hey friends, great news' ? 'PASS' : 'FAIL');
console.log('CHECK 4 dollar signs are safe     :', applyFixToText('pay now', 'now', 'for $& only') === 'pay for $& only' ? 'PASS' : 'FAIL');
