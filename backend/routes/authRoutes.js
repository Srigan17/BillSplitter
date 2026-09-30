const express = require('express');
const router = express.Router();
const {
  register,
  login,
  getMe,
  searchUserByEmail,
} = require('../controllers/authController');
const { protect } = require('../middleware/authMiddleware');

router.post('/register', register);
router.post('/login', login);
router.get('/me', protect, getMe);
router.get('/search', protect, searchUserByEmail);

module.exports = router;
