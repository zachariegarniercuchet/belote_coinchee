(() => {
  "use strict";

  const socket = io();

  let roomCode = null;
  let myName = null;
  let mySeatChosen = null; // 0-3 ou "board", mémorisé pour se rasseoir après reconnexion
  let lastLobbyState = null;
  let lastRenderedState = null;
  let dismissedDonneNumber = null;
  let recapState = null;
  let recapDonneNumber = null;
  let lastTrickAnimationKey = null;

  // Bulles d'annonce (enchères / coinche) : elles restent affichées tant que
  // dure la phase d'enchères (la nouvelle annonce d'un joueur remplace la
  // précédente), puis disparaissent une fois la phase terminée.
  const bidBubbleState = { donne: null, count: 0, clearedForPhase: false };

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
    const showBoardPanel = isBoard || !state.board_present;

    document.getElementById("board-panel").classList.toggle("hidden", !showBoardPanel);
    document.getElementById("hand-panel").classList.toggle("hidden", isBoard);

    if (showBoardPanel) renderBoardPanel(state);
    if (!isBoard) renderHandPanel(state);

    renderDonneRecap(state);
    renderGameOver(state);
  }

  function renderBoardPanel(state) {
    lastRenderedState = state;

    for (let seat = 0; seat < 4; seat++) {
      const marker = document.getElementById("seat-marker-" + seat);
      const name = nameOf(state, seat) + (state.your_seat === seat ? " (toi)" : "");
      const existingBubble = marker.querySelector(".speech-bubble");

      let nameHtml = escapeHtml(name);
      if (state.contract && state.contract.player === seat) {
        const c = state.contract;
        const color = (c.suit === "COEUR" || c.suit === "CARREAU") ? "#e0576a" : "#f7f1e3";
        let tag = (c.is_capot ? "Capot" : c.points) + " " + c.symbol;
        if (c.coinche_state === "COINCHE") tag += " (coinché)";
        if (c.coinche_state === "SURCOINCHE") tag += " (surcoinché)";
        nameHtml += ' <span class="contract-tag" style="color:' + color + '">' + escapeHtml(tag) + "</span>";
      }

      marker.innerHTML =
        '<div class="sm-name">' + nameHtml + "</div>" +
        '<div class="sm-cards">' + (state.hand_counts[String(seat)] || 0) + " cartes</div>";
      if (existingBubble) marker.appendChild(existingBubble); // on préserve une bulle en cours d'affichage
      marker.classList.toggle("active-turn", state.waiting_seat === seat);
      marker.classList.toggle("dealer", state.dealer === seat);
    }

    // Cartes posées "devant" chaque joueur pendant le pli en cours (ou pendant
    // la courte pause où le pli complet reste visible avant d'être ramassé).
    for (let seat = 0; seat < 4; seat++) {
      document.getElementById("trick-slot-" + seat).innerHTML = "";
    }
    let plays = state.current_trick && state.current_trick.length ? state.current_trick : state.completed_trick;
    if (plays && plays.length) {
      const isCollectedTrick = !(state.current_trick && state.current_trick.length);
      plays.forEach(p => {
        const slot = document.getElementById("trick-slot-" + p.seat);
        slot.appendChild(cardEl(p.card, "small" + (isCollectedTrick ? " trick-flying" : "")));
      });
    }

    renderTrickPile(state);
    handleBidBubbles(state);

    const tricksInfo = document.getElementById("tricks-info");
    tricksInfo.textContent =
      "Donne n°" + (state.donne_number || 1) +
      " · Plis — Équipe A " + state.tricks_won_this_donne["0"] +
      " · Équipe B " + state.tricks_won_this_donne["1"];
  }

  // ------------------------------------------------------------------
  // Pli ramassé : pile cliquable en haut à droite (dernier pli uniquement)
  // ------------------------------------------------------------------
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

    if (enchereActions.length) {
      // Une couleur, puis un chiffre : la légalité d'un montant ne dépend pas
      // de la couleur choisie, donc pas besoin d'une grille couleur × chiffre.
      const suits = [];
      const seenSuits = {};
      enchereActions.forEach(a => {
        if (!seenSuits[a.suit]) {
          seenSuits[a.suit] = true;
          suits.push({ name: a.suit, symbol: a.symbol });
        }
      });

      const pointsSet = new Set();
      let hasCapot = false;
      enchereActions.forEach(a => {
        if (a.is_capot) hasCapot = true;
        else if (a.points != null) pointsSet.add(a.points);
      });

      let selectedSuit = suits[0].name;
      const suitButtons = {};

      const suitRow = document.createElement("div");
      suitRow.className = "bid-suit-row";
      suits.forEach(s => {
        const btn = document.createElement("button");
        btn.className = "bid-suit-btn" + (s.name === selectedSuit ? " selected" : "");
        btn.textContent = s.symbol;
        btn.style.color = (s.name === "COEUR" || s.name === "CARREAU") ? "#e0576a" : "#f7f1e3";
        btn.onclick = () => {
          selectedSuit = s.name;
          Object.values(suitButtons).forEach(b => b.classList.remove("selected"));
          btn.classList.add("selected");
        };
        suitButtons[s.name] = btn;
        suitRow.appendChild(btn);
      });
      container.appendChild(suitRow);

      const numRow = document.createElement("div");
      numRow.className = "bid-num-row";
      Array.from(pointsSet).sort((a, b) => a - b).forEach(pts => {
        const chip = document.createElement("button");
        chip.className = "bid-chip";
        chip.textContent = String(pts);
        chip.onclick = () => {
          const match = enchereActions.find(a => a.suit === selectedSuit && !a.is_capot && a.points === pts);
          if (match) socket.emit("bid_choice", { code: roomCode, index: match.index });
        };
        numRow.appendChild(chip);
      });
      if (hasCapot) {
        const chip = document.createElement("button");
        chip.className = "bid-chip capot-chip";
        chip.textContent = "Capot";
        chip.onclick = () => {
          const match = enchereActions.find(a => a.suit === selectedSuit && a.is_capot);
          if (match) socket.emit("bid_choice", { code: roomCode, index: match.index });
        };
        numRow.appendChild(chip);
      }
      container.appendChild(numRow);
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
    container.appendChild(actionsRow);
  }

  function renderDonneRecap(state) {
    const overlay = document.getElementById("donne-recap");
    const content = document.getElementById("donne-recap-content");
    if (state.last_donne_result && state.donne_number !== recapDonneNumber) {
      recapState = state;
      recapDonneNumber = state.donne_number;
    }

    if (recapState && dismissedDonneNumber !== recapDonneNumber) {
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
      content.innerHTML =
        "<h2>Fin de la donne</h2>" +
        '<p class="result-line">' + contractLine + "</p>" +
        '<p class="result-line">Points faits : Équipe A <strong>' + r.raw_points["0"] +
        "</strong> · Équipe B <strong>" + r.raw_points["1"] + "</strong></p>" +
        '<p class="result-line result-outcome ' + (r.contract_reached ? "success" : "failed") + '">' +
        (r.contract_reached ? "Contrat réussi" : "Contrat raté") + "</p>" +
        '<div class="score-teams"><strong>' + escapeHtml(teamA) + '</strong><span>vs</span><strong>' + escapeHtml(teamB) + '</strong></div>' +
        '<div class="score-head"><span>Équipe A</span><span>Équipe B</span></div>' +
        '<table class="score-history"><tbody>' + rows + '</tbody><tfoot><tr><th>' + recapState.cumulative_scores["0"] + '</th><th>' + recapState.cumulative_scores["1"] + '</th></tr></tfoot></table>' +
        '<div class="score-caption">Total</div>' +
        '<p class="recap-hint">Clique sur le plateau pour continuer</p>';
      overlay.classList.remove("hidden");
    } else if (state.phase === "donne_annulee" && !recapState) {
      content.innerHTML =
        "<h2>Donne annulée</h2><p>Personne n'a assez enchéri (minimum 80). Nouvelle donne dans un instant...</p>";
      overlay.classList.remove("hidden");
    } else if (!recapState || dismissedDonneNumber === recapDonneNumber) {
      overlay.classList.add("hidden");
    }
  }

  document.getElementById("board-panel").addEventListener("click", () => {
    if (recapState || (lastRenderedState && lastRenderedState.phase === "donne_annulee")) {
      dismissedDonneNumber = recapDonneNumber;
      socket.emit("dismiss_recap", { code: roomCode });
      document.getElementById("donne-recap").classList.add("hidden");
    }
  });

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