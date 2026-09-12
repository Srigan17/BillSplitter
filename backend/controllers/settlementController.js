const Settlement = require('../models/Settlement');
const Group = require('../models/Group');
const Expense = require('../models/Expense');
const { calculateGroupFinances, round2 } = require('../utils/settlementCalculator');

// @desc    Get group financial balances, optimized settlements, and itemized debt breakdowns
// @route   GET /api/groups/:id/balances
// @access  Private
const getGroupBalances = async (req, res) => {
  try {
    const groupId = req.params.id;

    const group = await Group.findById(groupId).populate('members', 'name email');
    if (!group) {
      return res.status(404).json({
        success: false,
        message: 'Group not found',
      });
    }

    const isMember = group.members.some(
      (m) => m._id.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to view balances for this group',
      });
    }

    const expenses = await Expense.find({ groupId })
      .populate('payments.userId', 'name email')
      .populate('splits.userId', 'name email');

    const settlements = await Settlement.find({ groupId })
      .populate('fromUser', 'name email')
      .populate('toUser', 'name email')
      .sort({ settledAt: -1, createdAt: -1 });

    const calculation = calculateGroupFinances(
      group.members,
      expenses,
      settlements,
      req.user._id
    );

    // Current user's individual financial summary
    const currentUserMember = calculation.members.find(
      (m) => m.id === req.user._id.toString()
    ) || {
      paid: 0,
      owed: 0,
      netBalance: 0,
    };

    return res.status(200).json({
      success: true,
      data: {
        group: {
          _id: group._id,
          name: group.name,
          membersCount: group.members.length,
          totalExpenses: calculation.totalGroupSpending,
        },
        userSummary: {
          spent: currentUserMember.paid, // How much the user actually paid
          share: currentUserMember.owed, // How much the user owes
          netBalance: currentUserMember.netBalance, // Positive = receive, Negative = pay
        },
        members: calculation.members,
        groupCategorySpending: calculation.groupCategorySpending,
        userCategorySpending: calculation.userCategorySpending,
        optimizedSettlements: calculation.optimizedSettlements,
        youNeedToPay: calculation.youNeedToPay,
        youShouldReceive: calculation.youShouldReceive,
        settlementHistory: settlements.filter((s) => s.status === 'settled'),
      },
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error calculating balances',
    });
  }
};

// @desc    Get all settlements for a group
// @route   GET /api/groups/:id/settlements
// @access  Private
const getGroupSettlements = async (req, res) => {
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
        message: 'You are not authorized to view settlements in this group',
      });
    }

    const settlements = await Settlement.find({ groupId })
      .populate('fromUser', 'name email')
      .populate('toUser', 'name email')
      .sort({ createdAt: -1 });

    return res.status(200).json({
      success: true,
      data: settlements,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error fetching settlements',
    });
  }
};

// @desc    Create/Record a settlement transaction as settled
// @route   POST /api/groups/:id/settlements
// @access  Private
const recordSettlement = async (req, res) => {
  try {
    const groupId = req.params.id;
    const { fromUser, toUser, amount } = req.body;

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
        message: 'You are not authorized to record settlements in this group',
      });
    }

    if (!fromUser || !toUser) {
      return res.status(400).json({
        success: false,
        message: 'Both fromUser and toUser are required',
      });
    }

    if (fromUser.toString() === toUser.toString()) {
      return res.status(400).json({
        success: false,
        message: 'Payer and Receiver cannot be the same person',
      });
    }

    const numAmount = round2(Number(amount));
    if (isNaN(numAmount) || numAmount <= 0) {
      return res.status(400).json({
        success: false,
        message: 'Settlement amount must be greater than zero',
      });
    }

    const memberIdSet = new Set(group.members.map((m) => m.toString()));
    if (!memberIdSet.has(fromUser.toString()) || !memberIdSet.has(toUser.toString())) {
      return res.status(400).json({
        success: false,
        message: 'Both parties in the settlement must be members of the group',
      });
    }

    const settlement = await Settlement.create({
      groupId,
      fromUser,
      toUser,
      amount: numAmount,
      status: 'settled',
      settledAt: new Date(),
    });

    const populated = await Settlement.findById(settlement._id)
      .populate('fromUser', 'name email')
      .populate('toUser', 'name email');

    return res.status(201).json({
      success: true,
      message: 'Settlement recorded successfully',
      data: populated,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error recording settlement',
    });
  }
};

// @desc    Mark an existing pending settlement as settled
// @route   POST /api/settlements/:id/settle
// @access  Private
const markSettledById = async (req, res) => {
  try {
    const settlement = await Settlement.findById(req.params.id);
    if (!settlement) {
      return res.status(404).json({
        success: false,
        message: 'Settlement record not found',
      });
    }

    const group = await Group.findById(settlement.groupId);
    const isMember = group && group.members.some(
      (mId) => mId.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to update this settlement',
      });
    }

    settlement.status = 'settled';
    settlement.settledAt = new Date();
    await settlement.save();

    const populated = await Settlement.findById(settlement._id)
      .populate('fromUser', 'name email')
      .populate('toUser', 'name email');

    return res.status(200).json({
      success: true,
      message: 'Settlement marked as settled',
      data: populated,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error updating settlement',
    });
  }
};

module.exports = {
  getGroupBalances,
  getGroupSettlements,
  recordSettlement,
  markSettledById,
};
