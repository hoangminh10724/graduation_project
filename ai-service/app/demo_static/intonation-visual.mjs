// Synchronized moving stress & intonation visual for words and situational sentences.
const NS = 'http://www.w3.org/2000/svg';
const svgEl = (tag, attrs = {}) => {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
  return n;
};
const dom = (tag, cls = '', text = '') => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text) n.textContent = text;
  return n;
};

// Known syllable stress splits for single-word stress visualization (e.g. a-BOUT).
const WORD_SYLLABLES = {
  about: {tokens: ['a', 'BOUT'], weights: [0.3, 1], path: [0.35, 0.78]},
  above: {tokens: ['a', 'BOVE'], weights: [0.3, 1], path: [0.35, 0.76]},
  fifteen: {tokens: ['fif', 'TEEN'], weights: [0.45, 1], path: [0.42, 0.82]},
  fifty: {tokens: ['FIF', 'ty'], weights: [1, 0.3], path: [0.8, 0.32]},
  thirteen: {tokens: ['thir', 'TEEN'], weights: [0.45, 1], path: [0.42, 0.82]},
  thirty: {tokens: ['THIR', 'ty'], weights: [1, 0.3], path: [0.8, 0.32]},
  banana: {tokens: ['ba', 'NA', 'na'], weights: [0.3, 1, 0.3], path: [0.35, 0.8, 0.3]},
  window: {tokens: ['WIN', 'dow'], weights: [1, 0.35], path: [0.76, 0.34]},
  technique: {tokens: ['tech', 'NIQUE'], weights: [0.35, 1], path: [0.38, 0.8]},
  develop: {tokens: ['de', 'VEL', 'op'], weights: [0.3, 1, 0.3], path: [0.34, 0.8, 0.32]},
  photography: {tokens: ['pho', 'TOG', 'ra', 'phy'], weights: [0.3, 1, 0.25, 0.3], path: [0.35, 0.82, 0.38, 0.28]},
  photographic: {tokens: ['pho', 'to', 'GRAPH', 'ic'], weights: [0.55, 0.25, 1, 0.3], path: [0.5, 0.34, 0.84, 0.3]},
  greenhouse: {tokens: ['GREEN', 'house'], weights: [1, 0.5], path: [0.8, 0.44]},
  bookshop: {tokens: ['BOOK', 'shop'], weights: [1, 0.5], path: [0.8, 0.44]},
  monday: {tokens: ['MON', 'day'], weights: [1, 0.35], path: [0.76, 0.34]},
  tuesday: {tokens: ['TUES', 'day'], weights: [1, 0.35], path: [0.76, 0.34]},
  teacher: {tokens: ['TEA', 'cher'], weights: [1, 0.3], path: [0.78, 0.32]},
  letter: {tokens: ['LET', 'ter'], weights: [1, 0.3], path: [0.78, 0.32]},
  vision: {tokens: ['VI', 'sion'], weights: [1, 0.3], path: [0.78, 0.32]},
  weather: {tokens: ['WEA', 'ther'], weights: [1, 0.3], path: [0.78, 0.32]},
  really: {tokens: ['REAL', 'ly'], weights: [1, 0.45], path: [0.74, 0.36]},
  tomorrow: {tokens: ['to', 'MOR', 'row'], weights: [0.3, 1, 0.3], path: [0.34, 0.8, 0.32]},
  another: {tokens: ['a', 'NO', 'ther'], weights: [0.3, 1, 0.3], path: [0.34, 0.8, 0.32]},
  weekend: {tokens: ['WEEK', 'end'], weights: [1, 0.5], path: [0.78, 0.44]},
  record_noun: {tokens: ['RE', 'cord'], weights: [1, 0.35], path: [0.82, 0.3]},
  record_verb: {tokens: ['re', 'CORD'], weights: [0.3, 1], path: [0.34, 0.84]},
  export_noun: {tokens: ['EX', 'port'], weights: [1, 0.4], path: [0.82, 0.34]},
  export_verb: {tokens: ['ex', 'PORT'], weights: [0.3, 1], path: [0.34, 0.84]},
  present_noun: {tokens: ['PRE', 'sent'], weights: [1, 0.35], path: [0.82, 0.3]},
  present_verb: {tokens: ['pre', 'SENT'], weights: [0.3, 1], path: [0.34, 0.84]},
};

