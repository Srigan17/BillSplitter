const Group = require('../models/Group');
const User = require('../models/User');
const Expense = require('../models/Expense');
const Settlement = require('../models/Settlement');

// @desc    Get all groups for logged-in user
// @route   GET /api/groups
// @access  Private
const getGroups = async (req, res) => {
  try {
    const groups = await Group.find({ members: req.user._id })
      .populate('createdBy', 'name email')
      .populate('members', 'name email')
      .sort({ createdAt: -1 });

    return res.status(200).json({
      success: true,
      data: groups,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error fetching groups',
    });
  }
};

// @desc    Create a new group
// @route   POST /api/groups
// @access  Private
const createGroup = async (req, res) => {
  try {
    const { name } = req.body;

    if (!name || !name.trim()) {
      return res.status(400).json({
        success: false,
        message: 'Group name is required',
      });
    }

    const group = await Group.create({
      name: name.trim(),
      createdBy: req.user._id,
      members: [req.user._id],
    });

    const populatedGroup = await Group.findById(group._id)
      .populate('createdBy', 'name email')
      .populate('members', 'name email');

    return res.status(201).json({
      success: true,
      data: populatedGroup,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error creating group',
    });
  }
};

// @desc    Get group details by ID
// @route   GET /api/groups/:id
// @access  Private
const getGroupById = async (req, res) => {
  try {
    const group = await Group.findById(req.params.id)
      .populate('createdBy', 'name email')
      .populate('members', 'name email');

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
        message: 'You are not authorized to view this group',
      });
    }

    return res.status(200).json({
      success: true,
      data: group,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error fetching group details',
    });
  }
};

// @desc    Add member to group by email
// @route   POST /api/groups/:id/members
// @access  Private
const addMember = async (req, res) => {
  try {
    const { email } = req.body;

    if (!email || !email.trim()) {
      return res.status(400).json({
        success: false,
        message: 'Member email is required',
      });
    }

    const group = await Group.findById(req.params.id);
    if (!group) {
      return res.status(404).json({
        success: false,
        message: 'Group not found',
      });
    }

    // Check user is already member of group
    const isMember = group.members.some(
      (mId) => mId.toString() === req.user._id.toString()
    );
    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You must be a member of this group to add others',
      });
    }

    // Search user by email
    const userToAdd = await User.findOne({ email: email.toLowerCase().trim() });
    if (!userToAdd) {
      return res.status(404).json({
        success: false,
        message: 'User not found. They must be registered before being added.',
      });
    }

    // Check for duplicate member
    const alreadyInGroup = group.members.some(
      (mId) => mId.toString() === userToAdd._id.toString()
    );
    if (alreadyInGroup) {
      return res.status(400).json({
        success: false,
        message: 'This user is already a member of the group',
      });
    }

    group.members.push(userToAdd._id);
    await group.save();

    const updatedGroup = await Group.findById(group._id)
      .populate('createdBy', 'name email')
      .populate('members', 'name email');

    return res.status(200).json({
      success: true,
      message: `${userToAdd.name} was successfully added to the group`,
      data: updatedGroup,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error adding member',
    });
  }
};

// @desc    Remove member from group
// @route   DELETE /api/groups/:id/members/:userId
// @access  Private
const removeMember = async (req, res) => {
  try {
    const { id: groupId, userId } = req.params;

    const group = await Group.findById(groupId);
    if (!group) {
      return res.status(404).json({
        success: false,
        message: 'Group not found',
      });
    }

    // Only group creator can remove other members, or user can remove themselves
    const isCreator = group.createdBy.toString() === req.user._id.toString();
    const isSelf = userId === req.user._id.toString();

    if (!isCreator && !isSelf) {
      return res.status(403).json({
        success: false,
        message: 'Only the group creator can remove other members',
      });
    }

    // Verify member is in the group
    const memberIndex = group.members.findIndex(
      (mId) => mId.toString() === userId.toString()
    );
    if (memberIndex === -1) {
      return res.status(404).json({
        success: false,
        message: 'User is not a member of this group',
      });
    }

    // Check if user is associated with any existing expenses in the group
    const involvedInExpenses = await Expense.findOne({
      groupId,
      $or: [
        { 'payments.userId': userId },
        { 'splits.userId': userId },
      ],
    });

    if (involvedInExpenses) {
      return res.status(400).json({
        success: false,
        message:
          'Cannot remove member: this user is associated with existing expenses in this group. Delete or reassign those expenses before removing.',
      });
    }

    // Check if involved in pending settlements
    const involvedInSettlements = await Settlement.findOne({
      groupId,
      status: 'pending',
      $or: [{ fromUser: userId }, { toUser: userId }],
    });

    if (involvedInSettlements) {
      return res.status(400).json({
        success: false,
        message:
          'Cannot remove member: this user has pending settlements in this group.',
      });
    }

    group.members.splice(memberIndex, 1);
    await group.save();

    const updatedGroup = await Group.findById(group._id)
      .populate('createdBy', 'name email')
      .populate('members', 'name email');

    return res.status(200).json({
      success: true,
      message: 'Member removed successfully',
      data: updatedGroup,
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error removing member',
    });
  }
};

module.exports = {
  getGroups,
  createGroup,
  getGroupById,
  addMember,
  removeMember,
};
