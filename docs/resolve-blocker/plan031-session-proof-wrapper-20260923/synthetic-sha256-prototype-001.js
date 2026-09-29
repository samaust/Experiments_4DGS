// Synthetic-only functions.exec isolate prototype. No host API or process.
function utf8(s) {
  let a = [];
  for (let i = 0; i < s.length; i++) {
    let c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      let d = s.charCodeAt(++i);
      if (!(d >= 0xdc00 && d <= 0xdfff)) throw Error("bad surrogate");
      c = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00);
    } else if (c >= 0xdc00 && c <= 0xdfff) throw Error("bad surrogate");
    if (c < 128) a.push(c);
    else if (c < 2048) a.push(192 | c >> 6, 128 | c & 63);
    else if (c < 65536) a.push(224 | c >> 12, 128 | c >> 6 & 63, 128 | c & 63);
    else a.push(240 | c >> 18, 128 | c >> 12 & 63, 128 | c >> 6 & 63, 128 | c & 63);
  }
  return a;
}

function sha256(s) {
  let b = utf8(s), n = b.length, pr = [], h = [], k = [];
  for (let v = 2; pr.length < 64; v++) {
    let prime = true;
    for (let d = 2; d * d <= v; d++) if (v % d === 0) { prime = false; break; }
    if (prime) {
      pr.push(v);
      if (h.length < 8) h.push((Math.sqrt(v) % 1 * 4294967296) >>> 0);
      k.push((Math.cbrt(v) % 1 * 4294967296) >>> 0);
    }
  }
  b.push(128);
  while (b.length % 64 !== 56) b.push(0);
  let bits = BigInt(n) * 8n;
  for (let i = 7; i >= 0; i--) b.push(Number(bits >> BigInt(i * 8) & 255n));
  let rr = (x, q) => x >>> q | x << 32 - q;
  for (let off = 0; off < b.length; off += 64) {
    let w = new Array(64);
    for (let i = 0; i < 16; i++) {
      let j = off + i * 4;
      w[i] = (b[j] << 24 | b[j + 1] << 16 | b[j + 2] << 8 | b[j + 3]) >>> 0;
    }
    for (let i = 16; i < 64; i++) {
      let x = w[i - 15], y = w[i - 2];
      w[i] = (w[i - 16] + (rr(x, 7) ^ rr(x, 18) ^ x >>> 3) +
        w[i - 7] + (rr(y, 17) ^ rr(y, 19) ^ y >>> 10)) >>> 0;
    }
    let [a, c, d, e, f, g, j, l] = h;
    for (let i = 0; i < 64; i++) {
      let t1 = (l + (rr(f, 6) ^ rr(f, 11) ^ rr(f, 25)) +
        (f & g ^ ~f & j) + k[i] + w[i]) >>> 0;
      let t2 = ((rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) +
        (a & c ^ a & d ^ c & d)) >>> 0;
      l = j; j = g; g = f; f = (e + t1) >>> 0;
      e = d; d = c; c = a; a = (t1 + t2) >>> 0;
    }
    let v = [a, c, d, e, f, g, j, l];
    for (let i = 0; i < 8; i++) h[i] = (h[i] + v[i]) >>> 0;
  }
  return h.map(v => v.toString(16).padStart(8, "0")).join("");
}

// Known vectors checked inside functions.exec; fixture hash independently checked with Python.
const vectors = [
  ["", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
  ["abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],
  ["a".repeat(1000000), "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"],
  ["A\r\nβ🚀\r\nquote ' and \\ slash\n", "5de7a1a3a31fedc2e302ffa2d173f8973b19cfe975e060557526126279ead35b"]
];
for (const [input, expected] of vectors) {
  if (sha256(input) !== expected) throw Error("SHA-256 vector mismatch");
}
