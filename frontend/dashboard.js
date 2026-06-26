(function () {
  var API_BASE = window.location.origin;
  var TOKEN_KEY = "aam_token";
  var COMPANY_ID_KEY = "aam_company_id";
  var COMPANY_NAME_KEY = "aam_company_name";

  function token() { return localStorage.getItem(TOKEN_KEY); }

  async function api(path, options) {
    options = options || {};
    options.headers = Object.assign({}, options.headers, { Authorization: "Bearer " + token() });
    var res = await fetch(API_BASE + path, options);
    if (!res.ok) {
      var detail = "Request failed";
      try { detail = (await res.json()).detail || detail; } catch (e) {}
      throw new Error(detail);
    }
    var text = await res.text();
    return text ? JSON.parse(text) : null;
  }

  // ---------- Toasts ----------
  var TOAST_ICONS = {
    success: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="10" r="7.5"/><path d="M7 10.3l2 2 4-4.6"/></svg>',
    error: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="10" r="7.5"/><path d="M10 6.5v4.2"/><circle cx="10" cy="13.5" r=".3" fill="currentColor"/></svg>'
  };

  function toast(message, type) {
    type = type === "error" ? "error" : "success";
    var container = document.getElementById("toast-container");
    var el = document.createElement("div");
    el.className = "toast toast-" + type;
    el.innerHTML = TOAST_ICONS[type] + "<span>" + message + "</span>";
    container.appendChild(el);
    setTimeout(function () {
      el.classList.add("toast-leaving");
      setTimeout(function () { el.remove(); }, 200);
    }, 3800);
  }

  function setButtonLoading(btn, isLoading) {
    var label = btn.querySelector(".btn-label") || btn;
    if (isLoading) {
      btn.disabled = true;
      btn.dataset.originalHtml = label.innerHTML;
      label.innerHTML = '<span class="spinner"></span>';
    } else {
      btn.disabled = false;
      if (btn.dataset.originalHtml) label.innerHTML = btn.dataset.originalHtml;
    }
  }

  function emptyState(message) {
    return '<li style="display:block;"><div class="empty-state">' +
      '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M3 10l2.2-6h9.6L17 10v5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M3 10h4.5a2.5 2.5 0 0 0 5 0H17"/></svg>' +
      "<div>" + message + "</div></div></li>";
  }

  function skeletonRows(n) {
    var html = '<div class="skeleton-list">';
    for (var i = 0; i < n; i++) html += '<div class="skeleton-row"></div>';
    return html + "</div>";
  }

  // ---------- Auth view ----------
  var authView = document.getElementById("auth-view");
  var appView = document.getElementById("app-view");
  var authError = document.getElementById("auth-error");
  var authHeading = document.getElementById("auth-heading");

  document.querySelectorAll(".tab-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".tab-btn").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      var isLogin = btn.dataset.tab === "login";
      document.getElementById("login-form").classList.toggle("hidden", !isLogin);
      document.getElementById("register-form").classList.toggle("hidden", isLogin);
      authHeading.textContent = isLogin ? "Welcome back" : "Create your account";
      authError.classList.add("hidden");
    });
  });

  function showError(msg) {
    authError.textContent = msg;
    authError.classList.remove("hidden");
  }

  document.getElementById("login-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    var btn = e.target.querySelector("button[type=submit]");
    setButtonLoading(btn, true);
    try {
      var res = await fetch(API_BASE + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("login-email").value,
          password: document.getElementById("login-password").value
        })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Login failed");
      var data = await res.json();
      onAuthenticated(data);
    } catch (err) {
      showError(err.message);
    } finally {
      setButtonLoading(btn, false);
    }
  });

  document.getElementById("register-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    var btn = e.target.querySelector("button[type=submit]");
    setButtonLoading(btn, true);
    try {
      var res = await fetch(API_BASE + "/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: document.getElementById("reg-name").value,
          email: document.getElementById("reg-email").value,
          password: document.getElementById("reg-password").value,
          tone: document.getElementById("reg-tone").value,
          persona_name: document.getElementById("reg-persona").value || "Assistant"
        })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Registration failed");
      var data = await res.json();
      onAuthenticated(data, true);
    } catch (err) {
      showError(err.message);
    } finally {
      setButtonLoading(btn, false);
    }
  });

  function onAuthenticated(data, justRegistered) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(COMPANY_ID_KEY, data.company_id);
    localStorage.setItem(COMPANY_NAME_KEY, data.company_name);
    enterApp(!!justRegistered);
  }

  document.getElementById("logout-btn").addEventListener("click", function () {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(COMPANY_ID_KEY);
    localStorage.removeItem(COMPANY_NAME_KEY);
    appView.classList.add("hidden");
    authView.classList.remove("hidden");
  });

  // ---------- Mobile sidebar ----------
  var sidebar = document.getElementById("sidebar");
  var sidebarBackdrop = document.getElementById("sidebar-backdrop");

  function openSidebar() {
    sidebar.classList.add("open");
    sidebarBackdrop.classList.add("open");
  }
  function closeSidebar() {
    sidebar.classList.remove("open");
    sidebarBackdrop.classList.remove("open");
  }
  document.getElementById("sidebar-open").addEventListener("click", openSidebar);
  document.getElementById("sidebar-close").addEventListener("click", closeSidebar);
  sidebarBackdrop.addEventListener("click", closeSidebar);

  // ---------- App view ----------
  document.querySelectorAll(".nav-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".nav-btn").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      document.querySelectorAll(".section").forEach(function (s) { s.classList.add("hidden"); });
      document.getElementById("section-" + btn.dataset.section).classList.remove("hidden");
      closeSidebar();
    });
  });

  function embedSnippetFor(companyId, accentColor) {
    return '<script src="' + API_BASE + '/static/widget.js"\n' +
      '  data-company-id="' + companyId + '"\n' +
      '  data-accent="' + (accentColor || "#4f46e5") + '"></scr' + 'ipt>';
  }

  async function enterApp(justRegistered) {
    authView.classList.add("hidden");
    appView.classList.remove("hidden");
    document.getElementById("company-name-label").textContent = localStorage.getItem(COMPANY_NAME_KEY);
    document.getElementById("embed-snippet").textContent = embedSnippetFor(localStorage.getItem(COMPANY_ID_KEY));

    var results = await Promise.allSettled([
      loadDocuments(), loadGaps(), loadReminders(), loadLogs(), loadSettings(), loadStats(), loadBilling()
    ]);
    results.forEach(function (r) { if (r.status === "rejected") console.error(r.reason); });

    if (justRegistered) startOnboarding();
  }

  document.getElementById("copy-embed").addEventListener("click", function () {
    navigator.clipboard.writeText(document.getElementById("embed-snippet").textContent);
    var label = this.querySelector(".btn-label");
    var original = label.textContent;
    label.textContent = "Copied!";
    setTimeout(function () { label.textContent = original; }, 1500);
  });

  // ---------- Documents ----------
  async function loadDocuments() {
    var list = document.getElementById("doc-list");
    list.innerHTML = skeletonRows(2);
    var docs = await api("/documents/");
    document.getElementById("stat-docs").textContent = docs.length;
    list.innerHTML = "";
    if (docs.length === 0) {
      list.innerHTML = emptyState("No documents yet — upload one above to teach your assistant.");
      return;
    }
    docs.forEach(function (d) {
      var li = document.createElement("li");
      li.innerHTML = "<span>" + d.filename + "</span>";
      var btn = document.createElement("button");
      btn.textContent = "Remove";
      btn.onclick = async function () {
        try {
          await api("/documents/" + d.id, { method: "DELETE" });
          toast("Document removed");
          loadDocuments();
        } catch (err) { toast(err.message, "error"); }
      };
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

  document.getElementById("upload-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    var btn = e.target.querySelector("button[type=submit]");
    var fileInput = document.getElementById("upload-file");
    if (!fileInput.files[0]) return;
    var fd = new FormData();
    fd.append("file", fileInput.files[0]);
    setButtonLoading(btn, true);
    try {
      await api("/documents/upload", { method: "POST", body: fd });
      fileInput.value = "";
      toast("Document uploaded and indexed");
      loadDocuments();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false);
    }
  });

  // ---------- Knowledge gaps ----------
  var gapModal = document.getElementById("gap-modal");
  var gapModalQuestion = document.getElementById("gap-modal-question");
  var gapModalAnswer = document.getElementById("gap-modal-answer");
  var pendingGapId = null;

  function openGapModal(gapId, question) {
    pendingGapId = gapId;
    gapModalQuestion.textContent = "“" + question + "”";
    gapModalAnswer.value = "";
    gapModal.classList.remove("hidden");
    gapModalAnswer.focus();
  }
  function closeGapModal() {
    gapModal.classList.add("hidden");
    pendingGapId = null;
  }
  document.getElementById("gap-modal-cancel").addEventListener("click", closeGapModal);
  document.getElementById("gap-modal-submit").addEventListener("click", async function () {
    var answer = gapModalAnswer.value.trim();
    if (!answer || !pendingGapId) return;
    var btn = this;
    setButtonLoading(btn, true);
    try {
      await api("/gaps/" + pendingGapId + "/resolve", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: answer })
      });
      toast("Answer saved — your assistant has learned this");
      closeGapModal();
      loadGaps();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false);
    }
  });

  async function loadGaps() {
    var list = document.getElementById("gap-list");
    list.innerHTML = skeletonRows(2);
    var gaps = await api("/gaps/");
    document.getElementById("stat-gaps").textContent = gaps.length;
    list.innerHTML = "";
    if (gaps.length === 0) {
      list.innerHTML = emptyState("No open knowledge gaps right now.");
      return;
    }
    gaps.forEach(function (g) {
      var li = document.createElement("li");
      var span = document.createElement("span");
      span.textContent = g.question;
      li.appendChild(span);
      var btn = document.createElement("button");
      btn.className = "primary-action";
      btn.textContent = "Answer";
      btn.onclick = function () { openGapModal(g.id, g.question); };
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

  // ---------- Reminders ----------
  async function loadReminders() {
    var list = document.getElementById("reminder-list");
    list.innerHTML = skeletonRows(2);
    var reminders = await api("/reminders/");
    document.getElementById("stat-reminders").textContent = reminders.filter(function (r) { return !r.is_sent; }).length;
    list.innerHTML = "";
    if (reminders.length === 0) {
      list.innerHTML = emptyState("No reminders scheduled yet.");
      return;
    }
    reminders.forEach(function (r) {
      var li = document.createElement("li");
      var span = document.createElement("span");
      var recipient = r.channel === "email" ? r.customer_email : r.customer_phone;
      span.textContent = "[" + r.channel + "] " + recipient + " — " + r.message + " ";
      var meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = r.is_sent ? "sent" : "pending (" + r.trigger_type + ")";
      span.appendChild(meta);
      li.appendChild(span);
      var btn = document.createElement("button");
      btn.textContent = "Delete";
      btn.onclick = async function () {
        try {
          await api("/reminders/" + r.id, { method: "DELETE" });
          toast("Reminder deleted");
          loadReminders();
        } catch (err) { toast(err.message, "error"); }
      };
      li.appendChild(btn);
      list.appendChild(li);
    });
  }

  var remChannelSelect = document.getElementById("rem-channel");
  var remEmailInput = document.getElementById("rem-email");
  var remPhoneInput = document.getElementById("rem-phone");

  function updateReminderChannelFields() {
    var isEmail = remChannelSelect.value === "email";
    remEmailInput.classList.toggle("hidden", !isEmail);
    remPhoneInput.classList.toggle("hidden", isEmail);
  }
  remChannelSelect.addEventListener("change", updateReminderChannelFields);
  updateReminderChannelFields();

  document.getElementById("reminder-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    var btn = e.target.querySelector("button[type=submit]");
    var channel = remChannelSelect.value;
    setButtonLoading(btn, true);
    try {
      await api("/reminders/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: channel,
          customer_email: channel === "email" ? remEmailInput.value : null,
          customer_phone: channel !== "email" ? remPhoneInput.value : null,
          message: document.getElementById("rem-message").value,
          trigger_type: document.getElementById("rem-trigger").value,
          trigger_value: document.getElementById("rem-value").value
        })
      });
      document.getElementById("reminder-form").reset();
      updateReminderChannelFields();
      toast("Reminder scheduled");
      loadReminders();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false);
    }
  });

  // ---------- Chat logs ----------
  async function loadLogs() {
    var list = document.getElementById("log-list");
    list.innerHTML = skeletonRows(3);
    var logs = await api("/chat/logs/all");
    list.innerHTML = "";
    if (logs.length === 0) {
      list.innerHTML = emptyState("No conversations yet — they'll show up here once customers start chatting.");
      return;
    }
    logs.forEach(function (l) {
      var li = document.createElement("li");
      li.innerHTML = "<span><strong>" + l.role + "</strong>: " + l.content + "</span>" +
        "<span class='meta'>" + (l.sentiment || "") + "</span>";
      list.appendChild(li);
    });
  }

  // ---------- Settings ----------
  async function loadSettings() {
    var me = await api("/auth/me");
    document.getElementById("set-persona").value = me.persona_name;
    document.getElementById("set-tone").value = me.tone;
    document.getElementById("set-brand-color").value = me.brand_color || "#4f46e5";
    document.getElementById("set-logo-url").value = me.logo_url || "";
    document.getElementById("set-slack-webhook").value = me.slack_webhook_url || "";
    document.getElementById("embed-snippet").textContent = embedSnippetFor(me.id, me.brand_color);
  }

  document.getElementById("settings-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    var btn = e.target.querySelector("button[type=submit]");
    setButtonLoading(btn, true);
    try {
      await api("/auth/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          persona_name: document.getElementById("set-persona").value,
          tone: document.getElementById("set-tone").value,
          brand_color: document.getElementById("set-brand-color").value,
          logo_url: document.getElementById("set-logo-url").value,
          slack_webhook_url: document.getElementById("set-slack-webhook").value
        })
      });
      toast("Settings saved");
      loadSettings();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false);
    }
  });

  // ---------- Delete account ----------
  var deleteAccountModal = document.getElementById("delete-account-modal");
  var deleteAccountPassword = document.getElementById("delete-account-password");

  document.getElementById("open-delete-account").addEventListener("click", function () {
    deleteAccountPassword.value = "";
    deleteAccountModal.classList.remove("hidden");
    deleteAccountPassword.focus();
  });
  document.getElementById("delete-account-cancel").addEventListener("click", function () {
    deleteAccountModal.classList.add("hidden");
  });
  document.getElementById("delete-account-submit").addEventListener("click", async function () {
    var password = deleteAccountPassword.value;
    if (!password) return;
    var btn = this;
    setButtonLoading(btn, true);
    try {
      await api("/auth/account", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: password })
      });
      deleteAccountModal.classList.add("hidden");
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(COMPANY_ID_KEY);
      localStorage.removeItem(COMPANY_NAME_KEY);
      appView.classList.add("hidden");
      authView.classList.remove("hidden");
      toast("Account deleted");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false);
    }
  });

  // ---------- Usage stats (Overview) ----------
  var PLAN_LABELS = { free: "Free", pro: "Pro", enterprise: "Enterprise" };

  function renderUsageChart(dailyCounts) {
    var svg = document.getElementById("usage-chart");
    var W = 600, H = 130, pad = 8;
    if (!dailyCounts.length) { svg.innerHTML = ""; return; }
    var max = Math.max(1, ...dailyCounts.map(function (d) { return d.count; }));
    var n = dailyCounts.length;
    var stepX = n > 1 ? (W - pad * 2) / (n - 1) : 0;

    var points = dailyCounts.map(function (d, i) {
      var x = pad + i * stepX;
      var y = H - pad - (d.count / max) * (H - pad * 2);
      return { x: x, y: y, d: d };
    });

    var linePath = points.map(function (p, i) { return (i === 0 ? "M" : "L") + p.x.toFixed(1) + "," + p.y.toFixed(1); }).join(" ");
    var areaPath = linePath + " L" + points[n - 1].x.toFixed(1) + "," + (H - pad) + " L" + points[0].x.toFixed(1) + "," + (H - pad) + " Z";

    var dotsHtml = points.map(function (p) {
      return '<g class="chart-tooltip-group">' +
        '<rect class="hit" x="' + (p.x - stepX / 2) + '" y="0" width="' + (stepX || W) + '" height="' + H + '" />' +
        '<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="2.5" fill="#22d3ee" />' +
        '<text x="' + p.x.toFixed(1) + '" y="' + Math.max(10, p.y - 8) + '" text-anchor="middle">' + p.d.date + ": " + p.d.count + "</text>" +
        "</g>";
    }).join("");

    svg.innerHTML =
      '<defs><linearGradient id="usageGrad" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#22d3ee" stop-opacity="0.35" />' +
      '<stop offset="100%" stop-color="#22d3ee" stop-opacity="0" />' +
      "</linearGradient></defs>" +
      '<path class="chart-area" d="' + areaPath + '" fill="url(#usageGrad)" stroke="none" />' +
      '<path d="' + linePath + '" fill="none" stroke="#4f7cff" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />' +
      dotsHtml;
  }

  async function loadStats() {
    var stats = await api("/chat/stats");
    document.getElementById("stat-messages").textContent = stats.messages_this_month;
    document.getElementById("stat-messages-limit").textContent =
      stats.messages_limit ? "/ " + stats.messages_limit : "(unlimited)";
    document.getElementById("stat-plan-label").textContent = PLAN_LABELS[stats.plan] || stats.plan;

    renderUsageChart(stats.daily_counts);

    var counts = stats.daily_counts.map(function (d) { return d.count; });
    var half = Math.floor(counts.length / 2);
    var recent = counts.slice(half).reduce(function (a, b) { return a + b; }, 0);
    var prior = counts.slice(0, half).reduce(function (a, b) { return a + b; }, 0);
    var trendEl = document.getElementById("stat-messages-trend");
    if (prior === 0 && recent === 0) {
      trendEl.className = "trend flat"; trendEl.textContent = "—";
    } else if (prior === 0) {
      trendEl.className = "trend up"; trendEl.textContent = "new";
    } else {
      var pct = Math.round(((recent - prior) / prior) * 100);
      trendEl.className = "trend " + (pct > 0 ? "up" : pct < 0 ? "down" : "flat");
      trendEl.textContent = (pct > 0 ? "+" : "") + pct + "%";
    }

    var s = stats.sentiment_breakdown;
    var total = Math.max(1, s.positive + s.neutral + s.negative);
    var bar2 = document.getElementById("sentiment-bar");
    bar2.innerHTML =
      '<div class="seg-positive" style="width:' + (s.positive / total * 100) + '%"></div>' +
      '<div class="seg-neutral" style="width:' + (s.neutral / total * 100) + '%"></div>' +
      '<div class="seg-negative" style="width:' + (s.negative / total * 100) + '%"></div>';
    document.getElementById("sentiment-legend").innerHTML =
      '<span><i class="dot" style="background:#16a34a"></i> Positive (' + s.positive + ')</span>' +
      '<span><i class="dot" style="background:#cbd2e0"></i> Neutral (' + s.neutral + ')</span>' +
      '<span><i class="dot" style="background:#dc2626"></i> Negative (' + s.negative + ')</span>';
  }

  // ---------- Billing ----------
  async function loadBilling() {
    var plans = await api("/billing/plans");
    var status = await api("/billing/status");
    var cards = document.getElementById("plan-cards");
    cards.innerHTML = "";

    Object.keys(plans).forEach(function (planKey) {
      var plan = plans[planKey];
      var isCurrent = planKey === status.plan;
      var card = document.createElement("div");
      card.className = "plan-card" + (isCurrent ? " current" : "");

      var featureList = "<li>" +
        (plan.max_documents === null ? "Unlimited documents" : plan.max_documents + " document(s)") +
        "</li><li>" +
        (plan.max_messages_per_month === null ? "Unlimited messages/month" : plan.max_messages_per_month + " messages/month") +
        "</li>";

      var actionHtml;
      if (isCurrent) {
        actionHtml = "<button disabled>Current plan</button>";
      } else if (planKey === "enterprise") {
        actionHtml = '<a href="mailto:sales@example.com?subject=Enterprise%20plan"><button type="button">Contact sales</button></a>';
      } else if (planKey === "pro") {
        actionHtml = '<button type="button" class="upgrade-btn" data-plan="pro"><span class="btn-label">Upgrade to Pro</span></button>';
      } else {
        actionHtml = "<button disabled>—</button>";
      }

      card.innerHTML =
        "<h3>" + plan.label + "</h3>" +
        '<div class="price">' + plan.price_display + "</div>" +
        "<ul>" + featureList + "</ul>" +
        actionHtml;
      cards.appendChild(card);
    });

    document.getElementById("billing-not-configured").classList.toggle("hidden", status.billing_configured);

    cards.querySelectorAll(".upgrade-btn").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        setButtonLoading(btn, true);
        try {
          var result = await api("/billing/checkout", { method: "POST" });
          window.location.href = result.checkout_url;
        } catch (err) {
          toast(err.message, "error");
          setButtonLoading(btn, false);
        }
      });
    });
  }

  // ---------- Onboarding wizard ----------
  var onboardingModal = document.getElementById("onboarding-modal");
  var onbDots = document.querySelectorAll(".onboarding-progress span");

  function showOnboardingStep(n) {
    [1, 2, 3].forEach(function (i) {
      document.getElementById("onboarding-step-" + i).classList.toggle("hidden", i !== n);
    });
    onbDots.forEach(function (dot, i) { dot.classList.toggle("done", i < n); });
  }

  function startOnboarding() {
    showOnboardingStep(1);
    onboardingModal.classList.remove("hidden");
  }

  function finishOnboarding() {
    onboardingModal.classList.add("hidden");
    loadDocuments();
  }

  document.getElementById("onb-skip").addEventListener("click", finishOnboarding);
  document.getElementById("onb-finish").addEventListener("click", finishOnboarding);

  document.getElementById("onb-step1-next").addEventListener("click", async function () {
    var btn = this;
    var persona = document.getElementById("onb-persona").value;
    var tone = document.getElementById("onb-tone").value;
    setButtonLoading(btn, true);
    try {
      await api("/auth/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona_name: persona || "Assistant", tone: tone })
      });
      loadSettings();
      showOnboardingStep(2);
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setButtonLoading(btn, false);
    }
  });

  document.getElementById("onb-step2-next").addEventListener("click", function () {
    showOnboardingStep(3);
    document.getElementById("onb-embed-snippet").textContent = embedSnippetFor(localStorage.getItem(COMPANY_ID_KEY));
  });

  document.getElementById("onb-step2-upload").addEventListener("click", async function () {
    var btn = this;
    var fileInput = document.getElementById("onb-file");
    if (!fileInput.files[0]) {
      showOnboardingStep(3);
      document.getElementById("onb-embed-snippet").textContent = embedSnippetFor(localStorage.getItem(COMPANY_ID_KEY));
      return;
    }
    var fd = new FormData();
    fd.append("file", fileInput.files[0]);
    setButtonLoading(btn, true);
    try {
      await api("/documents/upload", { method: "POST", body: fd });
    } catch (err) {
      toast(err.message, "error");
      setButtonLoading(btn, false);
      return;
    }
    setButtonLoading(btn, false);
    showOnboardingStep(3);
    document.getElementById("onb-embed-snippet").textContent = embedSnippetFor(localStorage.getItem(COMPANY_ID_KEY));
  });

  // ---------- Status pill ----------
  (function checkStatus() {
    var pill = document.getElementById("status-pill");
    var text = document.getElementById("status-pill-text");
    fetch(API_BASE + "/health").then(function (res) {
      if (res.ok) {
        pill.className = "status-pill online";
        text.textContent = "All systems operational";
      } else {
        throw new Error("not ok");
      }
    }).catch(function () {
      pill.className = "status-pill offline";
      text.textContent = "Service unreachable";
    });
  })();

  // ---------- Search/filter for lists ----------
  function wireFilter(inputId, listId, matchFn) {
    var input = document.getElementById(inputId);
    var list = document.getElementById(listId);
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      Array.prototype.forEach.call(list.children, function (li) {
        if (li.querySelector(".empty-state") || li.querySelector(".skeleton-row")) return;
        var visible = !q || matchFn(li, q);
        li.style.display = visible ? "" : "none";
      });
    });
  }
  wireFilter("doc-search", "doc-list", function (li, q) { return li.textContent.toLowerCase().indexOf(q) !== -1; });
  wireFilter("gap-search", "gap-list", function (li, q) { return li.textContent.toLowerCase().indexOf(q) !== -1; });
  wireFilter("log-search", "log-list", function (li, q) { return li.textContent.toLowerCase().indexOf(q) !== -1; });

  // ---------- Playground tester ----------
  var pgMessages = document.getElementById("pg-messages");
  var pgInput = document.getElementById("pg-input");
  var pgSend = document.getElementById("pg-send");
  var pgHistory = [];

  function pgAppend(role, content) {
    var empty = pgMessages.querySelector(".pg-empty");
    if (empty) empty.remove();
    var div = document.createElement("div");
    div.className = "pg-msg " + role;
    div.textContent = content;
    pgMessages.appendChild(div);
    pgMessages.scrollTop = pgMessages.scrollHeight;
  }

  async function pgSendMessage() {
    var text = pgInput.value.trim();
    if (!text) return;
    pgInput.value = "";
    pgAppend("user", text);
    pgHistory.push({ role: "user", content: text });
    pgSend.disabled = true;
    try {
      var res = await fetch(API_BASE + "/chat/" + localStorage.getItem(COMPANY_ID_KEY), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, customer_id: "playground_" + localStorage.getItem(COMPANY_ID_KEY), conversation_history: pgHistory })
      });
      var data = await res.json();
      pgAppend("assistant", data.reply);
      pgHistory.push({ role: "assistant", content: data.reply });
    } catch (err) {
      pgAppend("assistant", "Couldn't reach the assistant — try again.");
    } finally {
      pgSend.disabled = false;
    }
  }
  pgSend.addEventListener("click", pgSendMessage);
  pgInput.addEventListener("keydown", function (e) { if (e.key === "Enter") pgSendMessage(); });

  // ---------- Boot ----------
  if (token()) enterApp(false);
})();
