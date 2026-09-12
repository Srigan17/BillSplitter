# ⚖️ Bill Splitter — Full-Stack Expense Splitting & Debt Settlement Application

A full-stack, responsive Bill Splitter web application designed to track group expenses, calculate fair shares, trace itemized debts back to individual expenses, and minimize settlement transactions with an optimized creditor-debtor matching algorithm.

---

## 🚀 Key Features

1. **User Authentication & Authorization**:
   - Secure registration, login, and token generation using **JWT** and **bcryptjs** password hashing.
   - Protected API routes and strict group-level authorization checks.
2. **Group Management**:
   - Create groups (e.g., *Goa Trip*, *Roommates*, *Office Outing*).
   - Add real registered users by exact email lookup (no fake members).
   - Safe member removal preventing deletion if members are tied to active expenses.
3. **Flexible Expense Splitting**:
   - Categories: **Food**, **Travel**, **Transport**, **Stay**, **Entertainment**, **Shopping**, **Other**.
   - Payer Options: **Single Payer** or **Multiple Payers** (with live sum & remainder balance indicators).
   - Split Methods:
     - **Equal (=)**: Split evenly across selected members.
     - **Percentage (%)**: Custom shares totaling exactly 100%.
     - **Exact Amount (₹)**: Specific amounts totaling the exact expense total.
4. **Expense-Level Debt Traceability**:
   - Clear audit trails explaining *"Why do I owe Rahul ₹750?"* by breaking down the exact proportional contribution across contributing expenses (*Dinner ₹300, Taxi ₹250, Hotel ₹200*).
5. **Optimized Settlement Algorithm**:
   - Server-side greedy creditor-debtor matching that calculates the minimum number of transactions needed to settle all group debts.
6. **External Settlement Tracking**:
   - Record external payments as **Settled** (`status: 'settled'`), dynamically updating net balances without altering historical expense data.
7. **Visual Analytics & Dashboard**:
   - Real-time **Chart.js** Doughnut chart for group category spending.
   - Clear separation between **Amount Spent (Paid Upfront)**, **Fair Share (Owed)**, and **Net Balance**.
   - Light and Dark mode support.

---

## 🛠️ Technology Stack

- **Backend**: Node.js, Express.js (REST API Architecture)
- **Database**: MongoDB with Mongoose ODM
- **Authentication**: JSON Web Tokens (JWT) & bcryptjs
- **Frontend**: HTML5, CSS3 (CSS Variables, Flexbox/Grid), Vanilla JavaScript (Modular ES6+)
- **Charts**: Chart.js

---

## 📂 Project Structure

```
bill-splitter/
│
├── backend/
│   ├── config/
│   │   └── db.js                    # MongoDB connection configuration
│   │
│   ├── controllers/
│   │   ├── authController.js        # Auth & user lookup logic
│   │   ├── groupController.js       # Group CRUD & member operations
│   │   ├── expenseController.js     # Expense management & split validations
│   │   └── settlementController.js  # Balances, audit breakdowns & settlements
│   │
│   ├── middleware/
│   │   └── authMiddleware.js        # JWT verification & group membership guards
│   │
│   ├── models/
│   │   ├── User.js                  # User schema with unique email & hashed password
│   │   ├── Group.js                 # Group schema referencing Users
│   │   ├── Expense.js               # Expense schema with multi-payer & multi-split
│   │   └── Settlement.js            # Settlement schema with status & timestamps
│   │
│   ├── routes/
│   │   ├── authRoutes.js            # /api/auth routes
│   │   ├── groupRoutes.js           # /api/groups routes
│   │   ├── expenseRoutes.js         # /api/expenses routes
│   │   └── settlementRoutes.js      # /api/settlements routes
│   │
│   ├── utils/
│   │   └── settlementCalculator.js  # Net balances, debt breakdown & greedy optimizer
│   │
│   ├── scripts/
│   │   └── test_scenario.js         # Test scenario validation script
│   │
│   ├── .env                         # Backend environment variables
│   ├── package.json
│   └── server.js                    # Express app entrypoint & static file server
│
├── frontend/
│   ├── index.html                   # Group Dashboard & Main SPA shell
│   ├── login.html                   # User login page
│   ├── register.html                # User registration page
│   │
│   ├── css/
│   │   ├── style.css                # Global styles, variables & dark theme
│   │   ├── auth.css                 # Auth views styling
│   │   └── responsive.css           # Mobile & tablet responsiveness
│   │
│   └── js/
│       ├── api.js                   # Fetch wrapper with JWT headers & error handling
│       ├── auth.js                  # Authentication & session state management
│       ├── dashboard.js             # Dashboard coordinator & Chart.js renderer
│       ├── groups.js                # Group switching, creation & member actions
│       ├── expenses.js              # Expense modal, split calculators & details
│       └── settlements.js           # Debts, audit breakdown modals & mark-settled
│
└── README.md
```

---

## ⚙️ Environment Variables

Create a `.env` file in the `backend/` directory:

```env
PORT=5000
MONGO_URI=mongodb://localhost:27017/billsplitter
JWT_SECRET=billsplitter_jwt_secret_key_super_secure_2026

# Email / SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
EMAIL_FROM="Bill Splitter <noreply@billsplitter.com>"
```

