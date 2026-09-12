const Expense = require('../models/Expense');
const Group = require('../models/Group');
const { round2 } = require('../utils/settlementCalculator');

const VALID_CATEGORIES = ['Food', 'Travel', 'Transport', 'Stay', 'Entertainment', 'Shopping', 'Other'];

// Helper to validate payments and splits
const validateExpensePayload = (group, payload) => {
  const { title, amount, category, payments, splits, splitMethod } = payload;

  if (!title || !title.trim()) {
    return 'Expense title is required';
  }

  const numAmount = Number(amount);
  if (isNaN(numAmount) || numAmount <= 0) {
    return 'Expense amount must be a positive number greater than zero';
  }

  if (category && !VALID_CATEGORIES.includes(category)) {
    return `Invalid category. Must be one of: ${VALID_CATEGORIES.join(', ')}`;
  }

  if (!Array.isArray(payments) || payments.length === 0) {
    return 'At least one payment is required';
  }

  if (!Array.isArray(splits) || splits.length === 0) {
    return 'At least one split participant is required';
  }

  const memberIdSet = new Set(group.members.map((m) => m.toString()));

  // Validate payments
  let totalPayments = 0;
  for (const p of payments) {
    if (!p.userId || !memberIdSet.has(p.userId.toString())) {
      return 'All payment users must be valid registered members of the group';
    }
    const pAmt = Number(p.amount);
    if (isNaN(pAmt) || pAmt <= 0) {
      return 'Each payment amount must be greater than zero';
    }
    totalPayments = round2(totalPayments + pAmt);
  }

  if (Math.abs(totalPayments - numAmount) > 0.02) {
    return `Total payments (₹${totalPayments}) must equal the expense total (₹${numAmount})`;
  }

  // Validate splits
  let totalSplits = 0;
  let totalPercentage = 0;

  for (const s of splits) {
    if (!s.userId || !memberIdSet.has(s.userId.toString())) {
      return 'All split participants must be valid registered members of the group';
    }
    const sAmt = Number(s.amount);
    if (isNaN(sAmt) || sAmt < 0) {
      return 'Split amounts cannot be negative';
    }
    totalSplits = round2(totalSplits + sAmt);

    if (splitMethod === 'percentage') {
      const sPct = Number(s.percentage);
      if (isNaN(sPct) || sPct < 0) {
        return 'Split percentage cannot be negative';
      }
      totalPercentage = round2(totalPercentage + sPct);
    }
  }

  if (splitMethod === 'percentage') {
    if (Math.abs(totalPercentage - 100) > 0.1) {
      return `Total split percentage (${totalPercentage}%) must equal exactly 100%`;
    }
  }

  if (Math.abs(totalSplits - numAmount) > 0.05) {
    return `Total split shares (₹${totalSplits}) must equal the expense total (₹${numAmount})`;
  }

  return null; // Valid
};

// @desc    Get all expenses for a group
// @route   GET /api/groups/:id/expenses
// @access  Private
const getGroupExpenses = async (req, res) => {
  try {
    const groupId = req.params.id;

    const group = await Group.findById(groupId);
    if (!group) {
      return res.status(404).json({
        success: false,
        message: 'Group not found',
      });
    }

    const isMember = group.members.some(
      (mId) => mId.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to view expenses in this group',
      });
    }

    const expenses = await Expense.find({ groupId })
      .populate('createdBy', 'name email')
      .populate('payments.userId', 'name email')
      .populate('splits.userId', 'name email')
      .sort({ date: -1, createdAt: -1 });

    return res.status(200).json({
      success: true,
      data: expenses,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error fetching group expenses',
    });
  }
};

