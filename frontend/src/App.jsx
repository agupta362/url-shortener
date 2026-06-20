import { useEffect, useState } from "react"
import {
  clearToken,
  createUrl,
  getShortLink,
  getToken,
  getUrls,
  login,
  register,
} from "./api"

function App() {
  const [page, setPage] = useState(getToken() ? "dashboard" : "login")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  const [longUrl, setLongUrl] = useState("")
  const [customCode, setCustomCode] = useState("")
  const [urls, setUrls] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (page === "dashboard") loadUrls()
  }, [page])

  async function loadUrls() {
    setLoading(true)
    setError("")
    try {
      setUrls(await getUrls())
    } catch (err) {
      handleSessionError(err)
    } finally {
      setLoading(false)
    }
  }

  function handleSessionError(err) {
    setError(err.message)
    if (err.message === "Session expired. Please log in again.") {
      setPage("login")
      setUrls([])
    }
  }

  async function handleRegister(e) {
    e.preventDefault()
    setError("")
    try {
      await register(name, email, password)
      setPage("login")
      setSuccess("Account created. Please log in.")
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleLogin(e) {
    e.preventDefault()
    setError("")
    setSuccess("")
    try {
      await login(email, password)
      setPage("dashboard")
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleCreateUrl(e) {
    e.preventDefault()
    setError("")
    setSuccess("")
    try {
      const result = await createUrl(longUrl, customCode)
      setSuccess(`Short link: ${result.short_url}`)
      setLongUrl("")
      setCustomCode("")
      await loadUrls()
    } catch (err) {
      handleSessionError(err)
    }
  }

  function handleLogout() {
    clearToken()
    setPage("login")
    setUrls([])
    setSuccess("")
    setError("")
  }

  if (page === "login") {
    return (
      <div className="page">
        <h1>URL Shortener</h1>
        {success && <p className="success">{success}</p>}
        {error && <p className="error">{error}</p>}
        <form className="card" onSubmit={handleLogin}>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button type="submit">Log in</button>
        </form>
        <p className="switch">
          No account?{" "}
          <button type="button" className="link" onClick={() => setPage("register")}>
            Sign up
          </button>
        </p>
      </div>
    )
  }

  if (page === "register") {
    return (
      <div className="page">
        <h1>Sign up</h1>
        {error && <p className="error">{error}</p>}
        <form className="card" onSubmit={handleRegister}>
          <label>
            Name
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button type="submit">Create account</button>
        </form>
        <p className="switch">
          Have an account?{" "}
          <button type="button" className="link" onClick={() => setPage("login")}>
            Log in
          </button>
        </p>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="header">
        <h1>Your links</h1>
        <button type="button" className="secondary" onClick={handleLogout}>
          Log out
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}

      <form className="card" onSubmit={handleCreateUrl}>
        <label>
          Long URL
          <input
            type="url"
            value={longUrl}
            onChange={(e) => setLongUrl(e.target.value)}
            placeholder="https://example.com"
            required
          />
        </label>
        <label>
          Custom code (optional)
          <input
            type="text"
            value={customCode}
            onChange={(e) => setCustomCode(e.target.value)}
            placeholder="my-link"
          />
        </label>
        <button type="submit">Shorten</button>
      </form>

      <h2>Saved links</h2>
      {loading && <p>Loading...</p>}
      {!loading && urls.length === 0 && <p className="muted">No links yet.</p>}
      {!loading &&
        urls.map((url) => (
          <div key={url.id} className="url-row">
            <div>
              <a href={getShortLink(url.short_code)} target="_blank" rel="noreferrer">
                {getShortLink(url.short_code)}
              </a>
              <p>{url.original_url}</p>
              <small>{url.clicks} clicks</small>
            </div>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                navigator.clipboard.writeText(getShortLink(url.short_code))
                setSuccess(`Copied: ${getShortLink(url.short_code)}`)
              }}
            >
              Copy
            </button>
          </div>
        ))}
    </div>
  )
}

export default App
