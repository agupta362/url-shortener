const API_URL = "http://localhost:8000"

export function getToken() {
  return localStorage.getItem("access_token")
}

export function setToken(token) {
  localStorage.setItem("access_token", token)
}

export function clearToken() {
  localStorage.removeItem("access_token")
}

export function getShortLink(shortCode) {
  return `${API_URL}/${shortCode}`
}

async function request(url, options) {
  const res = await fetch(url, options)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || "Request failed")
  return data
}

export function register(name, email, password) {
  return request(`${API_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  })
}

export async function login(email, password) {
  const data = await request(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  setToken(data.access_token)
  return data
}

export function getUrls() {
  return request(`${API_URL}/urls`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  }).then((data) => data.urls)
}

export function createUrl(originalUrl, customCode = "") {
  const body = { original_url: originalUrl }
  if (customCode) body.custom_code = customCode

  return request(`${API_URL}/urls`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(body),
  })
}
