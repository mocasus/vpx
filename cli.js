#!/usr/bin/env node
const { execSync, spawnSync } = require('child_process');
const crypto = require('crypto');
const token = process.argv[2] || crypto.randomBytes(16).toString('hex');

if (spawnSync('which', ['docker']).status !== 0) {
  console.error('Docker not found. Install: https://docs.docker.com/get-docker/');
  process.exit(1);
}

execSync('docker rm -f vpnx 2>/dev/null', { stdio: 'ignore' });
const r = spawnSync('docker', [
  'run', '-d', '--name', 'vpnx',
  '--cap-add', 'NET_ADMIN', '--device', '/dev/net/tun',
  '-p', '1080:1080', '-p', '8080:8080', '-p', '8000:8000',
  '-e', `API_TOKEN=${token}`, '--restart', 'unless-stopped',
  'mocasus/vpnx:latest'
], { stdio: 'inherit' });

if (r.status === 0) {
  console.log('');
  console.log('╔══════════════════════════════════════════╗');
  console.log('║          VPNX v2.0.0 — Ready!             ║');
  console.log('╠══════════════════════════════════════════╣');
  console.log(`║  API:     http://localhost:8000           ║`);
  console.log(`║  Token:   ${token.padEnd(32)}║`);
  console.log('║  SOCKS5:  localhost:1080                 ║');
  console.log('║  HTTP:    localhost:8080                 ║');
  console.log('╠══════════════════════════════════════════╣');
  console.log('║  Quick start:                            ║');
  console.log('║  curl -X POST localhost:8000/connect \\    ║');
  console.log('║    -H "Authorization: Bearer ' + token.slice(0, 8) + '..."      ║');
  console.log('╚══════════════════════════════════════════╝');
}
