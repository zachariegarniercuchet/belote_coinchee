(() => {
  "use strict";

  const socket = io();

  let roomCode = null;
  let myName = null;
  let mySeatChosen = null; // 0-3 ou "board", mémorisé pour se rasseoir après reconnexion
  let lastLobbyState = null;

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

  function renderSeats(state) {
    lastLobbyState = state;
    const wrap = document.getElementById("seats");
    wrap.innerHTML = "";
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
      const isMine = info.name && info.name === myName;
      if (isMine) row.classList.add("mine");

      label.innerHTML =
        '<div class="seat-label ' + teamClass + '">' + labelText + (teamClass ? (key % 2 === 0 ? " · Équipe A" : " · Équipe B") : "") + "</div>" +
        (info.name
          ? '<div class="seat-name">' + escapeHtml(info.name) + (isMine ? " (toi)" : "") + (info.connected ? "" : " · hors ligne") + "</div>"
          : '<div class="seat-empty-label">Libre</div>');
      row.appendChild(label);

      if (!info.name) {
        const btn = document.createElement("button");
        btn.className = "seat-take-btn";
        btn.textContent = "S'asseoir";
        btn.onclick = () => {
          mySeatChosen = key;
          socket.emit("take_seat", { code: roomCode, seat: key });
        };
        row.appendChild(btn);
      } else if (isMine) {
        const btn = document.createElement("button");
        btn.className = "seat-take-btn";
        btn.style.background = "transparent";
        btn.style.color = "rgba(247,241,227,.6)";
        btn.textContent = "Se lever";
        btn.onclick = () => {
          mySeatChosen = null;
          socket.emit("leave_seat", { code: roomCode });
        };
        row.appendChild(btn);
      }

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
    });
  });

  document.getElementById("btn-leave-lobby").addEventListener("click", () => {
    location.reload();
  });

  document.getElementById("btn-new-game").addEventListener("click", () => {
    socket.emit("new_game", { code: roomCode });
    document.getElementById("gameover-overlay").classList.add("hidden");
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

  function renderGame(state) {
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
    const showBoardPanel = isBoard || !state.board_present;

    document.getElementById("board-panel").classList.toggle("hidden", !showBoardPanel);
    document.getElementById("hand-panel").classList.toggle("hidden", isBoard);

    if (showBoardPanel) renderBoardPanel(state);
    if (!isBoard) renderHandPanel(state);

    renderDonneRecap(state);
    renderGameOver(state);
  }

  function renderBoardPanel(state) {
    for (let seat = 0; seat < 4; seat++) {
      const marker = document.getElementById("seat-marker-" + seat);
      const name = nameOf(state, seat) + (state.your_seat === seat ? " (toi)" : "");
      marker.innerHTML =
        '<div class="sm-name">' + escapeHtml(name) + "</div>" +
        '<div class="sm-cards">' + (state.hand_counts[String(seat)] || 0) + " cartes</div>";
      marker.classList.toggle("active-turn", state.waiting_seat === seat);
      marker.classList.toggle("dealer", state.dealer === seat);
    }

    const trickArea = document.getElementById("trick-area");
    trickArea.innerHTML = "";
    let plays = state.current_trick && state.current_trick.length ? state.current_trick : state.completed_trick;
    if (plays && plays.length) {
      plays.forEach(p => {
        const slot = document.createElement("div");
        slot.className = "card-slot";
        const label = document.createElement("div");
        label.textContent = nameOf(state, p.seat);
        slot.appendChild(cardEl(p.card, "small"));
        slot.appendChild(label);
        trickArea.appendChild(slot);
      });
    }

    const badge = document.getElementById("contract-badge");
    if (state.contract) {
      const c = state.contract;
      let txt = (c.is_capot ? "Capot" : c.points) + " " + c.symbol + " — " + nameOf(state, c.player);
      if (c.coinche_state === "COINCHE") txt += " (coinché)";
      if (c.coinche_state === "SURCOINCHE") txt += " (surcoinché)";
      badge.textContent = txt;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }

    const log = document.getElementById("bidding-log");
    log.innerHTML = "";
    state.bidding_history.slice(-10).forEach(h => {
      const d = document.createElement("div");
      d.textContent = nameOf(state, h.seat) + " : " + h.label;
      log.appendChild(d);
    });
    log.scrollTop = log.scrollHeight;

    const tricksInfo = document.getElementById("tricks-info");
    tricksInfo.innerHTML =
      "<div>Donne n°" + (state.donne_number || 1) + "</div>" +
      "<div>Plis : Équipe A " + state.tricks_won_this_donne["0"] +
      " — Équipe B " + state.tricks_won_this_donne["1"] + "</div>";
  }

  function renderHandPanel(state) {
    const banner = document.getElementById("turn-banner");
    if (state.your_turn) {
      banner.textContent = state.waiting_kind === "bid" ? "À toi d'enchérir !" : "À toi de jouer !";
      banner.classList.add("my-turn");
    } else {
      banner.classList.remove("my-turn");
      if (state.phase === "donne_end") banner.textContent = "Fin de la donne...";
      else if (state.phase === "donne_annulee") banner.textContent = "Donne annulée, nouvelle donne...";
      else if (state.phase === "game_end") banner.textContent = "Partie terminée !";
      else if (state.waiting_seat !== null && state.waiting_seat !== undefined) {
        banner.textContent = "Tour de " + nameOf(state, state.waiting_seat) + "...";
      } else {
        banner.textContent = "En attente...";
      }
    }

    const bidControls = document.getElementById("bid-controls");
    if (state.your_turn && state.waiting_kind === "bid" && state.legal_bid_actions.length) {
      bidControls.classList.remove("hidden");
      renderBidControls(state.legal_bid_actions);
    } else {
      bidControls.classList.add("hidden");
      bidControls.innerHTML = "";
    }

    const handWrap = document.getElementById("hand-cards");
    handWrap.innerHTML = "";
    const cardMode = state.your_turn && state.waiting_kind === "card";
    state.your_hand.forEach(card => {
      const legal = cardMode && state.legal_card_ids.includes(card.id);
      const cls = cardMode ? (legal ? "legal" : "disabled") : "";
      const el = cardEl(card, cls);
      if (legal) {
        el.addEventListener("click", () => {
          socket.emit("play_card", { code: roomCode, card_id: card.id });
        });
      }
      handWrap.appendChild(el);
    });
  }

  function renderBidControls(actions) {
    const container = document.getElementById("bid-controls");
    container.innerHTML = "";

    const passAction = actions.find(a => a.type === "PASSE");
    const coincheAction = actions.find(a => a.type === "COINCHE");
    const surcoincheAction = actions.find(a => a.type === "SURCOINCHE");
    const enchereActions = actions.filter(a => a.type === "ENCHERE");

    const bySuit = {};
    enchereActions.forEach(a => {
      (bySuit[a.suit] = bySuit[a.suit] || []).push(a);
    });

    Object.keys(bySuit).forEach(suit => {
      const list = bySuit[suit].sort((a, b) => (a.is_capot ? 9999 : a.points) - (b.is_capot ? 9999 : b.points));
      const row = document.createElement("div");
      row.className = "bid-row";
      const symbol = document.createElement("span");
      symbol.className = "bid-suit-symbol";
      symbol.textContent = list[0].symbol;
      symbol.style.color = (suit === "COEUR" || suit === "CARREAU") ? "#e0576a" : "#f7f1e3";
      row.appendChild(symbol);
      list.forEach(a => {
        const chip = document.createElement("button");
        chip.className = "bid-chip";
        chip.textContent = a.is_capot ? "Capot" : String(a.points);
        chip.onclick = () => socket.emit("bid_choice", { code: roomCode, index: a.index });
        row.appendChild(chip);
      });
      container.appendChild(row);
    });

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
    container.appendChild(actionsRow);
  }

  function renderDonneRecap(state) {
    const overlay = document.getElementById("donne-recap");
    const content = document.getElementById("donne-recap-content");
    if (state.phase === "donne_end" && state.last_donne_result) {
      const r = state.last_donne_result;
      const c = state.contract;
      const contractLine = c
        ? "Contrat : " + (c.is_capot ? "Capot" : c.points) + " " + c.symbol + " (" + nameOf(state, c.player) + ")"
        : "";
      content.innerHTML =
        "<h2>Fin de la donne</h2>" +
        '<p class="result-line">' + contractLine + "</p>" +
        '<p class="result-line">' + (r.contract_reached ? "Contrat réussi ✅" : "Contrat chuté ❌") + "</p>" +
        '<p class="result-score">' + r.final_scores["0"] + " — " + r.final_scores["1"] + "</p>" +
        '<p class="hint">Total : Équipe A ' + state.cumulative_scores["0"] +
        " · Équipe B " + state.cumulative_scores["1"] + "</p>";
      overlay.classList.remove("hidden");
    } else if (state.phase === "donne_annulee") {
      content.innerHTML =
        "<h2>Donne annulée</h2><p>Personne n'a assez enchéri (minimum 80). Nouvelle donne dans un instant...</p>";
      overlay.classList.remove("hidden");
    } else {
      overlay.classList.add("hidden");
    }
  }

  function renderGameOver(state) {
    const overlay = document.getElementById("gameover-overlay");
    if (state.game_over) {
      const winnerLabel = state.winner_team === 0 ? "Équipe A" : "Équipe B";
      document.getElementById("gameover-title").textContent = winnerLabel + " remporte la partie !";
      document.getElementById("gameover-detail").textContent =
        "Score final — Équipe A : " + state.cumulative_scores["0"] +
        " · Équipe B : " + state.cumulative_scores["1"];
      document.getElementById("donne-recap").classList.add("hidden");
      overlay.classList.remove("hidden");
      showScreen("screen-game");
    } else {
      overlay.classList.add("hidden");
    }
  }

  socket.on("state_update", state => {
    if (state.code !== roomCode) return;
    showScreen("screen-game");
    renderGame(state);
  });
})();