export function contourFromModel(model) {
  if (model.wordKey && WORD_SYLLABLES[model.wordKey]) {
    return {...WORD_SYLLABLES[model.wordKey], tone: 'stress'};
  }
  const raw = (model.marked || model.line || '').trim();
  const clean = raw.replace(/[*^!~]/g, '').trim();
  const bare = clean.toLowerCase().replace(/[^a-z']/g, '');

  // Single-word stress contour (e.g. about -> a BOUT), preserving base lexical stress weights
  if (!clean.includes(' ')) {
    if (raw.includes('^')) {
      const base = WORD_SYLLABLES[bare];
      const tokens = base ? base.tokens : [clean];
      const weights = base ? base.weights : [1];
      const path = tokens.length === 1 ? [0.35, 0.85] : tokens.map((_, i) => (i === tokens.length - 1 ? 0.86 : 0.42));
      return {tokens, weights, path, tone: 'rise'};
    }
    if (raw.includes('!')) {
      const base = WORD_SYLLABLES[bare];
      const tokens = base ? base.tokens : [clean];
      const weights = base ? base.weights : [1];
      const path = tokens.length === 1 ? [0.78, 0.24] : tokens.map((_, i) => (i === 0 ? 0.78 : 0.24));
      return {tokens, weights, path, tone: 'fall'};
    }
    if (WORD_SYLLABLES[bare]) {
      return {...WORD_SYLLABLES[bare], tone: 'stress'};
    }
    return {
      tokens: [clean.toUpperCase()],
      weights: [1],
      path: [0.48, 0.72],
      tone: 'word',
    };
  }

  // Multi-word sentence contour with *prominence*, ^rise^, !fall!, and ~ pause.
  const parts = raw.split(/\s+/).filter(Boolean);
  const tokens = [];
  const weights = [];
  const path = [];
  let tone = 'prominence';

  for (const part of parts) {
    if (part === '~') {
      tokens.push('‖');
      weights.push(0.2);
      path.push(0.32);
      continue;
    }
    const isStar = /\*[^*]+\*/.test(part);
    const isRise = /\^[^^]+\^/.test(part);
    const isFall = /![^!]+!/.test(part);
    const text = part.replace(/[*^!~]/g, '');
    if (isStar) {
      tokens.push(text.toUpperCase());
      weights.push(1);
      path.push(0.84);
    } else if (isRise) {
      tone = 'rise';
      tokens.push(text.toUpperCase());
      weights.push(0.95);
      path.push(0.88);
    } else if (isFall) {
      tone = 'fall';
      tokens.push(text.toUpperCase());
      weights.push(0.95);
      // Keep 1:1 token-to-point alignment with a distinct falling landing
      path.push(0.22);
    } else {
      const isFunction = /^(a|an|the|to|of|in|on|at|for|is|are|was|were|be|can|do|did|i|you|we|he|she|it|my|her|his|our|and|or|as)$/i.test(
        text.replace(/[^a-z]/gi, '')
      );
      tokens.push(text);
      weights.push(isFunction ? 0.3 : 0.52);
      path.push(isFunction ? 0.34 : 0.48);
    }
  }
  if (path.length === 1) path.push(path[0]);
  return {tokens, weights, path, tone};
}

function buildSmoothPath(points) {
  if (points.length < 2) return '';
  let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const midX = ((prev.x + curr.x) / 2).toFixed(1);
    d += ` C ${midX} ${prev.y.toFixed(1)}, ${midX} ${curr.y.toFixed(1)}, ${curr.x.toFixed(1)} ${curr.y.toFixed(1)}`;
  }
  return d;
}

/**
 * Render an interactive moving pitch/stress visual synced to audio (or standalone animation).
 * As the glowing line moves left-to-right, each syllable/word lights up simultaneously.
 */
export function renderIntonationVisual(parent, {tokens, weights, path, label = '', audioEl = null, durationMs = 1700, showButton = true, buttonLabel = ''}) {
  const card = dom('div', 'intonation-card');
  if (label) card.append(dom('p', 'intonation-label', label));

  const row = dom('div', 'intonation-tokens');
  row.setAttribute('aria-label', 'Stress and intonation syllables');
  const pills = tokens.map((tok, i) => {
    const pill = dom('span', 'intonation-token', tok);
    const w = weights[i] ?? 0.5;
    pill.dataset.prominent = String(w >= 0.85);
    pill.dataset.pause = String(tok === '‖');
    row.append(pill);
    return pill;
  });

  // Unified clock: compute explicit [tStart, tEnd] intervals per token so dot, nodes, and pills stay locked together
  const rawDurs = pills.map((_, i) => 0.55 + (weights[i] ?? 0.5));
  const totalDur = rawDurs.reduce((a, b) => a + b, 0) || 1;
  const spans = [];
  let acc = 0;
  for (const d of rawDurs) {
    const start = acc;
    acc += d / totalDur;
    spans.push({start, end: acc, mid: (start + acc) / 2});
  }

  const width = 520;
  const height = 110;
  const padX = 36;
  const usableW = width - padX * 2;
  const pointValues = path.length === pills.length
    ? path
    : pills.map((_, i) => path[Math.min(path.length - 1, Math.round((i * (path.length - 1)) / Math.max(1, pills.length - 1)))]);
  const pts = pills.length === 1
    ? [
        {x: padX, y: height - 18 - Math.max(0.08, Math.min(0.95, path[0] ?? 0.5)) * (height - 34)},
        {x: padX + usableW, y: height - 18 - Math.max(0.08, Math.min(0.95, path[path.length - 1] ?? 0.5)) * (height - 34)},
      ]
    : spans.map((sp, i) => ({
        x: padX + sp.mid * usableW,
        y: height - 18 - Math.max(0.08, Math.min(0.95, pointValues[i] ?? 0.5)) * (height - 34),
      }));

  const svg = svgEl('svg', {
    viewBox: `0 0 ${width} ${height}`,
    class: 'intonation-svg',
    role: 'img',
    'aria-label': `Moving stress and intonation contour for ${tokens.join(' ')}`,
  });

  // Subtle horizontal reference guides (high / mid / low)
  for (const y of [22, 55, 88]) {
    svg.append(svgEl('line', {x1: 16, y1: y, x2: width - 16, y2: y, stroke: '#e2e8de', 'stroke-width': 1, 'stroke-dasharray': '4 4'}));
  }

  const d = buildSmoothPath(pts);
  const track = svgEl('path', {d, fill: 'none', stroke: '#cbd8cc', 'stroke-width': 5, 'stroke-linecap': 'round'});
  const activeLine = svgEl('path', {d, fill: 'none', stroke: '#15574a', 'stroke-width': 5.5, 'stroke-linecap': 'round'});
  const glowDot = svgEl('circle', {cx: pts[0].x, cy: pts[0].y, r: 12, fill: '#f59e0b', opacity: 0.28});
  const dot = svgEl('circle', {cx: pts[0].x, cy: pts[0].y, r: 7, fill: '#d97706', stroke: '#fff', 'stroke-width': 2});

  const nodeCircles = pts.map((p, i) => {
    const prominent = (weights[Math.min(i, weights.length - 1)] ?? 0.5) >= 0.85;
    const c = svgEl('circle', {
      cx: p.x,
      cy: p.y,
      r: prominent ? 5.5 : 3.5,
      fill: prominent ? '#15574a' : '#8aa599',
    });
    svg.append(c);
    return c;
  });

  svg.append(track, activeLine, glowDot, dot);
  card.append(row, svg);

  const controls = dom('div', 'intonation-controls');
  const playBtn = dom('button', 'secondary intonation-play', buttonLabel || (audioEl ? 'Play & watch line' : 'Animate stress line'));
  playBtn.type = 'button';
  if (showButton) {
    controls.append(playBtn);
    card.append(controls);
  }
  parent.append(card);

  // Measure path length once mounted
  let totalLen = 500;
  try {
    totalLen = activeLine.getTotalLength() || 500;
  } catch {}
  activeLine.style.strokeDasharray = `${totalLen}`;
  activeLine.style.strokeDashoffset = `${totalLen}`;

  let rafId = 0;

  function setProgress(t) {
    const clamped = Math.max(0, Math.min(1, t));
    activeLine.style.strokeDashoffset = String(totalLen * (1 - clamped));
    try {
      const pt = activeLine.getPointAtLength(totalLen * clamped);
      dot.setAttribute('cx', pt.x.toFixed(1));
      dot.setAttribute('cy', pt.y.toFixed(1));
      glowDot.setAttribute('cx', pt.x.toFixed(1));
      glowDot.setAttribute('cy', pt.y.toFixed(1));
    } catch {
      const idx = Math.min(pts.length - 1, Math.floor(clamped * (pts.length - 1)));
      dot.setAttribute('cx', pts[idx].x);
      dot.setAttribute('cy', pts[idx].y);
    }

    // Unified single clock: pill and nodeCircles both follow spans[i]
    let activeIndex = -1;
    if (clamped > 0) {
      activeIndex = spans.findIndex(sp => clamped <= sp.end);
      if (activeIndex < 0) activeIndex = pills.length - 1;
    }
    pills.forEach((pill, i) => {
      const lit = i === activeIndex;
      const passed = activeIndex >= 0 && i < activeIndex;
      pill.classList.toggle('is-active', lit);
      pill.classList.toggle('is-passed', passed);
    });
    nodeCircles.forEach((c, i) => {
      const lit = activeIndex >= 0 && i === Math.min(activeIndex, nodeCircles.length - 1);
      const prominent = (weights[Math.min(i, weights.length - 1)] ?? 0.5) >= 0.85;
      c.setAttribute('fill', lit ? '#d97706' : prominent ? '#15574a' : '#8aa599');
    });
  }

  function stopAnim() {
    cancelAnimationFrame(rafId);
    rafId = 0;
  }

  function runTimerAnimation() {
    stopAnim();
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setProgress(1);
      return;
    }
    const start = performance.now();
    const tick = now => {
      const t = Math.min(1, (now - start) / durationMs);
      setProgress(t);
      if (t < 1) rafId = requestAnimationFrame(tick);
      else rafId = 0;
    };
    rafId = requestAnimationFrame(tick);
  }

  function syncToAudio() {
    stopAnim();
    const tick = () => {
      if (!audioEl || audioEl.paused || audioEl.ended) {
        if (audioEl?.ended) setProgress(1);
        rafId = 0;
        return;
      }
      const dur = Number.isFinite(audioEl.duration) && audioEl.duration > 0 ? audioEl.duration : durationMs / 1000;
      setProgress(audioEl.currentTime / dur);
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
  }

  if (audioEl) {
    audioEl.addEventListener('play', syncToAudio);
    audioEl.addEventListener('pause', stopAnim);
    audioEl.addEventListener('ended', () => {
      stopAnim();
      setProgress(1);
    });
  }

  playBtn.onclick = () => {
    if (audioEl) {
      audioEl.currentTime = 0;
      audioEl.play().catch(() => runTimerAnimation());
    } else {
      runTimerAnimation();
    }
  };

  return {card, setProgress, animate: runTimerAnimation, stop: stopAnim};
}
