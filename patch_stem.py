import sys, re

with open("/root/pilot-dashboard/assets/momentum.html", "r") as f:
    text = f.read()

# Replace Euclidean rendering
old_euclidean = """
  // Euclidean
  if (s.euclidean) {
    const e = s.euclidean;
    html += `<div class="stem-block stem-block-euclidean">
      <div class="stem-model stem-model-euclidean">⬡ Euclidean — Shatter the 5th Postulate</div>`;
    if (e.assumption) html += `<div class="stem-field"><span class="stem-label">Assumption</span><span class="stem-value">${escapeHtml(e.assumption)}</span></div>`;
    if (e.reframe) html += `<div class="stem-field"><span class="stem-label">Reframe</span><span class="stem-value">${escapeHtml(e.reframe)}</span></div>`;
    if (e.unlocked_action) html += `<div class="stem-action">${escapeHtml(e.unlocked_action)}</div>`;
    html += `</div>`;
  }
"""
new_euclidean = """
  // Euclidean
  if (s.euclidean) {
    const e = s.euclidean;
    html += `<div class="stem-block stem-block-euclidean">
      <div class="stem-model stem-model-euclidean">⬡ Euclidean — Shatter the 5th Postulate</div>`;
    if (typeof e === 'string') {
      html += `<div class="stem-desc-text">${escapeHtml(e)}</div>`;
    } else {
      if (e.assumption) html += `<div class="stem-field"><span class="stem-label">Assumption</span><span class="stem-value">${escapeHtml(e.assumption)}</span></div>`;
      if (e.reframe) html += `<div class="stem-field"><span class="stem-label">Reframe</span><span class="stem-value">${escapeHtml(e.reframe)}</span></div>`;
      if (e.unlocked_action) html += `<div class="stem-action">${escapeHtml(e.unlocked_action)}</div>`;
    }
    html += `</div>`;
  }
"""
text = text.replace(old_euclidean.strip(), new_euclidean.strip())

# Replace Probabilistic rendering
old_prob = """
  // Probabilistic
  if (s.probabilistic) {
    const p = s.probabilistic;
    html += `<div class="stem-block stem-block-probabilistic">
      <div class="stem-model stem-model-probabilistic">📊 Probabilistic — Optimal Bet Allocation</div>`;
    if (p.highest_ev_domain) html += `<div class="stem-field"><span class="stem-label">Highest EV Domain</span><span class="stem-value">${escapeHtml(p.highest_ev_domain)}</span></div>`;
    if (p.avoid_domain) html += `<div class="stem-field"><span class="stem-label">Avoid Domain</span><span class="stem-value">${escapeHtml(p.avoid_domain)}</span></div>`;
    if (p.allocation) html += `<div class="stem-action">${escapeHtml(p.allocation)}</div>`;
    html += `</div>`;
  }
"""
new_prob = """
  // Probabilistic
  if (s.probabilistic) {
    const p = s.probabilistic;
    html += `<div class="stem-block stem-block-probabilistic">
      <div class="stem-model stem-model-probabilistic">📊 Probabilistic — Optimal Bet Allocation</div>`;
    if (typeof p === 'string') {
      html += `<div class="stem-desc-text">${escapeHtml(p)}</div>`;
    } else {
      if (p.highest_ev_domain) html += `<div class="stem-field"><span class="stem-label">Highest EV Domain</span><span class="stem-value">${escapeHtml(p.highest_ev_domain)}</span></div>`;
      if (p.avoid_domain) html += `<div class="stem-field"><span class="stem-label">Avoid Domain</span><span class="stem-value">${escapeHtml(p.avoid_domain)}</span></div>`;
      if (p.allocation) html += `<div class="stem-action">${escapeHtml(p.allocation)}</div>`;
    }
    html += `</div>`;
  }
"""
text = text.replace(old_prob.strip(), new_prob.strip())

