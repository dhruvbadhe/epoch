// Checks the bridge's message handling against a RUNNING backend, without WhatsApp:
//   python -m uvicorn backend.main:app --port 8000      (in another terminal)
//   node backend/whatsapp/bridge/selftest.js
// Needs no npm install: whatsapp-web.js is only loaded by `npm start`.
process.env.ALLOWED_NUMBERS = '+91 90000 00001';
const assert = require('assert');
const { onMessage, forwardVoice } = require('./index.js');

const sent = [];
const client = { sendMessage: async (to, text) => sent.push({ to, text }) };
let nextId = 0;
const message = (over) => ({
  id: { _serialized: `selftest-${Date.now()}-${nextId++}` }, from: '919000000001@c.us', fromMe: false,
  isStatus: false, type: 'chat', body: '20 poti kanda Niphad',
  getContact: async () => ({ number: '919000000001' }), ...over,
});

(async () => {
  const first = message();
  await onMessage(client, first);
  assert.strictEqual(sent.length, 1);
  assert.strictEqual(sent[0].to, '919000000001@c.us');
  assert.ok(sent[0].text.includes('(≈ 10'), `unexpected reply: ${sent[0].text}`);

  await onMessage(client, first);                                              // same message id again
  await onMessage(client, message({ fromMe: true }));                          // our own message
  await onMessage(client, message({ from: '1203630@g.us' }));                  // group chat
  await onMessage(client, message({ from: 'status@broadcast', isStatus: true })); // status update
  await onMessage(client, message({ type: 'image' }));                         // not text or voice
  await onMessage(client, message({ getContact: async () => ({ number: '919999999999' }) })); // stranger
  assert.strictEqual(sent.length, 1, 'only the first message should be answered');

  // A voice note reaches the backend as a multipart upload. Without a speech-to-text key the
  // backend answers with its "please type it" reply; with a key, send a real recording instead.
  const voiceReply = await forwardVoice('919000000001', Buffer.from('OggS'), 'audio/ogg; codecs=opus');
  assert.ok(voiceReply.length > 0);
  console.log('bridge ok\ntext reply : ' + sent[0].text + '\nvoice reply: ' + voiceReply.split('\n')[0]);
})().catch((err) => {
  console.error('bridge selftest FAILED:', err.message);
  process.exit(1);
});
