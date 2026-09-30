const jwt = require('jsonwebtoken');
const User = require('../models/User');
const Group = require('../models/Group');

const protect = async (req, res, next) => {
  let token;

  if (
    req.headers.authorization &&
    req.headers.authorization.startsWith('Bearer')
  ) {
    token = req.headers.authorization.split(' ')[1];
  }

  if (!token) {
    return res.status(401).json({
      success: false,
      message: 'Not authorized to access this route, token missing',
    });
  }

  try {
    const decoded = jwt.verify(
      token,
      process.env.JWT_SECRET || 'billsplitter_jwt_secret_key_super_secure_2026'
    );

    const user = await User.findById(decoded.id).select('-password');
    if (!user) {
      return res.status(401).json({
        success: false,
        message: 'User no longer exists',
      });
    }

    req.user = user;
    next();
  } catch (error) {
    return res.status(401).json({
      success: false,
      message: 'Not authorized, token invalid or expired',
    });
  }
};

// Helper middleware to check if req.user is a member of the group specified in req.params.id or req.params.groupId or req.body.groupId
const checkGroupMembership = async (req, res, next) => {
  try {
    const groupId = req.params.id || req.params.groupId || req.body.groupId;
    if (!groupId) {
      return res.status(400).json({
        success: false,
        message: 'Group ID is required',
      });
    }

    const group = await Group.findById(groupId);
    if (!group) {
      return res.status(404).json({
        success: false,
        message: 'Group not found',
      });
    }

    const isMember = group.members.some(
      (memberId) => memberId.toString() === req.user._id.toString()
    );

    if (!isMember) {
      return res.status(403).json({
        success: false,
        message: 'You are not authorized to access this group',
      });
    }

    req.group = group;
    next();
  } catch (error) {
    return res.status(500).json({
      success: false,
      message: error.message || 'Error validating group membership',
    });
  }
};

module.exports = { protect, checkGroupMembership };
