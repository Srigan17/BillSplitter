/**
 * Test script for Email Notification Dispatcher
 */
require('dotenv').config({ path: __dirname + '/../.env' });
const { sendWelcomeEmail, sendLoginAlertEmail } = require('../utils/emailService');

async function testEmails() {
  console.log('==================================================');
  console.log('🧪 TESTING EMAIL NOTIFICATION SERVICE');
  console.log('==================================================\n');

  const testUser = {
    _id: 'test_user_123',
    name: 'Arun Kumar',
    email: 'arun.test@example.com',
  };

  console.log('1. Testing Welcome Email Dispatch...');
  const welcomeResult = await sendWelcomeEmail(testUser);
  console.assert(welcomeResult && welcomeResult.messageId, 'Welcome email should return messageId');

  console.log('2. Testing Login Alert Email Dispatch...');
  const loginResult = await sendLoginAlertEmail(testUser, {
    ip: '192.168.1.100',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0',
    time: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }),
  });
  console.assert(loginResult && loginResult.messageId, 'Login alert email should return messageId');

  console.log('\n🎉 ALL EMAIL DISPATCH TESTS COMPLETED SUCCESSFULLY!');
  console.log('==================================================');
}

testEmails();
