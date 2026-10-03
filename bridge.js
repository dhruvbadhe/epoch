// SellSmart WhatsApp bridge (whatsapp-web.js) -> FastAPI /wa-bridge
// Free, handles text + voice notes, any phone can message the linked number.
// UNOFFICIAL: WhatsApp doesn't allow unofficial clients. Link a SPARE SIM only, never a personal number.
//
// Run:  npm install   then   node bridge.js   (Node 18+, backend running with WA_PROVIDER=webjs)

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000/message';
const SECRET = process.env.WA_BRIDGE_SECRET || '';

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: '.wwebjs_auth' }), // remembers the login across restarts
  puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] },
});

client.on('qr', (qr) => {
  console.log('On the spare phone: WhatsApp > Settings > Linked devices > Link a device, then scan:');
  qrcode.generate(qr, { small: true });
});
client.on('ready', () => console.log('✅ Bridge ready. Message the spare number from any phone.'));
client.on('auth_failure', (m) => console.error('Auth failure:', m));
client.on('disconnected', (reason) => console.error('Disconnected:', reason));

client.on('message', async (msg) => {
  // only 1:1 chats; skip groups, status updates and channels
  const isDirectChat = msg.from.endsWith('@c.us') || msg.from.endsWith('@lid');
  if (msg.fromMe || msg.isStatus || !isDirectChat) return;

  const payload = { sender: msg.from };
  try {
    if (msg.type === 'chat') {
      payload.text = msg.body;
    } else if (msg.type === 'ptt' || msg.type === 'audio') { // ptt = voice note
      const media = await msg.downloadMedia();
      if (media) payload.audio_b64 = media.data; // base64 OGG/Opus
    }

    const res = await fetch(BACKEND, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Bridge-Secret': SECRET },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`backend returned ${res.status}`);
    const { reply } = await res.json();
    if (reply) await client.sendMessage(msg.from, reply);
  } catch (err) {
    console.error(`Failed for ${msg.from}:`, err.message);
  }
});

client.initialize();
