class PCMCapture extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const channels = inputs[0];
    if (channels?.length) {
      const mono = new Float32Array(channels[0].length);
      for (const channel of channels) for (let i = 0; i < mono.length; i++) mono[i] += channel[i] / channels.length;
      this.port.postMessage(mono.buffer, [mono.buffer]);
    }
    // Keep the audio graph active without playing the microphone to speakers.
    for (const output of outputs) for (const channel of output) channel.fill(0);
    return true;
  }
}
registerProcessor('wordspeak-pcm-capture', PCMCapture);