> **Note**: If SMTP credentials are not configured, the app will log outgoing emails to the console during development without failing or interrupting the user flow.

---

## 📦 Installation & Setup

### 1. Prerequisites
- [Node.js](https://nodejs.org/) (v16 or higher)
- [MongoDB](https://www.mongodb.com/) running locally or a MongoDB Atlas connection URI

### 2. Install Backend Dependencies
```bash
cd backend
npm install
```

---



## 🚦 Running the Full-Stack Node.js Application

### Option A: Run Backend & Serve Frontend
The Express backend is configured to automatically serve the frontend static files.

```bash
cd backend
npm start
```
Or for auto-reloading with nodemon:
```bash
npm run dev
```

Open your browser and navigate to:
```
http://localhost:5000
```

---

## 🧪 Running Scenario Tests

To execute the automated settlement and logic tests for **Scenario 1**, **Scenario 2**, and **Scenario 3**:

```bash
cd backend
npm run test:scenarios
```

---

## 📖 API Endpoints

### Authentication
- `POST /api/auth/register` — Register new user (`name`, `email`, `password`, `confirmPassword`)
- `POST /api/auth/login` — Login user (`email`, `password`)
- `GET /api/auth/me` — Get current logged-in user profile [Protected]
- `GET /api/auth/search?email=...` — Search registered user by exact email [Protected]

### Groups
- `GET /api/groups` — Get all groups the logged-in user belongs to [Protected]
- `POST /api/groups` — Create a new group (`name`) [Protected]
- `GET /api/groups/:id` — Get group details and members [Protected]
- `POST /api/groups/:id/members` — Add registered user by email (`email`) [Protected]
- `DELETE /api/groups/:id/members/:userId` — Remove member (safely validated) [Protected]

### Expenses
- `GET /api/groups/:id/expenses` — List all expenses in a group [Protected]
- `POST /api/groups/:id/expenses` — Create expense (with payments and splits) [Protected]
- `GET /api/expenses/:id` — Get individual expense details [Protected]
- `PUT /api/expenses/:id` — Update expense [Protected]
- `DELETE /api/expenses/:id` — Delete expense [Protected]

### Balances & Settlements
- `GET /api/groups/:id/balances` — Calculate net balances, personal spending, category totals, itemized debt breakdowns, and optimized settlements [Protected]
- `GET /api/groups/:id/settlements` — Get settlement records [Protected]
- `POST /api/groups/:id/settlements` — Record an external payment as settled (`fromUser`, `toUser`, `amount`) [Protected]
- `POST /api/settlements/:id/settle` — Mark pending settlement as settled [Protected]

---

## 🧮 Settlement Algorithm & Debt Traceability

### 1. Net Balance Calculation
For every group member:
$$\text{Net Balance} = (\text{Total Paid Upfront} - \text{Total Fair Share}) + (\text{Settled Paid} - \text{Settled Received})$$
- $\text{Net Balance} > 0$: Creditor (Should receive money)
- $\text{Net Balance} < 0$: Debtor (Needs to pay money)

### 2. Multi-Payer Itemized Debt Attribution
When multiple people contribute $P_i$ to an expense of total $E$, and a member $j$ has a fair share $S_j$, the amount member $j$ owes payer $i$ is:
$$\text{Debt}(j \to i) = S_j \times \frac{P_i}{E}$$
This allows clicking **View Breakdown** in the dashboard to trace every rupee back to the exact receipt.

### 3. Greedy Transaction Optimization
To minimize transactions across all group members:
1. Filter creditors ($\text{balance} > +₹0.01$) and debtors ($|\text{balance}| > ₹0.01$).
2. Sort both lists in descending order of remaining balance.
3. Match the maximum debtor with the maximum creditor and transfer:
   $$\text{Transfer Amount} = \min(|\text{Debtor Balance}|, \text{Creditor Balance})$$
4. Deduct the amount from both parties and repeat until all balances are $\le ₹0.01$.

---

## 🧪 Verified Test Scenarios

### Scenario 1: Single Payers with Equal Splits
- **Members**: Arun, Rahul, Priya (Group: *Goa Trip*)
- **Expenses**:
  - Dinner ₹900 (Paid by Arun, Equal split ₹300 each)
  - Hotel ₹3000 (Paid by Rahul, Equal split ₹1000 each)
  - Taxi ₹600 (Paid by Priya, Equal split ₹200 each)
- **Results**:
  - Total: ₹4500 (Fair share: ₹1500 each)
  - Arun: Paid ₹900, Net = -₹600
  - Rahul: Paid ₹3000, Net = +₹1500
  - Priya: Paid ₹600, Net = -₹900
  - **Optimized Settlements (2 steps)**:
    1. Priya $\to$ Rahul ₹900
    2. Arun $\to$ Rahul ₹600

### Scenario 2: Multi-Payer Expense
- **Expense**: Hotel ₹3000 (Stay)
- **Paid By**: Arun (₹2000), Rahul (₹1000)
- **Split**: Equal 3-way across Arun, Rahul, Priya (₹1000 each)
- **Results**:
  - Arun: Net = +₹1000
  - Rahul: Net = ₹0
  - Priya: Net = -₹1000
  - **Optimized Settlement (1 step)**:
    1. Priya $\to$ Arun ₹1000
