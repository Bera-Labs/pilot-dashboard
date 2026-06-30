import sys, re

with open("assets/momentum.html", "r") as f:
    text = f.read()

# CSS
css_addition = """
  .execution-script { display: flex; flex-direction: column; gap: 12px; }
  .exec-step { display: flex; background: var(--surface); border-left: 3px solid var(--accent); padding: 12px; border-radius: 4px; gap: 16px; align-items: flex-start; }
  .exec-step-num { font-family: 'Space Mono', monospace; color: var(--accent); font-weight: bold; font-size: 14px; min-width: 60px; text-transform: uppercase; }
  .exec-step-body { flex: 1; }
  .exec-step-action { color: var(--text); font-size: 15px; margin-bottom: 4px; font-weight: 500; }
  .exec-step-rule { color: var(--red); font-size: 13px; font-family: 'Space Mono', monospace; }
"""
text = text.replace(".calib-grid { display: grid;", css_addition + "\n  .calib-grid { display: grid;")

# render function
js_call = """
  // === 5.5 EXECUTION SCRIPT ===
  if (ma.execution_script && ma.execution_script.length > 0) {
    html += renderExecutionScript(ma.execution_script);
  }

  // === 6. ACTION QUEUE ===
"""
text = text.replace("  // === 6. ACTION QUEUE ===", js_call)

# renderExecutionScript function
js_func = """
function renderExecutionScript(script) {
  let html = '<div class="section fade-in">';
  html += '<div class="section-title">Deterministic Execution Script</div>';
  html += '<div class="execution-script">';

  script.forEach((step, i) => {
    html += `<div class="exec-step">
      <div class="exec-step-num">${escapeHtml(step.time_or_sequence || String(i+1))}</div>
      <div class="exec-step-body">
        <div class="exec-step-action">${escapeHtml(step.action)}</div>
        ${step.strict_rule ? `<div class="exec-step-rule">STRICT RULE: ${escapeHtml(step.strict_rule)}</div>` : ''}
      </div>
    </div>`;
  });

  html += '</div></div>';
  return html;
}

function renderActions(actions) {
"""
text = text.replace("function renderActions(actions) {", js_func)

with open("assets/momentum.html", "w") as f:
    f.write(text)
print("Patched!")
