export function encodeWav(samples, rate = 16000) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const ascii = (offset, value) => [...value].forEach((char, i) => view.setUint8(offset + i, char.charCodeAt(0)));
  ascii(0, 'RIFF'); view.setUint32(4, 36 + samples.length * 2, true); ascii(8, 'WAVE');
  ascii(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); ascii(36, 'data');
  view.setUint32(40, samples.length * 2, true);
  samples.forEach((sample, i) => {
    const value = Math.max(-1, Math.min(1, sample));
    view.setInt16(44 + i * 2, Math.max(-32768, Math.min(32767, Math.round(value * 32768))), true);
  });
  return new Blob([buffer], {type: 'audio/wav'});
}

export async function decodeAudio(blob) {
  if (blob.size > 30 * 1024 * 1024) throw new Error('Choose an audio file smaller than 30 MB.');
  // Decode directly at the model rate, avoiding a 16k -> device-rate -> 16k
  // round trip that can change predictions on an otherwise identical input.
  const context = new OfflineAudioContext(1, 1, 16000);
  return await context.decodeAudioData(await blob.arrayBuffer());
}

export async function prepareAudio(decoded, start, end, {gain = 1, onLevel = () => {}} = {}) {
  validateGain(gain);
  if (![start, end].every(Number.isFinite) || start < 0 || end > decoded.duration + 0.001 || end <= start)
    throw new Error('Choose a valid start and end inside the recording.');
  const duration = end - start;
  if (duration < 0.25 || duration > 4.001) throw new Error('Select one complete word lasting 0.25 to 4 seconds.');
  const context = new OfflineAudioContext(1, Math.round(duration * 16000), 16000);
  const source = context.createBufferSource(); source.buffer = decoded; source.connect(context.destination);
  source.start(0, start, duration);
  const rendered = await context.startRendering();
  const original = rendered.getChannelData(0);
  const samples = gainSamples(original, gain);
  onLevel({...sampleLevels(samples), rawPeak: sampleLevels(original).peak, gain, phase: 'finished'});
  return encodeWav(samples);
}

export function sampleLevels(samples) {
  let peak = 0, squares = 0, clipped = 0;
  for (const value of samples) {
    peak = Math.max(peak, Math.abs(value)); squares += value * value;
    if (Math.abs(value) >= .99) clipped++;
  }
  return {peak, rms: samples.length ? Math.sqrt(squares / samples.length) : 0,
    clippingFraction: samples.length ? clipped / samples.length : 0};
}

function validateGain(gain) {
  if (!Number.isFinite(gain) || gain < 1 || gain > 8) throw new Error('Choose an input boost between 1× and 8×.');
}

export function gainSamples(samples, gain) {
  validateGain(gain);
  return Float32Array.from(samples, value => value * gain);
}

export async function startPCMRecording({gain = 1, deviceId = '', autoGain = false, autoNormalize = false, workletUrl = '/demo/assets/capture-worklet.js', onLevel = () => {}} = {}) {
  validateGain(gain);
  const stream = await navigator.mediaDevices.getUserMedia({audio: {
    ...(deviceId ? {deviceId: {exact: deviceId}} : {}),
    channelCount: 1,
    echoCancellation: false,
    noiseSuppression: Boolean(autoGain),
    // Keep browser AGC off so syllable/word loudness dynamics are preserved;
    // linear post-capture autoNormalize boosts quiet mics without flattening prominence.
    autoGainControl: false,
  }});
  let context;
  try {
    try { context = new AudioContext({sampleRate: 16000}); }
    catch { context = new AudioContext(); }
    if (!context.audioWorklet) throw new Error('PCM recording is unavailable. Upload a file instead.');
    await context.audioWorklet.addModule(workletUrl);
    const chunks = [];
    const node = new AudioWorkletNode(context, 'wordspeak-pcm-capture');
    const deviceLabel = stream.getAudioTracks()[0]?.label || 'Default microphone';
    let lastMeter = 0;
    node.port.onmessage = event => {
      const chunk = new Float32Array(event.data); chunks.push(chunk);
      if (performance.now() - lastMeter >= 80) {
        lastMeter = performance.now();
        onLevel({...sampleLevels(gainSamples(chunk, gain)), rawPeak: sampleLevels(chunk).peak, gain, deviceLabel, phase: 'recording'});
      }
    };
    const source = context.createMediaStreamSource(stream);
    const mute = context.createGain(); mute.gain.value = 0;
    source.connect(node); node.connect(mute); mute.connect(context.destination);
    await context.resume();
    let stopped = false, rawBlob;
    return {get rawBlob() { return rawBlob; }, stop: async () => {
      if (stopped) throw new Error('Recording already stopped.');
      stopped = true; source.disconnect(); node.disconnect(); mute.disconnect();
      stream.getTracks().forEach(track => track.stop());
      let rate = context.sampleRate;
      await context.close();
      let samples = new Float32Array(chunks.reduce((count, chunk) => count + chunk.length, 0));
      let offset = 0; for (const chunk of chunks) { samples.set(chunk, offset); offset += chunk.length; }
      if (rate !== 16000 && samples.length > 0 && typeof OfflineAudioContext !== 'undefined') {
        const targetLen = Math.max(1, Math.round(samples.length * 16000 / rate));
        const off = new OfflineAudioContext(1, targetLen, 16000);
        const buf = off.createBuffer(1, samples.length, rate);
        buf.copyToChannel(samples, 0);
        const src = off.createBufferSource(); src.buffer = buf; src.connect(off.destination); src.start();
        samples = (await off.startRendering()).getChannelData(0);
        rate = 16000;
      }
      rawBlob = encodeWav(samples, rate);
      const rawStats = sampleLevels(samples);
      let effectiveGain = gain;
      let amplified = gainSamples(samples, gain);
      // If a laptop/headset mic is very quiet despite speech, safely normalize to ~0.72 peak without clipping.
      if (autoNormalize && rawStats.peak >= 0.002 && rawStats.peak * gain < 0.45) {
        effectiveGain = Math.min(12, 0.72 / rawStats.peak);
        amplified = Float32Array.from(samples, v => Math.max(-1, Math.min(1, v * effectiveGain)));
      }
      onLevel({...sampleLevels(amplified), rawPeak: rawStats.peak, gain: effectiveGain, deviceLabel, phase: 'finished'});
      return encodeWav(amplified, rate);
    }};
  } catch (error) {
    stream.getTracks().forEach(track => track.stop());
    if (context && context.state !== 'closed') await context.close();
    throw error;
  }
}
