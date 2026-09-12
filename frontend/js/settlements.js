/**
 * Settlements Module
 * Handles rendering:
 * 1. "You Need To Pay" with Itemized Debt Breakdown
 * 2. "You Should Receive" with Traceable Sources
 * 3. "Optimized Settlement Plan" with Greedy Minimum Transactions & [ Mark as Settled ]
 * 4. "Settlement History"
 */

const Settlements = {
  currentBalancesData: null,

  renderAll(balancesData) {
    this.currentBalancesData = balancesData;
    this.renderYouNeedToPay(balancesData.youNeedToPay || []);
    this.renderYouShouldReceive(balancesData.youShouldReceive || []);
    this.renderOptimizedPlan(balancesData.optimizedSettlements || []);
    this.renderHistory(balancesData.settlementHistory || []);
  },

  renderYouNeedToPay(debts) {
    const listEl = document.getElementById('youNeedToPayList');
    const badgeEl = document.getElementById('payTotalBadge');
    if (!listEl) return;

    let total = 0;
    debts.forEach((d) => (total += d.amount));

    if (badgeEl) badgeEl.textContent = `₹${total.toFixed(2)} Total`;

    if (debts.length === 0) {
      listEl.innerHTML = `
        <div style="font-size: 0.875rem; color: var(--text-muted); padding: 0.5rem 0;">
          🎉 You don't owe any money to anyone in this group.
        </div>
      `;
      return;
    }

    listEl.innerHTML = debts
      .map(
        (d, index) => `
        <div class="debt-item owe">
          <div class="debt-info">
            <span class="debt-names">You → ${d.toUserName}</span>
            <span style="font-size: 0.8125rem; color: var(--text-muted);">${d.expenses.length} contributing expense(s)</span>
          </div>
          <div class="debt-actions">
            <span class="debt-amount" style="color: var(--danger);">₹${d.amount.toFixed(2)}</span>
            <button class="btn btn-secondary btn-sm" onclick="Settlements.showDebtAuditModal('pay', ${index})">
              View Breakdown
            </button>
          </div>
        </div>
      `
      )
      .join('');
  },

  renderYouShouldReceive(receivables) {
    const listEl = document.getElementById('youShouldReceiveList');
    const badgeEl = document.getElementById('receiveTotalBadge');
    if (!listEl) return;

    let total = 0;
    receivables.forEach((r) => (total += r.amount));

    if (badgeEl) badgeEl.textContent = `₹${total.toFixed(2)} Total`;

    if (receivables.length === 0) {
      listEl.innerHTML = `
        <div style="font-size: 0.875rem; color: var(--text-muted); padding: 0.5rem 0;">
          ℹ️ No one owes you money right now.
        </div>
      `;
      return;
    }

    listEl.innerHTML = receivables
      .map(
        (r, index) => `
        <div class="debt-item receive">
          <div class="debt-info">
            <span class="debt-names">${r.fromUserName} → You</span>
            <span style="font-size: 0.8125rem; color: var(--text-muted);">${r.expenses.length} contributing expense(s)</span>
          </div>
          <div class="debt-actions">
            <span class="debt-amount" style="color: var(--success);">₹${r.amount.toFixed(2)}</span>
            <button class="btn btn-secondary btn-sm" onclick="Settlements.showDebtAuditModal('receive', ${index})">
              View Breakdown
            </button>
          </div>
        </div>
      `
      )
      .join('');
  },

  renderOptimizedPlan(settlements) {
    const listEl = document.getElementById('optimizedSettlementList');
    const badgeEl = document.getElementById('minTransactionsBadge');
    if (!listEl) return;

    if (badgeEl) {
      badgeEl.textContent = `${settlements.length} Transaction${settlements.length === 1 ? '' : 's'}`;
    }

    if (settlements.length === 0) {
      listEl.innerHTML = `
        <div style="font-size: 0.875rem; color: var(--text-muted); padding: 0.5rem 0;">
          ✨ All balances are fully settled! No transactions required.
        </div>
      `;
      return;
    }

    const currentUser = Auth.getUser();

    listEl.innerHTML = settlements
      .map((st) => {
        const isFromMe = st.fromUser === currentUser?._id;
        const isToMe = st.toUser === currentUser?._id;

        const fromLabel = isFromMe ? 'You' : st.fromUserName;
        const toLabel = isToMe ? 'You' : st.toUserName;

        return `
          <div class="debt-item" style="border-left-color: var(--primary);">
            <div class="debt-info">
              <span class="debt-names" style="font-size: 1rem;">${fromLabel} → ${toLabel}</span>
              <span style="font-size: 0.8125rem; color: var(--text-muted);">Direct settlement payment</span>
            </div>
            <div class="debt-actions">
              <span class="debt-amount" style="color: var(--primary);">₹${st.amount.toFixed(2)}</span>
              <button class="btn btn-success btn-sm" onclick="Settlements.handleMarkSettled('${st.fromUser}', '${st.toUser}', ${st.amount}, '${st.fromUserName}', '${st.toUserName}')">
                ✓ Mark as Settled
              </button>
            </div>
          </div>
        `;
      })
      .join('');
  },

  renderHistory(history) {
    const listEl = document.getElementById('settlementHistoryList');
    if (!listEl) return;

    if (history.length === 0) {
      listEl.innerHTML = `
        <div style="font-size: 0.8125rem; color: var(--text-muted); padding: 0.5rem 0;">
          No settlements recorded yet.
        </div>
      `;
      return;
    }

    listEl.innerHTML = history
      .map((h) => {
        const dateStr = new Date(h.settledAt || h.createdAt).toLocaleDateString('en-IN', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
        });

        return `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.625rem 0.75rem; background: var(--bg-card-hover); border-radius: var(--radius-md); font-size: 0.875rem;">
            <div>
              <span style="color: var(--success); font-weight: 700;">✅</span>
              <strong>${h.fromUser?.name || 'Member'}</strong> paid <strong>${h.toUser?.name || 'Member'}</strong>
            </div>
            <div style="text-align: right;">
              <strong style="color: var(--text-main);">₹${h.amount.toFixed(2)}</strong>
              <div style="font-size: 0.75rem; color: var(--text-muted);">${dateStr}</div>
            </div>
          </div>
        `;
      })
      .join('');
  },

  showDebtAuditModal(type, index) {
    if (!this.currentBalancesData) return;

    const modal = document.getElementById('debtAuditModal');
    const titleEl = document.getElementById('debtAuditTitle');
    const subtitleEl = document.getElementById('debtAuditSubtitle');
    const listEl = document.getElementById('debtAuditExpensesList');

    const debt =
      type === 'pay'
        ? this.currentBalancesData.youNeedToPay[index]
        : this.currentBalancesData.youShouldReceive[index];

    if (!debt) return;

    if (type === 'pay') {
      titleEl.textContent = `Why you owe ${debt.toUserName}`;
      subtitleEl.textContent = `Total Owed: ₹${debt.amount.toFixed(2)} from ${debt.expenses.length} expense(s):`;
    } else {
      titleEl.textContent = `Why ${debt.fromUserName} owes you`;
      subtitleEl.textContent = `Total Owed to you: ₹${debt.amount.toFixed(2)} from ${debt.expenses.length} expense(s):`;
    }

    listEl.innerHTML = debt.expenses
      .map((e) => {
        const icon = Expenses.categoryIcons[e.category] || '📦';
        const dateStr = new Date(e.date).toLocaleDateString('en-IN', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
        });

        return `
          <div class="card" style="padding: 0.875rem; background: var(--bg-card-hover); border-radius: var(--radius-md);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.375rem;">
              <div style="font-weight: 700; font-size: 0.9375rem;">
                <span>${icon}</span> ${e.title}
              </div>
              <span style="font-size: 0.8125rem; color: var(--text-muted);">${dateStr}</span>
            </div>
            
            <div style="font-size: 0.8125rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 0.125rem;">
              <div>Expense Total: ₹${e.expenseTotal.toFixed(2)} (${e.category})</div>
              <div>Portion breakdown: (User Share ₹${e.userShareTotal.toFixed(2)} × Payer Paid ₹${e.payerPaid.toFixed(2)} / Total ₹${e.expenseTotal.toFixed(2)})</div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem; padding-top: 0.375rem; border-top: 1px solid var(--border-color);">
              <span style="font-size: 0.8125rem; font-weight: 600;">Portion for this debt:</span>
              <strong style="font-size: 1rem; color: ${type === 'pay' ? 'var(--danger)' : 'var(--success)'};">₹${e.amountOwed.toFixed(2)}</strong>
            </div>
          </div>
        `;
      })
      .join('');

    modal.classList.add('active');
  },

  async handleMarkSettled(fromUserId, toUserId, amount, fromName, toName) {
    if (!Groups.currentGroup) return;

    if (!confirm(`Record that ${fromName} paid ${toName} ₹${amount.toFixed(2)} externally?`)) {
      return;
    }

    try {
      const res = await API.post(`/groups/${Groups.currentGroup._id}/settlements`, {
        fromUser: fromUserId,
        toUser: toUserId,
        amount: amount,
      });

      showToast(res.message || 'Settlement recorded successfully!', 'success');
      await Dashboard.refreshGroupData(Groups.currentGroup._id);
    } catch (error) {
      showToast(error.message || 'Failed to record settlement', 'error');
    }
  },
};
