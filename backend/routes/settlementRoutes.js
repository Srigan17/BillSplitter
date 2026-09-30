const express = require('express');
const router = express.Router();
const { markSettledById } = require('../controllers/settlementController');
const { protect } = require('../middleware/authMiddleware');

router.use(protect);

router.post('/:id/settle', markSettledById);

module.exports = router;
