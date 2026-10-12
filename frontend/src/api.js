async function request(method, url, body) {
  let response;

  try {
    response = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(
      "Cannot reach the backend. Make sure `python main.py` is still running.",
    );
  }

  let data = {};
  try {
    data = await response.json();
  } catch {
    // Some responses do not include a JSON body.
  }

  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }

  return data;
}

export const api = {
  status: () => request("GET", "/api/status"),
  questions: () => request("GET", "/api/questions"),
  addQuestion: (question) => request("POST", "/api/questions", question),
  deleteQuestion: (id) =>
    request("DELETE", `/api/questions/${encodeURIComponent(id)}`),
  summary: (payload) => request("POST", "/api/release/summary", payload),
  prepare: (payload) => request("POST", "/api/release/prepare", payload),
  confirm: (payload) => request("POST", "/api/release/confirm", payload),
  cancel: () => request("POST", "/api/release/cancel", {}),

  // XMLHttpRequest is used so the page can display upload progress.
  uploadArtifact(file, onProgress) {
    return new Promise((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", "/api/artifact");
      request.setRequestHeader("X-Filename", encodeURIComponent(file.name));

      request.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress?.(Math.round((event.loaded / event.total) * 100));
        }
      };

      request.onload = () => {
        let data = {};
        try {
          data = JSON.parse(request.responseText);
        } catch {
          // The response body was not JSON.
        }

        if (request.status >= 200 && request.status < 300) {
          resolve(data);
        } else {
          reject(new Error(data.error || "Upload failed."));
        }
      };

      request.onerror = () => {
        reject(
          new Error(
            "Cannot reach the backend. Make sure `python main.py` is still running.",
          ),
        );
      };

      request.send(file);
    });
  },
};
