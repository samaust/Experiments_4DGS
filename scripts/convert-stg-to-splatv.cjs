// Run the pinned viewer's PLY conversion without a browser or GPU.
// The worker code remains upstream; only file I/O and container assembly live here.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createHash } = require('node:crypto');
const { parseArgs } = require('node:util');

const { values } = parseArgs({ options: {
  viewer: { type: 'string' }, ply: { type: 'string' },
  cameras: { type: 'string' }, output: { type: 'string' },
} });
for (const key of ['viewer', 'ply', 'cameras', 'output']) {
  if (!values[key]) throw new Error(`Missing --${key}`);
}
const revision = '8b313fea028d32f3c978f06b0a8bd2050b03ff28';
const source = fs.readFileSync(path.join(values.viewer, 'hybrid.js'), 'utf8');
const start = source.indexOf('function createWorker(self) {');
const end = source.indexOf('\nconst vertexShaderSource =', start);
if (start < 0 || end < 0) throw new Error('Unsupported upstream worker layout');
const workerSource = source.slice(start, end);
if (createHash('sha256').update(workerSource).digest('hex') !== '75444eeded713d04a3a359d46361120bfb5c5288a9583dd0ec38b9b7ccd52661') {
  throw new Error('Worker differs from the pinned upstream conversion');
}
const cameras = JSON.parse(fs.readFileSync(values.cameras, 'utf8'));
if (!Array.isArray(cameras) || cameras.length === 0) throw new Error('Expected saved cameras');
const ply = fs.readFileSync(values.ply);
if (!ply.subarray(0, 100).toString().startsWith('ply\nformat binary_little_endian 1.0\n')) {
  throw new Error('The pinned converter requires binary little-endian PLY');
}
const headerEnd = ply.indexOf('end_header\n');
if (headerEnd < 0 || headerEnd > 10240) throw new Error('Invalid PLY header');
const match = /element vertex (\d+)\n/.exec(ply.subarray(0, headerEnd).toString());
if (!match || Number(match[1]) <= 0) throw new Error('No Gaussian vertices');
const count = Number(match[1]);
let converted;
const worker = { postMessage: message => { converted = message; } };
const quiet = { log() {}, time() {}, timeEnd() {} };
const createWorker = vm.runInNewContext(`(${workerSource})`, { TextDecoder, console: quiet });
createWorker(worker);
worker.onmessage({ data: { ply: ply.buffer.slice(ply.byteOffset, ply.byteOffset + ply.byteLength) } });
if (!converted?.texdata || converted.texdata.byteLength < count * 64) throw new Error('Incomplete conversion');
const { texdata, texwidth, texheight } = converted;
const metadata = Buffer.from(JSON.stringify([{ type: 'splat', size: texdata.byteLength, texwidth, texheight, cameras }]));
const magic = Buffer.alloc(8);
magic.writeUInt32LE(0x674b, 0);
magic.writeUInt32LE(metadata.length, 4);
const output = Buffer.concat([magic, metadata, Buffer.from(texdata.buffer)]);
fs.mkdirSync(path.dirname(path.resolve(values.output)), { recursive: true });
fs.writeFileSync(values.output, output, { flag: 'wx' });
console.log(JSON.stringify({ output: values.output, vertices: count, cameras: cameras.length, bytes: output.length, converterRevision: revision }));
