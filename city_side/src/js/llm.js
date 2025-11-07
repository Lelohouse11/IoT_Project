import { isSignedIn } from './auth.js';

export function initLLM() {
  const btn = document.getElementById('simulateLLM');
  const box = document.getElementById('llmOutput');
  btn?.addEventListener('click', () => {
    box.textContent = isSignedIn()
      ? 'AI: Highlighting congestion hotspots and recommending signage updates for next week.'
      : 'AI: Please sign in to access planning insights.';
  });
}
