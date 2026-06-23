(function () {
  var thisScript = document.currentScript;
  var companyId = thisScript.getAttribute("data-company-id");
  var apiBase = thisScript.getAttribute("data-api-base") || window.location.origin;
  var fallbackAccent = thisScript.getAttribute("data-accent") || "#4f46e5";

  if (!companyId) {
    console.error("adaptive-ai-messenger widget: missing data-company-id attribute on script tag");
    return;
  }

  var customerId = localStorage.getItem("aam_customer_id");
  if (!customerId) {
    customerId = "guest_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("aam_customer_id", customerId);
  }

  var historyKey = "aam_history_" + companyId;
  var history = JSON.parse(sessionStorage.getItem(historyKey) || "[]");

  async function fetchProfile() {
    try {
      var res = await fetch(apiBase + "/chat/" + companyId + "/profile");
      if (!res.ok) throw new Error("profile fetch failed");
      return await res.json();
    } catch (err) {
      return { persona_name: "Assistant", brand_color: fallbackAccent, logo_url: null };
    }
  }

  function buildWidget(profile) {
    var accent = profile.brand_color || fallbackAccent;
    var personaName = profile.persona_name || "Assistant";
    var logoHtml = profile.logo_url
      ? '<img src="' + profile.logo_url + '" alt="" class="aam-logo" />'
      : "";

    var style = document.createElement("style");
    style.textContent = `
      .aam-bubble { position: fixed; bottom: 20px; right: 20px; width: 58px; height: 58px;
        border-radius: 50%; background: ${accent}; color: #fff; display: flex; align-items: center;
        justify-content: center; cursor: pointer; box-shadow: 0 6px 20px rgba(0,0,0,.22); z-index: 99999;
        font-family: -apple-system, "Segoe UI", sans-serif; z-index: 99999;
        transition: transform 160ms cubic-bezier(.34,1.56,.64,1); overflow: hidden; }
      .aam-bubble:hover { transform: scale(1.06); }
      .aam-bubble svg { width: 26px; height: 26px; transition: opacity 120ms ease, transform 160ms ease; }
      .aam-bubble .aam-logo { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
      .aam-bubble .aam-icon-close { position: absolute; opacity: 0; transform: rotate(-90deg) scale(.5); }
      .aam-bubble.open .aam-icon-chat { opacity: 0; transform: rotate(90deg) scale(.5); }
      .aam-bubble.open .aam-icon-close { opacity: 1; transform: rotate(0) scale(1); position: static; }
      .aam-bubble .aam-badge {
        position: absolute; top: -2px; right: -2px; width: 11px; height: 11px; border-radius: 50%;
        background: #22c55e; border: 2px solid #fff;
      }
      .aam-panel { position: fixed; bottom: 90px; right: 20px; width: 350px; max-height: 500px;
        background: #fff; border-radius: 16px; box-shadow: 0 16px 50px rgba(0,0,0,.22); display: none;
        flex-direction: column; overflow: hidden; font-family: -apple-system, "Segoe UI", sans-serif; z-index: 99999;
        opacity: 0; transform: translateY(12px) scale(.98); transition: opacity 160ms ease, transform 160ms ease; }
      .aam-panel.open { display: flex; opacity: 1; transform: translateY(0) scale(1); }
      .aam-header { background: ${accent}; color: #fff; padding: 16px 16px; font-weight: 600;
        font-size: 14.5px; display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
      .aam-header .aam-logo { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
      .aam-header-sub { font-size: 11.5px; opacity: .85; font-weight: 400; display: flex; align-items: center; gap: 5px; margin-top: 2px; }
      .aam-header-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; display: inline-block; }
      .aam-messages { flex: 1; overflow-y: auto; padding: 14px; background: #f7f7fb; font-size: 13.5px; scroll-behavior: smooth; }
      .aam-msg { margin: 7px 0; padding: 9px 12px; border-radius: 14px; max-width: 82%; line-height: 1.45;
        animation: aamSlideIn 180ms ease; word-wrap: break-word; }
      .aam-msg.user { background: ${accent}; color: #fff; margin-left: auto; border-bottom-right-radius: 4px; }
      .aam-msg.assistant { background: #ebebf2; color: #222; border-bottom-left-radius: 4px; }
      .aam-typing { display: flex; gap: 4px; padding: 11px 14px; background: #ebebf2; border-radius: 14px;
        width: fit-content; margin: 7px 0; border-bottom-left-radius: 4px; animation: aamSlideIn 180ms ease; }
      .aam-typing span { width: 6px; height: 6px; border-radius: 50%; background: #9b9bab; animation: aamBounce 1.1s infinite ease-in-out; }
      .aam-typing span:nth-child(2) { animation-delay: .15s; }
      .aam-typing span:nth-child(3) { animation-delay: .3s; }
      .aam-input-row { display: flex; border-top: 1px solid #ececf2; padding: 8px; gap: 6px; flex-shrink: 0; background: #fff; }
      .aam-input { flex: 1; border: none; padding: 10px 12px; font-size: 13.5px; outline: none; background: #f3f3f8;
        border-radius: 10px; font-family: inherit; }
      .aam-input:focus { background: #ececf5; }
      .aam-send { border: none; background: ${accent}; color: #fff; width: 38px; height: 38px; border-radius: 10px;
        cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        transition: opacity 120ms ease; }
      .aam-send:hover { opacity: .88; }
      .aam-send svg { width: 16px; height: 16px; }
      .aam-escalate { background: #fff3cd; color: #7a5b00; font-size: 11.5px; padding: 8px 12px; border-radius: 10px;
        margin: 7px 0; display: flex; align-items: center; gap: 6px; animation: aamSlideIn 180ms ease; }
      .aam-escalate svg { width: 14px; height: 14px; flex-shrink: 0; }
      .aam-messages::-webkit-scrollbar { width: 6px; }
      .aam-messages::-webkit-scrollbar-thumb { background: #d6d6e2; border-radius: 3px; }

      @keyframes aamSlideIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes aamBounce { 0%, 60%, 100% { transform: translateY(0); opacity: .5; } 30% { transform: translateY(-4px); opacity: 1; } }

      @media (max-width: 480px) {
        .aam-panel { width: calc(100vw - 24px); right: 12px; bottom: 84px; max-height: 70vh; }
        .aam-bubble { right: 16px; bottom: 16px; }
      }
    `;
    document.head.appendChild(style);

    var bubble = document.createElement("div");
    bubble.className = "aam-bubble";
    bubble.innerHTML = logoHtml || (
      '<svg class="aam-icon-chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.4 8.4 0 0 1-1.1 4.2L21 21l-5.3-1a8.5 8.5 0 1 1 5.3-8.5z"/></svg>' +
      '<svg class="aam-icon-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>'
    );
    if (!logoHtml) bubble.innerHTML += '<span class="aam-badge"></span>';

    var panel = document.createElement("div");
    panel.className = "aam-panel";
    panel.innerHTML = `
      <div class="aam-header">
        ${logoHtml}
        <div>
          <div>${personaName}</div>
          <div class="aam-header-sub"><span class="aam-header-dot"></span>Usually replies instantly</div>
        </div>
      </div>
      <div class="aam-messages"></div>
      <div class="aam-input-row">
        <input class="aam-input" type="text" placeholder="Type a message..." />
        <button class="aam-send" aria-label="Send">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h14M11 4l6 6-6 6"/></svg>
        </button>
      </div>
    `;

    document.body.appendChild(bubble);
    document.body.appendChild(panel);

    var messagesEl = panel.querySelector(".aam-messages");
    var inputEl = panel.querySelector(".aam-input");
    var sendBtn = panel.querySelector(".aam-send");
    var typingEl = null;

    function renderHistory() {
      messagesEl.innerHTML = "";
      if (history.length === 0) {
        var welcome = document.createElement("div");
        welcome.className = "aam-msg assistant";
        welcome.textContent = "Hi! I'm " + personaName + ". Ask me anything about " + (document.title || "us") + ".";
        messagesEl.appendChild(welcome);
      }
      history.forEach(function (m) {
        var div = document.createElement("div");
        div.className = "aam-msg " + m.role;
        div.textContent = m.content;
        messagesEl.appendChild(div);
      });
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function showTyping() {
      typingEl = document.createElement("div");
      typingEl.className = "aam-typing";
      typingEl.innerHTML = "<span></span><span></span><span></span>";
      messagesEl.appendChild(typingEl);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function hideTyping() {
      if (typingEl) { typingEl.remove(); typingEl = null; }
    }

    bubble.addEventListener("click", function () {
      panel.classList.toggle("open");
      bubble.classList.toggle("open");
      if (panel.classList.contains("open")) {
        renderHistory();
        inputEl.focus();
      }
    });

    function appendMessage(role, content) {
      history.push({ role: role, content: content });
      sessionStorage.setItem(historyKey, JSON.stringify(history));
      renderHistory();
    }

    function appendNotice(text) {
      var div = document.createElement("div");
      div.className = "aam-escalate";
      div.innerHTML = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3 2.5 16h15z"/><path d="M10 8v4"/><circle cx="10" cy="14.2" r=".3" fill="currentColor"/></svg><span>' + text + "</span>";
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function sendMessage() {
      var text = inputEl.value.trim();
      if (!text) return;
      inputEl.value = "";
      appendMessage("user", text);
      showTyping();

      try {
        var res = await fetch(apiBase + "/chat/" + companyId, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            customer_id: customerId,
            conversation_history: history.map(function (m) { return { role: m.role, content: m.content }; })
          })
        });
        if (!res.ok) throw new Error("Request failed");
        var data = await res.json();
        hideTyping();
        appendMessage("assistant", data.reply);
        if (data.escalate) {
          appendNotice("This has been flagged for a human follow-up.");
        }
      } catch (err) {
        hideTyping();
        appendMessage("assistant", "Sorry, something went wrong reaching support. Please try again shortly.");
      }
    }

    sendBtn.addEventListener("click", sendMessage);
    inputEl.addEventListener("keydown", function (e) {
      if (e.key === "Enter") sendMessage();
    });
  }

  fetchProfile().then(buildWidget);
})();
