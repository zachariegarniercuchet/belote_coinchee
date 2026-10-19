(() => {
  "use strict";

  // ------------------------------------------------------------------
  // Comptes optionnels (Supabase) — le même fichier est utilisé par les
  // deux frontends (index.html servi par Flask et frontend-github-pages/).
  //
  // Règle du jeu : aucun compte n'est requis. Sans configuration
  // (window.BELOTE_SUPABASE vide) ou si la bibliothèque ne se charge pas,
  // ce script se tait et l'application reste exactement en mode invité.
  // Aucune clé secrète ici : la clé anon est publique, la protection des
  // données repose sur les politiques RLS de la base Supabase.
  // ------------------------------------------------------------------

  const SUPABASE_JS_URL =
    "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js";
  const cfg = window.BELOTE_SUPABASE || {};

  // API appelée par app.js pour enregistrer la fin d'une partie.
  const api = { enabled: false, session: null, recordGameEnd() {} };
  window.BeloteAuth = api;

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function toast(message) {
    const el = byId("toast");
    if (!el) return;
    el.textContent = message;
    el.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 3200);
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error("script non chargé : " + src));
      document.head.appendChild(script);
    });
  }

  function hideAccountArea() {
    const area = byId("auth-area");
    if (area) area.classList.add("hidden");
  }

  // Sans Supabase configuré, on ne montre strictement aucune trace de compte.
  if (!cfg.url || !cfg.anonKey) {
    hideAccountArea();
    return;
  }

  start().catch(error => {
    // Jamais au prix du jeu : on retombe en invité et on laisse une trace
    // dans la console pour déboguer.
    console.warn("[auth] comptes indisponibles :", error);
    hideAccountArea();
  });

  async function start() {
    if (!window.supabase || !window.supabase.createClient) {
      await loadScript(SUPABASE_JS_URL);
    }
    if (!window.supabase || !window.supabase.createClient) {
      throw new Error("supabase-js introuvable");
    }

    const client = window.supabase.createClient(cfg.url, cfg.anonKey, {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    });

    let session = null;
    let mode = "login";
    const attempts = new Map();   // game_id -> tentatives d'enregistrement
    const savedGames = new Set(); // game_id déjà enregistrés (anti-doublon)

    const MODES = {
      login: {
        title: "Connexion", tabs: true, name: false, email: true, password: true,
        emailLabel: "Email", passwordLabel: "Mot de passe",
        submit: "Se connecter", forgot: true,
        emailAuto: "username", passwordAuto: "current-password",
      },
      signup: {
        title: "Créer un compte", tabs: true, name: true, email: true, password: true,
        emailLabel: "Email", passwordLabel: "Mot de passe (6 caractères minimum)",
        submit: "Créer mon compte", forgot: false,
        emailAuto: "username", passwordAuto: "new-password",
      },
      forgot: {
        title: "Mot de passe oublié", tabs: false, name: false, email: true, password: false,
        emailLabel: "Email du compte", passwordLabel: "",
        submit: "Recevoir le lien par email", forgot: false,
        emailAuto: "username", passwordAuto: "off",
      },
      recovery: {
        title: "Nouveau mot de passe", tabs: false, name: false, email: false, password: true,
        emailLabel: "", passwordLabel: "Nouveau mot de passe",
        submit: "Enregistrer le mot de passe", forgot: false,
        emailAuto: "off", passwordAuto: "new-password",
      },
    };

    const ERRORS_FR = [
      // Codes GoTrue (error_code) — traités avec les messages via humanError().
      ["invalid_credentials", "Email ou mot de passe incorrect."],
      ["user_already_exists", "Un compte existe déjà avec cette adresse email."],
      ["user_not_found", "Aucun compte n'est enregistré avec cette adresse email."],
      ["email_not_confirmed", "Email non confirmé : clique d'abord sur le lien reçu par email."],
      ["weak_password", "Le mot de passe doit contenir au moins 6 caractères."],
      ["email_rate_limit_exceeded", "Trop d'emails envoyés récemment : réessaie dans quelques minutes."],
      ["validation_failed", "Vérifie l'adresse email et le mot de passe."],
      // Messages repris tels quels lorsqu'aucun code n'accompagne l'erreur.
      ["Invalid login credentials", "Email ou mot de passe incorrect."],
      ["User already registered", "Un compte existe déjà avec cette adresse email."],
      ["User not found", "Aucun compte n'est enregistré avec cette adresse email."],
      ["Email not confirmed", "Email non confirmé : clique d'abord sur le lien reçu par email."],
      ["Password should be at least 6 characters", "Le mot de passe doit contenir au moins 6 caractères."],
      ["Signup requires a valid password", "Choisis un mot de passe d'au moins 6 caractères."],
      ["Unable to validate email address", "Cette adresse email n'est pas valide."],
      ["is invalid", "Cette adresse email n'est pas valide."],
      ["email rate limit exceeded", "Trop d'emails envoyés récemment : réessaie dans quelques minutes."],
      ["Invalid Refresh Token", "Session expirée : reconnecte-toi."],
      ["same password", "Choisis un mot de passe différent de l'ancien."],
      // Table absente : PostgREST renvoie PGRST205 « Could not find the table… ».
      ["game_history", "Historique non installé : lance supabase/setup.sql (voir SUPABASE.md)."],
    ];

    function humanError(error) {
      const message = (error && error.message) || String(error || "");
      const code = (error && error.code) || "";
      if (/Failed to fetch|NetworkError|fetch failed|Load failed/i.test(message)) {
        return "Impossible de joindre le service de comptes (connexion internet ?).";
      }
      const haystack = message + " " + code;
      for (const [needle, answer] of ERRORS_FR) {
        if (haystack.indexOf(needle) !== -1) return answer;
      }
      return message || "Une erreur est survenue.";
    }

    function toggle(id, shown) {
      const el = byId(id);
      if (el) el.classList.toggle("hidden", !shown);
    }

    function clearMessages() {
      toggle("auth-error", false);
      toggle("auth-info", false);
    }

    function showError(text) {
      const el = byId("auth-error");
      if (el) {
        el.textContent = text;
        el.classList.remove("hidden");
      }
      toggle("auth-info", false);
    }

    function showInfo(text) {
      const el = byId("auth-info");
      if (el) {
        el.textContent = text;
        el.classList.remove("hidden");
      }
      toggle("auth-error", false);
    }

    // ----------------------------------------------------------------
    // Zone de compte sur l'écran d'accueil
    // ----------------------------------------------------------------
    function displayName() {
      const user = (session && session.user) || {};
      const meta = user.user_metadata || {};
      const raw = String(meta.display_name || meta.full_name || user.email || "").trim();
      if (!raw) return "Connecté·e";
      return raw.indexOf("@") !== -1 ? raw.split("@")[0] : raw;
    }

    function prefillName(name) {
      const value = name.slice(0, 20);
      ["join-name", "create-name"].forEach(id => {
        const input = byId(id);
        if (input && !input.value.trim()) input.value = value;
      });
    }

    function renderAccount() {
      const area = byId("auth-area");
      if (!area) return;
      if (!session) {
        area.innerHTML =
          '<div class="auth-guest">' +
          '<span class="auth-guest-text">Invité · aucun compte requis</span>' +
          '<button type="button" id="btn-auth-open" class="auth-chip auth-chip-primary">Connexion</button>' +
          "</div>" +
          '<span class="auth-hint">Connecte-toi pour conserver ton historique de parties.</span>';
        const open = byId("btn-auth-open");
        if (open) open.onclick = () => openAuth("login");
        return;
      }
      const label = displayName();
      const email = (session.user && session.user.email) || label;
      area.innerHTML =
        '<div class="auth-user-row">' +
        '<span class="auth-user-name" title="' + escapeHtml(email) + '">' + escapeHtml(label) + "</span>" +
        '<button type="button" id="btn-history" class="auth-chip">Mes parties</button>' +
        '<button type="button" id="btn-logout" class="auth-chip">Déconnexion</button>' +
        "</div>";
      const history = byId("btn-history");
      if (history) history.onclick = openHistory;
      const logout = byId("btn-logout");
      if (logout) logout.onclick = signOut;
      prefillName(label);
    }

    async function signOut() {
      const { error } = await client.auth.signOut();
      if (error) {
        toast(humanError(error));
        return;
      }
      toast("Déconnecté — tu joues en invité.");
    }

    // ----------------------------------------------------------------
    // Modale : connexion / inscription / mot de passe oublié / recovery
    // ----------------------------------------------------------------
    function setMode(next) {
      mode = MODES[next] ? next : "login";
      const m = MODES[mode];
      const title = byId("auth-title");
      if (title) title.textContent = m.title;
      toggle("auth-tabs", m.tabs);
      toggle("auth-name-row", m.name);
      toggle("auth-email-row", m.email);
      toggle("auth-password-row", m.password);
      toggle("btn-auth-forgot", m.forgot);
      const emailLabel = byId("auth-email-label");
      if (emailLabel) emailLabel.textContent = m.emailLabel;
      const passwordLabel = byId("auth-password-label");
      if (passwordLabel) passwordLabel.textContent = m.passwordLabel;
      const submit = byId("btn-auth-submit");
      if (submit) submit.textContent = m.submit;
      const email = byId("auth-email");
      if (email) email.setAttribute("autocomplete", m.emailAuto);
      const password = byId("auth-password");
      if (password) password.setAttribute("autocomplete", m.passwordAuto);
      document.querySelectorAll("#auth-tabs .auth-tab").forEach(button => {
        button.classList.toggle("active", button.dataset.mode === mode);
      });
      clearMessages();
    }

    function openAuth(next) {
      setMode(next);
      toggle("auth-overlay", true);
    }

    function closeAuth() {
      toggle("auth-overlay", false);
    }

    document.querySelectorAll("#auth-tabs .auth-tab").forEach(button => {
      button.addEventListener("click", () => setMode(button.dataset.mode));
    });
    const closeAuthButton = byId("btn-auth-close");
    if (closeAuthButton) closeAuthButton.addEventListener("click", closeAuth);
    const forgotButton = byId("btn-auth-forgot");
    if (forgotButton) forgotButton.addEventListener("click", () => setMode("forgot"));
    const authForm = byId("auth-form");
    if (authForm) {
      authForm.addEventListener("submit", event => {
        event.preventDefault();
        submitAuth();
      });
    }

    async function submitAuth() {
      const submit = byId("btn-auth-submit");
      const email = byId("auth-email").value.trim();
      const password = byId("auth-password").value;
      const name = byId("auth-name").value.trim().slice(0, 20);
      clearMessages();

      if (MODES[mode].email && !email) {
        showError("Entre ton adresse email.");
        return;
      }
      if (MODES[mode].password && !password) {
        showError("Entre ton mot de passe.");
        return;
      }
      if (mode === "signup" && password.length < 6) {
        showError("Le mot de passe doit contenir au moins 6 caractères.");
        return;
      }

      if (submit) {
        submit.disabled = true;
        submit.textContent = "…";
      }
      try {
        if (mode === "login") {
          const { error } = await client.auth.signInWithPassword({ email, password });
          if (error) {
            showError(humanError(error));
            return;
          }
          closeAuth();
          toast("Connecté !");
        } else if (mode === "signup") {
          const { data, error } = await client.auth.signUp({
            email,
            password,
            options: { data: { display_name: name || email.split("@")[0] } },
          });
          if (error) {
            showError(humanError(error));
            return;
          }
          if (data && data.session) {
            closeAuth();
            toast("Compte créé, bienvenue " + (name || "") + " !");
          } else {
            setMode("login");
            byId("auth-email").value = email;
            showInfo("Presque ! Ouvre le lien de confirmation envoyé à " + email +
                     ", puis connecte-toi.");
          }
        } else if (mode === "forgot") {
          const { error } = await client.auth.resetPasswordForEmail(email, {
            redirectTo: window.location.origin,
          });
          if (error) {
            showError(humanError(error));
            return;
          }
          setMode("login");
          byId("auth-email").value = email;
          showInfo("Si un compte existe pour " + email +
                   ", un lien de réinitialisation vient d'être envoyé.");
        } else if (mode === "recovery") {
          const { error } = await client.auth.updateUser({ password });
          if (error) {
            showError(humanError(error));
            return;
          }
          closeAuth();
          toast("Mot de passe modifié !");
        }
      } catch (error) {
        showError(humanError(error));
      } finally {
        if (submit) {
          submit.disabled = false;
          submit.textContent = MODES[mode].submit;
        }
      }
    }

    // ----------------------------------------------------------------
    // Historique des parties
    // ----------------------------------------------------------------
    function formatDate(iso) {
      try {
        return new Date(iso).toLocaleDateString("fr-FR", {
          day: "numeric",
          month: "short",
          year: "numeric",
        });
      } catch (error) {
        return "";
      }
    }

    function historyItem(row) {
      const outcome = (row.my_team === null || row.my_team === undefined)
        ? "Sur le plateau"
        : (Number(row.winner_team) === Number(row.my_team) ? "Victoire" : "Défaite");
      const outcomeClass = (row.my_team === null || row.my_team === undefined)
        ? ""
        : (Number(row.winner_team) === Number(row.my_team) ? "history-win" : "history-loss");
      const salon = row.room_code ? " · salon " + escapeHtml(row.room_code) : "";
      return (
        '<div class="history-item">' +
        "<div>" +
        '<div class="hist-when">' + escapeHtml(formatDate(row.played_at)) + salon + "</div>" +
        '<div class="hist-meta ' + outcomeClass + '">' + outcome + " · " +
        escapeHtml(row.donne_count || 0) + " donnes · " + escapeHtml(row.target_score || 0) + " pts</div>" +
        "</div>" +
        '<div class="hist-score" title="Équipe A – Équipe B">' +
        escapeHtml(row.score_a || 0) + " – " + escapeHtml(row.score_b || 0) +
        "</div>" +
        "</div>"
      );
    }

    function renderHistory(rows) {
      const stats = byId("history-stats");
      const list = byId("history-list");
      const decided = rows.filter(row => row.my_team !== null && row.my_team !== undefined);
      const wins = decided.filter(row => Number(row.winner_team) === Number(row.my_team)).length;
      if (stats) {
        stats.innerHTML =
          "<div><b>" + rows.length + "</b>parties</div>" +
          "<div><b>" + wins + "</b>victoires</div>" +
          "<div><b>" + (decided.length - wins) + "</b>défaites</div>";
      }
      if (!list) return;
      if (!rows.length) {
        list.innerHTML =
          '<p class="history-empty">Aucune partie enregistrée pour l\'instant. ' +
          "Ta prochaine partie terminée s'affichera ici, sur n'importe quel appareil.</p>";
        return;
      }
      list.innerHTML = rows.map(historyItem).join("");
    }

    async function openHistory() {
      toggle("history-overlay", true);
      const stats = byId("history-stats");
      const list = byId("history-list");
      if (stats) stats.textContent = "Chargement…";
      if (list) list.innerHTML = "";
      const { data, error } = await client
        .from("game_history")
        .select("played_at, room_code, target_score, donne_count, score_a, score_b, winner_team, my_team")
        .order("played_at", { ascending: false })
        .limit(50);
      if (error) {
        if (stats) stats.textContent = "";
        if (list) {
          list.innerHTML =
            '<p class="history-empty">' + escapeHtml(humanError(error)) + "</p>";
        }
        return;
      }
      renderHistory(data || []);
    }

    const closeHistoryButton = byId("btn-history-close");
    if (closeHistoryButton) {
      closeHistoryButton.addEventListener("click", () => toggle("history-overlay", false));
    }

    // ----------------------------------------------------------------
    // Fin d'une partie : une ligne par partie et par compte connecté.
    // ----------------------------------------------------------------
    api.recordGameEnd = function recordGameEnd(state) {
      if (!session || !state || !state.game_over) return;
      const gameId = state.game_id;
      if (!gameId || savedGames.has(gameId)) return;
      if (state.winner_team === null || state.winner_team === undefined) return;

      const scores = state.cumulative_scores || {};
      const seat = state.your_seat;
      const seatNumber = Number.isInteger(seat) ? seat : null;
      const row = {
        user_id: session.user.id,
        game_id: gameId,
        room_code: state.code || null,
        target_score: Number(state.target_score) || 0,
        donne_count: Number(state.donne_number) || 0,
        score_a: Number(scores["0"]) || 0,
        score_b: Number(scores["1"]) || 0,
        winner_team: Number(state.winner_team),
        my_seat: seatNumber,
        my_team: seatNumber === null ? null : seatNumber % 2,
        players: state.seats_names || null,
      };

      savedGames.add(gameId);
      const tries = (attempts.get(gameId) || 0) + 1;
      attempts.set(gameId, tries);
      client
        .from("game_history")
        .insert(row)
        .then(({ error }) => {
          if (!error) return;
          console.warn("[auth] partie non enregistrée :", error.message);
          // Deux ou trois diffusion sont émises en fin de partie : on autorise
          // une nouvelle tentative, sans boucle infinie en cas d'erreur RLS.
          if (tries < 3) savedGames.delete(gameId);
        });
    };

    // ----------------------------------------------------------------
    // Écoute de session
    // ----------------------------------------------------------------
    client.auth.onAuthStateChange((event, nextSession) => {
      session = nextSession || null;
      api.session = session;
      renderAccount();
      if (event === "PASSWORD_RECOVERY") {
        setMode("recovery");
        toggle("auth-overlay", true);
      }
    });

    const { data } = await client.auth.getSession();
    session = data.session;
    api.session = session;
    api.enabled = true;
    renderAccount();
    const area = byId("auth-area");
    if (area) area.classList.remove("hidden");
  }
})();
