/**
 * Test Scenario Runner for Bill Splitter Settlement Logic & Calculations
 * Validates:
 * Scenario 1: Arun (₹900 Food), Rahul (₹3000 Stay), Priya (₹600 Transport) -> Equal 3-way split
 * Scenario 2: Hotel (₹3000) -> Arun paid ₹2000, Rahul paid ₹1000, 3-way split -> Priya pays Arun ₹1000
 * Scenario 3: Settlement record and balance reconciliation
 */

const { calculateGroupFinances, calculateOptimizedSettlements } = require('../utils/settlementCalculator');

function runTests() {
  console.log('==================================================');
  console.log('🧪 RUNNING BILL SPLITTER LOGIC & SCENARIO TESTS');
  console.log('==================================================\n');

  // Define Mock Users
  const arun = { _id: 'user_arun', name: 'Arun', email: 'arun@example.com' };
  const rahul = { _id: 'user_rahul', name: 'Rahul', email: 'rahul@example.com' };
  const priya = { _id: 'user_priya', name: 'Priya', email: 'priya@example.com' };
  const members = [arun, rahul, priya];

  // --- SCENARIO 1 TEST ---
  console.log('▶ TEST 1: SCENARIO 1 (Equal splits with different single payers)');
  const expenses1 = [
    {
      _id: 'exp1',
      title: 'Dinner',
      amount: 900,
      category: 'Food',
      date: new Date(),
      payments: [{ userId: arun._id, amount: 900 }],
      splits: [
        { userId: arun._id, amount: 300 },
        { userId: rahul._id, amount: 300 },
        { userId: priya._id, amount: 300 },
      ],
      splitMethod: 'equal',
    },
    {
      _id: 'exp2',
      title: 'Hotel',
      amount: 3000,
      category: 'Stay',
      date: new Date(),
      payments: [{ userId: rahul._id, amount: 3000 }],
      splits: [
        { userId: arun._id, amount: 1000 },
        { userId: rahul._id, amount: 1000 },
        { userId: priya._id, amount: 1000 },
      ],
      splitMethod: 'equal',
    },
    {
      _id: 'exp3',
      title: 'Taxi',
      amount: 600,
      category: 'Transport',
      date: new Date(),
      payments: [{ userId: priya._id, amount: 600 }],
      splits: [
        { userId: arun._id, amount: 200 },
        { userId: rahul._id, amount: 200 },
        { userId: priya._id, amount: 200 },
      ],
      splitMethod: 'equal',
    },
  ];

  const res1 = calculateGroupFinances(members, expenses1, [], arun._id);

  console.log('Total Group Spending:', res1.totalGroupSpending, '(Expected: 4500)');
  console.assert(res1.totalGroupSpending === 4500, 'Total group spending should be 4500');

  const arunSummary = res1.members.find((m) => m.id === arun._id);
  const rahulSummary = res1.members.find((m) => m.id === rahul._id);
  const priyaSummary = res1.members.find((m) => m.id === priya._id);

  console.log('Arun: Paid =', arunSummary.paid, ', Share =', arunSummary.owed, ', Balance =', arunSummary.netBalance, '(Expected: -600)');
  console.log('Rahul: Paid =', rahulSummary.paid, ', Share =', rahulSummary.owed, ', Balance =', rahulSummary.netBalance, '(Expected: +1500)');
  console.log('Priya: Paid =', priyaSummary.paid, ', Share =', priyaSummary.owed, ', Balance =', priyaSummary.netBalance, '(Expected: -900)');

  console.assert(arunSummary.netBalance === -600, 'Arun balance must be -600');
  console.assert(rahulSummary.netBalance === 1500, 'Rahul balance must be +1500');
  console.assert(priyaSummary.netBalance === -900, 'Priya balance must be -900');

  console.log('Optimized Settlements:', res1.optimizedSettlements);
  console.assert(res1.optimizedSettlements.length === 2, 'Should have exactly 2 optimized transactions');

  // Verify settlements match requirements: Priya -> Rahul 900 and Arun -> Rahul 600
  const priyaToRahul = res1.optimizedSettlements.find((s) => s.fromUser === priya._id && s.toUser === rahul._id);
  const arunToRahul = res1.optimizedSettlements.find((s) => s.fromUser === arun._id && s.toUser === rahul._id);

  console.assert(priyaToRahul && priyaToRahul.amount === 900, 'Priya must pay Rahul 900');
  console.assert(arunToRahul && arunToRahul.amount === 600, 'Arun must pay Rahul 600');

  console.log('✅ Scenario 1 Passed Successfully!\n');

  // --- SCENARIO 2 TEST ---
  console.log('▶ TEST 2: SCENARIO 2 (Multi-payer expense)');
  const expenses2 = [
    {
      _id: 'exp_hotel_multi',
      title: 'Hotel',
      amount: 3000,
      category: 'Stay',
      date: new Date(),
      payments: [
        { userId: arun._id, amount: 2000 },
        { userId: rahul._id, amount: 1000 },
      ],
      splits: [
        { userId: arun._id, amount: 1000 },
        { userId: rahul._id, amount: 1000 },
        { userId: priya._id, amount: 1000 },
      ],
      splitMethod: 'equal',
    },
  ];

  const res2 = calculateGroupFinances(members, expenses2, [], priya._id);

  const arunS2 = res2.members.find((m) => m.id === arun._id);
  const rahulS2 = res2.members.find((m) => m.id === rahul._id);
  const priyaS2 = res2.members.find((m) => m.id === priya._id);

  console.log('Arun Balance:', arunS2.netBalance, '(Expected: +1000)');
  console.log('Rahul Balance:', rahulS2.netBalance, '(Expected: 0)');
  console.log('Priya Balance:', priyaS2.netBalance, '(Expected: -1000)');

  console.assert(arunS2.netBalance === 1000, 'Arun balance must be +1000');
  console.assert(rahulS2.netBalance === 0, 'Rahul balance must be 0');
  console.assert(priyaS2.netBalance === -1000, 'Priya balance must be -1000');

  console.log('Optimized Settlements:', res2.optimizedSettlements);
  console.assert(res2.optimizedSettlements.length === 1, 'Should have exactly 1 transaction');
  console.assert(
    res2.optimizedSettlements[0].fromUser === priya._id &&
    res2.optimizedSettlements[0].toUser === arun._id &&
    res2.optimizedSettlements[0].amount === 1000,
    'Priya must pay Arun 1000'
  );

  console.log('✅ Scenario 2 Passed Successfully!\n');

  // --- SCENARIO 3 TEST ---
  console.log('▶ TEST 3: SCENARIO 3 (Settlement Reconciliation)');
  // Add a settled record where Priya pays Arun 1000 for scenario 2
  const settlements = [
    {
      _id: 'set1',
      fromUser: priya._id,
      toUser: arun._id,
      amount: 1000,
      status: 'settled',
      settledAt: new Date(),
    },
  ];

  const res3 = calculateGroupFinances(members, expenses2, settlements, priya._id);

  const arunS3 = res3.members.find((m) => m.id === arun._id);
  const priyaS3 = res3.members.find((m) => m.id === priya._id);

  console.log('Post-Settlement Arun Net Balance:', arunS3.netBalance, '(Expected: 0)');
  console.log('Post-Settlement Priya Net Balance:', priyaS3.netBalance, '(Expected: 0)');
  console.log('Post-Settlement Remaining Transactions:', res3.optimizedSettlements.length, '(Expected: 0)');

  console.assert(arunS3.netBalance === 0, 'Arun balance after settlement must be 0');
  console.assert(priyaS3.netBalance === 0, 'Priya balance after settlement must be 0');
  console.assert(res3.optimizedSettlements.length === 0, 'No pending settlements after full payment');

  console.log('✅ Scenario 3 Passed Successfully!\n');

  console.log('🎉 ALL SETTLEMENT & BUSINESS LOGIC TESTS PASSED!');
  console.log('==================================================');
}

runTests();
