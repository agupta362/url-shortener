const API_URL = "http://18.219.235.112:8002"

export function getToken() {
  return localStorage.getItem("access_token")
}

export function getRefreshToken() {
  return localStorage.getItem("refresh_token")
}

export function setToken(token) {
  localStorage.setItem("access_token", token)
}

export function setRefreshToken(token) {
  localStorage.setItem("refresh_token", token)
}

export function clearToken() {
  localStorage.removeItem("access_token")
  localStorage.removeItem("refresh_token")
}

export function getShortLink(shortCode) {
  return `${API_URL}/${shortCode}`
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    clearToken()
    throw new Error("Session expired. Please log in again.")
  }

  const res = await fetch(`${API_URL}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  const data = await res.json()

  if (!res.ok) {
    clearToken()
    throw new Error("Session expired. Please log in again.")
  }

  setToken(data.access_token)
  return data.access_token
}

async function request(url, options = {}, retried = false) {
  const res = await fetch(url, options)
  const data = await res.json()

  const hadAuth = options.headers?.Authorization

  if (res.status === 401 && hadAuth && !retried && getRefreshToken()) {
    await refreshAccessToken()
    return request(
      url,
      {
        ...options,
        headers: { ...options.headers, Authorization: `Bearer ${getToken()}` },
      },
      true
    )
  }

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
  setRefreshToken(data.refresh_token)
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
