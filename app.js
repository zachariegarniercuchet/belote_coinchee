(() => {
  "use strict";

  // Si ce fichier est servi directement par le serveur Flask (dev local ou
  // Render sert aussi le front), on se connecte a la meme origine : io().
  // Si ce fichier est servi ailleurs (ex. GitHub Pages) et doit appeler un
  // backend distant, definissez window.BELOTE_BACKEND_URL avant de charger
  // ce script, ex. :
  //   <script>window.BELOTE_BACKEND_URL = "https://votre-app.onrender.com";</script>
  const BACKEND_URL = window.BELOTE_BACKEND_URL || "";
  const socket = BACKEND_URL ? io(BACKEND_URL) : io();

  let roomCode = null;
  let myName = null;
  let mySeatChosen = null; // 0-3 ou "board", mémorisé pour se rasseoir après reconnexion
  let lastLobbyState = null;
  let lastRenderedState = null;
  let dismissedDonneNumber = null;
  let recapState = null;
  let recapDonneNumber = null;
  let lastTrickAnimationKey = null;
  let dismissedClaimDonneNumber = null;

  // Bulles d'annonce (enchères / coinche) : elles restent affichées tant que
  // dure la phase d'enchères (la nouvelle annonce d'un joueur remplace la
  // précédente), puis disparaissent une fois la phase terminée.
  const bidBubbleState = { donne: null, count: 0, clearedForPhase: false };
  const beloteBubbleState = { donne: null, count: 0, timer: null };

  // Formulaire d'enchère (popup centrale) : on choisit couleur + montant,
  // puis on valide avec "Confirmer". Mémorisé entre deux state_update.
  const bidFormState = { key: null, suit: null, points: null, isCapot: false };

  // Tenir compte du plateau réellement disponible, y compris en paysage.
  const tableFelt = document.querySelector(".table-felt");
  if (typeof window.ResizeObserver === "function") {
    new window.ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        const cardWidth = Math.max(24, Math.min(62, width * .11, height * .14));
        tableFelt.style.setProperty("--played-card-w", cardWidth + "px");
      }
    }).observe(tableFelt);
  }

  // ------------------------------------------------------------------
  // Navigation entre écrans
  // ------------------------------------------------------------------
  function showScreen(id) {
    document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
    document.getElementById(id).classList.remove("hidden");
  }

  function showToast(message) {
    const el = document.getElementById("toast");
    el.textContent = message;
    el.classList.remove("hidden");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => el.classList.add("hidden"), 3200);
  }

  // ------------------------------------------------------------------
  // Écran accueil
  // ------------------------------------------------------------------
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
      document.getElementById("tab-" + btn.dataset.tab).classList.remove("hidden");
    });
  });

  document.getElementById("btn-create").addEventListener("click", () => {
    const name = document.getElementById("create-name").value.trim();
    if (!name) { showToast("Entre ton prénom."); return; }
    myName = name;
    socket.emit("create_room", { name });
  });

  document.getElementById("btn-join").addEventListener("click", () => {
    const name = document.getElementById("join-name").value.trim();
    const code = document.getElementById("join-code").value.trim().toUpperCase();
    if (!name) { showToast("Entre ton prénom."); return; }
    if (code.length < 4) { showToast("Entre le code du salon (4 caractères)."); return; }
    myName = name;
    roomCode = code;
    socket.emit("join_lobby", { code, name });
  });

  // ------------------------------------------------------------------
  // Lobby
  // ------------------------------------------------------------------
  function enterLobby(code) {
    roomCode = code;
    document.getElementById("lobby-code").textContent = code;
    document.getElementById("lobby-qr").src = "/room/" + code + "/qr.png";
    fetch("/room/" + code + "/info")
      .then(r => r.json())
      .then(d => { document.getElementById("lobby-url").textContent = d.join_url; })
      .catch(() => {});
    showScreen("screen-lobby");
  }

  const SEAT_KEYS = [0, 1, 2, 3, "board"];

  function findBot(botId) {
    return (lastLobbyState && lastLobbyState.available_bots || []).find(b => b.id === botId);
  }

  function botStars(bot) {
    return bot ? "★".repeat(bot.level) + "☆".repeat(5 - bot.level) : "";
  }

  function botAvatarUrl(file) {
    return BACKEND_URL.replace(/\/+$/, "") + "/assets/bots/" + encodeURIComponent(file);
  }

  function botAvatar(file, name, extraClass = "") {
    if (!file) return null;
    const img = document.createElement("img");
    img.className = "bot-avatar " + extraClass;
    img.src = botAvatarUrl(file);
    img.dataset.avatar = file;
    img.alt = "Portrait de " + name;
    img.width = 48;
    img.height = 48;
    img.loading = "lazy";
    img.decoding = "async";
    return img;
  }

  // Identité stable à table : prénom distinct + famille/version du catalogue.
  function botSeatName(botId, seat) {
    const bot = findBot(botId);
    if (!bot) return botId;
    const name = (bot.names && bot.names[seat]) || bot.label;
    return name + " " + botStars(bot);
  }

  function showBotInfo(botId, seat) {
    const bot = findBot(botId);
    if (!bot) return;
    const name = (bot.names && bot.names[seat]) || bot.label;
    const avatar = document.getElementById("bot-info-avatar");
    const portrait = bot.avatars && bot.avatars[seat];
    avatar.classList.toggle("hidden", !portrait);
    if (portrait) {
      avatar.src = botAvatarUrl(portrait);
      avatar.alt = "Portrait de " + name;
    }
    document.getElementById("bot-info-name").textContent = name;
    document.getElementById("bot-info-engine").textContent = "Version : " + bot.label +
      " · Niveau indicatif : " + botStars(bot);
    document.getElementById("bot-info-author").textContent = "Auteur : " + bot.author;
    document.getElementById("bot-info-desc").textContent = bot.description;
    document.getElementById("bot-info-overlay").classList.remove("hidden");
  }

  function hideBotInfo() {
    document.getElementById("bot-info-overlay").classList.add("hidden");
  }

  function renderSeats(state) {
    lastLobbyState = state;
    mySeatChosen = state.your_seat ?? null;
    const wrap = document.getElementById("seats");
    wrap.innerHTML = "";
    const bots = state.available_bots || [];
    const choices = state.bot_choices || {};
    SEAT_KEYS.forEach(key => {
      const info = state.seats[String(key)];
      const row = document.createElement("div");
      row.className = "seat-row";

      const label = document.createElement("div");
      let labelText, teamClass = "";
      if (key === "board") {
        labelText = "🖥️ Plateau (écran partagé)";
      } else {
        labelText = "Joueur " + (key + 1);
        teamClass = key % 2 === 0 ? "team-a" : "team-b";
      }
      const isMine = key === mySeatChosen;
      if (isMine) row.classList.add("mine");

      label.innerHTML =
        '<div class="seat-label ' + teamClass + '">' + labelText + (teamClass ? (key % 2 === 0 ? " · Équipe A" : " · Équipe B") : "") + "</div>" +
        (info.name
          ? '<div class="seat-name">' + escapeHtml(info.name) + (isMine ? " (toi)" : "") + (info.connected ? "" : " · hors ligne") + "</div>"
          : key === "board"
            ? '<div class="seat-empty-label">Libre</div>'
            : '<div class="seat-empty-label">🤖 ' + escapeHtml(botSeatName(choices[String(key)], key)) + "</div>");
      row.appendChild(label);
      if (!info.name && key !== "board") {
        const bot = findBot(choices[String(key)]);
        const avatar = bot && botAvatar(bot.avatars && bot.avatars[key], bot.names[key], "lobby-avatar");
        if (avatar) label.insertBefore(avatar, label.querySelector(".seat-empty-label"));
      }

      const controls = document.createElement("div");
      controls.className = "seat-controls";

      // Sélecteur de bot sous chaque siège vide : le choix est partagé
      // (stocké dans la room, diffusé à tout le lobby via lobby_update).
      if (!info.name && key !== "board" && bots.length) {
        row.classList.add("with-bot");
        const picker = document.createElement("div");
        picker.className = "bot-picker";
        const pickerControls = document.createElement("div");
        pickerControls.className = "bot-picker-controls";
        const select = document.createElement("select");
        select.className = "bot-select";
        select.title = "Choisir une famille et une version de bot";
        select.setAttribute("aria-label", "Version du bot pour le joueur " + (key + 1));
        select.setAttribute("aria-describedby", "bot-summary-" + key);
        const families = new Map();
        bots.forEach(b => {
          const family = b.family || b.label;
          if (!families.has(family)) {
            const group = document.createElement("optgroup");
            group.label = family + (b.theme ? " · " + b.theme : "");
            families.set(family, group);
            select.appendChild(group);
          }
          const opt = document.createElement("option");
          opt.value = b.id;
          opt.textContent = b.label + " " + botStars(b);
          if (b.id === choices[String(key)]) opt.selected = true;
          families.get(family).appendChild(opt);
        });
        select.onchange = () => {
          socket.emit("set_bot", { code: roomCode, seat: key, bot_id: select.value });
        };
        pickerControls.appendChild(select);

        // La fiche détaille la méthode et crédite l'auteur du bot choisi.
        const infoBtn = document.createElement("button");
        infoBtn.className = "info-btn";
        infoBtn.textContent = "ⓘ";
        infoBtn.title = "Méthode et auteur du bot";
        infoBtn.setAttribute("aria-label", "À propos du bot pour le joueur " + (key + 1));
        infoBtn.onclick = () => showBotInfo(select.value, key);
        pickerControls.appendChild(infoBtn);
        picker.appendChild(pickerControls);
        const summary = document.createElement("p");
        summary.className = "bot-summary";
        summary.id = "bot-summary-" + key;
        const selectedBot = findBot(choices[String(key)]);
        summary.textContent = selectedBot
          ? "Par " + selectedBot.author + " — " + selectedBot.description : "";
        picker.appendChild(summary);
        controls.appendChild(picker);
      }

      if (!info.name) {
        const btn = document.createElement("button");
        btn.className = "seat-take-btn";
        btn.textContent = "S'asseoir";
        btn.onclick = () => {
          socket.emit("take_seat", { code: roomCode, seat: key });
        };
        controls.appendChild(btn);
      } else if (isMine) {
        const btn = document.createElement("button");
        btn.className = "seat-take-btn";
        btn.style.background = "transparent";
        btn.style.color = "rgba(247,241,227,.6)";
        btn.textContent = "Se lever";
        btn.onclick = () => {
          socket.emit("leave_seat", { code: roomCode });
        };
        controls.appendChild(btn);
      }

      if (controls.childNodes.length) row.appendChild(controls);

      wrap.appendChild(row);
    });

    if (state.target_score) {
      document.getElementById("target-score").value = String(state.target_score);
    }

    if (state.game_in_progress) {
      showScreen("screen-game");
    }
  }

  document.getElementById("btn-start").addEventListener("click", () => {
    socket.emit("start_game", {
      code: roomCode,
      target_score: parseInt(document.getElementById("target-score").value, 10),
      fill_bots: document.getElementById("fill-bots").checked,
      bots: (lastLobbyState && lastLobbyState.bot_choices) || {},
    });
  });

  document.getElementById("btn-leave-lobby").addEventListener("click", () => {
    location.reload();
  });

  document.getElementById("bot-info-close").addEventListener("click", hideBotInfo);
  document.getElementById("bot-info-overlay").addEventListener("click", e => {
    if (e.target.id === "bot-info-overlay") hideBotInfo();
  });

  function resetGameView() {
    resetBeloteBubbles();
    recapState = null;
    recapDonneNumber = null;
    dismissedDonneNumber = null;
    dismissedClaimDonneNumber = null;
    lastTrickAnimationKey = null;
    bidBubbleState.donne = null;
    bidFormState.key = null;
    document.getElementById("donne-recap").classList.remove("recap-final");
    ["donne-recap", "claim-notice", "last-trick-popup"].forEach(id =>
      document.getElementById(id).classList.add("hidden"));
  }

  document.getElementById("donne-recap").addEventListener("click", event => {
    if (!event.target.closest("#btn-new-game")) return;
    event.stopPropagation();
    if (!lastRenderedState || !lastRenderedState.game_over) return;
    resetGameView();
    socket.emit("new_game", { code: roomCode });
    showScreen("screen-lobby");
  });

  // ------------------------------------------------------------------
  // Socket events — salon
  // ------------------------------------------------------------------
  socket.on("room_created", data => {
    roomCode = data.code;
    myName = data.name;
    enterLobby(data.code);
  });

  socket.on("lobby_joined", data => {
    roomCode = data.code;
    enterLobby(data.code);
    renderSeats(data);
  });

  socket.on("lobby_update", data => {
    if (data.code !== roomCode) return;
    renderSeats(data);
  });

  socket.on("game_started", () => {
    resetGameView();
    showScreen("screen-game");
  });

  socket.on("error_message", d => showToast(d.message));

  socket.on("connect", () => {
    if (roomCode && myName) {
      socket.emit("join_lobby", { code: roomCode, name: myName });
      if (mySeatChosen !== null) {
        socket.emit("take_seat", { code: roomCode, seat: mySeatChosen });
      }
      socket.emit("request_state", { code: roomCode });
    }
  });

  // ------------------------------------------------------------------
  // Écran de jeu
  // ------------------------------------------------------------------
  function nameOf(state, seat) {
    if (seat === null || seat === undefined) return "";
    const n = state.seats_names[String(seat)];
    return n || ("Joueur " + (seat + 1));
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function cardEl(card, extraClasses) {
    const div = document.createElement("div");
    div.className = "playing-card " + card.color + (extraClasses ? " " + extraClasses : "");
    div.innerHTML =
      '<div class="pc-rank">' + card.rank + "</div>" +
      '<div class="pc-suit">' + card.symbol + "</div>";
    return div;
  }

  function claimVisible(state) {
    return !!(state && state.claim && dismissedClaimDonneNumber !== state.donne_number &&
      (!state.board_present || state.your_seat === "board"));
  }

  function renderClaim(state) {
    const visible = claimVisible(state);
    document.querySelector(".table-felt").classList.toggle("claim-visible", visible);
    document.getElementById("claim-notice").classList.toggle("hidden", !visible);
    if (!visible) return;
    const claim = state.claim;
    document.getElementById("claim-title").textContent = nameOf(state, claim.seat) + " table !";
    const count = claim.remaining_tricks;
    const reason = claim.reason === "trumps"
      ? "Il ne lui reste que des atouts, et personne d’autre n’en a."
      : "Il n’y a plus d’atouts et toutes ses cartes sont maîtresses.";
    document.getElementById("claim-detail").textContent =
      reason + (count === 1 ? " Le dernier pli est" : " Les " + count + " derniers plis sont") +
      " pour l’équipe " + (claim.seat % 2 === 0 ? "A" : "B") + ".";
    document.getElementById("last-trick-popup").classList.add("hidden");
  }

  document.getElementById("btn-claim-scores").addEventListener("click", event => {
    event.stopPropagation();
    if (!lastRenderedState) return;
    dismissedClaimDonneNumber = lastRenderedState.donne_number;
    renderGame(lastRenderedState);
  });

  function renderGame(state) {
    lastRenderedState = state;
    if (state.your_seat !== undefined && state.your_seat !== "board") {
      mySeatChosen = state.your_seat;
    } else if (state.your_seat === "board") {
      mySeatChosen = "board";
    }

    document.getElementById("game-code").textContent = roomCode;
    document.getElementById("score-a").textContent = state.cumulative_scores["0"];
    document.getElementById("score-b").textContent = state.cumulative_scores["1"];
    document.getElementById("target-display").textContent = state.target_score;

    const isBoard = state.your_seat === "board";
    // Mode manette : un siège "plateau" est pris (tablette au centre) et je
    // suis un joueur sur téléphone -> pas de plateau, juste statut + enchère + main.
    const controllerMode = !isBoard && !!state.board_present;
    const boardPanel = document.getElementById("board-panel");
    const phonePanel = document.getElementById("phone-panel");
    const felt = boardPanel.querySelector(".table-felt");
    const bidControls = document.getElementById("bid-controls");
    const handCards = document.getElementById("hand-cards");
    if (controllerMode) {
      boardPanel.classList.add("hidden");
      phonePanel.classList.remove("hidden");
      document.getElementById("phone-bid-slot").appendChild(bidControls);
      document.getElementById("phone-hand-slot").appendChild(handCards);
    } else {
      phonePanel.classList.add("hidden");
      boardPanel.classList.remove("hidden");
      felt.appendChild(bidControls);
      felt.appendChild(handCards);
    }

    renderBoardPanel(state);
    if (!isBoard) renderHandPanel(state);

    renderClaim(state);
    renderDonneRecap(state);
  }

  function renderBoardPanel(state) {
    lastRenderedState = state;
    // Les identifiants restent ceux du jeu ; seule la position visuelle tourne.
    // Le plateau partagé conserve la vue de référence du siège 0.
    const viewer = Number.isInteger(state.your_seat) ? state.your_seat : 0;

    for (let seat = 0; seat < 4; seat++) {
      const marker = document.getElementById("seat-marker-" + seat);
      const position = String((seat - viewer + 4) % 4);
      marker.dataset.position = position;
      document.getElementById("trick-slot-" + seat).dataset.position = position;
      const name = nameOf(state, seat) + (state.your_seat === seat ? " (toi)" : "");

      let nameHtml = escapeHtml(name);
      if (state.contract && state.contract.player === seat) {
        const c = state.contract;
        const color = (c.suit === "COEUR" || c.suit === "CARREAU") ? "#e0576a" : "#f7f1e3";
        let tag = (c.is_capot ? "Capot" : c.points) + " " + c.symbol;
        if (c.coinche_state === "COINCHE") tag += " (coinché)";
        if (c.coinche_state === "SURCOINCHE") tag += " (surcoinché)";
        nameHtml += ' <span class="contract-tag" style="color:' + color + '">' + escapeHtml(tag) + "</span>";
      }

      let nameEl = marker.querySelector(".sm-name");
      if (!nameEl) {
        nameEl = document.createElement("div");
        nameEl.className = "sm-name";
        marker.prepend(nameEl);
      }
      nameEl.innerHTML = nameHtml;
      // Les profils explicites du serveur concernent les bots, jamais les humains.
      const profile = state.bot_profiles && state.bot_profiles[String(seat)];
      let avatar = marker.querySelector(".seat-avatar");
      if (!profile || !profile.avatar) {
        if (avatar) avatar.remove();
      } else if (!avatar || avatar.dataset.avatar !== profile.avatar) {
        if (avatar) avatar.remove();
        avatar = botAvatar(profile.avatar, nameOf(state, seat), "seat-avatar");
        marker.insertBefore(avatar, nameEl);
      }
      marker.classList.toggle("has-bot-avatar", !!(profile && profile.avatar));
      // Laisser la bulle attachée : seules les nouvelles annonces la rejouent.
      marker.querySelectorAll(".claimed-hand").forEach(row => row.remove());
      marker.classList.toggle("active-turn", state.waiting_seat === seat);
      marker.classList.toggle("dealer", state.dealer === seat);
      marker.classList.toggle("claim-winner", claimVisible(state) && state.claim.seat === seat);
      if (claimVisible(state)) {
        const row = document.createElement("div");
        row.className = "claimed-hand";
        row.setAttribute("aria-label", "Cartes restantes de " + nameOf(state, seat));
        (state.claim.hands[String(seat)] || []).forEach(card => row.appendChild(cardEl(card, "small")));
        marker.appendChild(row);
      }
    }

    renderTrickPile(state);
    renderPlayedCards(state);
    handleBidBubbles(state);
    handleBeloteBubbles(state);

    const tricksInfo = document.getElementById("tricks-info");
    let turnTxt = "";
    if (state.your_turn) {
      turnTxt = state.waiting_kind === "bid" ? " · À toi d'enchérir !" : " · À toi de jouer !";
    } else if (state.waiting_seat !== null && state.waiting_seat !== undefined) {
      turnTxt = " · Tour de " + nameOf(state, state.waiting_seat);
    }
    tricksInfo.textContent =
      "Donne n°" + (state.donne_number || 1) +
      " · Plis — Équipe A " + state.tricks_won_this_donne["0"] +
      " · Équipe B " + state.tricks_won_this_donne["1"] +
      ((state.belote_team !== null && state.belote_team !== undefined)
        ? " · Belote Équipe " + (String(state.belote_team) === "0" ? "A" : "B") + " (+20)" : "") +
      turnTxt;
  }

  // ------------------------------------------------------------------
  // Pli ramassé : pile cliquable en haut à droite (dernier pli uniquement)
  // ------------------------------------------------------------------
  function trickCollectionDelay(state) {
    const lastTrick = state.tricks_won_this_donne["0"] + state.tricks_won_this_donne["1"] === 8;
    // Synchronisé avec LAST_TRICK_EXTRA_PAUSE côté serveur : une seconde de plus.
    return 350 + (lastTrick ? 1000 : 0);
  }

  function renderPlayedCards(state) {
    const current = state.current_trick || [];
    const plays = claimVisible(state) ? [] : (current.length ? current : state.completed_trick || []);
    const collecting = !current.length && plays.length === 4;
    const winner = state.last_completed_trick_winner_seat;
    const key = state.donne_number + ":" + plays.map(p => p.seat + ":" + p.card.id).join(",");
    const cards = [];

    for (let seat = 0; seat < 4; seat++) {
      const slot = document.getElementById("trick-slot-" + seat);
      const play = plays.find(p => p.seat === seat);
      const cardKey = play ? state.donne_number + ":" + play.card.id : null;
      let card = slot.firstElementChild;
      // Ne pas recréer le pli ni relancer sa pause sur une diffusion identique.
      if (!play || !card || card.dataset.playedKey !== cardKey) {
        slot.innerHTML = "";
        card = play ? cardEl(play.card, "small") : null;
        if (card) {
          card.dataset.playedKey = cardKey;
          slot.appendChild(card);
        }
      }
      slot.classList.toggle("collecting", collecting);
      if (card) cards.push(card);
    }

    if (!collecting || !Number.isInteger(winner) || cards.every(card => card.dataset.collectionKey === key)) return;
    const pile = document.querySelector("#trick-pile-" + (winner % 2 === 0 ? "a" : "b") + " .trick-pile-card");
    const target = pile.getBoundingClientRect();
    const rects = cards.map(card => card.getBoundingClientRect());
    const centerX = rects.reduce((sum, r) => sum + r.left + r.width / 2, 0) / cards.length;
    const centerY = rects.reduce((sum, r) => sum + r.top + r.height / 2, 0) / cards.length;
    cards.forEach((card, index) => {
      const rect = rects[index];
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const stackOffset = (index - 1.5) * 2;
      card.style.setProperty("--gather-x", (centerX + stackOffset - x) + "px");
      card.style.setProperty("--gather-y", (centerY + stackOffset - y) + "px");
      card.style.setProperty("--collect-x", (target.left + target.width / 2 - x) + "px");
      card.style.setProperty("--collect-y", (target.top + target.height / 2 - y) + "px");
      card.style.setProperty("--collect-delay", trickCollectionDelay(state) + "ms");
      card.dataset.collectionKey = key;
      card.classList.add("trick-flying");
    });
  }

  function renderTrickPile(state) {
    const piles = [document.getElementById("trick-pile-a"), document.getElementById("trick-pile-b")];
    const popup = document.getElementById("last-trick-popup");
    const hasLastTrick = state.last_completed_trick && state.last_completed_trick.length;
    const winnerSeat = state.last_completed_trick_winner_seat;
    const winnerTeam = winnerSeat === null || winnerSeat === undefined ? null : winnerSeat % 2;

    piles.forEach((pile, team) => {
      const count = state.tricks_won_this_donne[String(team)] || 0;
      pile.classList.toggle("clickable", hasLastTrick && winnerTeam === team);
      pile.classList.toggle("pile-winner", hasLastTrick && winnerTeam === team);
      pile.querySelector(".trick-pile-count").textContent = count + (count === 1 ? " pli" : " plis");
    });

    if (!hasLastTrick) {
      popup.classList.add("hidden");
    }

    const animationKey = state.donne_number + ":" + (state.tricks_won_this_donne["0"] || 0) + ":" + (state.tricks_won_this_donne["1"] || 0);
    if (hasLastTrick && animationKey !== lastTrickAnimationKey) {
      lastTrickAnimationKey = animationKey;
      const pile = piles[winnerTeam];
      pile.style.setProperty("--pile-arrival-delay", trickCollectionDelay(state) + 1000 + "ms");
      pile.classList.remove("pile-arrival");
      void pile.offsetWidth;
      pile.classList.add("pile-arrival");
    }

    if (!popup.classList.contains("hidden")) {
      renderLastTrickPopup(state);
    }
  }

  function renderLastTrickPopup(state) {
    const content = document.getElementById("last-trick-popup-content");
    content.innerHTML = "";
    if (!state.last_completed_trick || !state.last_completed_trick.length) return;

    const title = document.createElement("div");
    title.className = "last-trick-title";
    title.textContent = "Dernier pli · Équipe " + (state.last_completed_trick_winner_seat % 2 === 0 ? "A" : "B");
    content.appendChild(title);

    const row = document.createElement("div");
    row.className = "last-trick-row";
    state.last_completed_trick.forEach(p => {
      const slot = document.createElement("div");
      slot.className = "card-slot";
      slot.appendChild(cardEl(p.card, "small"));
      const label = document.createElement("div");
      label.textContent = nameOf(state, p.seat) +
        (state.last_completed_trick_winner_seat === p.seat ? " 🏆" : "");
      slot.appendChild(label);
      row.appendChild(slot);
    });
    content.appendChild(row);
  }

  ["trick-pile-a", "trick-pile-b"].forEach(id => document.getElementById(id).addEventListener("click", event => {
    if (!event.currentTarget.classList.contains("clickable")) return;
    const popup = document.getElementById("last-trick-popup");
    const willShow = popup.classList.contains("hidden");
    if (willShow && lastRenderedState) {
      renderLastTrickPopup(lastRenderedState);
      popup.classList.remove("hidden");
    } else {
      popup.classList.add("hidden");
    }
  }));

  // ------------------------------------------------------------------
  // Bulles d'annonce pendant les enchères ("90 ♦", "Coinché"...)
  // ------------------------------------------------------------------
  function handleBidBubbles(state) {
    if (state.donne_number !== bidBubbleState.donne) {
      bidBubbleState.donne = state.donne_number;
      bidBubbleState.count = 0;
      bidBubbleState.clearedForPhase = false;
      document.querySelectorAll(".speech-bubble").forEach(b => b.remove());
    }

    if (state.phase !== "bidding") {
      // La phase d'enchères est terminée : les bulles laissent place à
      // l'étiquette de contrat affichée à côté du nom du preneur.
      if (!bidBubbleState.clearedForPhase) {
        document.querySelectorAll(".speech-bubble").forEach(b => b.remove());
        bidBubbleState.clearedForPhase = true;
      }
      return;
    }

    const hist = state.bidding_history || [];
    if (hist.length > bidBubbleState.count) {
      hist.slice(bidBubbleState.count).forEach(h => showBidBubble(h.seat, h));
      bidBubbleState.count = hist.length;
    }
  }

  function resetBeloteBubbles(donne = null) {
    clearTimeout(beloteBubbleState.timer);
    beloteBubbleState.donne = donne;
    beloteBubbleState.count = 0;
    beloteBubbleState.timer = null;
    document.querySelectorAll(".belote-bubble").forEach(bubble => bubble.remove());
  }

  function handleBeloteBubbles(state) {
    if (beloteBubbleState.donne !== state.donne_number) resetBeloteBubbles(state.donne_number);
    const announcements = state.belote_announcements || [];
    if (announcements.length <= beloteBubbleState.count) return;
    beloteBubbleState.count = announcements.length;
    if (state.phase !== "trick") return;

    const entry = announcements[announcements.length - 1];
    const plays = (state.current_trick && state.current_trick.length
      ? state.current_trick : state.completed_trick) || [];
    // À la reconnexion, ne pas rejouer une annonce dont la carte a déjà été ramassée.
    if (!plays.some(play => play.seat === entry.seat && play.card.id === entry.card_id)) return;
    clearTimeout(beloteBubbleState.timer);
    showBidBubble(entry.seat, { type: "BELOTE", label: entry.label });
    const bubble = document.querySelector("#seat-marker-" + entry.seat + " .speech-bubble");
    bubble.classList.add("belote-bubble");
    bubble.setAttribute("role", "status");
    beloteBubbleState.timer = setTimeout(() => bubble.remove(), 3200);
  }

  function showBidBubble(seat, entry) {
    const marker = document.getElementById("seat-marker-" + seat);
    if (!marker) return;

    let bubble = marker.querySelector(".speech-bubble");
    if (!bubble) {
      bubble = document.createElement("div");
      bubble.className = "speech-bubble";
      marker.appendChild(bubble);
    }
    bubble.textContent = entry.label;
    // Comme sur les cartes : rouge pour cœur/carreau, noir pour pique/trèfle.
    if (entry.type === "ENCHERE" && entry.suit) {
      bubble.style.color = (entry.suit === "COEUR" || entry.suit === "CARREAU") ? "#b3273a" : "#1a1a1a";
    } else {
      bubble.style.color = "";
    }
    bubble.classList.remove("fade-out");
    bubble.classList.add("visible");
    // Une nouvelle annonce, même identique (« Passe »), doit se voir.
    bubble.classList.remove("announcement-replay");
    void bubble.offsetWidth;
    bubble.classList.add("announcement-replay");
  }

  function animateHandReorder(previous, cards, handWrap) {
    const ids = new Set(cards.map(card => card.id));
    const oldOrder = Array.from(previous.keys()).filter(id => ids.has(id));
    const newOrder = cards.map(card => card.id).filter(id => previous.has(id));
    if (oldOrder.join(",") === newOrder.join(",") ||
        (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches)) return;

    // Les mêmes éléments DOM passent de leur ancienne position à la nouvelle.
    // Capturer la position visuelle permet aussi de repartir d'une animation en cours.
    Array.from(handWrap.children).forEach(el => {
      const old = previous.get(el.dataset.cardId);
      if (!old || !old.rect.width || typeof el.animate !== "function") return;
      el.getAnimations().forEach(animation => animation.cancel());
      const rect = el.getBoundingClientRect();
      const dx = old.rect.left - rect.left;
      const dy = old.rect.top - rect.top;
      if (Math.abs(dx) + Math.abs(dy) < 0.5) return;
      const computed = getComputedStyle(el).transform;
      const base = computed === "none" ? "" : computed;
      el.animate([
        { transform: "translate(" + dx + "px," + dy + "px) " + base },
        { transform: base || "none" },
      ], { duration: 420, easing: "cubic-bezier(.22,.61,.36,1)" });
    });
  }

  function renderHandPanel(state) {
    const phoneStatus = document.getElementById("phone-status");
    if (phoneStatus) {
      const c = state.contract;
      const cTxt = c ? ("Contrat " + (c.is_capot ? "Capot" : c.points) + " " + c.symbol) : "Enchères…";
      let turn = "";
      if (state.your_turn) turn = state.waiting_kind === "bid" ? "À toi d'enchérir !" : "À toi de jouer !";
      else if (state.waiting_seat !== null && state.waiting_seat !== undefined) turn = "Tour de " + nameOf(state, state.waiting_seat);
      phoneStatus.textContent = cTxt + " · Plis A" + state.tricks_won_this_donne["0"] +
        "-B" + state.tricks_won_this_donne["1"] + (turn ? " · " + turn : "");
    }
    const bidControls = document.getElementById("bid-controls");
    if (state.your_turn && state.waiting_kind === "bid" && state.legal_bid_actions.length) {
      bidControls.classList.remove("hidden");
      renderBidControls(state);
    } else {
      bidControls.classList.add("hidden");
      bidControls.innerHTML = "";
    }

    const handWrap = document.getElementById("hand-cards");
    const previous = new Map(Array.from(handWrap.children).map(el => [
      el.dataset.cardId, { el, rect: el.getBoundingClientRect() },
    ]));
    const ids = new Set(state.your_hand.map(card => card.id));
    previous.forEach((old, id) => { if (!ids.has(id)) old.el.remove(); });
    const cardMode = state.your_turn && state.waiting_kind === "card";
    const n = state.your_hand.length;
    const center = (n - 1) / 2;
    state.your_hand.forEach((card, i) => {
      const legal = cardMode && state.legal_card_ids.includes(card.id);
      const cls = cardMode ? (legal ? "legal" : "disabled") : "";
      const old = previous.get(card.id);
      const el = old ? old.el : cardEl(card, cls);
      el.dataset.cardId = card.id;
      el.className = "playing-card " + card.color + (cls ? " " + cls : "");
      const off = i - center;
      el.style.setProperty("--r", (off * 7).toFixed(1) + "deg");
      el.style.setProperty("--y", (Math.abs(off) * Math.abs(off) * 2.2).toFixed(1) + "px");
      el.style.zIndex = String(i);
      if (!old) {
        const isPlayable = () => lastRenderedState && lastRenderedState.your_turn &&
          lastRenderedState.waiting_kind === "card" && lastRenderedState.legal_card_ids.includes(card.id);
        let downX = 0, downY = 0, dx = 0, dy = 0, isDown = false, isDrag = false;
        el.addEventListener("pointerdown", e => {
          if (!isPlayable()) return;
          isDown = true; isDrag = false; dx = 0; dy = 0;
          downX = e.clientX; downY = e.clientY;
          try { el.setPointerCapture(e.pointerId); } catch (_) {}
        });
        el.addEventListener("pointermove", e => {
          if (!isDown) return;
          dx = e.clientX - downX; dy = e.clientY - downY;
          if (Math.abs(dx) + Math.abs(dy) > 10) {
            isDrag = true;
            el.classList.add("dragging");
            el.style.transform = "translate(" + dx + "px," + dy + "px) scale(1.08)";
          }
        });
        const resetDrag = () => {
          isDown = false;
          el.classList.remove("dragging");
          el.style.transform = "";
        };
        el.addEventListener("pointerup", e => {
          if (!isDown) return;
          const wasDrag = isDrag;
          const upDy = e.clientY - downY;
          resetDrag();
          if (!isPlayable()) return;
          if (wasDrag) {
            // Glissé vers le plateau (vers le haut) = jouer la carte.
            if (upDy < -60) socket.emit("play_card", { code: roomCode, card_id: card.id });
          } else {
            // Simple tap / clic = jouer la carte.
            socket.emit("play_card", { code: roomCode, card_id: card.id });
          }
        });
        el.addEventListener("pointercancel", resetDrag);
      }
      if (handWrap.children[i] !== el) handWrap.insertBefore(el, handWrap.children[i] || null);
    });
    animateHandReorder(previous, state.your_hand, handWrap);
  }

  function renderBidControls(state) {
    const actions = state.legal_bid_actions;
    const container = document.getElementById("bid-controls");
    const turnKey = state.donne_number + ":" + state.your_seat + ":" + (state.bidding_history || []).length;
    const key = turnKey + "|" + actions.map(a => a.index + ":" + a.type + ":" + (a.suit || "") + ":" + (a.points == null ? "" : a.points) + ":" + (a.is_capot ? "C" : "")).join("|");
    if (bidFormState.key !== key) {
      bidFormState.key = key;
      bidFormState.points = null;
      bidFormState.isCapot = false;
      const teamSeats = Number.isInteger(state.your_seat)
        ? [state.your_seat, (state.your_seat + 2) % 4] : [];
      const teamBid = (state.bidding_history || []).slice().reverse().find(entry =>
        teamSeats.includes(entry.seat) && entry.type === "ENCHERE" && entry.suit);
      const firstEnchere = (teamBid && actions.find(a =>
        a.type === "ENCHERE" && a.suit === teamBid.suit)) ||
        actions.find(a => a.type === "ENCHERE");
      bidFormState.suit = firstEnchere ? firstEnchere.suit : null;
    }
    container.innerHTML = "";

    const title = document.createElement("h3");
    title.className = "bid-title";
    title.textContent = "Que prends-tu ?";
    container.appendChild(title);

    const passAction = actions.find(a => a.type === "PASSE");
    const coincheAction = actions.find(a => a.type === "COINCHE");
    const surcoincheAction = actions.find(a => a.type === "SURCOINCHE");
    const enchereActions = actions.filter(a => a.type === "ENCHERE");

    if (enchereActions.length) {
      const suits = [];
      const seenSuits = {};
      enchereActions.forEach(a => {
        if (!seenSuits[a.suit]) {
          seenSuits[a.suit] = true;
          suits.push({ name: a.suit, symbol: a.symbol });
        }
      });
      if (!suits.find(s => s.name === bidFormState.suit)) bidFormState.suit = suits[0].name;

      const pointsSet = new Set();
      let hasCapot = false;
      enchereActions.forEach(a => {
        if (a.is_capot) hasCapot = true;
        else if (a.points != null) pointsSet.add(a.points);
      });

      const suitRow = document.createElement("div");
      suitRow.className = "bid-suit-row";
      const suitButtons = {};
      suits.forEach(s => {
        const btn = document.createElement("button");
        btn.className = "bid-suit-btn" + (s.name === bidFormState.suit ? " selected" : "");
        btn.textContent = s.symbol;
        btn.style.color = (s.name === "COEUR" || s.name === "CARREAU") ? "#e0576a" : "#f7f1e3";
        btn.onclick = () => {
          bidFormState.suit = s.name;
          Object.entries(suitButtons).forEach(([name, b]) => b.classList.toggle("selected", name === s.name));
          refreshConfirm();
        };
        suitButtons[s.name] = btn;
        suitRow.appendChild(btn);
      });
      container.appendChild(suitRow);

      const amounts = Array.from(pointsSet).sort((a, b) => a - b).map(points =>
        ({ label: String(points), points, isCapot: false }));
      if (hasCapot) amounts.push({ label: "Capot", points: null, isCapot: true });
      // TODO Générale : les huit plis par le seul annonceur ; règles et score à définir.
      // amounts.push({ label: "Générale", points: null, isCapot: false, isGenerale: true });
      let amountIndex = amounts.findIndex(amount =>
        amount.points === bidFormState.points && amount.isCapot === bidFormState.isCapot);
      if (amountIndex < 0) amountIndex = 0;

      const amountRow = document.createElement("div");
      amountRow.className = "bid-amount-row";
      const decrease = document.createElement("button");
      decrease.className = "bid-chip bid-step-btn";
      decrease.textContent = "−";
      decrease.setAttribute("aria-label", "Diminuer l’enchère");
      const amountDisplay = document.createElement("output");
      amountDisplay.className = "bid-amount";
      amountDisplay.setAttribute("aria-live", "polite");
      amountDisplay.setAttribute("aria-label", "Montant du contrat");
      const increase = document.createElement("button");
      increase.className = "bid-chip bid-step-btn";
      increase.textContent = "+";
      increase.setAttribute("aria-label", "Augmenter l’enchère");
      const selectAmount = index => {
        amountIndex = Math.max(0, Math.min(amounts.length - 1, index));
        const amount = amounts[amountIndex];
        bidFormState.points = amount.points;
        bidFormState.isCapot = amount.isCapot;
        amountDisplay.textContent = amount.label;
        decrease.disabled = amountIndex === 0;
        increase.disabled = amountIndex === amounts.length - 1;
        refreshConfirm();
      };
      decrease.onclick = () => selectAmount(amountIndex - 1);
      increase.onclick = () => selectAmount(amountIndex + 1);
      amountRow.appendChild(decrease);
      amountRow.appendChild(amountDisplay);
      amountRow.appendChild(increase);
      container.appendChild(amountRow);

      const confirmBtn = document.createElement("button");
      confirmBtn.className = "bid-chip bid-confirm-btn";
      confirmBtn.textContent = "Confirmer";
      const refreshConfirm = () => {
        const ok = bidFormState.suit && (bidFormState.isCapot || bidFormState.points != null) &&
          enchereActions.some(a => a.suit === bidFormState.suit && !!a.is_capot === bidFormState.isCapot &&
            (bidFormState.isCapot || a.points === bidFormState.points));
        confirmBtn.disabled = !ok;
      };
      confirmBtn.onclick = () => {
        const match = enchereActions.find(a => a.suit === bidFormState.suit && !!a.is_capot === bidFormState.isCapot &&
          (bidFormState.isCapot || a.points === bidFormState.points));
        if (match) socket.emit("bid_choice", { code: roomCode, index: match.index });
      };
      selectAmount(amountIndex);
      container.appendChild(confirmBtn);
    }

    const actionsRow = document.createElement("div");
    actionsRow.className = "bid-actions-row";
    if (passAction) {
      const b = document.createElement("button");
      b.className = "bid-chip pass";
      b.textContent = "Passer";
      b.onclick = () => socket.emit("bid_choice", { code: roomCode, index: passAction.index });
      actionsRow.appendChild(b);
    }
    if (coincheAction) {
      const b = document.createElement("button");
      b.className = "bid-chip coinche";
      b.textContent = "Coincher";
      b.onclick = () => socket.emit("bid_choice", { code: roomCode, index: coincheAction.index });
      actionsRow.appendChild(b);
    }
    if (surcoincheAction) {
      const b = document.createElement("button");
      b.className = "bid-chip coinche";
      b.textContent = "Surcoincher";
      b.onclick = () => socket.emit("bid_choice", { code: roomCode, index: surcoincheAction.index });
      actionsRow.appendChild(b);
    }
    if (actionsRow.childNodes.length) container.appendChild(actionsRow);
  }

  function isFinalRecap(state) {
    return !!(state && (state.final_donne || state.game_over));
  }

  function renderDonneRecap(state) {
    const overlay = document.getElementById("donne-recap");
    if (claimVisible(state)) {
      overlay.classList.add("hidden");
      return;
    }
    const content = document.getElementById("donne-recap-content");
    const canViewRecap = !state.board_present || state.your_seat === "board" || isFinalRecap(state);
    if (!canViewRecap) {
      overlay.classList.add("hidden");
      return;
    }
    if (state.last_donne_result && (state.donne_number !== recapDonneNumber || isFinalRecap(state))) {
      recapState = state;
      recapDonneNumber = state.donne_number;
    }

    const finalRecap = isFinalRecap(recapState);
    overlay.classList.toggle("recap-final", finalRecap);
    if (recapState && (finalRecap || dismissedDonneNumber !== recapDonneNumber)) {
      const r = recapState.last_donne_result;
      const c = recapState.contract;
      const contractLine = c
        ? "Contrat : " + (c.is_capot ? "Capot" : c.points) + " " + c.symbol + " (" + nameOf(recapState, c.player) + ")"
        : "";
      const teamA = nameOf(recapState, 0) + " et " + nameOf(recapState, 2);
      const teamB = nameOf(recapState, 1) + " et " + nameOf(recapState, 3);
      const rows = (recapState.score_history || []).map(score =>
        "<tr><td>" + score["0"] + "</td><td>" + score["1"] + "</td></tr>"
      ).join("");
      const dixVal = r.dix_de_der_value || 10;
      const belVal = r.belote_bonus || 20;
      const totalOf = (tk) => (r.total_points ? r.total_points[tk]
        : (r.raw_points[tk] + ((r.dix_de_der_team !== null && String(r.dix_de_der_team) === tk) ? dixVal : 0)
          + ((r.belote_team !== null && String(r.belote_team) === tk) ? belVal : 0)));
      const detailTextOf = (tk) => {
        let txt = "Plis " + r.raw_points[tk];
        if (r.dix_de_der_team !== null && String(r.dix_de_der_team) === tk) txt += " + dix de der " + dixVal;
        if (r.belote_team !== null && String(r.belote_team) === tk) txt += " + belote " + belVal;
        txt += " = " + totalOf(tk);
        return txt;
      };
      const preneurLabel = "Équipe " + (String(r.preneur_team) === "0" ? "A" : "B");
      const f0 = r.final_scores ? r.final_scores["0"] : 0;
      const f1 = r.final_scores ? r.final_scores["1"] : 0;
      const markedLine = "Points marqués : Équipe A +" + f0 + " · Équipe B +" + f1;
      content.innerHTML =
        (finalRecap ? "<h2>Fin de la partie</h2>" : "<h2>Fin de la donne</h2>") +
        (finalRecap ? '<p class="final-winner" role="status">Équipe ' +
          (recapState.winner_team === 0 ? "A" : "B") + " remporte la partie !</p>" +
          '<p class="score-caption">Dernière donne · n°' + recapDonneNumber + "</p>" : "") +
        '<p class="result-line">' + escapeHtml(contractLine) + "</p>" +
        '<p class="result-line">Équipe A — <span class="pts-toggle" data-team="0" title="' + detailTextOf("0") + '"><strong>' + totalOf("0") + "</strong></span></p>" +
        '<p class="result-line">Équipe B — <span class="pts-toggle" data-team="1" title="' + detailTextOf("1") + '"><strong>' + totalOf("1") + "</strong></span></p>" +
        '<div class="pts-detail hidden" id="pts-detail"></div>' +
        '<p class="result-line result-outcome ' + (r.contract_reached ? "success" : "failed") + '">' +
        (r.contract_reached ? "Contrat réussi (" + preneurLabel + ")" : "Contrat raté (" + preneurLabel + " : 0)") + "</p>" +
        '<p class="result-line">' + markedLine + "</p>" +
        '<div class="score-teams"><strong>' + escapeHtml(teamA) + '</strong><span>vs</span><strong>' + escapeHtml(teamB) + '</strong></div>' +
        '<div class="score-head"><span>Équipe A</span><span>Équipe B</span></div>' +
        '<table class="score-history"><tbody>' + rows + '</tbody><tfoot><tr><th>' + recapState.cumulative_scores["0"] + '</th><th>' + recapState.cumulative_scores["1"] + '</th></tr></tfoot></table>' +
        '<div class="score-caption">Total</div>' +
        (finalRecap
          ? '<p class="recap-hint">Touchez les points pour voir le détail de la dernière donne.</p>' +
            '<button id="btn-new-game" class="btn btn-primary"' +
            (recapState.game_over ? "" : " disabled") + ">Retour au salon</button>"
          : '<p class="recap-hint">Touchez les points pour voir le détail (plis, dix de der, belote) — cliquez n’importe où pour continuer</p>');
      content.querySelectorAll(".pts-toggle").forEach(el => {
        el.addEventListener("click", ev => {
          ev.stopPropagation();
          const d = content.querySelector("#pts-detail");
          const tk = el.getAttribute("data-team");
          const txt = (tk === "0" ? "Équipe A : " : "Équipe B : ") + detailTextOf(tk);
          if (d.textContent === txt && !d.classList.contains("hidden")) {
            d.classList.add("hidden");
          } else {
            d.textContent = txt;
            d.classList.remove("hidden");
          }
        });
      });
      overlay.classList.remove("hidden");
    } else if (state.phase === "donne_annulee" && !recapState) {
      content.innerHTML =
        "<h2>Donne annulée</h2><p>Personne n'a assez enchéri (minimum 80). Nouvelle donne dans un instant...</p>";
      overlay.classList.remove("hidden");
    } else if (!recapState || dismissedDonneNumber === recapDonneNumber) {
      overlay.classList.add("hidden");
    }
  }

  document.addEventListener("click", () => {
    const canDismiss = lastRenderedState &&
      (!lastRenderedState.board_present || lastRenderedState.your_seat === "board");
    if (canDismiss && (recapState || (lastRenderedState.phase === "donne_annulee"))) {
      if (isFinalRecap(recapState)) return;
      if (claimVisible(lastRenderedState)) return;
      dismissedDonneNumber = recapDonneNumber;
      socket.emit("dismiss_recap", { code: roomCode });
      document.getElementById("donne-recap").classList.add("hidden");
    }
  });


  socket.on("state_update", state => {
    if (state.code !== roomCode) return;
    showScreen("screen-game");
    renderGame(state);
    // Compte connecté : enregistre la fin de partie (no-op en mode invité).
    if (state.game_over) window.BeloteAuth?.recordGameEnd(state);
  });
})();
