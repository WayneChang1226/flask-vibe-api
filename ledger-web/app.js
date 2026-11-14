/**
 * 個人記帳本 手機版前端應用程式 (Vanilla JavaScript)
 * 遵守 docs/前端串接.md 規範
 */

(function () {
  'use strict';

  // ==========================================
  // 全域狀態管理
  // ==========================================
  const STATE = {
    apiBaseUrl: null,
    currentView: 'view-connection',
    currentMonth: getTodayMonthString(),
    accounts: [],
    incomeCategories: [],
    expenseCategories: [],
    monthlyEntries: [], // 本月記帳即時清單
    quickCatType: 'expense', // 'expense' | 'income'
  };

  // ==========================================
  // DOM 元件參考
  // ==========================================
  const DOM = {
    header: document.querySelector('.app-header'),
    btnClearConn: document.getElementById('btn-clear-connection'),
    globalAlert: document.getElementById('global-alert'),
    alertMessage: document.getElementById('alert-message'),
    bottomNav: document.getElementById('bottom-nav'),
    navItems: document.querySelectorAll('.nav-item'),
    viewPanels: document.querySelectorAll('.view-panel'),

    // 連線頁
    viewConnection: document.getElementById('view-connection'),
    formConnection: document.getElementById('form-connection'),
    inputApiUrl: document.getElementById('input-api-url'),

    // 首頁
    viewHome: document.getElementById('view-home'),
    homeMonthDisplay: document.getElementById('home-month-display'),
    homeIncomeTwd: document.getElementById('home-income-twd'),
    homeExpenseTwd: document.getElementById('home-expense-twd'),
    homeNetTwd: document.getElementById('home-net-twd'),
    homeAccountsList: document.getElementById('home-accounts-list'),
    homeEmptyAccounts: document.getElementById('home-empty-accounts'),
    btnCreateCashAccount: document.getElementById('btn-create-cash-account'),
    btnRefreshHome: document.getElementById('btn-refresh-home'),

    // 記帳頁
    viewAccounting: document.getElementById('view-accounting'),
    btnTabExpense: document.getElementById('btn-tab-expense'),
    btnTabIncome: document.getElementById('btn-tab-income'),
    panelExpenseForm: document.getElementById('panel-expense-form'),
    panelIncomeForm: document.getElementById('panel-income-form'),
    formExpense: document.getElementById('form-expense'),
    formIncome: document.getElementById('form-income'),
    expSpentOn: document.getElementById('exp-spent-on'),
    expAmount: document.getElementById('exp-amount'),
    expCategory: document.getElementById('exp-category'),
    expAccount: document.getElementById('exp-account'),
    expMerchant: document.getElementById('exp-merchant'),
    expNote: document.getElementById('exp-note'),
    expSettledOn: document.getElementById('exp-settled-on'),
    btnQuickExpCat: document.getElementById('btn-quick-exp-cat'),
    incReceivedOn: document.getElementById('inc-received-on'),
    incAmount: document.getElementById('inc-amount'),
    incCategory: document.getElementById('inc-category'),
    incAccount: document.getElementById('inc-account'),
    incSource: document.getElementById('inc-source'),
    incNote: document.getElementById('inc-note'),
    btnQuickIncCat: document.getElementById('btn-quick-inc-cat'),
    accountingRecentList: document.getElementById('accounting-recent-list'),

    // 投資頁
    viewInvestments: document.getElementById('view-investments'),
    btnFetchQuotes: document.getElementById('btn-fetch-quotes'),
    investmentsFeedback: document.getElementById('investments-feedback'),
    investmentsList: document.getElementById('investments-list'),

    // 發票頁
    viewInvoices: document.getElementById('view-invoices'),
    invoicesList: document.getElementById('invoices-list'),
    btnRefreshInvoices: document.getElementById('btn-refresh-invoices'),

    // 快速建立分類 Modal
    modalQuickCategory: document.getElementById('modal-quick-category'),
    modalCatTitle: document.getElementById('modal-cat-title'),
    formQuickCat: document.getElementById('form-quick-cat'),
    inputCatName: document.getElementById('input-cat-name'),
    btnCancelCat: document.getElementById('btn-cancel-cat'),
  };

  // ==========================================
  // 工具函式
  // ==========================================

  function getTodayDateString() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  function getTodayMonthString() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }

  function formatCurrency(num) {
    const val = Number(num) || 0;
    return val.toLocaleString('zh-TW', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  let alertTimeout = null;
  function showAlert(msg, isSuccess = false) {
    if (!DOM.globalAlert) return;
    DOM.alertMessage.textContent = msg;
    DOM.globalAlert.className = isSuccess ? 'alert success' : 'alert';
    DOM.globalAlert.style.display = 'flex';

    if (alertTimeout) clearTimeout(alertTimeout);
    alertTimeout = setTimeout(() => {
      DOM.globalAlert.style.display = 'none';
    }, 4500);
  }

  function hideAlert() {
    if (DOM.globalAlert) DOM.globalAlert.style.display = 'none';
  }

  // ==========================================
  // URL 整理與連線檢查
  // ==========================================

  /**
   * 依規範整理 URL：
   * 主機是 localhost 且 port 是 5000 時，改為 127.0.0.1，保留協定與路徑。
   */
  function normalizeApiUrl(rawUrl) {
    const trimmed = String(rawUrl).trim();
    if (!trimmed) {
      throw new Error('請輸入後端服務網址');
    }

    let urlObj;
    try {
      urlObj = new URL(trimmed);
    } catch (e) {
      throw new Error('網址格式不正確，必須以 http:// 或 https:// 開頭');
    }

    if (urlObj.protocol !== 'http:' && urlObj.protocol !== 'https:') {
      throw new Error('網址必須是 http 或 https 協定');
    }

    // 若主機是 localhost 且 port 是 5000，改成 127.0.0.1
    if ((urlObj.hostname === 'localhost' || urlObj.hostname === '[::1]') && urlObj.port === '5000') {
      urlObj.hostname = '127.0.0.1';
    }

    // 移除末尾多餘的斜線
    let normalized = urlObj.origin + urlObj.pathname.replace(/\/+$/, '');
    return normalized;
  }

  /**
   * 統一 API Fetch 封裝
   * 遵守規範：
   * - GET 加上 _t 毫秒時間戳記防快取
   * - 僅有 body 時加上 Content-Type: application/json
   * - cache: 'no-store', mode: 'cors'
   * - 失敗時拋出 message，連不上時為「目前連不上記帳服務」
   */
  async function apiFetch(endpoint, options = {}) {
    if (!STATE.apiBaseUrl) {
      throw new Error('尚未設定後端連線網址');
    }

    const method = (options.method || 'GET').toUpperCase();
    const fullUrl = new URL(STATE.apiBaseUrl + endpoint);

    if (method === 'GET') {
      fullUrl.searchParams.set('_t', Date.now().toString());
    }

    const headers = { ...options.headers };
    if (options.body && typeof options.body === 'string') {
      headers['Content-Type'] = 'application/json';
    }

    let response;
    try {
      response = await fetch(fullUrl.toString(), {
        method,
        headers,
        body: options.body,
        cache: 'no-store',
        mode: 'cors',
      });
    } catch (err) {
      // 網路錯誤、CORS 擋下、離線等
      throw new Error('目前連不上記帳服務');
    }

    let json;
    try {
      json = await response.json();
    } catch (e) {
      if (!response.ok) {
        throw new Error('目前連不上記帳服務');
      }
      return null;
    }

    if (!response.ok || (json && json.code >= 400)) {
      const msg = (json && json.message) ? json.message : '目前連不上記帳服務';
      throw new Error(msg);
    }

    return json;
  }

  /**
   * 驗證健康檢查端點
   */
  async function verifyHealth(baseUrl) {
    const healthUrl = new URL(baseUrl + '/api/health');
    healthUrl.searchParams.set('_t', Date.now().toString());

    let res;
    try {
      res = await fetch(healthUrl.toString(), {
        method: 'GET',
        cache: 'no-store',
        mode: 'cors',
      });
    } catch (err) {
      throw new Error('目前連不上記帳服務');
    }

    let json;
    try {
      json = await res.json();
    } catch (e) {
      throw new Error('目前連不上記帳服務');
    }

    if (!res.ok || json.code !== 200 || !json.data || json.data.status !== 'ok') {
      const msg = json && json.message ? json.message : '目前連不上記帳服務';
      throw new Error(msg);
    }

    return true;
  }

  // ==========================================
  // 畫面切換與導覽
  // ==========================================

  function switchView(viewId) {
    STATE.currentView = viewId;

    DOM.viewPanels.forEach((panel) => {
      if (panel.id === viewId) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });

    if (viewId === 'view-connection') {
      DOM.bottomNav.style.display = 'none';
      DOM.btnClearConn.style.display = 'none';
    } else {
      DOM.bottomNav.style.display = 'flex';
      DOM.btnClearConn.style.display = 'inline-block';

      DOM.navItems.forEach((btn) => {
        if (btn.getAttribute('data-view') === viewId) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });
    }

    // 進入各頁面時觸發資料載入
    if (viewId === 'view-home') {
      loadHomeData();
    } else if (viewId === 'view-accounting') {
      loadAccountingData();
    } else if (viewId === 'view-investments') {
      loadInvestmentsData();
    } else if (viewId === 'view-invoices') {
      loadInvoicesData();
    }
  }

  // ==========================================
  // 首頁邏輯 (Home View)
  // ==========================================

  async function loadHomeData() {
    DOM.homeMonthDisplay.textContent = STATE.currentMonth;
    try {
      // 1. 取得本月生活現金流彙總
      const summaryRes = await apiFetch(`/api/summary?month=${encodeURIComponent(STATE.currentMonth)}`);
      if (summaryRes && summaryRes.data) {
        const income = Number(summaryRes.data.income_twd) || 0;
        const expense = Number(summaryRes.data.expense_twd) || 0;
        const net = income - expense;

        DOM.homeIncomeTwd.textContent = formatCurrency(income);
        DOM.homeExpenseTwd.textContent = formatCurrency(expense);
        DOM.homeNetTwd.textContent = formatCurrency(net);
      }

      // 2. 取得帳戶清單與個別餘額
      const accountsRes = await apiFetch('/api/accounts');
      const accounts = (accountsRes && accountsRes.data) ? accountsRes.data : [];
      STATE.accounts = accounts;

      if (accounts.length === 0) {
        DOM.homeAccountsList.innerHTML = '';
        DOM.homeEmptyAccounts.style.display = 'flex';
        return;
      }

      DOM.homeEmptyAccounts.style.display = 'none';
      DOM.homeAccountsList.innerHTML = '<p class="form-hint">計算帳戶餘額中...</p>';

      // 並行取得每個帳戶之餘額
      const balancePromises = accounts.map((acc) =>
        apiFetch(`/api/accounts/${acc.id}/balance`).catch(() => null)
      );
      const balanceResults = await Promise.all(balancePromises);

      let cardsHtml = '';
      accounts.forEach((acc, index) => {
        const balData = balanceResults[index] ? balanceResults[index].data : null;
        const twdBal = balData ? balData.twd_balance : acc.opening_balance;
        const kindLabel = getAccountKindLabel(acc.kind);

        cardsHtml += `
          <div class="account-card">
            <div class="account-info">
              <div class="account-name-row">
                <span class="account-name">${escapeHtml(acc.name)}</span>
                <span class="account-badge">${kindLabel}</span>
              </div>
              <span class="account-curr">${escapeHtml(acc.currency)}</span>
            </div>
            <div class="account-balance-val">$ ${formatCurrency(twdBal)}</div>
          </div>
        `;
      });

      DOM.homeAccountsList.innerHTML = cardsHtml;
    } catch (err) {
      showAlert(err.message);
    }
  }

  function getAccountKindLabel(kind) {
    switch (kind) {
      case 'cash': return '現金';
      case 'bank': return '銀行';
      case 'credit_card': return '信用卡';
      case 'broker': return '券商交割戶';
      default: return kind || '帳戶';
    }
  }

  async function handleCreateCashAccount() {
    try {
      DOM.btnCreateCashAccount.disabled = true;
      const payload = {
        name: '現金錢包',
        kind: 'cash',
        currency: 'TWD',
        opening_balance: 0.0,
      };

      const res = await apiFetch('/api/accounts', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      showAlert('已成功建立現金錢包！', true);
      await loadHomeData();
    } catch (err) {
      showAlert(err.message);
    } finally {
      DOM.btnCreateCashAccount.disabled = false;
    }
  }

  // ==========================================
  // 記帳頁邏輯 (Accounting View)
  // ==========================================

  async function loadAccountingData() {
    // 預設填入今日日期
    if (!DOM.expSpentOn.value) DOM.expSpentOn.value = getTodayDateString();
    if (!DOM.incReceivedOn.value) DOM.incReceivedOn.value = getTodayDateString();

    try {
      // 載入帳戶
      const accRes = await apiFetch('/api/accounts');
      STATE.accounts = (accRes && accRes.data) ? accRes.data : [];
      renderAccountDropdowns();

      // 載入兩種分類
      const [expCatRes, incCatRes] = await Promise.all([
        apiFetch('/api/expense-categories').catch(() => ({ data: [] })),
        apiFetch('/api/income-categories').catch(() => ({ data: [] })),
      ]);

      STATE.expenseCategories = (expCatRes && expCatRes.data) ? expCatRes.data : [];
      STATE.incomeCategories = (incCatRes && incCatRes.data) ? incCatRes.data : [];

      renderCategoryDropdowns();

      // 載入本月初始明細
      await loadMonthRecentEntries();
    } catch (err) {
      showAlert(err.message);
    }
  }

  function renderAccountDropdowns() {
    const optionsHtml = STATE.accounts.length === 0
      ? '<option value="">尚無可用帳戶</option>'
      : STATE.accounts.map((acc) => `<option value="${acc.id}">${escapeHtml(acc.name)} (${acc.currency})</option>`).join('');

    DOM.expAccount.innerHTML = optionsHtml;
    DOM.incAccount.innerHTML = optionsHtml;
  }

  function renderCategoryDropdowns() {
    // 花費分類
    if (STATE.expenseCategories.length === 0) {
      DOM.expCategory.innerHTML = '<option value="">尚無分類 (點右側 + 建立)</option>';
    } else {
      DOM.expCategory.innerHTML = STATE.expenseCategories
        .map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`)
        .join('');
    }

    // 入帳分類
    if (STATE.incomeCategories.length === 0) {
      DOM.incCategory.innerHTML = '<option value="">尚無分類 (點右側 + 建立)</option>';
    } else {
      DOM.incCategory.innerHTML = STATE.incomeCategories
        .map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`)
        .join('');
    }
  }

  async function loadMonthRecentEntries() {
    try {
      const today = new Date();
      const y = today.getFullYear();
      const m = today.getMonth() + 1;
      const lastDay = new Date(y, m, 0).getDate();
      const dateFrom = `${STATE.currentMonth}-01`;
      const dateTo = `${STATE.currentMonth}-${String(lastDay).padStart(2, '0')}`;

      const [expRes, incRes] = await Promise.all([
        apiFetch(`/api/expenses?date_from=${dateFrom}&date_to=${dateTo}`).catch(() => ({ data: [] })),
        apiFetch(`/api/incomes?date_from=${dateFrom}&date_to=${dateTo}`).catch(() => ({ data: [] })),
      ]);

      const expenses = (expRes && expRes.data) ? expRes.data.map((e) => ({ ...e, _type: 'expense', date: e.spent_on })) : [];
      const incomes = (incRes && incRes.data) ? incRes.data.map((i) => ({ ...i, _type: 'income', date: i.received_on })) : [];

      const combined = [...expenses, ...incomes].sort((a, b) => {
        if (b.date !== a.date) return b.date.localeCompare(a.date);
        return (b.id || 0) - (a.id || 0);
      });

      STATE.monthlyEntries = combined;
      renderRecentList();
    } catch (e) {
      // 忽略列表錯誤
    }
  }

  function renderRecentList() {
    if (STATE.monthlyEntries.length === 0) {
      DOM.accountingRecentList.innerHTML = '<p class="form-hint" style="text-align: center;">本月尚無任何記帳記錄</p>';
      return;
    }

    const html = STATE.monthlyEntries.slice(0, 30).map((item) => {
      const isIncome = item._type === 'income';
      const title = isIncome
        ? (item.source || item.note || '未命名收入')
        : (item.merchant || item.note || '未命名支出');
      const dateStr = item.date || '';
      const amountStr = (isIncome ? '+ ' : '- ') + formatCurrency(item.amount);
      const amountClass = isIncome ? 'income' : 'expense';

      return `
        <div class="recent-item">
          <div class="recent-left">
            <span class="recent-title">${escapeHtml(title)}</span>
            <span class="recent-meta">${escapeHtml(dateStr)}</span>
          </div>
          <span class="recent-amount ${amountClass}">${amountStr}</span>
        </div>
      `;
    }).join('');

    DOM.accountingRecentList.innerHTML = html;
  }

  // 提交花費
  async function handleExpenseSubmit(e) {
    e.preventDefault();
    hideAlert();

    const spentOn = DOM.expSpentOn.value.trim();
    const amountVal = DOM.expAmount.value.trim();
    const categoryIdVal = DOM.expCategory.value;
    const accountIdVal = DOM.expAccount.value;
    const merchant = DOM.expMerchant.value.trim() || null;
    const note = DOM.expNote.value.trim() || null;
    const settledOn = DOM.expSettledOn.value.trim() || null;

    if (!spentOn) return showAlert('消費日期為必填項目');
    if (!amountVal || Number(amountVal) <= 0) return showAlert('金額必須大於 0');
    if (!categoryIdVal) return showAlert('請選擇花費分類');
    if (!accountIdVal) return showAlert('請選擇扣款帳戶');
    if (!merchant && !note) return showAlert('商家與備註不可同時為空，至少需填寫一項');

    const payload = {
      spent_on: spentOn,
      amount: Number(amountVal),
      currency: 'TWD',
      fx_rate_to_twd: 1.0,
      category_id: Number(categoryIdVal),
      account_id: Number(accountIdVal),
      merchant,
      note,
      settled_on: settledOn,
    };

    try {
      const res = await apiFetch('/api/expenses', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      showAlert('花費建立成功！', true);

      // 把新列放在本月清單最上方
      const newItem = {
        ...res.data,
        _type: 'expense',
        date: res.data.spent_on,
      };
      STATE.monthlyEntries.unshift(newItem);
      renderRecentList();

      // 清理表單數值
      DOM.expAmount.value = '';
      DOM.expMerchant.value = '';
      DOM.expNote.value = '';
      DOM.expSettledOn.value = '';
    } catch (err) {
      showAlert(err.message);
    }
  }

  // 提交入帳
  async function handleIncomeSubmit(e) {
    e.preventDefault();
    hideAlert();

    const receivedOn = DOM.incReceivedOn.value.trim();
    const amountVal = DOM.incAmount.value.trim();
    const categoryIdVal = DOM.incCategory.value;
    const accountIdVal = DOM.incAccount.value;
    const source = DOM.incSource.value.trim() || null;
    const note = DOM.incNote.value.trim() || null;

    if (!receivedOn) return showAlert('入帳日期為必填項目');
    if (!amountVal || Number(amountVal) <= 0) return showAlert('金額必須大於 0');
    if (!categoryIdVal) return showAlert('請選擇入帳分類');
    if (!accountIdVal) return showAlert('請選擇存入帳戶');
    if (!source && !note) return showAlert('來源與備註不可同時為空，至少需填寫一項');

    const payload = {
      received_on: receivedOn,
      amount: Number(amountVal),
      currency: 'TWD',
      fx_rate_to_twd: 1.0,
      category_id: Number(categoryIdVal),
      account_id: Number(accountIdVal),
      source,
      note,
    };

    try {
      const res = await apiFetch('/api/incomes', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      showAlert('入帳建立成功！', true);

      // 把新列放在本月清單最上方
      const newItem = {
        ...res.data,
        _type: 'income',
        date: res.data.received_on,
      };
      STATE.monthlyEntries.unshift(newItem);
      renderRecentList();

      // 清理表單數值
      DOM.incAmount.value = '';
      DOM.incSource.value = '';
      DOM.incNote.value = '';
    } catch (err) {
      showAlert(err.message);
    }
  }

  // 快速建立分類 Modal
  function openQuickCategoryModal(type) {
    STATE.quickCatType = type;
    DOM.modalCatTitle.textContent = type === 'expense' ? '快速新增花費分類' : '快速新增入帳分類';
    DOM.inputCatName.value = '';
    if (typeof DOM.modalQuickCategory.showModal === 'function') {
      DOM.modalQuickCategory.showModal();
    } else {
      DOM.modalQuickCategory.style.display = 'block';
    }
  }

  function closeQuickCategoryModal() {
    if (typeof DOM.modalQuickCategory.close === 'function') {
      DOM.modalQuickCategory.close();
    } else {
      DOM.modalQuickCategory.style.display = 'none';
    }
  }

  async function handleQuickCategorySubmit(e) {
    e.preventDefault();
    const name = DOM.inputCatName.value.trim();
    if (!name) return showAlert('分類名稱不能為空');

    const endpoint = STATE.quickCatType === 'expense' ? '/api/expense-categories' : '/api/income-categories';

    try {
      const res = await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ name }),
      });

      showAlert(`分類「${name}」建立成功！`, true);
      closeQuickCategoryModal();

      if (STATE.quickCatType === 'expense') {
        STATE.expenseCategories.push(res.data);
        renderCategoryDropdowns();
        DOM.expCategory.value = res.data.id;
      } else {
        STATE.incomeCategories.push(res.data);
        renderCategoryDropdowns();
        DOM.incCategory.value = res.data.id;
      }
    } catch (err) {
      showAlert(err.message);
    }
  }

  // ==========================================
  // 投資頁邏輯 (Investments View)
  // ==========================================

  async function loadInvestmentsData() {
    DOM.investmentsFeedback.style.display = 'none';
    DOM.investmentsList.innerHTML = '<p class="form-hint" style="text-align:center;">載入投資標的中...</p>';

    try {
      const res = await apiFetch('/api/instruments');
      const instruments = (res && res.data) ? res.data : [];

      // 只列出 tw_stock
      const twStocks = instruments.filter((item) => item.market === 'tw_stock');

      if (twStocks.length === 0) {
        DOM.investmentsList.innerHTML = '<div class="card empty-card"><p>目前尚無台股標的</p></div>';
        return;
      }

      // 並行取得每個標的之 holding 與 quote
      const detailsPromises = twStocks.map(async (stock) => {
        let holding = null;
        let quote = null;

        try {
          const hRes = await apiFetch(`/api/instruments/${stock.id}/holding`);
          holding = hRes ? hRes.data : null;
        } catch (e) {
          // 無持有
        }

        try {
          const qRes = await apiFetch(`/api/instruments/${stock.id}/quote`);
          quote = (qRes && qRes.data && qRes.data.price != null) ? qRes.data.price : null;
        } catch (e) {
          // 無報價或端點未實作
        }

        return { stock, holding, quote };
      });

      const results = await Promise.all(detailsPromises);

      let html = '';
      results.forEach(({ stock, holding, quote }) => {
        const qty = holding ? Number(holding.quantity) || 0 : 0;
        const avgCost = holding ? Number(holding.average_cost) || 0 : 0;
        const quoteText = quote != null ? `$ ${formatCurrency(quote)}` : '還沒有報價';

        html += `
          <div class="invest-card">
            <div class="invest-header">
              <span class="invest-name">${escapeHtml(stock.name)}</span>
              <span class="invest-symbol">${escapeHtml(stock.symbol)}</span>
            </div>
            <div class="invest-row">
              <span class="invest-row-label">持有數量</span>
              <span class="invest-row-value">${qty.toLocaleString()} 股</span>
            </div>
            <div class="invest-row">
              <span class="invest-row-label">平均成本</span>
              <span class="invest-row-value">$ ${formatCurrency(avgCost)}</span>
            </div>
            <div class="invest-row">
              <span class="invest-row-label">最新報價</span>
              <span class="invest-row-value">${quoteText}</span>
            </div>
          </div>
        `;
      });

      DOM.investmentsList.innerHTML = html;
    } catch (err) {
      showAlert(err.message);
      DOM.investmentsList.innerHTML = '';
    }
  }

  async function handleFetchQuotes() {
    DOM.btnFetchQuotes.disabled = true;
    DOM.btnFetchQuotes.textContent = '抓取中...';
    hideAlert();

    try {
      const res = await apiFetch('/api/tw-stock-quotes/fetch', {
        method: 'POST',
        body: '{}',
      });

      // missing 與 skipped 用一句人話帶過
      const data = res.data || {};
      const missing = data.missing != null ? data.missing : 0;
      const skipped = data.skipped != null ? data.skipped : 0;
      const msg = `台股報價更新完成（略過 ${skipped} 檔、缺少 ${missing} 檔）`;

      DOM.investmentsFeedback.textContent = msg;
      DOM.investmentsFeedback.style.display = 'block';
    } catch (err) {
      DOM.investmentsFeedback.textContent = err.message || '證交所目前沒有回應';
      DOM.investmentsFeedback.style.display = 'block';
    } finally {
      DOM.btnFetchQuotes.disabled = false;
      DOM.btnFetchQuotes.textContent = '抓取台股報價';
      // 完成後重讀
      await loadInvestmentsData();
    }
  }

  // ==========================================
  // 發票頁邏輯 (Invoices View)
  // ==========================================

  async function loadInvoicesData() {
    DOM.invoicesList.innerHTML = '<p class="form-hint" style="text-align:center;">載入發票清單中...</p>';

    try {
      const res = await apiFetch('/api/invoices');
      const invoices = (res && res.data) ? res.data : [];

      if (invoices.length === 0) {
        DOM.invoicesList.innerHTML = '<div class="card empty-card"><p>目前尚無發票記錄</p></div>';
        return;
      }

      let html = '';
      invoices.forEach((inv) => {
        const badgeInfo = getPrizeStatusBadge(inv.prize_status);
        html += `
          <div class="invoice-card">
            <div class="invoice-left">
              <span class="invoice-num">${escapeHtml(inv.number)}</span>
              <span class="invoice-date">${escapeHtml(inv.issued_on)}</span>
            </div>
            <div class="invoice-right">
              <span class="invoice-amt">$ ${formatCurrency(inv.amount)}</span>
              <span class="invoice-badge ${badgeInfo.className}">${badgeInfo.text}</span>
            </div>
          </div>
        `;
      });

      DOM.invoicesList.innerHTML = html;
    } catch (err) {
      showAlert(err.message);
      DOM.invoicesList.innerHTML = '';
    }
  }

  function getPrizeStatusBadge(status) {
    switch (status) {
      case 'won': return { text: '已中獎', className: 'badge-won' };
      case 'claimed': return { text: '已領獎', className: 'badge-claimed' };
      case 'lost': return { text: '未中獎', className: 'badge-lost' };
      case 'void': return { text: '已作廢', className: 'badge-void' };
      case 'unchecked':
      default:
        return { text: '未對獎', className: 'badge-unchecked' };
    }
  }

  // ==========================================
  // 事件綁定與初始化
  // ==========================================

  function bindEvents() {
    // 連線表單提交
    DOM.formConnection.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert();

      const raw = DOM.inputApiUrl.value;
      let normalized;
      try {
        normalized = normalizeApiUrl(raw);
      } catch (err) {
        return showAlert(err.message);
      }

      const submitBtn = document.getElementById('btn-connect');
      submitBtn.disabled = true;
      submitBtn.textContent = '連線中...';

      try {
        await verifyHealth(normalized);
        STATE.apiBaseUrl = normalized;

        // 寫入 localStorage 的 ledger.connection，只含 apiBaseUrl
        localStorage.setItem('ledger.connection', JSON.stringify({ apiBaseUrl: normalized }));
        showAlert('連線成功！', true);
        switchView('view-home');
      } catch (err) {
        showAlert(err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '連線並進入首頁';
      }
    });

    // 清除連線
    DOM.btnClearConn.addEventListener('click', () => {
      localStorage.removeItem('ledger.connection');
      STATE.apiBaseUrl = null;
      DOM.inputApiUrl.value = '';
      showAlert('已清除連線設定');
      switchView('view-connection');
    });

    // 底部導覽點擊
    DOM.navItems.forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetView = btn.getAttribute('data-view');
        if (targetView && targetView !== STATE.currentView) {
          switchView(targetView);
        }
      });
    });

    // 首頁重新整理
    DOM.btnRefreshHome.addEventListener('click', loadHomeData);

    // 快速建立現金帳戶
    DOM.btnCreateCashAccount.addEventListener('click', handleCreateCashAccount);

    // 記帳標籤切換
    DOM.btnTabExpense.addEventListener('click', () => {
      DOM.btnTabExpense.classList.add('active');
      DOM.btnTabIncome.classList.remove('active');
      DOM.panelExpenseForm.style.display = 'block';
      DOM.panelIncomeForm.style.display = 'none';
    });

    DOM.btnTabIncome.addEventListener('click', () => {
      DOM.btnTabIncome.classList.add('active');
      DOM.btnTabExpense.classList.remove('active');
      DOM.panelExpenseForm.style.display = 'none';
      DOM.panelIncomeForm.style.display = 'block';
    });

    // 記帳表單提交
    DOM.formExpense.addEventListener('submit', handleExpenseSubmit);
    DOM.formIncome.addEventListener('submit', handleIncomeSubmit);

    // 快速分類 Modal 觸發與處理
    DOM.btnQuickExpCat.addEventListener('click', () => openQuickCategoryModal('expense'));
    DOM.btnQuickIncCat.addEventListener('click', () => openQuickCategoryModal('income'));
    DOM.btnCancelCat.addEventListener('click', closeQuickCategoryModal);
    DOM.formQuickCat.addEventListener('submit', handleQuickCategorySubmit);

    // 投資頁抓取報價
    DOM.btnFetchQuotes.addEventListener('click', handleFetchQuotes);

    // 發票頁重新整理
    DOM.btnRefreshInvoices.addEventListener('click', loadInvoicesData);
  }

  // 應用程式初始化
  async function initApp() {
    bindEvents();

    const stored = localStorage.getItem('ledger.connection');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed && parsed.apiBaseUrl) {
          const normalized = normalizeApiUrl(parsed.apiBaseUrl);
          DOM.inputApiUrl.value = normalized;

          // 已存過的連線，下次打開先重查這一次
          await verifyHealth(normalized);
          STATE.apiBaseUrl = normalized;
          switchView('view-home');
          return;
        }
      } catch (err) {
        showAlert('先前連線已失效或無法連線，請重新設定');
        switchView('view-connection');
        return;
      }
    }

    // 預設為連線頁
    switchView('view-connection');
  }

  // 啟動
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }
})();
