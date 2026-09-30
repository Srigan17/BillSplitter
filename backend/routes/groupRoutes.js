const express = require('express');
const router = express.Router();
const {
  getGroups,
  createGroup,
  getGroupById,
  addMember,
  removeMember,
} = require('../controllers/groupController');
const {
  getGroupExpenses,
  createExpense,
} = require('../controllers/expenseController');
const {
  getGroupBalances,
  getGroupSettlements,
  recordSettlement,
} = require('../controllers/settlementController');
const { protect } = require('../middleware/authMiddleware');

router.use(protect);

router.route('/')
  .get(getGroups)
  .post(createGroup);

router.route('/:id')
  .get(getGroupById);

router.route('/:id/members')
  .post(addMember);

router.route('/:id/members/:userId')
  .delete(removeMember);

router.route('/:id/expenses')
  .get(getGroupExpenses)
  .post(createExpense);

router.route('/:id/balances')
  .get(getGroupBalances);

router.route('/:id/settlements')
  .get(getGroupSettlements)
  .post(recordSettlement);

module.exports = router;
