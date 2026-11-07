const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function getWorkspace() {
  const response = await fetch(`${BASE_URL}/api/workspace`, {
    headers: { 'Accept': 'application/json' }
  });
  
  if (!response.ok) throw new Error(`Status ${response.status}`);
  const data = await response.json();
  
  return { data, isMock: false };
}

export async function checkBackendHealth() {
  try {
    const response = await fetch(`${BASE_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}

export async function submitPost(payload) {
  const response = await fetch(`${BASE_URL}/api/submissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error('Submission failed');
  return response.json();
}

export async function getSubmissionDetail(id) {
  const response = await fetch(`${BASE_URL}/api/submissions/${id}`);
  if (!response.ok) throw new Error('Failed to fetch submission detail');
  return response.json();
}

export async function recordDecision(findingId, payload) {
  const response = await fetch(`${BASE_URL}/api/findings/${findingId}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error('Failed to record decision');
  return response.json();
}

export async function resubmitPost(subId, newText) {
  const response = await fetch(`${BASE_URL}/api/submissions/${subId}/resubmit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: newText })
  });
  if (!response.ok) throw new Error('Resubmission failed');
  return response.json();
}

/* --- M7: Manager & Dashboard Endpoints --- */
export async function getSubmissions() {
  const response = await fetch(`${BASE_URL}/api/submissions`);
  if (!response.ok) throw new Error('Failed to fetch queue');
  return response.json();
}

export async function submitApproval(subId, payload) {
  const response = await fetch(`${BASE_URL}/api/submissions/${subId}/approval`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    let reason = `Approval failed (${response.status})`;
    try { const data = await response.json(); if (data.detail) reason = data.detail; } catch { /* no JSON body */ }
    throw new Error(reason);
  }
  return response.json();
}

export async function getDashboard() {
  const response = await fetch(`${BASE_URL}/api/dashboard`);
  if (!response.ok) throw new Error('Failed to fetch dashboard metrics');
  return response.json();
}
