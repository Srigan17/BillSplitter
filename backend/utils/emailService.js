const nodemailer = require('nodemailer');

/**
 * Creates and returns the Nodemailer transporter.
 * If SMTP credentials are provided in .env, it uses them.
 * Otherwise, it creates a test account (Ethereal) or logs to console as fallback.
 */
let transporter = null;

const getTransporter = async () => {
  if (transporter) return transporter;

  const host = process.env.SMTP_HOST || 'smtp.gmail.com';
  const user = process.env.SMTP_USER || 'owelessapp@gmail.com';
  const pass = process.env.SMTP_PASS;

  if (pass) {
    transporter = nodemailer.createTransport({
      host: host,
      port: Number(process.env.SMTP_PORT) || 587,
      secure: process.env.SMTP_SECURE === 'true',
      auth: {
        user: user,
        pass: pass,
      },
    });
    console.log(`📧 SMTP Transporter initialized with host: ${host} for user: ${user}`);
  } else {
    // In development or when SMTP_PASS is not provided, use a fallback transport that logs to console
    console.log('ℹ️ No SMTP_PASS provided in .env. Using fallback mail logger.');
    transporter = {
      sendMail: async (mailOptions) => {
        console.log('\n================== 📧 EMAIL NOTIFICATION DISPATCHED ==================');
        console.log(`To: ${mailOptions.to}`);
        console.log(`From: ${mailOptions.from || process.env.EMAIL_FROM || '"Oweless" <owelessapp@gmail.com>'}`);
        console.log(`Subject: ${mailOptions.subject}`);
        console.log('--------------------------- Content Preview ---------------------------');
        console.log(mailOptions.text || mailOptions.html.replace(/<[^>]*>?/gm, ' ').slice(0, 300) + '...');
        console.log('======================================================================\n');
        return { messageId: 'simulated-' + Date.now(), response: 'Email logged to console' };
      },
    };
  }

  return transporter;
};

/**
 * Send Welcome Email on successful user registration
 * @param {Object} user - { _id, name, email }
 */
