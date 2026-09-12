const mongoose = require('mongoose');

const paymentSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    amount: {
      type: Number,
      required: true,
      min: [0.01, 'Payment amount must be greater than 0'],
    },
  },
  { _id: false }
);

const splitSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    amount: {
      type: Number,
      required: true,
      min: [0, 'Split amount cannot be negative'],
    },
    percentage: {
      type: Number,
      default: null,
    },
  },
  { _id: false }
);

const expenseSchema = new mongoose.Schema(
  {
    groupId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Group',
      required: true,
      index: true,
    },
    title: {
      type: String,
      required: [true, 'Expense title is required'],
      trim: true,
    },
    amount: {
      type: Number,
      required: [true, 'Expense amount is required'],
      min: [0.01, 'Expense amount must be greater than 0'],
    },
    category: {
      type: String,
      required: [true, 'Expense category is required'],
      enum: ['Food', 'Travel', 'Transport', 'Stay', 'Entertainment', 'Shopping', 'Other'],
      default: 'Other',
    },
    date: {
      type: Date,
      default: Date.now,
    },
    payments: {
      type: [paymentSchema],
      required: true,
      validate: [v => v.length > 0, 'At least one payment record is required'],
    },
    splits: {
      type: [splitSchema],
      required: true,
      validate: [v => v.length > 0, 'At least one split record is required'],
    },
    splitMethod: {
      type: String,
      enum: ['equal', 'percentage', 'exact'],
      default: 'equal',
    },
    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    createdAt: {
      type: Date,
      default: Date.now,
    },
  },
  { timestamps: false }
);

module.exports = mongoose.model('Expense', expenseSchema);