// @desc    Create a new expense in a group
// @route   POST /api/groups/:id/expenses
// @access  Private
const createExpense = async (req, res) => {
  try {
    const groupId = req.params.id;

    const group = await Group.findById(groupId);
    if (!group) {
      return res.status(404).json({
        success: false,
        message: 'Group not found',
      });
    }

    const isMember = group.members.some(
      (mId) => mId.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to add expenses to this group',
      });
    }

    const validationError = validateExpensePayload(group, req.body);
    if (validationError) {
      return res.status(400).json({
        success: false,
        message: validationError,
      });
    }

    const { title, amount, category, date, payments, splits, splitMethod } = req.body;

    const expense = await Expense.create({
      groupId,
      title: title.trim(),
      amount: round2(Number(amount)),
      category: category || 'Other',
      date: date ? new Date(date) : new Date(),
      payments: payments.map((p) => ({
        userId: p.userId,
        amount: round2(Number(p.amount)),
      })),
      splits: splits.map((s) => ({
        userId: s.userId,
        amount: round2(Number(s.amount)),
        percentage: s.percentage ? Number(s.percentage) : null,
      })),
      splitMethod: splitMethod || 'equal',
      createdBy: req.user._id,
    });

    const populatedExpense = await Expense.findById(expense._id)
      .populate('createdBy', 'name email')
      .populate('payments.userId', 'name email')
      .populate('splits.userId', 'name email');

    return res.status(201).json({
      success: true,
      data: populatedExpense,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error creating expense',
    });
  }
};

// @desc    Get expense details by ID
// @route   GET /api/expenses/:id
// @access  Private
const getExpenseById = async (req, res) => {
  try {
    const expense = await Expense.findById(req.params.id)
      .populate('createdBy', 'name email')
      .populate('payments.userId', 'name email')
      .populate('splits.userId', 'name email');

    if (!expense) {
      return res.status(404).json({
        success: false,
        message: 'Expense not found',
      });
    }

    const group = await Group.findById(expense.groupId);
    const isMember = group && group.members.some(
      (mId) => mId.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to view this expense',
      });
    }

    return res.status(200).json({
      success: true,
      data: expense,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error fetching expense',
    });
  }
};

// @desc    Update an expense
// @route   PUT /api/expenses/:id
// @access  Private
const updateExpense = async (req, res) => {
  try {
    const expense = await Expense.findById(req.params.id);
    if (!expense) {
      return res.status(404).json({
        success: false,
        message: 'Expense not found',
      });
    }

    const group = await Group.findById(expense.groupId);
    const isMember = group && group.members.some(
      (mId) => mId.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to update expenses in this group',
      });
    }

    const validationError = validateExpensePayload(group, req.body);
    if (validationError) {
      return res.status(400).json({
        success: false,
        message: validationError,
      });
    }

    const { title, amount, category, date, payments, splits, splitMethod } = req.body;

    expense.title = title.trim();
    expense.amount = round2(Number(amount));
    expense.category = category || 'Other';
    expense.date = date ? new Date(date) : expense.date;
    expense.payments = payments.map((p) => ({
      userId: p.userId,
      amount: round2(Number(p.amount)),
    }));
    expense.splits = splits.map((s) => ({
      userId: s.userId,
      amount: round2(Number(s.amount)),
      percentage: s.percentage ? Number(s.percentage) : null,
    }));
    expense.splitMethod = splitMethod || expense.splitMethod;

    await expense.save();

    const updatedExpense = await Expense.findById(expense._id)
      .populate('createdBy', 'name email')
      .populate('payments.userId', 'name email')
      .populate('splits.userId', 'name email');

    return res.status(200).json({
      success: true,
      data: updatedExpense,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error updating expense',
    });
  }
};

// @desc    Delete an expense
// @route   DELETE /api/expenses/:id
// @access  Private
const deleteExpense = async (req, res) => {
  try {
    const expense = await Expense.findById(req.params.id);
    if (!expense) {
      return res.status(404).json({
        success: false,
        message: 'Expense not found',
      });
    }

    const group = await Group.findById(expense.groupId);
    const isMember = group && group.members.some(
      (mId) => mId.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to delete expenses in this group',
      });
    }

    await Expense.findByIdAndDelete(req.params.id);

    return res.status(200).json({
      success: true,
      message: 'Expense deleted successfully',
      data: {},
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error deleting expense',
    });
  }
};

module.exports = {
  getGroupExpenses,
  createExpense,
  getExpenseById,
  updateExpense,
  deleteExpense,
};
