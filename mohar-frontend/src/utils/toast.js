// Tiny toast helper: toast('Saved'), toast('Something failed', 'error')
export function toast(text, type = 'ok') {
  window.dispatchEvent(new CustomEvent('mohar:toast', { detail: { text, type, id: Date.now() + Math.random() } }));
}
