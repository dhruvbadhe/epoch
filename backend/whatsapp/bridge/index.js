// QR-linked WhatsApp bridge (whatsapp-web.js). It only moves messages:
//   message in -> POST /message on the backend -> send the reply back.
// No logic lives here. Run:  npm install && npm start   (Node 20.12 or newer)
//
// This is an unofficial linked-device bridge for the prototype. A real deployment would use
// the official WhatsApp Business API (see ../cloud_api.py).
const path = require('path');

try {
  process.loadEnvFile(path.join(__dirname, '..', '..', '..', '.env'));
} catch {
  // no .env yet: defaults below apply and nobody is on the allow-list
}

const BACKEND_URL = (process.env.BACKEND_URL || 'http://localhost:8000').replace(/\/+$/, '');
const digits = (value) => String(value || '').replace(/\D/g, '');
const ALLOWED = new Set((process.env.ALLOWED_NUMBERS || '').split(',').map(digits).filter(Boolean));
const mask = (number) => '…' + number.slice(-4);

const handled = [];                       // ids of messages already answered
function alreadyHandled(id) {
  if (handled.includes(id)) return true;
  handled.push(id);
  if (handled.length > 500) handled.shift();
  return false;
}

async function reply(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.reply) {
    throw new Error(`backend ${response.status}: ${data.error || 'no reply'}`);
  }
  return data.reply;
}

async function forwardText(sender, text) {
  return reply(await fetch(`${BACKEND_URL}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sender, text }),
  }));
}

async function forwardVoice(sender, audioBuffer, mimetype) {
  const form = new FormData();
  form.append('sender', sender);
  form.append('audio', new Blob([audioBuffer], { type: (mimetype || 'audio/ogg').split(';')[0] }), 'voice.ogg');
  return reply(await fetch(`${BACKEND_URL}/message`, { method: 'POST', body: form }));
}

async function onMessage(client, msg) {
  // Ignore our own messages, status updates and group chats.
  if (msg.fromMe || msg.isStatus || msg.from === 'status@broadcast' || msg.from.endsWith('@g.us')) return;
  const isVoice = msg.type === 'ptt' || msg.type === 'audio';
  if (msg.type !== 'chat' && !isVoice) return;
  if (alreadyHandled(msg.id._serialized)) return;

  // Reply only to the team's test numbers.
  const contact = await msg.getContact().catch(() => null);
  const sender = digits((contact && contact.number) || msg.from.split('@')[0]);
  if (!ALLOWED.has(sender)) {
    console.log(`ignored message from ${mask(sender)} (not in ALLOWED_NUMBERS)`);
    return;
  }

  let text;
  if (isVoice) {
    const media = await msg.downloadMedia();
    if (!media) throw new Error('voice note could not be downloaded');
    text = await forwardVoice(sender, Buffer.from(media.data, 'base64'), media.mimetype);
  } else {
    text = await forwardText(sender, msg.body);
  }
  await client.sendMessage(msg.from, text);
  console.log(`${new Date().toISOString()} ${isVoice ? 'voice' : 'text'} from ${mask(sender)} answered`);
}

function start() {
  const { Client, LocalAuth } = require('whatsapp-web.js');
  const qrcode = require('qrcode-terminal');

  const client = new Client({
    authStrategy: new LocalAuth({ dataPath: path.join(__dirname, '.wwebjs_auth') }),   // scan the QR once
    puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] },
  });
  client.on('qr', (qr) => {
    console.log('Scan with WhatsApp > Linked devices > Link a device:');
    qrcode.generate(qr, { small: true });
  });
  client.on('ready', () => {
    const who = [...ALLOWED].map(mask).join(', ') || 'NOBODY (set ALLOWED_NUMBERS in .env)';
    console.log(`WhatsApp bridge ready. Backend: ${BACKEND_URL}. Replying to: ${who}`);
  });
  client.on('auth_failure', (message) => console.error('WhatsApp login failed:', message));
  client.on('disconnected', (reason) => console.error('WhatsApp disconnected:', reason));
  client.on('message', (msg) => {
    onMessage(client, msg).catch((err) => console.error('message not answered:', err.message));
  });
  client.initialize();
}

if (require.main === module) start();

module.exports = { forwardText, forwardVoice, onMessage, alreadyHandled, ALLOWED, BACKEND_URL };
