class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new ApiError("Backend trả về dữ liệu không hợp lệ", response.status);
  }

  const payload = await response.json();
  if (!response.ok) {
    throw new ApiError(payload.detail || "Yêu cầu đến Backend thất bại", response.status);
  }
  return payload;
}

async function requestJson(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: { Accept: "application/json", ...options.headers },
    });
    return await readJson(response);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("Không thể kết nối Backend local");
  }
}

export function getHealth() {
  return requestJson("/health");
}

export function transcribeAudio({ file, language, beamSize, model, hotwords }) {
  if (!(file instanceof File)) {
    return Promise.reject(new ApiError("Chưa có tệp âm thanh để xử lý"));
  }

  const form = new FormData();
  form.append("file", file);
  form.append("language", language);
  form.append("beam_size", String(beamSize));
  form.append("model", model);
  form.append("hotwords", hotwords);

  return requestJson("/v1/audio/transcriptions", {
    method: "POST",
    body: form,
  });
}
