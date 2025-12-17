import { CONFIG } from './config.js';

export function initLLM() {
  console.log('initLLM: Starting...');

  const btn = document.getElementById('llmAnalyzeBtn');
  const testBtn = document.getElementById('testBtn');
  const output = document.getElementById('llmOutput');
  const statusPill = document.getElementById('llmStatus');

  if (testBtn) {
      console.log('initLLM: Test Button found');
      testBtn.onclick = () => {
          console.log('Test Button Clicked');
          if (output) output.innerHTML = '<h3 style="color: #2ecc71">Hello World</h3><p>JavaScript is working!</p>';
      };
  } else {
      console.error('initLLM: Test Button NOT found');
  }

  if (!btn) {
    console.error('initLLM: Button #llmAnalyzeBtn not found!');
    return;
  }

  // Visual confirmation
  btn.style.border = '2px solid #2ecc71'; 
  console.log('initLLM: Button found and bordered.');

  // Direct event listener
  btn.onclick = async () => {
    console.log('initLLM: Button clicked!');
    
    if (btn.disabled) return;

    // UI Loading State
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';
    if (statusPill) {
        statusPill.textContent = 'Processing';
        statusPill.className = 'pill warn';
    }
    if (output) {
        output.innerHTML = '<div style="color:var(--muted); text-align:center;"><div class="spinner"></div> Gathering data...</div>';
    }

    // Gather Data
    const bounds = window.map ? window.map.getBounds() : null;
    const filters = window.getMapFilters ? window.getMapFilters() : {};
    
    const payload = {
        startTime: filters.start || '-1h',
        endTime: filters.end || 'now()',
        bounds: bounds ? {
            north: bounds.getNorth(),
            south: bounds.getSouth(),
            east: bounds.getEast(),
            west: bounds.getWest()
        } : null
    };

    console.log('initLLM: Sending payload', payload);

    try {
        const res = await fetch(`${CONFIG.LLM_BACKEND}/api/llm/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const text = await res.text();
        let data = {};
        try { data = JSON.parse(text); } catch(e) {}

        if (!res.ok) {
            throw new Error(data.error || data.message || `HTTP ${res.status}`);
        }

        const report = data.output || data.text || text;
        if (output) output.innerHTML = report.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

    } catch (err) {
        console.error('initLLM: Error', err);
        if (output) output.innerHTML = `<div style="color:#e74c3c"><strong>Error:</strong> ${err.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze Visible Area';
        if (statusPill) {
            statusPill.textContent = 'Ready';
            statusPill.className = 'pill';
        }
    }
  };
}

