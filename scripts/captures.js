// Captures d'écran des pages principales (Edge sans fenêtre).
//   node scripts/captures.js [url_de_base] [dossier]
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
const base = process.argv[2] || 'http://127.0.0.1:8765';
const dossier = process.argv[3] || path.join(__dirname, '..', 'docs', 'captures');
fs.mkdirSync(dossier, { recursive: true });
const pages = [['accueil', '/', 1280, 2200], ['connecteurs', '/connecteurs', 1280, 1100],
  ['fiche', '/connecteurs/momo-xof-mcp', 1280, 2000], ['demandes', '/demandes', 1280, 900],
  ['carte', '/carte', 1280, 1500], ['mobile', '/', 390, 2400]];
for (const [nom, url, l, h] of pages) {
  const sortie = path.join(dossier, nom + '.png');
  execFileSync('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', `--window-size=${l},${h}`,
    `--user-data-dir=${process.env.TEMP}\\edge-mfa`, `--screenshot=${sortie}`, base + url,
  ], { stdio: 'ignore', timeout: 60000 });
  console.log(sortie);
}
