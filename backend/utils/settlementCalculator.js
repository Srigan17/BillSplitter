/**
 * Settlement and Balance Calculator
 * Handles:
 * 1. Net balance calculations for all members.
 * 2. Expense-level debt breakdown (traceability: why user owes whom for which expenses).
 * 3. Minimal transaction settlement algorithm (Greedy Creditor-Debtor Matching).
 * 4. Category-wise spending aggregations.
 */

const round2 = (num) => Math.round((num + Number.EPSILON) * 100) / 100;

/**
 * Calculate member balances, spending, categories, debt breakdowns, and optimized settlements.
 * @param {Array} members - Array of User objects / IDs
 * @param {Array} expenses - Array of Expense objects
 * @param {Array} settlements - Array of Settlement objects
 * @param {String} currentUserId - (Optional) User ID for tailored summaries
 */
function calculateGroupFinances(members, expenses, settlements = [], currentUserId = null) {
  // Member map for quick lookup
  const memberMap = {};
  members.forEach((m) => {
    const id = (m._id || m).toString();
    memberMap[id] = {
      id,
      name: m.name || 'Unknown',
      email: m.email || '',
      paid: 0,
      owed: 0,
      settledPaid: 0,
      settledReceived: 0,
      netBalance: 0,
    };
  });

  // Category totals
  const groupCategorySpending = {
    Food: 0,
    Travel: 0,
    Transport: 0,
    Stay: 0,
    Entertainment: 0,
    Shopping: 0,
    Other: 0,
  };

  const userCategorySpending = {};
  Object.keys(groupCategorySpending).forEach((cat) => {
    userCategorySpending[cat] = 0;
  });

  // Track raw pairwise debts from expenses: pairwiseDebts[debtorId][creditorId] = { total: 0, expenses: [] }
  const pairwiseDebts = {};
  Object.keys(memberMap).forEach((dId) => {
    pairwiseDebts[dId] = {};
    Object.keys(memberMap).forEach((cId) => {
      if (dId !== cId) {
        pairwiseDebts[dId][cId] = {
          fromUser: dId,
          fromUserName: memberMap[dId].name,
          toUser: cId,
          toUserName: memberMap[cId].name,
          totalAmount: 0,
          expenses: [],
        };
      }
    });
  });

  // 1. Process Expenses
  let totalGroupSpending = 0;

  expenses.forEach((expense) => {
    const expAmount = expense.amount || 0;
    const cat = expense.category || 'Other';
    if (groupCategorySpending[cat] !== undefined) {
      groupCategorySpending[cat] = round2(groupCategorySpending[cat] + expAmount);
    } else {
      groupCategorySpending['Other'] = round2(groupCategorySpending['Other'] + expAmount);
    }
    totalGroupSpending = round2(totalGroupSpending + expAmount);

    // Payments (Who actually spent money)
    expense.payments.forEach((p) => {
      const payerId = (p.userId._id || p.userId).toString();
      const pAmt = p.amount || 0;
      if (memberMap[payerId]) {
        memberMap[payerId].paid = round2(memberMap[payerId].paid + pAmt);

        if (currentUserId && payerId === currentUserId.toString()) {
          const userCat = expense.category || 'Other';
          if (userCategorySpending[userCat] !== undefined) {
            userCategorySpending[userCat] = round2(userCategorySpending[userCat] + pAmt);
          } else {
            userCategorySpending['Other'] = round2(userCategorySpending['Other'] + pAmt);
          }
        }
      }
    });

    // Splits (Who owes how much fair share)
    expense.splits.forEach((s) => {
      const splitId = (s.userId._id || s.userId).toString();
      const sAmt = s.amount || 0;
      if (memberMap[splitId]) {
        memberMap[splitId].owed = round2(memberMap[splitId].owed + sAmt);
      }
    });

    // Calculate Pairwise Debt Breakdown for this expense
    // If payer P paid Pi of total E, and split user S owes Sj:
    // S owes P an amount = Sj * (Pi / E)
    if (expAmount > 0) {
      expense.splits.forEach((s) => {
        const debtorId = (s.userId._id || s.userId).toString();
        const splitShare = s.amount || 0;

        if (splitShare > 0) {
          expense.payments.forEach((p) => {
            const creditorId = (p.userId._id || p.userId).toString();
            const payerPaid = p.amount || 0;

            if (debtorId !== creditorId && payerPaid > 0) {
              const portionOwed = round2(splitShare * (payerPaid / expAmount));
              if (portionOwed > 0.001) {
                if (pairwiseDebts[debtorId] && pairwiseDebts[debtorId][creditorId]) {
                  const pair = pairwiseDebts[debtorId][creditorId];
                  pair.totalAmount = round2(pair.totalAmount + portionOwed);
                  pair.expenses.push({
                    expenseId: expense._id,
                    title: expense.title,
                    category: expense.category,
                    date: expense.date,
                    expenseTotal: expAmount,
                    payerPaid: payerPaid,
                    userShareTotal: splitShare,
                    amountOwed: portionOwed,
                  });
                }
              }
            }
          });
        }
      });
    }
  });

  // 2. Process Settled Settlements
  settlements.forEach((st) => {
    if (st.status === 'settled') {
      const fromId = (st.fromUser._id || st.fromUser).toString();
      const toId = (st.toUser._id || st.toUser).toString();
      const stAmt = st.amount || 0;

      if (memberMap[fromId]) {
        memberMap[fromId].settledPaid = round2(memberMap[fromId].settledPaid + stAmt);
      }
      if (memberMap[toId]) {
        memberMap[toId].settledReceived = round2(memberMap[toId].settledReceived + stAmt);
      }
    }
  });

  // 3. Compute Net Balance for each member
  // Net Balance = (Total Paid - Total Owed) + (Settled Paid - Settled Received)
  Object.values(memberMap).forEach((m) => {
    m.netBalance = round2(m.paid - m.owed + m.settledPaid - m.settledReceived);
  });

  // 4. Optimized Settlement Algorithm (Minimizing transactions)
  const optimizedSettlements = calculateOptimizedSettlements(memberMap);

  // 5. Tailored Debt Summaries for Logged In User
  let youNeedToPay = [];
  let youShouldReceive = [];

  if (currentUserId) {
    const cId = currentUserId.toString();

    // Debts you owe to other members
    if (pairwiseDebts[cId]) {
      Object.keys(pairwiseDebts[cId]).forEach((targetId) => {
        const debt = pairwiseDebts[cId][targetId];
        if (debt.totalAmount > 0.01) {
          youNeedToPay.push({
            toUser: targetId,
            toUserName: memberMap[targetId]?.name || 'Member',
            amount: debt.totalAmount,
            expenses: debt.expenses,
          });
        }
      });
    }

    // Debts other members owe you
    Object.keys(pairwiseDebts).forEach((otherId) => {
      if (otherId !== cId && pairwiseDebts[otherId][cId]) {
        const debt = pairwiseDebts[otherId][cId];
        if (debt.totalAmount > 0.01) {
          youShouldReceive.push({
            fromUser: otherId,
            fromUserName: memberMap[otherId]?.name || 'Member',
            amount: debt.totalAmount,
            expenses: debt.expenses,
          });
        }
      }
    });
  }

  return {
    members: Object.values(memberMap),
    totalGroupSpending,
    groupCategorySpending,
    userCategorySpending,
    optimizedSettlements,
    pairwiseDebts,
    youNeedToPay,
    youShouldReceive,
  };
}

