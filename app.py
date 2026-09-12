import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
import json
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Bill Splitter",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .metric-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        border-left: 5px solid #6366f1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 0.85rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .metric-val { font-size: 1.75rem; font-weight: 800; color: #1e293b; margin: 4px 0; }
    .badge-receive { background-color: #d1fae5; color: #065f46; padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem; }
    .badge-pay { background-color: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem; }
    .badge-settled { background-color: #e0e7ff; color: #3730a3; padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem; }
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
        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Groups Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """)
        # Group Members Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        # Expenses Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            payments TEXT NOT NULL, -- JSON: [{"userId": 1, "amount": 500}]
            splits TEXT NOT NULL,   -- JSON: [{"userId": 1, "amount": 250, "percentage": 50}]
            split_method TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """)
        # Settlements Table
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
        return True, {"id": user_id, "name": name.strip(), "email": email}

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
        # Fetch members
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

        # Fetch expenses
        cursor.execute("SELECT * FROM expenses WHERE group_id = ? ORDER BY date DESC", (group_id,))
        expenses = [dict(row) for row in cursor.fetchall()]

        # Fetch settlements
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

        # Pairwise attribution
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

    # Account for settled settlements
    for st in settlements:
        f_id = st["from_user"]
        t_id = st["to_user"]
        s_amt = st["amount"]
        if f_id in member_map:
            member_map[f_id]["settled_paid"] = round2(member_map[f_id]["settled_paid"] + s_amt)
        if t_id in member_map:
            member_map[t_id]["settled_received"] = round2(member_map[t_id]["settled_received"] + s_amt)

    # Net balances
    for m in member_map.values():
        m["net_balance"] = round2((m["paid"] - m["owed"]) + (m["settled_paid"] - m["settled_received"]))

    # Greedy Settlement Optimization
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

    # Tailored lists for current user
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
    st.markdown("<h1 style='text-align: center;'>⚖️ Bill Splitter</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Effortless group expense splitting & optimized debt settlements</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔐 Log In", "📝 Sign Up"])

        with tab_login:
            st.subheader("Login to your account")
            login_email = st.text_input("Email Address", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Log In", type="primary", use_container_width=True):
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
            reg_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email Address", key="reg_email")
            reg_password = st.text_input("Password (min 6 characters)", type="password", key="reg_password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
            if st.button("Create Account", type="primary", use_container_width=True):
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

    # Fetch user's groups
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

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👋 Hi, {current_user['name']}")
        st.caption(current_user["email"])
        if st.button("🚪 Log Out", use_container_width=True):
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
                "Select Active Group",
                options=list(group_options.keys()),
                format_func=lambda x: group_options[x],
                index=list(group_options.keys()).index(st.session_state.active_group_id),
            )
            st.session_state.active_group_id = selected_gid
        else:
            st.info("You are not part of any group yet.")

        # Create Group Dialog / Form
        with st.expander("➕ Create New Group"):
            new_gname = st.text_input("Group Name", placeholder="e.g. Goa Trip, Roommates")
            if st.button("Create Group", type="primary", use_container_width=True):
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

    # Main Body
    if not st.session_state.active_group_id:
        st.info("👈 Create or select a group from the sidebar to start tracking expenses.")
    else:
        active_gid = st.session_state.active_group_id
        finances = calculate_group_finances(active_gid, current_user["id"])

        # Group Title & Banner
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM groups WHERE id = ?", (active_gid,))
            group_name = cursor.fetchone()["name"]

        st.markdown(f"# ⚖️ {group_name}")
        
        # Members List & Add Member
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            member_names = [f"{m['name']} {'(You)' if m['id'] == current_user['id'] else ''}" for m in finances["members"]]
            st.markdown(f"**Members ({len(member_names)}):** " + " • ".join(member_names))
        with col_m2:
            with st.popover("👤 + Add Member"):
                add_email = st.text_input("Registered User Email")
                if st.button("Add to Group", type="primary"):
                    if add_email.strip():
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT id, name FROM users WHERE email = ?", (add_email.lower().strip(),))
                            found_user = cursor.fetchone()
                            if not found_user:
                                st.error("User not found. They must register first.")
                            else:
                                cursor.execute("SELECT * FROM group_members WHERE group_id = ? AND user_id = ?", (active_gid, found_user["id"]))
                                if cursor.fetchone():
                                    st.warning("User is already in this group.")
                                else:
                                    cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (active_gid, found_user["id"]))
                                    conn.commit()
                                    st.success(f"Added {found_user['name']} to group!")
                                    st.rerun()

        # 4 Top Metrics Cards
        curr_member_stat = next((m for m in finances["members"] if m["id"] == current_user["id"]), None)
        user_paid = curr_member_stat["paid"] if curr_member_stat else 0.0
        user_owed = curr_member_stat["owed"] if curr_member_stat else 0.0
        net_bal = curr_member_stat["net_balance"] if curr_member_stat else 0.0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Total Group Spending</div>
                <div class="metric-val">₹{finances['totalGroupSpending']:,.2f}</div>
                <small style="color: #64748b;">All expenses combined</small>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">You Paid (Spent)</div>
                <div class="metric-val">₹{user_paid:,.2f}</div>
                <small style="color: #64748b;">Paid by you upfront</small>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Your Fair Share</div>
                <div class="metric-val">₹{user_owed:,.2f}</div>
                <small style="color: #64748b;">Your total share owed</small>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            if net_bal > 0.01:
                badge = f'<span class="badge-receive">You Receive ₹{net_bal:,.2f}</span>'
            elif net_bal < -0.01:
                badge = f'<span class="badge-pay">You Owe ₹{abs(net_bal):,.2f}</span>'
            else:
                badge = '<span class="badge-settled">All Settled (₹0.00)</span>'

            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Your Net Balance</div>
                <div class="metric-val">₹{abs(net_bal):,.2f}</div>
                <div>{badge}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabs for Dashboard Sections
        tab_debts, tab_add_exp, tab_expenses, tab_analytics, tab_history = st.tabs([
            "⚡ Balances & Settlements",
            "💳 + Add Expense",
            "🧾 Expenses List",
            "📊 Analytics & Charts",
            "📜 Settlement History",
        ])

        # TAB 1: Balances & Settlements
        with tab_debts:
            col_l, col_r = st.columns(2)

            with col_l:
                st.markdown("### 🔴 You Need to Pay")
                if not finances["youNeedToPay"]:
                    st.success("🎉 You don't owe any money to anyone in this group!")
                else:
                    for item in finances["youNeedToPay"]:
                        with st.expander(f"You → **{item['toUserName']}**: ₹{item['amount']:,.2f}"):
                            st.write(f"Contributing expenses ({len(item['expenses'])}):")
                            for exp_item in item["expenses"]:
                                st.markdown(f"- **{exp_item['title']}** ({exp_item['category']}): Total ₹{exp_item['expenseTotal']:,.2f} ➔ Your debt portion: **₹{exp_item['amountOwed']:,.2f}**")

                st.markdown("### 🟢 You Should Receive")
                if not finances["youShouldReceive"]:
                    st.info("ℹ️ No one owes you money right now.")
                else:
                    for item in finances["youShouldReceive"]:
                        with st.expander(f"**{item['fromUserName']}** → You: ₹{item['amount']:,.2f}"):
                            st.write(f"Contributing expenses ({len(item['expenses'])}):")
                            for exp_item in item["expenses"]:
                                st.markdown(f"- **{exp_item['title']}** ({exp_item['category']}): Total ₹{exp_item['expenseTotal']:,.2f} ➔ Portion owed to you: **₹{exp_item['amountOwed']:,.2f}**")

            with col_r:
                st.markdown("### ⚡ Optimized Settlement Plan")
                st.caption("Greedy algorithm minimizing total transactions across all members")
                
                if not finances["optimizedSettlements"]:
                    st.success("✨ All members are fully settled! No payments required.")
                else:
                    for idx, st_item in enumerate(finances["optimizedSettlements"]):
                        is_from_me = st_item["fromUser"] == current_user["id"]
                        is_to_me = st_item["toUser"] == current_user["id"]
                        
                        from_label = "You" if is_from_me else st_item["fromUserName"]
                        to_label = "You" if is_to_me else st_item["toUserName"]

                        c1, c2 = st.columns([3, 2])
                        with c1:
                            st.markdown(f"**{from_label}** ➔ **{to_label}**: `₹{st_item['amount']:,.2f}`")
                        with c2:
                            if st.button("✓ Mark as Settled", key=f"settle_btn_{idx}"):
                                with get_db() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                    INSERT INTO settlements (group_id, from_user, to_user, amount, status, settled_at)
                                    VALUES (?, ?, ?, ?, 'settled', CURRENT_TIMESTAMP)
                                    """, (active_gid, st_item["fromUser"], st_item["toUser"], st_item["amount"]))
                                    conn.commit()
                                st.success(f"Settlement of ₹{st_item['amount']:,.2f} recorded!")
                                st.rerun()

        # TAB 2: Add Expense
        with tab_add_exp:
            st.markdown("### Add a New Group Expense")
            with st.form("add_expense_form", clear_on_submit=True):
                fe_col1, fe_col2 = st.columns(2)
                with fe_col1:
                    exp_title = st.text_input("Expense Title", placeholder="e.g. Dinner, Hotel, Taxi")
                    exp_amount = st.number_input("Total Amount (₹)", min_value=0.01, step=1.0, format="%.2f")
                with fe_col2:
                    exp_cat = st.selectbox("Category", ["Food", "Travel", "Transport", "Stay", "Entertainment", "Shopping", "Other"])
                    exp_date = st.date_input("Date", value=datetime.today())

                st.divider()
                st.markdown("#### Who Paid?")
                payer_mode = st.radio("Payer Mode", ["Single Payer", "Multiple Payers"], horizontal=True)

                payments_payload = []
                if payer_mode == "Single Payer":
                    payer_id = st.selectbox(
                        "Paid By",
                        options=[m["id"] for m in finances["members"]],
                        format_func=lambda uid: next(m["name"] for m in finances["members"] if m["id"] == uid),
                    )
                    payments_payload.append({"userId": payer_id, "amount": exp_amount})
                else:
                    st.caption("Specify amount paid by each person:")
                    for m in finances["members"]:
                        p_val = st.number_input(f"Paid by {m['name']} (₹)", min_value=0.0, max_value=float(exp_amount) if exp_amount > 0 else 100000.0, step=1.0, key=f"mp_{m['id']}")
                        if p_val > 0:
                            payments_payload.append({"userId": m["id"], "amount": p_val})

                st.divider()
                st.markdown("#### How to Split?")
                split_mode = st.radio("Split Method", ["Equal (=)", "Percentage (%)", "Exact Amount (₹)"], horizontal=True)

                splits_payload = []
                if split_mode == "Equal (=)":
                    selected_members = st.multiselect(
                        "Split with Members",
                        options=[m["id"] for m in finances["members"]],
                        default=[m["id"] for m in finances["members"]],
                        format_func=lambda uid: next(m["name"] for m in finances["members"] if m["id"] == uid),
                    )
                    if selected_members:
                        eq_share = round2(exp_amount / len(selected_members))
                        for uid in selected_members:
                            splits_payload.append({"userId": uid, "amount": eq_share})
                elif split_mode == "Percentage (%)":
                    for m in finances["members"]:
                        pct = st.number_input(f"{m['name']} Share (%)", min_value=0.0, max_value=100.0, step=1.0, key=f"sp_pct_{m['id']}")
                        if pct > 0:
                            splits_payload.append({"userId": m["id"], "amount": round2((exp_amount * pct) / 100.0), "percentage": pct})
                else:
                    for m in finances["members"]:
                        s_exact = st.number_input(f"{m['name']} Share (₹)", min_value=0.0, step=1.0, key=f"sp_ex_{m['id']}")
                        if s_exact > 0:
                            splits_payload.append({"userId": m["id"], "amount": round2(s_exact)})

                submit_exp = st.form_submit_button("Save Expense", type="primary")

                if submit_exp:
                    if not exp_title.strip():
                        st.error("Please provide an expense title.")
                    elif exp_amount <= 0:
                        st.error("Expense amount must be greater than zero.")
                    else:
                        sum_payments = round2(sum(p["amount"] for p in payments_payload))
                        sum_splits = round2(sum(s["amount"] for s in splits_payload))

                        if abs(sum_payments - exp_amount) > 0.05:
                            st.error(f"Total payments (₹{sum_payments:,.2f}) do not match expense amount (₹{exp_amount:,.2f})")
                        elif abs(sum_splits - exp_amount) > 0.1:
                            st.error(f"Total split shares (₹{sum_splits:,.2f}) do not match expense amount (₹{exp_amount:,.2f})")
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
                            st.success(f"Expense '{exp_title}' recorded!")
                            st.rerun()

        # TAB 3: Expenses List
        with tab_expenses:
            st.markdown("### Group Expense History")
            if not finances["expenses"]:
                st.info("No expenses recorded yet.")
            else:
                for exp in finances["expenses"]:
                    payments = json.loads(exp["payments"])
                    splits = json.loads(exp["splits"])
                    
                    payer_names = [f"{next((m['name'] for m in finances['members'] if m['id'] == p['userId']), 'User')} (₹{p['amount']:,.2f})" for p in payments]
                    
                    with st.expander(f"**{exp['title']}** — `₹{exp['amount']:,.2f}` ({exp['category']} • {exp['date']})"):
                        st.markdown(f"**Paid By:** {', '.join(payer_names)}")
                        st.markdown("**Splits:**")
                        for s in splits:
                            s_name = next((m['name'] for m in finances['members'] if m['id'] == s['userId']), 'User')
                            st.markdown(f"- {s_name}: ₹{s['amount']:,.2f}")

                        if st.button("🗑️ Delete Expense", key=f"del_exp_{exp['id']}"):
                            with get_db() as conn:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM expenses WHERE id = ?", (exp["id"],))
                                conn.commit()
                            st.success("Expense deleted.")
                            st.rerun()

        # TAB 4: Analytics
        with tab_analytics:
            st.markdown("### Category Spending Breakdown")
            c_chart1, c_chart2 = st.columns(2)

            group_cat_df = pd.DataFrame(
                [{"Category": k, "Amount": v} for k, v in finances["groupCategorySpending"].items() if v > 0]
            )

            with c_chart1:
                st.markdown("#### 🏢 Group Spending by Category")
                if not group_cat_df.empty:
                    fig = px.pie(group_cat_df, values="Amount", names="Category", hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No spending recorded.")

            with c_chart2:
                st.markdown("#### 👤 Your Upfront Spending by Category")
                user_cat_df = pd.DataFrame(
                    [{"Category": k, "Amount": v} for k, v in finances["userCategorySpending"].items() if v > 0]
                )
                if not user_cat_df.empty:
                    fig_user = px.pie(user_cat_df, values="Amount", names="Category", hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
                    fig_user.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_user, use_container_width=True)
                else:
                    st.info("You haven't paid upfront for any expenses in this group yet.")

        # TAB 5: Settlement History
        with tab_history:
            st.markdown("### Completed Settlements")
            if not finances["settlements"]:
                st.info("No settlements recorded yet.")
            else:
                for st_record in finances["settlements"]:
                    from_name = next((m["name"] for m in finances["members"] if m["id"] == st_record["from_user"]), "User")
                    to_name = next((m["name"] for m in finances["members"] if m["id"] == st_record["to_user"]), "User")
                    st.markdown(f"✅ **{from_name}** paid **{to_name}** `₹{st_record['amount']:,.2f}` on *{st_record['settled_at']}*")
