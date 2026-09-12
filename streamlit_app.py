import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Try importing plotly; fallback gracefully if not installed
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Set page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="Oweless — Smart Expense Sharing",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS matching modern reference design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Top Header Banner */
    .hero-banner {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.2);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        color: white !important;
    }
    .hero-sub {
        font-size: 0.95rem;
        opacity: 0.9;
        margin-top: 0.25rem;
        color: #e0e7ff;
    }

    /* KPI Stat Cards */
    .stats-card {
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white;
        border-radius: 1rem;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stats-card.positive {
        background: linear-gradient(135deg, #10b981, #059669);
    }
    .stats-card.negative {
        background: linear-gradient(135deg, #ef4444, #dc2626);
    }
    .stats-number {
        font-size: 1.75rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
        color: white;
    }
    .stats-label {
        font-size: 0.85rem;
        opacity: 0.9;
        font-weight: 500;
        color: #f1f5f9;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Member Items */
    .member-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: #f8fafc;
        border-radius: 0.75rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.5rem;
    }
    .member-avatar {
        width: 2.5rem;
        height: 2.5rem;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #f59e0b);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 1rem;
    }
    .member-name {
        font-weight: 600;
        color: #1e293b;
    }
    .member-balance-tag {
        font-size: 0.8rem;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
    }
    .tag-positive { background: #d1fae5; color: #065f46; }
    .tag-negative { background: #fee2e2; color: #991b1b; }
    .tag-settled { background: #e0e7ff; color: #3730a3; }

    /* Settlement Item */
    .settlement-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        padding: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }

    /* Form Validation Box */
    .validation-box {
        padding: 0.6rem 0.9rem;
        border-radius: 0.5rem;
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    .val-valid { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    .val-warn { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .val-err { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
</style>
""", unsafe_allow_html=True)

# ----------------- DATABASE UTILITIES (SQLite) -----------------
DB_FILE = "billsplitter.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            payments TEXT NOT NULL,
            splits TEXT NOT NULL,
            split_method TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            from_user INTEGER,
            to_user INTEGER,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            settled_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (from_user) REFERENCES users(id),
            FOREIGN KEY (to_user) REFERENCES users(id)
        )
        """)
        conn.commit()

init_db()

# ----------------- AUTHENTICATION HELPERS -----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def send_welcome_email_py(name: str, to_email: str):
    """
    Sends a welcome email from owelessapp@gmail.com to the user upon account creation.
    Supports credentials via Streamlit Secrets (st.secrets) or environment variables.
    Falls back gracefully to console logging if SMTP_PASS is omitted.
    """
    from email.header import Header

    smtp_pass = None
    try:
        if hasattr(st, "secrets") and "SMTP_PASS" in st.secrets:
            smtp_pass = st.secrets["SMTP_PASS"]
    except Exception:
        pass
    if not smtp_pass:
        smtp_pass = os.environ.get("SMTP_PASS")

    smtp_user = "owelessapp@gmail.com"
    try:
        if hasattr(st, "secrets") and "SMTP_USER" in st.secrets:
            smtp_user = st.secrets["SMTP_USER"]
    except Exception:
        pass
    if os.environ.get("SMTP_USER"):
        smtp_user = os.environ.get("SMTP_USER")

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    sender_name = "Oweless"
    sender_email = smtp_user or "owelessapp@gmail.com"

    subject_text = f"Welcome to Oweless, {name}! ⚖️"
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

    text_body = f"""Hello {name},

Your Oweless account has been successfully created with email {to_email}.

Welcome aboard!
Oweless Team
owelessapp@gmail.com
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
    .header {{ background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); color: #ffffff; padding: 30px 20px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
    .header p {{ margin: 8px 0 0 0; opacity: 0.9; font-size: 14px; }}
    .body {{ padding: 30px 25px; line-height: 1.6; }}
    .welcome-box {{ background: #e0e7ff; border-left: 4px solid #6366f1; padding: 15px; border-radius: 6px; margin: 20px 0; color: #3730a3; }}
    .features-list {{ list-style: none; padding: 0; margin: 20px 0; }}
    .features-list li {{ padding: 8px 0; display: flex; align-items: center; }}
    .features-list li span {{ margin-right: 10px; font-size: 18px; }}
    .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>⚖️ Welcome to Oweless</h1>
      <p>Fair, transparent, and hassle-free expense sharing</p>
    </div>
    <div class="body">
      <h2>Hello, {name}! 👋</h2>
      <p>Your account has been successfully created. You're all set to start tracking shared expenses, finding optimal settlements, and keeping accounts clear with your friends, roommates, and colleagues.</p>
      
      <div class="welcome-box">
        <strong>Registered Email:</strong> {to_email}<br>
        <strong>Account Created:</strong> {now_str}
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
</html>"""

    if not smtp_pass:
        try:
            print("\n================== EMAIL NOTIFICATION DISPATCHED ==================")
            print(f"To: {to_email}")
            print(f"From: {sender_name} <{sender_email}>")
            print(f"Subject: Welcome to Oweless, {name}!")
            print("--------------------------- Content Preview ---------------------------")
            print(f"Hello {name},\n\nYour Oweless account has been successfully created with email {to_email}.\n\nWelcome aboard!\nOweless Team\nowelessapp@gmail.com")
            print("======================================================================\n")
        except Exception:
            pass
        return False, "SMTP_PASS not configured (Logged to console)"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject_text, "utf-8").encode()
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to_email

        part1 = MIMEText(text_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, [to_email], msg.as_string())
        print(f"Welcome email sent successfully to {to_email} from {sender_email}")
        return True, "Email sent successfully"
    except Exception as e:
        print(f"Failed to dispatch email to {to_email}: {e}")
        return False, str(e)

def register_user(name, email, password):
    email = email.lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return False, "User with this email already exists."
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name.strip(), email, hash_password(password)),
        )
        conn.commit()
        user_id = cursor.lastrowid
        user_data = {"id": user_id, "name": name.strip(), "email": email}
        
        # Dispatch welcome email from owelessapp@gmail.com
        send_welcome_email_py(user_data["name"], user_data["email"])
        
        return True, user_data

def login_user(email, password):
    email = email.lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, password FROM users WHERE email = ?", (email,)
        )
        user = cursor.fetchone()
        if user and user["password"] == hash_password(password):
            return True, {"id": user["id"], "name": user["name"], "email": user["email"]}
        return False, "Invalid email or password."

# ----------------- FINANCIAL & SETTLEMENT ALGORITHM -----------------
def round2(val):
    return round(val + 1e-9, 2)

def calculate_group_finances(group_id, current_user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT u.id, u.name, u.email 
        FROM users u 
        JOIN group_members gm ON u.id = gm.user_id 
        WHERE gm.group_id = ?
        """, (group_id,))
        members = [dict(row) for row in cursor.fetchall()]
        member_map = {
            m["id"]: {
                "id": m["id"],
                "name": m["name"],
                "email": m["email"],
                "paid": 0.0,
                "owed": 0.0,
                "settled_paid": 0.0,
                "settled_received": 0.0,
                "net_balance": 0.0,
            }
            for m in members
        }

        cursor.execute("SELECT * FROM expenses WHERE group_id = ? ORDER BY date DESC, id DESC", (group_id,))
        expenses = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM settlements WHERE group_id = ? AND status = 'settled' ORDER BY settled_at DESC", (group_id,))
        settlements = [dict(row) for row in cursor.fetchall()]

    group_category_spending = {
        "Food": 0.0, "Travel": 0.0, "Transport": 0.0, "Stay": 0.0,
        "Entertainment": 0.0, "Shopping": 0.0, "Other": 0.0
    }
    user_category_spending = {k: 0.0 for k in group_category_spending}

    pairwise_debts = {
        d_id: {
            c_id: {"total": 0.0, "expenses": []}
            for c_id in member_map if c_id != d_id
        }
        for d_id in member_map
    }

    total_group_spending = 0.0

    for exp in expenses:
        amt = exp["amount"]
        cat = exp["category"] if exp["category"] in group_category_spending else "Other"
        group_category_spending[cat] = round2(group_category_spending[cat] + amt)
        total_group_spending = round2(total_group_spending + amt)

        payments = json.loads(exp["payments"])
        splits = json.loads(exp["splits"])

        for p in payments:
            uid = p["userId"]
            p_amt = p["amount"]
            if uid in member_map:
                member_map[uid]["paid"] = round2(member_map[uid]["paid"] + p_amt)
                if uid == current_user_id:
                    user_category_spending[cat] = round2(user_category_spending[cat] + p_amt)

        for s in splits:
            uid = s["userId"]
            s_amt = s["amount"]
            if uid in member_map:
                member_map[uid]["owed"] = round2(member_map[uid]["owed"] + s_amt)

        if amt > 0:
            for s in splits:
                debtor_id = s["userId"]
                split_share = s["amount"]
                if split_share > 0:
                    for p in payments:
                        creditor_id = p["userId"]
                        payer_paid = p["amount"]
                        if debtor_id != creditor_id and payer_paid > 0:
                            portion_owed = round2(split_share * (payer_paid / amt))
                            if portion_owed > 0.001 and debtor_id in pairwise_debts and creditor_id in pairwise_debts[debtor_id]:
                                pairwise_debts[debtor_id][creditor_id]["total"] = round2(
                                    pairwise_debts[debtor_id][creditor_id]["total"] + portion_owed
                                )
                                pairwise_debts[debtor_id][creditor_id]["expenses"].append({
                                    "title": exp["title"],
                                    "category": exp["category"],
                                    "date": exp["date"],
                                    "expenseTotal": amt,
                                    "payerPaid": payer_paid,
                                    "userShareTotal": split_share,
                                    "amountOwed": portion_owed,
                                })

    for st_rec in settlements:
        f_id = st_rec["from_user"]
        t_id = st_rec["to_user"]
        s_amt = st_rec["amount"]
        if f_id in member_map:
            member_map[f_id]["settled_paid"] = round2(member_map[f_id]["settled_paid"] + s_amt)
        if t_id in member_map:
            member_map[t_id]["settled_received"] = round2(member_map[t_id]["settled_received"] + s_amt)

    for m in member_map.values():
        m["net_balance"] = round2((m["paid"] - m["owed"]) + (m["settled_paid"] - m["settled_received"]))

    creditors = [
        {"userId": m["id"], "name": m["name"], "balance": m["net_balance"]}
        for m in member_map.values() if m["net_balance"] > 0.01
    ]
    debtors = [
        {"userId": m["id"], "name": m["name"], "balance": abs(m["net_balance"])}
        for m in member_map.values() if m["net_balance"] < -0.01
    ]

    optimized_settlements = []
    while creditors and debtors:
        creditors.sort(key=lambda x: x["balance"], reverse=True)
        debtors.sort(key=lambda x: x["balance"], reverse=True)

        c = creditors[0]
        d = debtors[0]
        transfer_amt = round2(min(c["balance"], d["balance"]))

        if transfer_amt >= 0.01:
            optimized_settlements.append({
                "fromUser": d["userId"],
                "fromUserName": d["name"],
                "toUser": c["userId"],
                "toUserName": c["name"],
                "amount": transfer_amt,
            })

        c["balance"] = round2(c["balance"] - transfer_amt)
        d["balance"] = round2(d["balance"] - transfer_amt)

        if c["balance"] < 0.01:
            creditors.pop(0)
        if d["balance"] < 0.01:
            debtors.pop(0)

    you_need_to_pay = []
    if current_user_id in pairwise_debts:
        for target_id, debt_info in pairwise_debts[current_user_id].items():
            if debt_info["total"] > 0.01:
                you_need_to_pay.append({
                    "toUser": target_id,
                    "toUserName": member_map[target_id]["name"],
                    "amount": debt_info["total"],
                    "expenses": debt_info["expenses"],
                })

    you_should_receive = []
    for other_id, creditors_map in pairwise_debts.items():
        if other_id != current_user_id and current_user_id in creditors_map:
            debt_info = creditors_map[current_user_id]
            if debt_info["total"] > 0.01:
                you_should_receive.append({
                    "fromUser": other_id,
                    "fromUserName": member_map[other_id]["name"],
                    "amount": debt_info["total"],
                    "expenses": debt_info["expenses"],
                })

    return {
        "members": list(member_map.values()),
        "totalGroupSpending": total_group_spending,
        "groupCategorySpending": group_category_spending,
        "userCategorySpending": user_category_spending,
        "optimizedSettlements": optimized_settlements,
        "youNeedToPay": you_need_to_pay,
        "youShouldReceive": you_should_receive,
        "expenses": expenses,
        "settlements": settlements,
    }

# ----------------- SESSION STATE -----------------
if "user" not in st.session_state:
    st.session_state.user = None
if "active_group_id" not in st.session_state:
    st.session_state.active_group_id = None

# ----------------- AUTHENTICATION VIEW -----------------
if not st.session_state.user:
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #4f46e5; margin-bottom: 0.5rem;">⚖️ Oweless</h1>
        <p style="font-size: 1.1rem; color: #64748b;">Smart, transparent expense sharing & automated settlement calculations</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["🔐 Log In", "📝 Sign Up"])

            with tab_login:
                st.subheader("Login to your account")
                login_email = st.text_input("Email Address", key="login_email_input")
                login_password = st.text_input("Password", type="password", key="login_password_input")
                if st.button("Log In", type="primary", use_container_width=True, key="login_submit_btn"):
                    if not login_email or not login_password:
                        st.error("Please provide both email and password.")
                    else:
                        success, res = login_user(login_email, login_password)
                        if success:
                            st.session_state.user = res
                            st.rerun()
                        else:
                            st.error(res)

            with tab_register:
                st.subheader("Create a new account")
                reg_name = st.text_input("Full Name", key="reg_name_input")
                reg_email = st.text_input("Email Address", key="reg_email_input")
                reg_password = st.text_input("Password (min 6 characters)", type="password", key="reg_password_input")
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm_input")
                if st.button("Create Account", type="primary", use_container_width=True, key="reg_submit_btn"):
                    if not reg_name or not reg_email or not reg_password:
                        st.error("Please fill in all fields.")
                    elif reg_password != reg_confirm:
                        st.error("Passwords do not match.")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        success, res = register_user(reg_name, reg_email, reg_password)
                        if success:
                            st.success("Account created successfully! Logging you in...")
                            st.session_state.user = res
                            st.rerun()
                        else:
                            st.error(res)

# ----------------- MAIN LOGGED-IN DASHBOARD -----------------
else:
    current_user = st.session_state.user

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT g.id, g.name, COUNT(gm.user_id) as member_count 
        FROM groups g 
        JOIN group_members gm ON g.id = gm.group_id 
        WHERE g.id IN (SELECT group_id FROM group_members WHERE user_id = ?) 
        GROUP BY g.id ORDER BY g.created_at DESC
        """, (current_user["id"],))
        user_groups = [dict(row) for row in cursor.fetchall()]

    # Sidebar: Group Management & Profile
    with st.sidebar:
        st.markdown(f"### 👤 {current_user['name']}")
        st.caption(current_user["email"])
        if st.button("🚪 Log Out", use_container_width=True, key="logout_sidebar_btn"):
            st.session_state.user = None
            st.session_state.active_group_id = None
            st.rerun()

        st.divider()
        st.markdown("### 👥 Your Groups")

        if user_groups:
            group_options = {g["id"]: f"{g['name']} ({g['member_count']} members)" for g in user_groups}
            if st.session_state.active_group_id not in group_options:
                st.session_state.active_group_id = user_groups[0]["id"]

            selected_gid = st.selectbox(
                "Active Group",
                options=list(group_options.keys()),
                format_func=lambda x: group_options[x],
                index=list(group_options.keys()).index(st.session_state.active_group_id),
                key="sidebar_group_select",
            )
            st.session_state.active_group_id = selected_gid
        else:
            st.info("You are not part of any group yet.")

        with st.expander("➕ Create New Group"):
            new_gname = st.text_input("Group Name", placeholder="e.g. Goa Trip, Roommates", key="new_group_name_input")
            if st.button("Create Group", type="primary", use_container_width=True, key="create_group_submit_btn"):
                if new_gname.strip():
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO groups (name, created_by) VALUES (?, ?)", (new_gname.strip(), current_user["id"]))
                        new_gid = cursor.lastrowid
                        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (new_gid, current_user["id"]))
                        conn.commit()
                    st.success(f"Group '{new_gname}' created!")
                    st.session_state.active_group_id = new_gid
                    st.rerun()
                else:
                    st.error("Please enter a group name.")

    if not st.session_state.active_group_id:
        st.info("👈 Create or select a group from the sidebar to start tracking expenses.")
    else:
        active_gid = st.session_state.active_group_id
        finances = calculate_group_finances(active_gid, current_user["id"])

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM groups WHERE id = ?", (active_gid,))
            group_name = cursor.fetchone()["name"]

        # Hero Banner
        st.markdown(f"""
        <div class="hero-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <h1 class="hero-title">{group_name}</h1>
                    <div class="hero-sub">{len(finances['members'])} Members • Total Group Spending: ₹{finances['totalGroupSpending']:,.2f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick Add Member Bar
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            member_chips = []
            for m in finances["members"]:
                is_me = m["id"] == current_user["id"]
                bal = m["net_balance"]
                bal_tag = f"+₹{bal:,.2f}" if bal > 0.01 else f"-₹{abs(bal):,.2f}" if bal < -0.01 else "Settled"
                member_chips.append(f"**{m['name']}{' (You)' if is_me else ''}** (`{bal_tag}`)")
            st.markdown("👥 " + " • ".join(member_chips))
        with col_m2:
            with st.popover("➕ Add Member by Email"):
                add_email = st.text_input("User Email Address", key="add_member_email_input")
                if st.button("Add Member", type="primary", key="add_member_submit_btn"):
                    if add_email.strip():
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT id, name FROM users WHERE email = ?", (add_email.lower().strip(),))
                            found_user = cursor.fetchone()
                            if not found_user:
                                st.error("User not found. They must register with this email first.")
                            else:
                                cursor.execute("SELECT * FROM group_members WHERE group_id = ? AND user_id = ?", (active_gid, found_user["id"]))
                                if cursor.fetchone():
                                    st.warning("User is already a member of this group.")
                                else:
                                    cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (active_gid, found_user["id"]))
                                    conn.commit()
                                    st.success(f"Added {found_user['name']} to group!")
                                    st.rerun()

        # Top 4 KPI Metric Cards
        curr_member_stat = next((m for m in finances["members"] if m["id"] == current_user["id"]), None)
        user_paid = curr_member_stat["paid"] if curr_member_stat else 0.0
        user_owed = curr_member_stat["owed"] if curr_member_stat else 0.0
        net_bal = curr_member_stat["net_balance"] if curr_member_stat else 0.0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">₹{finances['totalGroupSpending']:,.2f}</div>
                <div class="stats-label">Total Group Expenses</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">₹{user_paid:,.2f}</div>
                <div class="stats-label">You Paid (Spent)</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">₹{user_owed:,.2f}</div>
                <div class="stats-label">Your Fair Share</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            card_class = "positive" if net_bal > 0.01 else "negative" if net_bal < -0.01 else ""
            status_text = f"You Receive ₹{net_bal:,.2f}" if net_bal > 0.01 else f"You Owe ₹{abs(net_bal):,.2f}" if net_bal < -0.01 else "All Settled (₹0.00)"
            st.markdown(f"""
            <div class="stats-card {card_class}">
                <div class="stats-number">₹{abs(net_bal):,.2f}</div>
                <div class="stats-label">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Tab Navigation
        tab_debts, tab_add_exp, tab_expenses, tab_breakdown, tab_analytics, tab_history = st.tabs([
            "⚡ Balances & Settlements",
            "💳 + Add Expense",
            "🧾 Expense List",
            "👥 Member Breakdown",
            "📊 Analytics & Charts",
            "📜 History",
        ])

        # ----------------- TAB 1: Balances & Settlements -----------------
        with tab_debts:
            col_l, col_r = st.columns(2)

            with col_l:
                st.markdown("### 🔴 You Need to Pay")
                if not finances["youNeedToPay"]:
                    st.success("🎉 You don't owe any money in this group!")
                else:
                    for idx, item in enumerate(finances["youNeedToPay"]):
                        with st.expander(f"You → **{item['toUserName']}**: ₹{item['amount']:,.2f}", expanded=True):
                            st.write(f"Contributing expenses ({len(item['expenses'])}):")
                            for exp_item in item["expenses"]:
                                st.markdown(f"- **{exp_item['title']}** ({exp_item['category']}): Total ₹{exp_item['expenseTotal']:,.2f} ➔ Your debt: **₹{exp_item['amountOwed']:,.2f}**")

                st.markdown("### 🟢 You Should Receive")
                if not finances["youShouldReceive"]:
                    st.info("ℹ️ No one owes you money right now.")
                else:
                    for idx, item in enumerate(finances["youShouldReceive"]):
                        with st.expander(f"**{item['fromUserName']}** → You: ₹{item['amount']:,.2f}", expanded=True):
                            st.write(f"Contributing expenses ({len(item['expenses'])}):")
                            for exp_item in item["expenses"]:
                                st.markdown(f"- **{exp_item['title']}** ({exp_item['category']}): Total ₹{exp_item['expenseTotal']:,.2f} ➔ Amount for you: **₹{exp_item['amountOwed']:,.2f}**")

            with col_r:
                st.markdown("### ⚡ Optimized Settlement Plan")
                st.caption(f"Greedy algorithm minimizing transactions ({len(finances['optimizedSettlements'])} total needed)")
                
                if not finances["optimizedSettlements"]:
                    st.success("✨ All members are fully settled! No payments required.")
                else:
                    for idx, st_item in enumerate(finances["optimizedSettlements"]):
                        is_from_me = st_item["fromUser"] == current_user["id"]
                        is_to_me = st_item["toUser"] == current_user["id"]
                        
                        from_label = "You" if is_from_me else st_item["fromUserName"]
                        to_label = "You" if is_to_me else st_item["toUserName"]

                        with st.container(border=True):
                            c1, c2 = st.columns([3, 2])
                            with c1:
                                st.markdown(f"**{from_label}** ➔ **{to_label}**")
                                st.markdown(f"<h3 style='color: #4f46e5; margin: 0;'>₹{st_item['amount']:,.2f}</h3>", unsafe_allow_html=True)
                            with c2:
                                if st.button("✓ Mark as Settled", key=f"settle_action_btn_{active_gid}_{idx}"):
                                    with get_db() as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                        INSERT INTO settlements (group_id, from_user, to_user, amount, status, settled_at)
                                        VALUES (?, ?, ?, ?, 'settled', CURRENT_TIMESTAMP)
                                        """, (active_gid, st_item["fromUser"], st_item["toUser"], st_item["amount"]))
                                        conn.commit()
                                    st.success(f"Settlement of ₹{st_item['amount']:,.2f} recorded!")
                                    st.rerun()

        # ----------------- TAB 2: Add Expense (Interactive Dynamic Multiple Payers) -----------------
        with tab_add_exp:
            st.markdown("### Add a New Group Expense")
            
            fe_col1, fe_col2 = st.columns(2)
            with fe_col1:
                exp_title = st.text_input("Expense Title", placeholder="e.g. Dinner at Restaurant, Hotel, Taxi", key="exp_title_in")
                exp_amount = st.number_input("Total Amount (₹)", min_value=0.01, step=10.0, format="%.2f", key="exp_amount_in")
            with fe_col2:
                exp_cat = st.selectbox("Category", ["Food", "Travel", "Transport", "Stay", "Entertainment", "Shopping", "Other"], key="exp_cat_in")
                exp_date = st.date_input("Date", value=datetime.today(), key="exp_date_in")

            st.divider()
            st.markdown("#### 💳 Who Paid for this Expense?")
            payer_mode = st.radio("Payment Method", ["Single Payer", "Multiple Payers"], horizontal=True, key="payer_mode_radio")

            payments_payload = []
            if payer_mode == "Single Payer":
                single_payer_id = st.selectbox(
                    "Paid By",
                    options=[m["id"] for m in finances["members"]],
                    format_func=lambda uid: next(f"{m['name']}{' (You)' if m['id'] == current_user['id'] else ''}" for m in finances["members"] if m["id"] == uid),
                    key="single_payer_select"
                )
                payments_payload.append({"userId": single_payer_id, "amount": exp_amount})
                st.info(f"Paid ₹{exp_amount:,.2f} by {next(m['name'] for m in finances['members'] if m['id'] == single_payer_id)}")
            else:
                st.markdown("**Enter how much each member paid:**")
                multi_payer_cols = st.columns(min(len(finances["members"]), 3))
                total_paid_entered = 0.0

                for i, m in enumerate(finances["members"]):
                    col_idx = i % min(len(finances["members"]), 3)
                    with multi_payer_cols[col_idx]:
                        is_me = m["id"] == current_user["id"]
                        p_val = st.number_input(
                            f"{m['name']}{' (You)' if is_me else ''} paid (₹)",
                            min_value=0.0,
                            step=10.0,
                            format="%.2f",
                            key=f"multi_payer_amt_{active_gid}_{m['id']}"
                        )
                        if p_val > 0:
                            payments_payload.append({"userId": m["id"], "amount": p_val})
                            total_paid_entered += p_val

                diff_paid = round2(exp_amount - total_paid_entered)
                if abs(diff_paid) < 0.01:
                    st.markdown(f'<div class="validation-box val-valid">✅ Total Paid (₹{total_paid_entered:,.2f}) matches Expense Total (₹{exp_amount:,.2f})</div>', unsafe_allow_html=True)
                elif diff_paid > 0:
                    st.markdown(f'<div class="validation-box val-warn">⚠️ Total Paid so far: ₹{total_paid_entered:,.2f} — Missing ₹{diff_paid:,.2f}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="validation-box val-err">❌ Overpaid by ₹{abs(diff_paid):,.2f} (Total Paid: ₹{total_paid_entered:,.2f})</div>', unsafe_allow_html=True)

            st.divider()
            st.markdown("#### ➗ How to Split?")
            split_mode = st.radio("Split Method", ["Equal (=)", "Percentage (%)", "Exact Amount (₹)"], horizontal=True, key="split_mode_radio")

            splits_payload = []
            if split_mode == "Equal (=)":
                selected_split_members = st.multiselect(
                    "Select members sharing this bill:",
                    options=[m["id"] for m in finances["members"]],
                    default=[m["id"] for m in finances["members"]],
                    format_func=lambda uid: next(f"{m['name']}{' (You)' if m['id'] == current_user['id'] else ''}" for m in finances["members"] if m["id"] == uid),
                    key="split_equal_multiselect"
                )
                if selected_split_members:
                    eq_share = round2(exp_amount / len(selected_split_members))
                    for uid in selected_split_members:
                        splits_payload.append({"userId": uid, "amount": eq_share})
                    st.caption(f"Each selected member owes **₹{eq_share:,.2f}** ({len(selected_split_members)} members)")
            elif split_mode == "Percentage (%)":
                st.markdown("**Enter percentage share for each member (Must total 100%):**")
                pct_cols = st.columns(min(len(finances["members"]), 3))
                total_pct_entered = 0.0

                for i, m in enumerate(finances["members"]):
                    col_idx = i % min(len(finances["members"]), 3)
                    with pct_cols[col_idx]:
                        is_me = m["id"] == current_user["id"]
                        pct_val = st.number_input(
                            f"{m['name']}{' (You)' if is_me else ''} (%)",
                            min_value=0.0,
                            max_value=100.0,
                            step=5.0,
                            format="%.1f",
                            key=f"split_pct_val_{active_gid}_{m['id']}"
                        )
                        if pct_val > 0:
                            s_amt = round2((exp_amount * pct_val) / 100.0)
                            splits_payload.append({"userId": m["id"], "amount": s_amt, "percentage": pct_val})
                            total_pct_entered += pct_val

                diff_pct = round2(100.0 - total_pct_entered)
                if abs(diff_pct) < 0.1:
                    st.markdown(f'<div class="validation-box val-valid">✅ Percentages total 100% (Balanced)</div>', unsafe_allow_html=True)
                elif diff_pct > 0:
                    st.markdown(f'<div class="validation-box val-warn">⚠️ Total Percentage: {total_pct_entered:.1f}% — Remaining: {diff_pct:.1f}%</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="validation-box val-err">❌ Total Percentage: {total_pct_entered:.1f}% (Exceeds 100% by {abs(diff_pct):.1f}%)</div>', unsafe_allow_html=True)
            else:
                st.markdown("**Enter exact amount share for each member:**")
                exact_cols = st.columns(min(len(finances["members"]), 3))
                total_exact_entered = 0.0

                for i, m in enumerate(finances["members"]):
                    col_idx = i % min(len(finances["members"]), 3)
                    with exact_cols[col_idx]:
                        is_me = m["id"] == current_user["id"]
                        exact_val = st.number_input(
                            f"{m['name']}{' (You)' if is_me else ''} share (₹)",
                            min_value=0.0,
                            step=10.0,
                            format="%.2f",
                            key=f"split_exact_val_{active_gid}_{m['id']}"
                        )
                        if exact_val > 0:
                            splits_payload.append({"userId": m["id"], "amount": round2(exact_val)})
                            total_exact_entered += exact_val

                diff_exact = round2(exp_amount - total_exact_entered)
                if abs(diff_exact) < 0.02:
                    st.markdown(f'<div class="validation-box val-valid">✅ Split total (₹{total_exact_entered:,.2f}) matches Expense Total</div>', unsafe_allow_html=True)
                elif diff_exact > 0:
                    st.markdown(f'<div class="validation-box val-warn">⚠️ Total Split: ₹{total_exact_entered:,.2f} — Missing ₹{diff_exact:,.2f}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="validation-box val-err">❌ Total Split: ₹{total_exact_entered:,.2f} (Over by ₹{abs(diff_exact):,.2f})</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Save Expense", type="primary", use_container_width=True, key="save_expense_main_btn"):
                if not exp_title.strip():
                    st.error("Please enter an expense title.")
                elif exp_amount <= 0:
                    st.error("Expense amount must be greater than zero.")
                elif not payments_payload:
                    st.error("Please specify at least one payer.")
                elif not splits_payload:
                    st.error("Please specify who splits this expense.")
                else:
                    sum_payments = round2(sum(p["amount"] for p in payments_payload))
                    sum_splits = round2(sum(s["amount"] for s in splits_payload))

                    if abs(sum_payments - exp_amount) > 0.05:
                        st.error(f"Total payments (₹{sum_payments:,.2f}) do not match expense total (₹{exp_amount:,.2f})")
                    elif abs(sum_splits - exp_amount) > 0.1:
                        st.error(f"Total split shares (₹{sum_splits:,.2f}) do not match expense total (₹{exp_amount:,.2f})")
                    else:
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                            INSERT INTO expenses (group_id, title, amount, category, date, payments, splits, split_method, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                active_gid,
                                exp_title.strip(),
                                exp_amount,
                                exp_cat,
                                str(exp_date),
                                json.dumps(payments_payload),
                                json.dumps(splits_payload),
                                split_mode,
                                current_user["id"],
                            ))
                            conn.commit()
                        st.success(f"Expense '{exp_title}' recorded successfully!")
                        st.rerun()

        # ----------------- TAB 3: Expense List (Filterable) -----------------
        with tab_expenses:
            st.markdown("### 🧾 Group Expense History")
            if not finances["expenses"]:
                st.info("No expenses recorded yet in this group.")
            else:
                filter_choice = st.radio("Filter By:", ["All", "Recent (Last 5)", "Highest Amount"], horizontal=True, key="exp_filter_radio")
                
                sorted_expenses = list(finances["expenses"])
                if filter_choice == "Recent (Last 5)":
                    sorted_expenses = sorted_expenses[:5]
                elif filter_choice == "Highest Amount":
                    sorted_expenses = sorted(sorted_expenses, key=lambda x: x["amount"], reverse=True)

                for exp in sorted_expenses:
                    payments = json.loads(exp["payments"])
                    splits = json.loads(exp["splits"])
                    
                    payer_names = [f"{next((m['name'] for m in finances['members'] if m['id'] == p['userId']), 'User')} (₹{p['amount']:,.2f})" for p in payments]
                    
                    with st.expander(f"**{exp['title']}** — `₹{exp['amount']:,.2f}` ({exp['category']} • {exp['date']})"):
                        st.markdown(f"**Paid By:** {', '.join(payer_names)}")
                        st.markdown("**Splits:**")
                        for s in splits:
                            s_name = next((m['name'] for m in finances['members'] if m['id'] == s['userId']), 'User')
                            st.markdown(f"- {s_name}: ₹{s['amount']:,.2f}")

                        if st.button("🗑️ Delete Expense", key=f"del_exp_btn_{exp['id']}"):
                            with get_db() as conn:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM expenses WHERE id = ?", (exp["id"],))
                                conn.commit()
                            st.success("Expense deleted.")
                            st.rerun()

        # ----------------- TAB 4: Individual Member Breakdown -----------------
        with tab_breakdown:
            st.markdown("### 👥 Member Financial Breakdown")
            st.caption("Detailed overview of what each person paid upfront vs their fair share")

            for m in finances["members"]:
                is_me = m["id"] == current_user["id"]
                bal = m["net_balance"]
                bal_tag = f"Gets ₹{bal:,.2f}" if bal > 0.01 else f"Owes ₹{abs(bal):,.2f}" if bal < -0.01 else "All Settled"
                tag_style = "tag-positive" if bal > 0.01 else "tag-negative" if bal < -0.01 else "tag-settled"
                initial = m["name"][0].upper() if m["name"] else "U"

                with st.container(border=True):
                    c_av, c_info = st.columns([1, 6])
                    with c_av:
                        st.markdown(f'<div class="member-avatar">{initial}</div>', unsafe_allow_html=True)
                    with c_info:
                        st.markdown(f"**{m['name']}{' (You)' if is_me else ''}** &nbsp; <span class='member-balance-tag {tag_style}'>{bal_tag}</span>", unsafe_allow_html=True)
                        b1, b2, b3 = st.columns(3)
                        with b1:
                            st.metric(label="Paid Upfront", value=f"₹{m['paid']:,.2f}")
                        with b2:
                            st.metric(label="Fair Share Owed", value=f"₹{m['owed']:,.2f}")
                        with b3:
                            st.metric(label="Net Balance", value=f"₹{m['net_balance']:,.2f}")

        # ----------------- TAB 5: Analytics & Plotly Charts (Fixed Duplicate Element IDs) -----------------
        with tab_analytics:
            st.markdown("### 📊 Category Spending Analytics")
            c_chart1, c_chart2 = st.columns(2)

            group_cat_df = pd.DataFrame(
                [{"Category": k, "Amount": v} for k, v in finances["groupCategorySpending"].items() if v > 0]
            )

            with c_chart1:
                st.markdown("#### 🏢 Group Spending by Category")
                if not group_cat_df.empty:
                    if HAS_PLOTLY:
                        fig_group = px.pie(
                            group_cat_df,
                            values="Amount",
                            names="Category",
                            hole=0.5,
                            color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        fig_group.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                        st.plotly_chart(fig_group, use_container_width=True, key="plotly_group_chart_unique_id")
                    else:
                        st.bar_chart(group_cat_df.set_index("Category"))
                else:
                    st.info("No group spending recorded yet.")

            with c_chart2:
                st.markdown("#### 👤 Your Upfront Spending by Category")
                user_cat_df = pd.DataFrame(
                    [{"Category": k, "Amount": v} for k, v in finances["userCategorySpending"].items() if v > 0]
                )
                if not user_cat_df.empty:
                    if HAS_PLOTLY:
                        fig_user = px.pie(
                            user_cat_df,
                            values="Amount",
                            names="Category",
                            hole=0.5,
                            color_discrete_sequence=px.colors.qualitative.Safe
                        )
                        fig_user.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                        st.plotly_chart(fig_user, use_container_width=True, key="plotly_user_chart_unique_id")
                    else:
                        st.bar_chart(user_cat_df.set_index("Category"))
                else:
                    st.info("You haven't paid upfront for any expenses in this group yet.")

        # ----------------- TAB 6: History -----------------
        with tab_history:
            st.markdown("### 📜 Completed Settlements History")
            if not finances["settlements"]:
                st.info("No settlements recorded yet.")
            else:
                for st_record in finances["settlements"]:
                    from_name = next((m["name"] for m in finances["members"] if m["id"] == st_record["from_user"]), "User")
                    to_name = next((m["name"] for m in finances["members"] if m["id"] == st_record["to_user"]), "User")
                    st.markdown(f"✅ **{from_name}** paid **{to_name}** `₹{st_record['amount']:,.2f}` on *{st_record['settled_at']}*")
