// Simple LLM client: text input -> POST to LLM API -> output
// Uses demo.py-compatible API: POST { prompt, model } with X-API-Key

export function initLLM() {
  const input = document.getElementById('llmPrompt');
  const sendBtn = document.getElementById('llmSend');
  const output = document.getElementById('llmOutput');

  if (!output) return;

  const BACKEND = window.LLM_BACKEND_BASE || 'http://localhost:8080';
  const API_URL = `${BACKEND}/api/llm/chat`;
  const MODEL = window.LLM_MODEL || 'deepseek-r1:8b';

  function setLoading(loading) {
    if (!sendBtn) return;
    sendBtn.disabled = loading;
    sendBtn.textContent = loading ? 'Sending…' : 'Send';
  }

  async function sendPrompt() {
    const prompt = (input?.value || '').trim();
    if (!prompt) {
      output.textContent = 'Please enter a prompt.';
      return;
    }
    setLoading(true);
    output.textContent = 'Thinking…';

    const payload = { prompt, model: MODEL };
    const headers = { 'Content-Type': 'application/json' };

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { raw: text }; }
      if (!res.ok) {
        const msg = data && (data.error || data.message || data.raw || `HTTP ${res.status}`);
        output.textContent = `Error: ${msg}`;
        return;
      }
      output.textContent = (data && (data.output || data.text || data.answer)) || text || 'No output.';
    } catch (e) {
      output.textContent = `Network error: ${e}`;
    } finally {
      setLoading(false);
    }
  }

  sendBtn?.addEventListener('click', sendPrompt);
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendPrompt();
    }
  });
}
