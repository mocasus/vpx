#!/usr/bin/env node
const { execSync, spawnSync } = require('child_process');
const crypto = require('crypto');
const token = process.argv[2] || crypto.randomBytes(16).toString('hex');
if (spawnSync('which', ['docker']).status !== 0) {
  console.error('Docker not found. Install: https://docs.docker.com/get-docker/');
  process.exit(1);
}
execSync('docker rm -f vpx 2>/dev/null', { stdio: 'ignore' });
const r = spawnSync('docker', [
  'run', '-d', '--name', 'vpx',
  '--cap-add', 'NET_ADMIN', '--device', '/dev/net/tun',
  '-p', '1080:1080', '-p', '8080:8080', '-p', '8000:8000',
  '-e', `API_TOKEN=${token}`, '--restart', 'unless-stopped',
  'mocasus/vpx:latest'
], { stdio: 'inherit' });
if (r.status === 0) {
  console.log(`\nVPX started!\nAPI: http://localhost:8000\nToken: ${token}` +
              `\nSOCKS5: localhost:1080\nHTTP: localhost:8080`);
}