const sendWelcomeEmail = async (user) => {
  try {
    const mailer = await getTransporter();
    const fromAddress = process.env.EMAIL_FROM || '"Oweless" <owelessapp@gmail.com>';

    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 0; }
          .container { max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }
          .header { background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); color: #ffffff; padding: 30px 20px; text-align: center; }
          .header h1 { margin: 0; font-size: 24px; font-weight: 700; }
          .header p { margin: 8px 0 0 0; opacity: 0.9; font-size: 14px; }
          .body { padding: 30px 25px; line-height: 1.6; }
          .welcome-box { background: #e0e7ff; border-left: 4px solid #6366f1; padding: 15px; border-radius: 6px; margin: 20px 0; color: #3730a3; }
          .features-list { list-style: none; padding: 0; margin: 20px 0; }
          .features-list li { padding: 8px 0; display: flex; align-items: center; }
          .features-list li span { margin-right: 10px; font-size: 18px; }
          .footer { background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>⚖️ Welcome to Oweless</h1>
            <p>Fair, transparent, and hassle-free expense sharing</p>
          </div>
          <div class="body">
            <h2>Hello, ${user.name}! 👋</h2>
            <p>Your account has been successfully created. You're all set to start tracking shared expenses, finding optimal settlements, and keeping accounts clear with your friends, roommates, and colleagues.</p>
            
            <div class="welcome-box">
              <strong>Registered Email:</strong> ${user.email}<br>
              <strong>Account Created:</strong> ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
            </div>

            <h3>What you can do with Oweless:</h3>
            <ul class="features-list">
              <li><span>👥</span> <strong>Create Groups:</strong> Organize trips, flats, dinners, and events.</li>
              <li><span>💳</span> <strong>Flexible Splitting:</strong> Split equally, by percentages, or exact amounts with single or multiple payers.</li>
              <li><span>⚡</span> <strong>Minimised Settlements:</strong> Let our algorithm reduce debt transfers down to the fewest payments.</li>
              <li><span>🔍</span> <strong>Itemized Audit Trails:</strong> Trace every rupee back to the original bill so there's never any confusion.</li>
            </ul>

            <p style="margin-top: 25px;">Log in to your dashboard anytime to get started!</p>
          </div>
          <div class="footer">
            <p>This is an automated notification from Oweless (owelessapp@gmail.com). Please do not reply directly to this email.</p>
          </div>
        </div>
      </body>
      </html>
    `;

    const mailOptions = {
      from: fromAddress,
      to: user.email,
      subject: `Welcome to Oweless, ${user.name}! ⚖️`,
      text: `Hello ${user.name},\n\nYour Oweless account has been successfully created with email ${user.email}.\n\nWelcome aboard!\nOweless Team\nowelessapp@gmail.com`,
      html: htmlContent,
    };

    const info = await mailer.sendMail(mailOptions);
    console.log(`✅ Welcome email dispatched to ${user.email} (Message ID: ${info.messageId})`);
    return info;
  } catch (error) {
    console.error(`❌ Failed to send welcome email to ${user.email}:`, error.message);
  }
};

/**
 * Send Security Alert Email on successful user login
 * @param {Object} user - { _id, name, email }
 * @param {Object} details - { ip, userAgent, time }
 */
const sendLoginAlertEmail = async (user, details = {}) => {
  try {
    const mailer = await getTransporter();
    const fromAddress = process.env.EMAIL_FROM || '"Oweless" <owelessapp@gmail.com>';

    const loginTime = details.time || new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
    const ipAddress = details.ip || 'Unknown IP';
    const clientAgent = details.userAgent || 'Web Browser';

    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 0; }
          .container { max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }
          .header { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: #ffffff; padding: 25px 20px; text-align: center; }
          .header h1 { margin: 0; font-size: 22px; font-weight: 700; }
          .body { padding: 30px 25px; line-height: 1.6; }
          .alert-box { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 16px; border-radius: 8px; margin: 20px 0; }
          .alert-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
          .alert-row:last-child { border-bottom: none; }
          .alert-label { color: #64748b; font-weight: 600; }
          .alert-value { color: #1e293b; font-weight: 500; }
          .security-note { font-size: 13px; color: #64748b; margin-top: 20px; background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; border-radius: 4px; color: #92400e; }
          .footer { background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🔐 Security Alert: Successful Login</h1>
          </div>
          <div class="body">
            <h2>Hi ${user.name},</h2>
            <p>You have successfully logged into your <strong>Oweless</strong> account.</p>
            
            <div class="alert-box">
              <div class="alert-row">
                <span class="alert-label">Account Email:</span>
                <span class="alert-value">${user.email}</span>
              </div>
              <div class="alert-row">
                <span class="alert-label">Timestamp:</span>
                <span class="alert-value">${loginTime} (IST)</span>
              </div>
              <div class="alert-row">
                <span class="alert-label">IP Address:</span>
                <span class="alert-value">${ipAddress}</span>
              </div>
              <div class="alert-row">
                <span class="alert-label">Device / Browser:</span>
                <span class="alert-value">${clientAgent}</span>
              </div>
            </div>

            <div class="security-note">
              <strong>Was this you?</strong> If you recognize this activity, no further action is needed. If you did not log in, please secure your account immediately.
            </div>
          </div>
          <div class="footer">
            <p>This is a security notification sent to ${user.email} for your Oweless account (owelessapp@gmail.com).</p>
          </div>
        </div>
      </body>
      </html>
    `;

    const mailOptions = {
      from: fromAddress,
      to: user.email,
      subject: `Security Alert: Successful Login to Oweless`,
      text: `Hello ${user.name},\n\nYou have successfully logged into your Oweless account on ${loginTime} (IP: ${ipAddress}).\n\nIf this was not you, please secure your account immediately.\n\nOweless Team\nowelessapp@gmail.com`,
      html: htmlContent,
    };

    const info = await mailer.sendMail(mailOptions);
    console.log(`✅ Login alert email dispatched to ${user.email} (Message ID: ${info.messageId})`);
    return info;
  } catch (error) {
    console.error(`❌ Failed to send login alert email to ${user.email}:`, error.message);
  }
};

module.exports = {
  sendWelcomeEmail,
  sendLoginAlertEmail,
};
