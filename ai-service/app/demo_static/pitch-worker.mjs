import {pitchFrames} from './pitch.mjs';
self.onmessage=({data})=>self.postMessage(pitchFrames(data.samples,data.rate));
