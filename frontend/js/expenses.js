/**
 * Expenses Module
 * Manages expense creation (single & multi payers, equal / % / exact split methods),
 * expense listing, and detailed expense view modals.
 */

const Expenses = {
  expensesList: [],
  selectedExpense: null,

  categoryIcons: {
    Food: '🍔',
    Travel: '✈️',
    Transport: '🚕',
    Stay: '🏨',
    Entertainment: '🎬',
    Shopping: '🛍️',
    Other: '📦',
  },

  async loadExpenses(groupId) {
    try {
      const res = await API.get(`/groups/${groupId}/expenses`);
      this.expensesList = res.data || [];
      this.renderExpensesList();
    } catch (error) {
      showToast(error.message || 'Failed to load expenses', 'error');
    }
  },

  renderExpensesList() {
    const listEl = document.getElementById('recentExpensesList');
    if (!listEl) return;

    if (this.expensesList.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state" style="padding: 2rem 1rem;">
          <div style="font-size: 2rem;">🧾</div>
          <div style="font-weight: 600;">No expenses yet</div>
          <p style="font-size: 0.8125rem; color: var(--text-muted);">Add your first group expense to get started</p>
        </div>
      `;
      return;
    }

    const currentUser = Auth.getUser();

    listEl.innerHTML = this.expensesList
      .map((exp) => {
        const icon = this.categoryIcons[exp.category] || '📦';
        const dateStr = new Date(exp.date).toLocaleDateString('en-IN', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
        });

        // Determine payer display text
        let payerText = '';
        if (exp.payments.length === 1) {
          const p = exp.payments[0];
          const isMe = p.userId?._id === currentUser?._id;
          payerText = `Paid by ${isMe ? 'You' : p.userId?.name || 'Member'}`;
        } else {
          payerText = `Paid by ${exp.payments.length} people`;
        }

        // Determine current user's share
        const mySplit = exp.splits.find((s) => s.userId?._id === currentUser?._id);
        const myPayment = exp.payments.find((p) => p.userId?._id === currentUser?._id);
        const myPaidAmt = myPayment ? myPayment.amount : 0;
        const myShareAmt = mySplit ? mySplit.amount : 0;

        let shareTag = '';
        if (myPaidAmt > 0 && myShareAmt > 0) {
          shareTag = `<span class="expense-share-tag">You paid ₹${myPaidAmt.toFixed(2)}, share ₹${myShareAmt.toFixed(2)}</span>`;
        } else if (myPaidAmt > 0) {
          shareTag = `<span class="expense-share-tag" style="color: var(--success);">You paid ₹${myPaidAmt.toFixed(2)}</span>`;
        } else if (myShareAmt > 0) {
          shareTag = `<span class="expense-share-tag" style="color: var(--danger);">Your share ₹${myShareAmt.toFixed(2)}</span>`;
        }

        return `
          <div class="expense-item" onclick="Expenses.openDetailsModal('${exp._id}')">
            <div class="expense-left">
              <div class="category-icon-box">${icon}</div>
              <div class="expense-meta">
                <span class="expense-title">${exp.title}</span>
                <span class="expense-subtitle">${exp.category} • ${payerText} • ${dateStr}</span>
              </div>
            </div>
            <div class="expense-right">
              <span class="expense-amount">₹${exp.amount.toFixed(2)}</span>
              ${shareTag}
            </div>
          </div>
        `;
      })
      .join('');
  },

  initAddExpenseModal() {
    if (!Groups.currentGroup) return;

    const modal = document.getElementById('addExpenseModal');
    const form = document.getElementById('addExpenseForm');
    const members = Groups.currentGroup.members || [];
    const currentUser = Auth.getUser();

    // Reset Form
    form.reset();
    document.getElementById('expenseDate').valueAsDate = new Date();
    document.getElementById('addExpenseAlert').className = 'alert-box';

    // Populate Single Payer Select
    const singleSelect = document.getElementById('singlePayerSelect');
    singleSelect.innerHTML = members
      .map(
        (m) =>
          `<option value="${m._id}" ${
            m._id === currentUser?._id ? 'selected' : ''
          }>${m.name}${m._id === currentUser?._id ? ' (You)' : ''}</option>`
      )
      .join('');

    // Populate Multi Payer List
    const multiList = document.getElementById('multiPayerInputsList');
    multiList.innerHTML = members
      .map(
        (m) => `
        <div class="payer-split-row">
          <span class="split-user-name">${m.name}${m._id === currentUser?._id ? ' (You)' : ''}</span>
          <div class="split-input-wrap">
            <span class="split-currency-symbol">₹</span>
            <input type="number" step="0.01" min="0" class="form-control multi-payer-input" data-user-id="${m._id}" placeholder="0.00">
          </div>
        </div>
      `
      )
      .join('');

    // Populate Split Inputs List
    this.renderSplitInputs();
    this.attachCalculationListeners();

    modal.classList.add('active');
  },

  renderSplitInputs() {
    const splitMethod = document.querySelector('input[name="splitMethod"]:checked')?.value || 'equal';
    const splitList = document.getElementById('splitInputsList');
    const members = Groups.currentGroup?.members || [];
    const currentUser = Auth.getUser();
    const totalAmount = parseFloat(document.getElementById('expenseAmount')?.value) || 0;

    if (splitMethod === 'equal') {
      splitList.innerHTML = members
        .map(
          (m) => `
          <div class="payer-split-row">
            <label style="display: flex; align-items: center; gap: 0.625rem; cursor: pointer; flex: 1;">
              <input type="checkbox" class="split-equal-check" data-user-id="${m._id}" checked style="width: 18px; height: 18px; accent-color: var(--primary);">
              <span class="split-user-name">${m.name}${m._id === currentUser?._id ? ' (You)' : ''}</span>
            </label>
            <span class="split-equal-amount" data-user-id="${m._id}" style="font-weight: 600; font-size: 0.9375rem; color: var(--text-muted);">
              ₹0.00
            </span>
          </div>
        `
        )
        .join('');
    } else if (splitMethod === 'percentage') {
      splitList.innerHTML = members
        .map(
          (m) => `
          <div class="payer-split-row">
            <span class="split-user-name">${m.name}${m._id === currentUser?._id ? ' (You)' : ''}</span>
            <div class="split-input-wrap">
              <input type="number" step="0.01" min="0" max="100" class="form-control split-percent-input" data-user-id="${m._id}" placeholder="0">
              <span class="split-currency-symbol">%</span>
            </div>
            <span class="split-calc-val" data-user-id="${m._id}" style="font-size: 0.8125rem; color: var(--text-muted); min-width: 60px; text-align: right;">
              ₹0.00
            </span>
          </div>
        `
        )
        .join('');
    } else if (splitMethod === 'exact') {
      splitList.innerHTML = members
        .map(
          (m) => `
          <div class="payer-split-row">
            <span class="split-user-name">${m.name}${m._id === currentUser?._id ? ' (You)' : ''}</span>
            <div class="split-input-wrap">
              <span class="split-currency-symbol">₹</span>
              <input type="number" step="0.01" min="0" class="form-control split-exact-input" data-user-id="${m._id}" placeholder="0.00">
            </div>
          </div>
        `
        )
        .join('');
    }

    this.recalculateSplits();
  },

  attachCalculationListeners() {
    const amountInput = document.getElementById('expenseAmount');
    if (amountInput) {
      amountInput.addEventListener('input', () => {
        this.recalculateMultiPayer();
        this.recalculateSplits();
      });
    }

    // Toggle Single vs Multi Payer
    document.querySelectorAll('input[name="payerType"]').forEach((radio) => {
      radio.addEventListener('change', (e) => {
        const isMulti = e.target.value === 'multiple';
        document.getElementById('singlePayerContainer').style.display = isMulti ? 'none' : 'block';
        document.getElementById('multiPayerContainer').style.display = isMulti ? 'block' : 'none';
        this.recalculateMultiPayer();
      });
    });

    // Toggle Split Method
    document.querySelectorAll('input[name="splitMethod"]').forEach((radio) => {
      radio.addEventListener('change', () => {
        this.renderSplitInputs();
      });
    });

    // Dynamic Multi-payer Input changes
    const multiList = document.getElementById('multiPayerInputsList');
    if (multiList) {
      multiList.addEventListener('input', () => this.recalculateMultiPayer());
    }

    // Dynamic Split Input changes
    const splitList = document.getElementById('splitInputsList');
    if (splitList) {
      splitList.addEventListener('input', () => this.recalculateSplits());
      splitList.addEventListener('change', () => this.recalculateSplits());
    }
  },

  recalculateMultiPayer() {
    const payerType = document.querySelector('input[name="payerType"]:checked')?.value;
    if (payerType !== 'multiple') return;

    const totalAmount = parseFloat(document.getElementById('expenseAmount')?.value) || 0;
    const inputs = document.querySelectorAll('.multi-payer-input');
    let sumPaid = 0;

    inputs.forEach((input) => {
      sumPaid += parseFloat(input.value) || 0;
    });

    const diff = totalAmount - sumPaid;
    const summaryPill = document.getElementById('multiPayerSummary');
    const remainderSpan = document.getElementById('multiPayerRemainder');

    if (summaryPill && remainderSpan) {
      summaryPill.children[0].textContent = `Total Paid: ₹${sumPaid.toFixed(2)}`;

      if (Math.abs(diff) < 0.01 && totalAmount > 0) {
        summaryPill.className = 'calc-summary-pill valid';
        remainderSpan.textContent = '✓ Exact match';
      } else if (diff > 0) {
        summaryPill.className = 'calc-summary-pill invalid';
        remainderSpan.textContent = `Remaining: ₹${diff.toFixed(2)}`;
      } else {
        summaryPill.className = 'calc-summary-pill invalid';
        remainderSpan.textContent = `Overpaid by: ₹${Math.abs(diff).toFixed(2)}`;
      }
    }
  },

  recalculateSplits() {
    const splitMethod = document.querySelector('input[name="splitMethod"]:checked')?.value || 'equal';
    const totalAmount = parseFloat(document.getElementById('expenseAmount')?.value) || 0;
    const summaryPill = document.getElementById('splitSummaryPill');
    const labelEl = document.getElementById('splitSummaryLabel');
    const statusEl = document.getElementById('splitSummaryStatus');

    if (splitMethod === 'equal') {
      const checkedBoxes = Array.from(document.querySelectorAll('.split-equal-check:checked'));
      const count = checkedBoxes.length;
      const share = count > 0 && totalAmount > 0 ? totalAmount / count : 0;

      document.querySelectorAll('.split-equal-amount').forEach((span) => {
        const uid = span.getAttribute('data-user-id');
        const isChecked = document.querySelector(`.split-equal-check[data-user-id="${uid}"]`)?.checked;
        span.textContent = isChecked ? `₹${share.toFixed(2)}` : '₹0.00';
      });

      if (labelEl) labelEl.textContent = `Split across ${count} members (${count > 0 ? `₹${share.toFixed(2)} each` : 'none'})`;
      if (statusEl) statusEl.textContent = count > 0 ? '✓ Balanced' : 'Select at least 1 person';
      if (summaryPill) summaryPill.className = count > 0 ? 'calc-summary-pill valid' : 'calc-summary-pill invalid';
    } else if (splitMethod === 'percentage') {
      let sumPct = 0;
      const inputs = document.querySelectorAll('.split-percent-input');
      inputs.forEach((input) => {
        const pct = parseFloat(input.value) || 0;
        sumPct += pct;
        const uid = input.getAttribute('data-user-id');
        const calcValEl = document.querySelector(`.split-calc-val[data-user-id="${uid}"]`);
        if (calcValEl) {
          const val = (totalAmount * pct) / 100;
          calcValEl.textContent = `₹${val.toFixed(2)}`;
        }
      });

      const diff = 100 - sumPct;
      if (labelEl) labelEl.textContent = `Total Percentage: ${sumPct.toFixed(1)}%`;
      if (Math.abs(diff) < 0.05) {
        if (statusEl) statusEl.textContent = '✓ 100% Balanced';
        if (summaryPill) summaryPill.className = 'calc-summary-pill valid';
      } else {
        if (statusEl) statusEl.textContent = diff > 0 ? `Remaining: ${diff.toFixed(1)}%` : `Excess: ${Math.abs(diff).toFixed(1)}%`;
        if (summaryPill) summaryPill.className = 'calc-summary-pill invalid';
      }
    } else if (splitMethod === 'exact') {
      let sumExact = 0;
      const inputs = document.querySelectorAll('.split-exact-input');
      inputs.forEach((input) => {
        sumExact += parseFloat(input.value) || 0;
      });

      const diff = totalAmount - sumExact;
      if (labelEl) labelEl.textContent = `Total Assigned: ₹${sumExact.toFixed(2)}`;
      if (Math.abs(diff) < 0.02 && totalAmount > 0) {
        if (statusEl) statusEl.textContent = '✓ Balanced';
        if (summaryPill) summaryPill.className = 'calc-summary-pill valid';
      } else {
        if (statusEl) statusEl.textContent = diff > 0 ? `Remaining: ₹${diff.toFixed(2)}` : `Over by: ₹${Math.abs(diff).toFixed(2)}`;
        if (summaryPill) summaryPill.className = 'calc-summary-pill invalid';
      }
    }
  },

  async handleSaveExpense() {
    const alertBox = document.getElementById('addExpenseAlert');
    const submitBtn = document.getElementById('submitAddExpenseBtn');

    const title = document.getElementById('expenseTitle').value.trim();
    const amount = parseFloat(document.getElementById('expenseAmount').value);
    const category = document.getElementById('expenseCategory').value;
    const date = document.getElementById('expenseDate').value;
    const payerType = document.querySelector('input[name="payerType"]:checked').value;
    const splitMethod = document.querySelector('input[name="splitMethod"]:checked').value;

    if (!title) throw new Error('Please enter an expense title');
    if (isNaN(amount) || amount <= 0) throw new Error('Amount must be greater than zero');

    // Build Payments Array
    const payments = [];
    if (payerType === 'single') {
      const payerId = document.getElementById('singlePayerSelect').value;
      payments.push({ userId: payerId, amount: amount });
    } else {
      let sumPaid = 0;
      document.querySelectorAll('.multi-payer-input').forEach((input) => {
        const pAmt = parseFloat(input.value) || 0;
        if (pAmt > 0) {
          payments.push({ userId: input.getAttribute('data-user-id'), amount: pAmt });
          sumPaid += pAmt;
        }
      });
      if (Math.abs(sumPaid - amount) > 0.02) {
        throw new Error(`Total payments (₹${sumPaid.toFixed(2)}) must equal expense amount (₹${amount.toFixed(2)})`);
      }
    }

    // Build Splits Array
    const splits = [];
    if (splitMethod === 'equal') {
      const checkedBoxes = Array.from(document.querySelectorAll('.split-equal-check:checked'));
      if (checkedBoxes.length === 0) throw new Error('Select at least one member to split with');

      const equalShare = amount / checkedBoxes.length;
      checkedBoxes.forEach((cb) => {
        splits.push({
          userId: cb.getAttribute('data-user-id'),
          amount: equalShare,
        });
      });
    } else if (splitMethod === 'percentage') {
      let sumPct = 0;
      document.querySelectorAll('.split-percent-input').forEach((input) => {
        const pct = parseFloat(input.value) || 0;
        if (pct > 0) {
          splits.push({
            userId: input.getAttribute('data-user-id'),
            amount: (amount * pct) / 100,
            percentage: pct,
          });
          sumPct += pct;
        }
      });
      if (Math.abs(sumPct - 100) > 0.1) {
        throw new Error(`Total percentages (${sumPct.toFixed(1)}%) must equal exactly 100%`);
      }
    } else if (splitMethod === 'exact') {
      let sumExact = 0;
      document.querySelectorAll('.split-exact-input').forEach((input) => {
        const sAmt = parseFloat(input.value) || 0;
        if (sAmt > 0) {
          splits.push({
            userId: input.getAttribute('data-user-id'),
            amount: sAmt,
          });
          sumExact += sAmt;
        }
      });
      if (Math.abs(sumExact - amount) > 0.05) {
        throw new Error(`Total split amounts (₹${sumExact.toFixed(2)}) must equal expense amount (₹${amount.toFixed(2)})`);
      }
    }

    const payload = {
      title,
      amount,
      category,
      date,
      payments,
      splits,
      splitMethod,
    };

    const res = await API.post(`/groups/${Groups.currentGroup._id}/expenses`, payload);
    showToast(`Expense "${res.data.title}" added!`, 'success');
    document.getElementById('addExpenseModal').classList.remove('active');
    await Dashboard.refreshGroupData(Groups.currentGroup._id);
  },

  async openDetailsModal(expenseId) {
    try {
      const res = await API.get(`/expenses/${expenseId}`);
      const exp = res.data;
      this.selectedExpense = exp;

      const modal = document.getElementById('expenseDetailsModal');
      const titleEl = document.getElementById('expDetailTitle');
      const catEl = document.getElementById('expDetailCategory');
      const dateEl = document.getElementById('expDetailDate');
      const totalEl = document.getElementById('expDetailTotal');
      const shareBox = document.getElementById('expDetailUserShareBox');
      const paymentsList = document.getElementById('expDetailPaymentsList');
      const splitsList = document.getElementById('expDetailSplitsList');

      const icon = this.categoryIcons[exp.category] || '📦';
      titleEl.textContent = `${icon} ${exp.title}`;
      catEl.textContent = exp.category;
      dateEl.textContent = new Date(exp.date).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
      totalEl.textContent = `₹${exp.amount.toFixed(2)}`;

      // User Share sentence logic
      const currentUser = Auth.getUser();
      const mySplit = exp.splits.find((s) => s.userId?._id === currentUser?._id);
      const myPayment = exp.payments.find((p) => p.userId?._id === currentUser?._id);

      const myShare = mySplit ? mySplit.amount : 0;
      const myPaid = myPayment ? myPayment.amount : 0;
      const diff = myPaid - myShare;

      let shareHtml = `
        <div style="font-size: 0.9375rem; font-weight: 600; margin-bottom: 0.25rem;">Your Share Summary:</div>
        <div style="font-size: 0.875rem; color: var(--text-muted);">
          Your share: <strong>₹${myShare.toFixed(2)}</strong> • You paid: <strong>₹${myPaid.toFixed(2)}</strong>
        </div>
      `;

      if (diff > 0.01) {
        shareHtml += `<div style="font-size: 0.875rem; font-weight: 700; color: var(--success); margin-top: 0.375rem;">Therefore: You are owed ₹${diff.toFixed(2)} for this expense.</div>`;
      } else if (diff < -0.01) {
        shareHtml += `<div style="font-size: 0.875rem; font-weight: 700; color: var(--danger); margin-top: 0.375rem;">Therefore: You owe ₹${Math.abs(diff).toFixed(2)} for this expense.</div>`;
      } else {
        shareHtml += `<div style="font-size: 0.875rem; font-weight: 700; color: var(--primary); margin-top: 0.375rem;">Therefore: Your share is completely balanced.</div>`;
      }
      shareBox.innerHTML = shareHtml;

      // Paid By List
      paymentsList.innerHTML = exp.payments
        .map(
          (p) => `
          <div style="display: flex; justify-content: space-between; font-size: 0.9375rem; padding: 0.25rem 0;">
            <span>${p.userId?.name || 'Member'}${p.userId?._id === currentUser?._id ? ' (You)' : ''}</span>
            <strong style="color: var(--text-main);">₹${p.amount.toFixed(2)}</strong>
          </div>
        `
        )
        .join('');

      // Splits List
      splitsList.innerHTML = exp.splits
        .map(
          (s) => `
          <div style="display: flex; justify-content: space-between; font-size: 0.9375rem; padding: 0.25rem 0;">
            <span>${s.userId?.name || 'Member'}${s.userId?._id === currentUser?._id ? ' (You)' : ''}${s.percentage ? ` (${s.percentage}%)` : ''}</span>
            <strong style="color: var(--text-main);">₹${s.amount.toFixed(2)}</strong>
          </div>
        `
        )
        .join('');

      modal.classList.add('active');
    } catch (error) {
      showToast(error.message || 'Failed to open expense details', 'error');
    }
  },

  async deleteExpense() {
    if (!this.selectedExpense) return;
    if (!confirm(`Are you sure you want to delete "${this.selectedExpense.title}"?`)) return;

    try {
      await API.delete(`/expenses/${this.selectedExpense._id}`);
      showToast('Expense deleted successfully', 'success');
      document.getElementById('expenseDetailsModal').classList.remove('active');
      await Dashboard.refreshGroupData(Groups.currentGroup._id);
    } catch (error) {
      showToast(error.message || 'Failed to delete expense', 'error');
    }
  },

  initListeners() {
    const openExpenseBtn = document.getElementById('openAddExpenseBtn');
    const inlineExpenseBtn = document.getElementById('addExpenseInlineBtn');

    const openModal = () => {
      if (!Groups.currentGroup) {
        showToast('Please select or create a group first', 'error');
        return;
      }
      this.initAddExpenseModal();
    };

    if (openExpenseBtn) openExpenseBtn.addEventListener('click', openModal);
    if (inlineExpenseBtn) inlineExpenseBtn.addEventListener('click', openModal);

    const expenseForm = document.getElementById('addExpenseForm');
    if (expenseForm) {
      expenseForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('submitAddExpenseBtn');
        const alertBox = document.getElementById('addExpenseAlert');

        try {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Saving...';
          alertBox.className = 'alert-box';
          await this.handleSaveExpense();
        } catch (err) {
          alertBox.textContent = err.message || 'Failed to save expense';
          alertBox.className = 'alert-box error active';
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Save Expense';
        }
      });
    }

    const deleteBtn = document.getElementById('deleteExpenseBtn');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => this.deleteExpense());
    }
  },
};
