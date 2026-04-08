/*
 * Admin auth — JWT login UI shared across pages.
 *
 * - Stores token in localStorage under "adminToken"
 * - Renders login button or "Admin ▾" menu in the sidebar
 * - Provides authFetch() helper that attaches the bearer token
 * - Pages that require admin (admin-browser, suspicious) call requireAdmin()
 *   on load and redirect home if no token is present.
 */

const TOKEN_KEY = "adminToken";
const USERNAME_KEY = "adminUsername";

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token, username) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USERNAME_KEY, username);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
}

function isLoggedIn() {
    return !!getToken();
}

/**
 * Fetch wrapper that attaches the admin bearer token.
 * On 401, clears the token and reloads (forces re-login).
 */
async function authFetch(url, options = {}) {
    const token = getToken();
    const headers = new Headers(options.headers || {});
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (options.body && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }
    const resp = await fetch(url, { ...options, headers });
    if (resp.status === 401) {
        clearToken();
        renderAuthUI();
        alert("Přihlášení vypršelo, přihlaš se znovu.");
        window.location.href = "/";
    }
    return resp;
}

/**
 * Pages that strictly require admin call this on load.
 * Redirects home if no token.
 */
function requireAdmin() {
    if (!isLoggedIn()) {
        window.location.href = "/";
    }
}

/**
 * Render the login button (or admin dropdown) into the sidebar.
 * Sidebar must contain a <div id="auth-slot"></div> placeholder.
 * Also reveals or hides any sidebar links marked with data-admin-only.
 */
function renderAuthUI() {
    const slot = document.getElementById("auth-slot");
    if (slot) {
        if (isLoggedIn()) {
            const username = localStorage.getItem(USERNAME_KEY) || "admin";
            slot.innerHTML = `
                <div class="p-3 border-top bg-light">
                    <div class="small text-muted mb-1">Přihlášen jako</div>
                    <div class="fw-bold mb-2">${escapeHtml(username)}</div>
                    <button id="logoutBtn" class="btn btn-sm btn-outline-secondary w-100">Odhlásit</button>
                </div>
            `;
            document.getElementById("logoutBtn").addEventListener("click", logout);
        } else {
            slot.innerHTML = `
                <div class="p-3 border-top bg-light">
                    <button id="loginBtn" class="btn btn-sm btn-primary w-100">Přihlásit (admin)</button>
                </div>
            `;
            document.getElementById("loginBtn").addEventListener("click", showLoginModal);
        }
    }

    // Show/hide admin-only sidebar links
    document.querySelectorAll("[data-admin-only]").forEach(el => {
        el.style.display = isLoggedIn() ? "" : "none";
    });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
}

function showLoginModal() {
    // Build modal once
    let modal = document.getElementById("loginModal");
    if (!modal) {
        const div = document.createElement("div");
        div.innerHTML = `
            <div class="modal fade" id="loginModal" tabindex="-1" aria-hidden="true">
              <div class="modal-dialog modal-sm">
                <div class="modal-content">
                  <div class="modal-header">
                    <h5 class="modal-title">Přihlášení adminů</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                  </div>
                  <div class="modal-body">
                    <form id="loginForm">
                      <div class="mb-2">
                        <label class="form-label small">Username</label>
                        <input type="text" class="form-control form-control-sm" id="loginUsername" autocomplete="username" required>
                      </div>
                      <div class="mb-2">
                        <label class="form-label small">Heslo</label>
                        <input type="password" class="form-control form-control-sm" id="loginPassword" autocomplete="current-password" required>
                      </div>
                      <div id="loginError" class="text-danger small mb-2" style="display:none"></div>
                      <button type="submit" class="btn btn-primary btn-sm w-100">Přihlásit</button>
                    </form>
                  </div>
                </div>
              </div>
            </div>
        `;
        document.body.appendChild(div.firstElementChild);
        modal = document.getElementById("loginModal");
        document.getElementById("loginForm").addEventListener("submit", submitLogin);
    }
    new bootstrap.Modal(modal).show();
    setTimeout(() => document.getElementById("loginUsername").focus(), 200);
}

async function submitLogin(e) {
    e.preventDefault();
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;
    const errBox = document.getElementById("loginError");
    errBox.style.display = "none";

    try {
        const resp = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await resp.json();
        if (!resp.ok) {
            errBox.textContent = data.error || "Přihlášení selhalo";
            errBox.style.display = "";
            return;
        }
        setToken(data.token, data.username);
        bootstrap.Modal.getInstance(document.getElementById("loginModal")).hide();
        renderAuthUI();
    } catch (err) {
        errBox.textContent = "Chyba sítě";
        errBox.style.display = "";
    }
}

function logout() {
    clearToken();
    renderAuthUI();
    // If on admin page, bounce to home
    if (window.location.pathname.startsWith("/admin/")) {
        window.location.href = "/";
    }
}

// Auto-render on load
document.addEventListener("DOMContentLoaded", renderAuthUI);

// Expose globally
window.adminAuth = { authFetch, requireAdmin, isLoggedIn, getToken };