# Replace Bets rendering
old_bets = """
  // Thinking in Bets
  if (s.bets) {
    const b = s.bets;
    html += `<div class="stem-block stem-block-bets">
      <div class="stem-model stem-model-bets">🎰 Thinking in Bets — Highest-EV Decision</div>`;
    if (b.best_decision) html += `<div class="stem-field"><span class="stem-label">Best Decision</span><span class="stem-value">${escapeHtml(b.best_decision)}</span></div>`;
    if (b.reasoning) html += `<div class="stem-field"><span class="stem-label">Reasoning</span><span class="stem-value">${escapeHtml(b.reasoning)}</span></div>`;
    if (b.info_trigger) html += `<div class="stem-field"><span class="stem-label">Info Trigger / Bet-Changer</span><span class="stem-value">${escapeHtml(b.info_trigger)}</span></div>`;
    if (b.hedge) html += `<div class="stem-field"><span class="stem-label">Hedge</span><span class="stem-value">${escapeHtml(b.hedge)}</span></div>`;
    html += `</div>`;
  }
"""
new_bets = """
  // Thinking in Bets
  if (s.bets) {
    const b = s.bets;
    html += `<div class="stem-block stem-block-bets">
      <div class="stem-model stem-model-bets">🎰 Thinking in Bets — Highest-EV Decision</div>`;
    if (typeof b === 'string') {
      html += `<div class="stem-desc-text">${escapeHtml(b)}</div>`;
    } else {
      if (b.best_decision) html += `<div class="stem-field"><span class="stem-label">Best Decision</span><span class="stem-value">${escapeHtml(b.best_decision)}</span></div>`;
      if (b.reasoning) html += `<div class="stem-field"><span class="stem-label">Reasoning</span><span class="stem-value">${escapeHtml(b.reasoning)}</span></div>`;
      if (b.info_trigger) html += `<div class="stem-field"><span class="stem-label">Info Trigger / Bet-Changer</span><span class="stem-value">${escapeHtml(b.info_trigger)}</span></div>`;
      if (b.hedge) html += `<div class="stem-field"><span class="stem-label">Hedge</span><span class="stem-value">${escapeHtml(b.hedge)}</span></div>`;
    }
    html += `</div>`;
  }
"""
text = text.replace(old_bets.strip(), new_bets.strip())

# Replace Warp-Speed rendering
old_warp = """
  // Warp-Speed
  if (s.warp_speed) {
    const w = s.warp_speed;
    html += `<div class="stem-block stem-block-warp">
      <div class="stem-model stem-model-warp">🚀 Warp-Speed — Throughput Plan</div>`;
    if (w.bottleneck) html += `<div class="stem-field"><span class="stem-label">Bottleneck</span><span class="stem-value">${escapeHtml(w.bottleneck)}</span></div>`;
    if (w.parallelize) html += `<div class="stem-field"><span class="stem-label">Parallelize</span><span class="stem-value">${escapeHtml(w.parallelize)}</span></div>`;
    if (w.sequence) html += `<div class="stem-field"><span class="stem-label">Sequence</span><span class="stem-value">${escapeHtml(w.sequence)}</span></div>`;
    if (w.kill_defer) html += `<div class="stem-field"><span class="stem-label">Kill / Defer</span><span class="stem-value">${escapeHtml(w.kill_defer)}</span></div>`;
    if (w.plan) html += `<div class="stem-action">${escapeHtml(w.plan)}</div>`;
    html += `</div>`;
  }
"""
new_warp = """
  // Warp-Speed
  if (s.warp_speed) {
    const w = s.warp_speed;
    html += `<div class="stem-block stem-block-warp">
      <div class="stem-model stem-model-warp">🚀 Warp-Speed — Throughput Plan</div>`;
    if (typeof w === 'string') {
      html += `<div class="stem-desc-text">${escapeHtml(w)}</div>`;
    } else {
      if (w.bottleneck) html += `<div class="stem-field"><span class="stem-label">Bottleneck</span><span class="stem-value">${escapeHtml(w.bottleneck)}</span></div>`;
      if (w.parallelize) html += `<div class="stem-field"><span class="stem-label">Parallelize</span><span class="stem-value">${escapeHtml(w.parallelize)}</span></div>`;
      if (w.sequence) html += `<div class="stem-field"><span class="stem-label">Sequence</span><span class="stem-value">${escapeHtml(w.sequence)}</span></div>`;
      if (w.kill_defer) html += `<div class="stem-field"><span class="stem-label">Kill / Defer</span><span class="stem-value">${escapeHtml(w.kill_defer)}</span></div>`;
      if (w.plan) html += `<div class="stem-action">${escapeHtml(w.plan)}</div>`;
    }
    html += `</div>`;
  }
"""
text = text.replace(old_warp.strip(), new_warp.strip())

# Add CSS for stem-desc-text
css = """
  .stem-action { margin-top: 12px; color: var(--green); font-weight: 500; font-size: 14px; border-top: 1px solid var(--border); padding-top: 12px; }
"""
new_css = """
  .stem-action { margin-top: 12px; color: var(--green); font-weight: 500; font-size: 14px; border-top: 1px solid var(--border); padding-top: 12px; }
  .stem-desc-text { color: var(--text); font-size: 14px; line-height: 1.6; padding: 4px 0; }
  .stem-block { padding: 20px; }
  .stem-model { margin-bottom: 12px; }
  .forecast-scenario { font-size: 14px; line-height: 1.6; color: var(--text); }
"""
text = text.replace(css.strip(), new_css.strip())

with open("/root/pilot-dashboard/assets/momentum.html", "w") as f:
    f.write(text)

print("HTML Patched!")
