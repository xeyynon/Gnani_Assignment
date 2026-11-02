/* Turns microphone audio (any sample rate, floats) into 16 kHz signed 16-bit samples.
   Averaging the input samples that fall into each output sample acts as a simple low-pass filter. */
function makeResampler(inRate, outRate) {
  const ratio = inRate / outRate;
  let acc = 0, n = 0, phase = 0;
  return function (input) {
    const out = [];
    for (let i = 0; i < input.length; i++) {
      acc += input[i]; n++; phase += 1;
      if (phase >= ratio) { out.push(acc / n); acc = 0; n = 0; phase -= ratio; }
    }
    const pcm = new Int16Array(out.length);
    for (let i = 0; i < out.length; i++) {
      const s = Math.max(-1, Math.min(1, out[i]));
      pcm[i] = s < 0 ? s * 32768 : s * 32767;
    }
    return pcm;
  };
}

const workletSource = `
  const makeResampler = ${makeResampler.toString()};
  class Capture extends AudioWorkletProcessor {
    constructor() { super(); this.resample = makeResampler(sampleRate, 16000); }
    process(inputs) {
      const ch = inputs[0] && inputs[0][0];
      if (ch && ch.length) {
        const pcm = this.resample(ch);
        if (pcm.length) this.port.postMessage(pcm, [pcm.buffer]);
      }
      return true;
    }
  }
  registerProcessor('capture', Capture);`;