/**
 * Greedy Creditor-Debtor matching to find minimum settlement transactions
 */
function calculateOptimizedSettlements(memberMap) {
  const creditors = [];
  const debtors = [];

  Object.values(memberMap).forEach((m) => {
    const bal = round2(m.netBalance);
    if (bal > 0.01) {
      creditors.push({
        userId: m.id,
        name: m.name,
        balance: bal,
      });
    } else if (bal < -0.01) {
      debtors.push({
        userId: m.id,
        name: m.name,
        balance: Math.abs(bal),
      });
    }
  });

  const settlements = [];

  while (creditors.length > 0 && debtors.length > 0) {
    // Sort descending by remaining balance
    creditors.sort((a, b) => b.balance - a.balance);
    debtors.sort((a, b) => b.balance - a.balance);

    const creditor = creditors[0];
    const debtor = debtors[0];

    const amount = round2(Math.min(creditor.balance, debtor.balance));

    if (amount >= 0.01) {
      settlements.push({
        fromUser: debtor.userId,
        fromUserName: debtor.name,
        toUser: creditor.userId,
        toUserName: creditor.name,
        amount: amount,
      });
    }

    creditor.balance = round2(creditor.balance - amount);
    debtor.balance = round2(debtor.balance - amount);

    if (creditor.balance < 0.01) {
      creditors.shift();
    }
    if (debtor.balance < 0.01) {
      debtors.shift();
    }
  }

  return settlements;
}

module.exports = {
  calculateGroupFinances,
  calculateOptimizedSettlements,
  round2,
};
