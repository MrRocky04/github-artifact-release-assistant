async function request(method, url, body) {
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Cannot reach the backend. Make sure `python main.py` is still running.");
  }
  let data = {};
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export const api = {
  status: () => request("GET", "/api/status"),
  questions: () => request("GET", "/api/questions"),
  addQuestion: (q) => request("POST", "/api/questions", q),
  deleteQuestion: (id) => request("DELETE", `/api/questions/${encodeURIComponent(id)}`),
  summary: (p) => request("POST", "/api/release/summary", p),
  prepare: (p) => request("POST", "/api/release/prepare", p),
  confirm: (p) => request("POST", "/api/release/confirm", p),
  cancel: () => request("POST", "/api/release/cancel", {}),

  // XMLHttpRequest so the page can show upload progress
  uploadArtifact(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/artifact");
      xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name));
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(Math.round((e.loaded / e.total) * 100));
      xhr.onload = () => {
        let data = {};
        try { data = JSON.parse(xhr.responseText); } catch { /* ignore */ }
        xhr.status >= 200 && xhr.status < 300 ? resolve(data) : reject(new Error(data.error || "Upload failed."));
      };
      xhr.onerror = () => reject(new Error("Cannot reach the backend. Make sure `python main.py` is still running."));
      xhr.send(file);
    });
  },
};
