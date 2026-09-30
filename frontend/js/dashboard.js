/**
 * Dashboard Coordinator Module
 * Orchestrates financial summaries, Chart.js category visualizations, and theme management.
 */

const Dashboard = {
  categoryChartInstance: null,

  async init() {
    if (!Auth.requireAuth()) return;

    Auth.initUserHeader();
    this.initTheme();
    this.initModalClosers();

    // Initialize sub-module listeners
    Groups.initListeners();
    Expenses.initListeners();

    // Load user groups & dashboard
    await Groups.loadGroups();
  },

  async refreshGroupData(groupId) {
    if (!groupId) return;

    try {
      // 1. Fetch Balances & Settlement Metrics
      const res = await API.get(`/groups/${groupId}/balances`);
      const data = res.data;

      // 2. Update Top 4 Metric Cards
      this.renderTopMetrics(data);

      // 3. Render Chart.js Category Breakdown & Lists
      this.renderCategoryBreakdowns(data.groupCategorySpending, data.userCategorySpending);

      // 4. Render Debt Sections & Settlements
      Settlements.renderAll(data);

      // 5. Load Recent Expenses List
      await Expenses.loadExpenses(groupId);
    } catch (error) {
      showToast(error.message || 'Error updating dashboard data', 'error');
    }
  },

  renderTopMetrics(data) {
    const groupTotalEl = document.getElementById('metricGroupTotal');
    const userSpentEl = document.getElementById('metricUserSpent');
    const userShareEl = document.getElementById('metricUserShare');
    const netBalanceEl = document.getElementById('metricNetBalance');
    const netBadgeEl = document.getElementById('metricNetBadge');
    const netCardEl = document.getElementById('netBalanceCard');

    const totalGroup = data.group?.totalExpenses || 0;
    const spent = data.userSummary?.spent || 0;
    const share = data.userSummary?.share || 0;
    const net = data.userSummary?.netBalance || 0;

    if (groupTotalEl) groupTotalEl.textContent = `₹${totalGroup.toFixed(2)}`;
    if (userSpentEl) userSpentEl.textContent = `₹${spent.toFixed(2)}`;
    if (userShareEl) userShareEl.textContent = `₹${share.toFixed(2)}`;

    if (netBalanceEl && netBadgeEl && netCardEl) {
      netBalanceEl.textContent = `₹${Math.abs(net).toFixed(2)}`;

      netCardEl.classList.remove('positive', 'negative');

      if (net > 0.01) {
        netCardEl.classList.add('positive');
        netBadgeEl.className = 'badge-status receive';
        netBadgeEl.textContent = `You will receive ₹${net.toFixed(2)}`;
      } else if (net < -0.01) {
        netCardEl.classList.add('negative');
        netBadgeEl.className = 'badge-status pay';
        netBadgeEl.textContent = `You need to pay ₹${Math.abs(net).toFixed(2)}`;
      } else {
        netBadgeEl.className = 'badge-status settled';
        netBadgeEl.textContent = 'All Settled (₹0.00)';
      }
    }
  },

  renderCategoryBreakdowns(groupCats = {}, userCats = {}) {
    const groupListEl = document.getElementById('groupCategoryList');
    const userListEl = document.getElementById('userCategoryList');

    const categoryColors = {
      Food: '#ef4444',
      Travel: '#3b82f6',
      Transport: '#f59e0b',
      Stay: '#8b5cf6',
      Entertainment: '#ec4899',
      Shopping: '#10b981',
      Other: '#64748b',
    };

    // Render Group Category List
    if (groupListEl) {
      const activeCats = Object.entries(groupCats).filter(([_, val]) => val > 0);
      if (activeCats.length === 0) {
        groupListEl.innerHTML = '<span style="font-size: 0.8125rem; color: var(--text-muted);">No group spending yet.</span>';
      } else {
        groupListEl.innerHTML = activeCats
          .map(([cat, amount]) => {
            const icon = Expenses.categoryIcons[cat] || '📦';
            return `
              <div style="display: flex; justify-content: space-between; font-size: 0.875rem; padding: 0.125rem 0;">
                <span>${icon} ${cat}</span>
                <strong>₹${amount.toFixed(2)}</strong>
              </div>
            `;
          })
          .join('');
      }
    }

    // Render User Personal Category List
    if (userListEl) {
      const activeUserCats = Object.entries(userCats).filter(([_, val]) => val > 0);
      if (activeUserCats.length === 0) {
        userListEl.innerHTML = '<span style="font-size: 0.8125rem; color: var(--text-muted);">You have not paid upfront for any expenses yet.</span>';
      } else {
        userListEl.innerHTML = activeUserCats
          .map(([cat, amount]) => {
            const icon = Expenses.categoryIcons[cat] || '📦';
            return `
              <div style="display: flex; justify-content: space-between; font-size: 0.875rem; padding: 0.125rem 0;">
                <span>${icon} ${cat}</span>
                <strong>₹${amount.toFixed(2)}</strong>
              </div>
            `;
          })
          .join('');
      }
    }

    // Update Chart.js Doughnut
    this.updateCategoryChart(groupCats, categoryColors);
  },

  updateCategoryChart(groupCats, categoryColors) {
    const canvas = document.getElementById('categoryChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const labels = Object.keys(groupCats);
    const data = Object.values(groupCats);
    const backgroundColors = labels.map((cat) => categoryColors[cat] || '#64748b');

    const totalSpending = data.reduce((acc, v) => acc + v, 0);

    if (this.categoryChartInstance) {
      this.categoryChartInstance.destroy();
    }

    if (totalSpending === 0) {
      // Empty placeholder doughnut
      this.categoryChartInstance = new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels: ['No Data'],
          datasets: [
            {
              data: [1],
              backgroundColor: ['#e2e8f0'],
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { enabled: false },
          },
          cutout: '70%',
        },
      });
      return;
    }

    this.categoryChartInstance = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: labels.filter((_, idx) => data[idx] > 0),
        datasets: [
          {
            data: data.filter((val) => val > 0),
            backgroundColor: backgroundColors.filter((_, idx) => data[idx] > 0),
            borderWidth: 2,
            borderColor: document.documentElement.getAttribute('data-theme') === 'dark' ? '#1e293b' : '#ffffff',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 12,
              padding: 12,
              font: { family: 'Inter', size: 11, weight: '500' },
              color: document.documentElement.getAttribute('data-theme') === 'dark' ? '#94a3b8' : '#64748b',
            },
          },
        },
        cutout: '65%',
      },
    });
  },

  initTheme() {
    const themeBtn = document.getElementById('themeToggleBtn');
    const savedTheme = localStorage.getItem('billsplitter_theme') || 'light';

    document.documentElement.setAttribute('data-theme', savedTheme);
    if (themeBtn) {
      themeBtn.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
      themeBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('billsplitter_theme', next);
        themeBtn.textContent = next === 'dark' ? '☀️' : '🌙';

        if (Groups.currentGroup) {
          Dashboard.refreshGroupData(Groups.currentGroup._id);
        }
      });
    }
  },

  initModalClosers() {
    document.querySelectorAll('.close-modal-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.modal-overlay').forEach((modal) => {
          modal.classList.remove('active');
        });
      });
    });

    document.querySelectorAll('.modal-overlay').forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.remove('active');
        }
      });
    });
  },
};

// Initialize Dashboard on DOM load
document.addEventListener('DOMContentLoaded', () => {
  Dashboard.init();
});
