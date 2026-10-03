// SahiDaam WhatsApp bridge (whatsapp-web.js) -> FastAPI POST /message
// Free, handles text + voice notes, any phone can message the linked number.
// UNOFFICIAL: WhatsApp doesn't allow unofficial clients. Link a SPARE SIM only, never a personal number.
//
// Run (repo root, backend on :8000):  npm install   then   node bridge.js
// Text  -> POST /message JSON {sender, text}
// Voice -> POST /message multipart: sender + audio (voice.ogg, audio/ogg); the backend transcribes it (Groq)
//          and its reply already starts with "Heard: ..." when the voice note wasn't fully understood.

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000/message';
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const APOLOGY = 'माफ करा, काहीतरी चूक झाली. कृपया पुन्हा पाठवा. / माफ़ कीजिए, कुछ गड़बड़ हुई। कृपया फिर से भेजें।';

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: '.wwebjs_auth' }), // remembers the login across restarts
  puppeteer: {
    headless: true,
    executablePath: CHROME, // the installed Chrome; no Chromium download needed
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

client.on('qr', (qr) => {
  console.log('On the spare phone: WhatsApp > Settings > Linked devices > Link a device, then scan:');
  qrcode.generate(qr, { small: true });
});
client.on('ready', () => console.log('✅ Bridge ready. Message the spare number from any phone.'));
client.on('auth_failure', (m) => console.error('Auth failure:', m));
client.on('disconnected', (reason) => console.error('Disconnected:', reason));

async function ask(msg) {
  if (msg.type === 'chat') {
    return fetch(BACKEND, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender: msg.from, text: msg.body }),
    });
  }
  if (msg.type === 'ptt' || msg.type === 'audio') { // ptt = voice note
    const media = await msg.downloadMedia();
    if (!media || !media.data) throw new Error('voice note could not be downloaded');
    const form = new FormData();
    form.append('sender', msg.from);
    form.append('audio', new Blob([Buffer.from(media.data, 'base64')], { type: 'audio/ogg' }), 'voice.ogg');
    console.log(`voice note from ${msg.from.slice(-8)}: ${Math.round(media.data.length * 0.75)} bytes`);
    return fetch(BACKEND, { method: 'POST', body: form });
  }
  return null; // images, stickers, ...: ignored
}

client.on('message', async (msg) => {
  // only 1:1 chats; skip groups, status updates and channels
  const isDirectChat = msg.from.endsWith('@c.us') || msg.from.endsWith('@lid');
  if (msg.fromMe || msg.isStatus || !isDirectChat) return;
  try {
    const res = await ask(msg);
    if (!res) return;
    if (!res.ok) throw new Error(`backend returned ${res.status}`);
    const { reply, transcript } = await res.json();
    if (transcript !== undefined) console.log(`  heard: ${transcript}`);
    if (reply) await client.sendMessage(msg.from, reply);
  } catch (err) {
    console.error(`Failed for ${msg.from}:`, err.message);
    try { await client.sendMessage(msg.from, APOLOGY); } catch (_) { /* nothing more to do */ }
  }
});

client.initialize();
