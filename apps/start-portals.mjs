import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const children = ['customer-web', 'management-web'].map(portal => spawn(process.execPath, [fileURLToPath(new URL(`./${portal}/server.mjs`, import.meta.url))], { stdio: 'inherit', env: process.env }));
let stopping = false;
function stop(code = 0) { if(stopping) return; stopping = true; for(const child of children) child.kill('SIGTERM'); process.exitCode = code; }
process.on('SIGINT', () => stop());
process.on('SIGTERM', () => stop());
for(const child of children) child.on('exit', code => { if(!stopping) stop(code || 1); });
