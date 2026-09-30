import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import json
import time
import random
from datetime import datetime

# Try importing plotly; fallback gracefully if not installed
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Set page configuration - must be the first Streamlit command
st.set_page_config(
    page_title="Bill Splitter - Smart Expense Management",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------- STYLES MATCHING BILLSPLITTER.HTML -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --primary-color: #6366f1;
        --primary-dark: #4f46e5;
        --secondary-color: #10b981;
        --accent-color: #f59e0b;
        --danger-color: #ef4444;
        --warning-color: #f59e0b;
        --bg-color: #ffffff;
        --surface-color: #f8fafc;
        --card-color: #ffffff;
        --text-primary: #1f2937;
        --text-secondary: #6b7280;
        --text-muted: #9ca3af;
        --border-color: #e5e7eb;
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        --shadow-xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #ffffff;
        color: #1f2937;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }

    /* Top Sticky Header */
    .bs-header {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        padding: 1.25rem 2rem;
        border-radius: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.35);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .bs-logo {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(45deg, #ffffff, #e0e7ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .bs-header-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .bs-action-pill {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        color: white;
        padding: 0.4rem 0.9rem;
        border-radius: 0.6rem;
        font-size: 0.85rem;
        font-weight: 600;
        backdrop-filter: blur(10px);
    }

    /* Section Titles */
    .bs-section-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: #1f2937;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .bs-section-icon {
        font-size: 1.4rem;
    }

    /* Card Panels */
    .bs-card {
        background: #ffffff;
        border-radius: 1.25rem;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 1.5rem;
    }

    /* KPI Stat Cards (Dashboard) */
    .stats-card {
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white;
        border-radius: 1.25rem;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
        margin-bottom: 1rem;
    }
    .stats-card.secondary {
        background: linear-gradient(135deg, #10b981, #059669);
    }
    .stats-number {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
        color: white;
    }
    .stats-label {
        font-size: 0.95rem;
        opacity: 0.92;
        color: #e0e7ff;
        font-weight: 500;
    }

    /* Members Section */
    .member-item {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        padding: 0.75rem 1rem;
        background: #f8fafc;
        border-radius: 0.75rem;
        border: 1px solid #e5e7eb;
        margin-bottom: 0.5rem;
    }
    .member-avatar {
        width: 2.75rem;
        height: 2.75rem;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #f59e0b);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 1.15rem;
        flex-shrink: 0;
    }
    .member-name {
        font-weight: 600;
        color: #1f2937;
        font-size: 0.95rem;
    }
    .member-balance {
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 0.15rem;
    }
    .member-balance.positive { color: #10b981; }
    .member-balance.negative { color: #ef4444; }
    .member-balance.settled { color: #6b7280; }

    /* Settlement Item */
    .settlement-item {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 0.85rem;
        padding: 0.85rem 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.6rem;
    }
    .settlement-arrow {
        font-size: 1.25rem;
        color: #6366f1;
        font-weight: bold;
    }
    .settlement-amount {
        font-size: 1.15rem;
        font-weight: 800;
        color: #10b981;
    }

    /* Expense Item */
    .expense-item {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 1rem;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
    }
    .expense-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    .expense-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.25rem;
    }
    .expense-meta {
        color: #6b7280;
        font-size: 0.85rem;
        display: flex;
        gap: 1rem;
    }
    .expense-amount {
        font-size: 1.4rem;
        font-weight: 800;
        color: #6366f1;
    }

    /* Validation indicator box */
    .validation-box {
        padding: 0.6rem 0.9rem;
        border-radius: 0.5rem;
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .val-valid { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    .val-warn { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .val-err { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 2.5rem 1.5rem;
        color: #6b7280;
        background: #f8fafc;
        border-radius: 1rem;
        border: 1px dashed #cbd5e1;
    }
    .empty-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
        opacity: 0.7;
    }
    .empty-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.25rem;
    }
    .empty-description {
        font-size: 0.88rem;
    }

    /* Streamlit Button Tweaks */
    div.stButton > button {
        border-radius: 0.6rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- AVATAR COLOR GENERATOR -----------------
AVATAR_GRADIENTS = [
    "linear-gradient(135deg, #6366f1, #f59e0b)",
    "linear-gradient(135deg, #ec4899, #f43f5e)",
    "linear-gradient(135deg, #10b981, #059669)",
    "linear-gradient(135deg, #f59e0b, #d97706)",
    "linear-gradient(135deg, #06b6d4, #0284c7)",
    "linear-gradient(135deg, #8b5cf6, #d946ef)",
]

def get_avatar_gradient(name: str) -> str:
    h = sum(ord(c) for c in (name or "Friend"))
    return AVATAR_GRADIENTS[h % len(AVATAR_GRADIENTS)]

# ----------------- DATABASE (SQLite) -----------------
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

# ----------------- USER & MEMBER HELPERS -----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def quick_start_user(name: str):
    clean_name = name.strip()
    if not clean_name:
        return False, "Please enter your name."
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email FROM users WHERE LOWER(name) = ? LIMIT 1", (clean_name.lower(),))
        existing = cursor.fetchone()
        if existing:
            return True, {"id": existing["id"], "name": existing["name"], "email": existing["email"]}
        
        unique_token = hashlib.md5(f"{clean_name}_{time.time()}_{random.random()}".encode()).hexdigest()[:6]
        placeholder_email = f"{clean_name.lower().replace(' ', '_')}_{unique_token}@billsplitter.local"
        placeholder_pw = hash_password(f"pw_{unique_token}")
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (clean_name, placeholder_email, placeholder_pw),
        )
        conn.commit()
        user_id = cursor.lastrowid
        return True, {"id": user_id, "name": clean_name, "email": placeholder_email}

def add_member_by_name(group_id: int, member_name: str):
    clean_name = member_name.strip()
    if not clean_name:
        return False, "Please enter a member name."
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT u.id, u.name 
        FROM users u
        JOIN group_members gm ON u.id = gm.user_id
        WHERE gm.group_id = ? AND LOWER(TRIM(u.name)) = LOWER(?)
        """, (group_id, clean_name))
        if cursor.fetchone():
            return False, f"Member '{clean_name}' already exists in this group."
        
        unique_token = hashlib.md5(f"{clean_name}_{group_id}_{time.time()}_{random.random()}".encode()).hexdigest()[:8]
        placeholder_email = f"{clean_name.lower().replace(' ', '_')}_{unique_token}@billsplitter.local"
        placeholder_pw = hash_password(f"pw_{unique_token}")
        
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (clean_name, placeholder_email, placeholder_pw)
        )
        new_uid = cursor.lastrowid
        cursor.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
            (group_id, new_uid)
        )
        conn.commit()
        return True, f"Added {clean_name} to the group!"

def remove_member_by_id(group_id: int, user_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
        urow = cursor.fetchone()
        name = urow["name"] if urow else "Member"
        
        cursor.execute("DELETE FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
        conn.commit()
        return True, f"Removed {name} from group."

# ----------------- FINANCIAL CALCULATIONS -----------------
def round2(val: float) -> float:
    return round(val + 1e-9, 2)

def calculate_group_finances(group_id: int, current_user_id: int):
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

        try:
            payments = json.loads(exp["payments"])
            splits = json.loads(exp["splits"])
        except Exception:
            payments = []
            splits = []

        for p in payments:
            uid = p.get("userId") or p.get("memberId")
            p_amt = p["amount"]
            if uid in member_map:
                member_map[uid]["paid"] = round2(member_map[uid]["paid"] + p_amt)
                if uid == current_user_id:
                    user_category_spending[cat] = round2(user_category_spending[cat] + p_amt)

        for s in splits:
            uid = s.get("userId") or s.get("memberId")
            s_amt = s["amount"]
            if uid in member_map:
                member_map[uid]["owed"] = round2(member_map[uid]["owed"] + s_amt)

        if amt > 0:
            for s in splits:
                debtor_id = s.get("userId") or s.get("memberId")
                split_share = s["amount"]
                if split_share > 0:
                    for p in payments:
                        creditor_id = p.get("userId") or p.get("memberId")
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

    return {
        "members": list(member_map.values()),
        "totalGroupSpending": total_group_spending,
        "groupCategorySpending": group_category_spending,
        "userCategorySpending": user_category_spending,
        "optimizedSettlements": optimized_settlements,
        "expenses": expenses,
        "settlements": settlements,
    }

# ----------------- SESSION STATE -----------------
if "user" not in st.session_state:
    st.session_state.user = None
if "active_group_id" not in st.session_state:
    st.session_state.active_group_id = None
if "exp_filter" not in st.session_state:
    st.session_state.exp_filter = "All"

# Auto-login default user if none set for instant demo experience
if not st.session_state.user:
    ok, default_u = quick_start_user("Srigan")
    if ok:
        st.session_state.user = default_u

current_user = st.session_state.user

# Ensure user has at least one group
with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute("""
    SELECT g.id, g.name, COUNT(gm.user_id) as member_count 
    FROM groups g 
    JOIN group_members gm ON g.id = gm.group_id 
    WHERE g.id IN (SELECT group_id FROM group_members WHERE user_id = ?) 
    GROUP BY g.id ORDER BY g.created_at ASC
    """, (current_user["id"],))
    user_groups = [dict(row) for row in cursor.fetchall()]

if not user_groups:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO groups (name, created_by) VALUES (?, ?)", ("My Group", current_user["id"]))
        new_gid = cursor.lastrowid
        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (new_gid, current_user["id"]))
        conn.commit()
        st.session_state.active_group_id = new_gid
        st.rerun()

group_ids = [g["id"] for g in user_groups]
if st.session_state.active_group_id not in group_ids:
    st.session_state.active_group_id = user_groups[0]["id"]

active_gid = st.session_state.active_group_id
active_group_obj = next((g for g in user_groups if g["id"] == active_gid), user_groups[0])
finances = calculate_group_finances(active_gid, current_user["id"])

# ----------------- TOP HEADER BAR -----------------
st.markdown(f"""
<header class="bs-header">
    <div style="display: flex; align-items: center; gap: 1rem;">
        <h1 class="bs-logo">Bill Splitter</h1>
    </div>
    <div class="bs-header-actions">
        <span class="bs-action-pill">👥 {active_group_obj['name']}</span>
        <span class="bs-action-pill">👤 {current_user['name']}</span>
    </div>
</header>
""", unsafe_allow_html=True)

# ----------------- 2-COLUMN MAIN LAYOUT (SIDEBAR + CONTENT) -----------------
col_sidebar, col_content = st.columns([1, 2], gap="large")

# ================= LEFT COLUMN: SIDEBAR =================
with col_sidebar:
    # 1. GROUP MANAGEMENT
    with st.container():
        st.markdown("""
        <h2 class="bs-section-title">
            <span class="bs-section-icon">👥</span> Groups
        </h2>
        """, unsafe_allow_html=True)

        group_names = {g["id"]: g["name"] for g in user_groups}
        sel_g = st.selectbox(
            "Select Group",
            options=list(group_names.keys()),
            format_func=lambda gid: group_names[gid],
            index=list(group_names.keys()).index(active_gid),
            label_visibility="collapsed",
            key="bs_group_select"
        )
        if sel_g != active_gid:
            st.session_state.active_group_id = sel_g
            st.rerun()

        with st.expander("➕ Add Group"):
            with st.form("bs_add_group_form", clear_on_submit=True):
                new_g_title = st.text_input("Group Name", placeholder="e.g., Trip to Paris, Goa 2026")
                if st.form_submit_button("Create Group", type="primary", use_container_width=True):
                    if new_g_title.strip():
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO groups (name, created_by) VALUES (?, ?)", (new_g_title.strip(), current_user["id"]))
                            new_created_gid = cursor.lastrowid
                            cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", (new_created_gid, current_user["id"]))
                            conn.commit()
                        st.session_state.active_group_id = new_created_gid
                        st.rerun()

    st.markdown("<hr style='margin: 1.25rem 0; border: 0; height: 1px; background: #e5e7eb;'>", unsafe_allow_html=True)

    # 2. MEMBERS SECTION
    with st.container():
        st.markdown("""
        <h3 class="bs-section-title">
            <span class="bs-section-icon">👤</span> Members
        </h3>
        """, unsafe_allow_html=True)

        members_list = finances["members"]
        if not members_list:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">👤</div>
                <div class="empty-title">No members yet</div>
                <div class="empty-description">Add members to start splitting expenses</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for member in members_list:
                is_me = member["id"] == current_user["id"]
                bal = member["net_balance"]
                bal_class = "positive" if bal > 0.01 else "negative" if bal < -0.01 else "settled"
                bal_text = f"Gets ${bal:,.2f}" if bal > 0.01 else f"Owes ${abs(bal):,.2f}" if bal < -0.01 else "Settled"
                avatar_grad = get_avatar_gradient(member["name"])
                initial = member["name"][0].upper() if member["name"] else "M"

                col_m_info, col_m_del = st.columns([5, 1])
                with col_m_info:
                    st.markdown(f"""
                    <div class="member-item">
                        <div class="member-avatar" style="background: {avatar_grad};">{initial}</div>
                        <div style="flex: 1;">
                            <div class="member-name">{member['name']} {'(You)' if is_me else ''}</div>
                            <div class="member-balance {bal_class}">{bal_text}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_m_del:
                    if not is_me:
                        if st.button("✕", key=f"del_member_btn_{active_gid}_{member['id']}", help=f"Remove {member['name']}"):
                            remove_member_by_id(active_gid, member["id"])
                            time.sleep(0.2)
                            st.rerun()

        # Add Member Form (Simple Name Input)
        with st.form("bs_add_member_quick_form", clear_on_submit=True):
            st.markdown("<div style='font-size: 0.9rem; font-weight: 600; margin-top: 0.5rem;'>Add Member</div>", unsafe_allow_html=True)
            col_in, col_btn = st.columns([3, 1])
            with col_in:
                new_m_name = st.text_input("Member Name", placeholder="Enter member name (e.g. Rahul, Priya)", label_visibility="collapsed")
            with col_btn:
                submitted_m = st.form_submit_button("Add", type="primary", use_container_width=True)

            if submitted_m:
                if not new_m_name.strip():
                    st.warning("Please enter a member name.")
                else:
                    success, msg = add_member_by_name(active_gid, new_m_name)
                    if success:
                        st.success(msg)
                        time.sleep(0.2)
                        st.rerun()
                    else:
                        st.warning(msg)

    st.markdown("<hr style='margin: 1.25rem 0; border: 0; height: 1px; background: #e5e7eb;'>", unsafe_allow_html=True)

    # 3. SETTLEMENT SUMMARY SECTION
    with st.container():
        st.markdown("""
        <h3 class="bs-section-title">
            <span class="bs-section-icon">💰</span> Settlements
        </h3>
        """, unsafe_allow_html=True)

        if not finances["optimizedSettlements"]:
            st.markdown("""
            <div style="background: #f8fafc; border-radius: 0.75rem; padding: 1rem; text-align: center; color: #10b981; font-weight: 600; border: 1px solid #e5e7eb;">
                ✨ All debts are settled!
            </div>
            """, unsafe_allow_html=True)
        else:
            for idx, st_item in enumerate(finances["optimizedSettlements"]):
                col_st_info, col_st_btn = st.columns([3, 1])
                with col_st_info:
                    st.markdown(f"""
                    <div class="settlement-item">
                        <div style="font-weight: 600; font-size: 0.92rem; color: #1f2937;">
                            {st_item['fromUserName']} <span class="settlement-arrow">➔</span> {st_item['toUserName']}
                        </div>
                        <div class="settlement-amount">${st_item['amount']:,.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_st_btn:
                    if st.button("✓ Settle", key=f"settle_sidebar_btn_{active_gid}_{idx}", type="primary", use_container_width=True):
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                            INSERT INTO settlements (group_id, from_user, to_user, amount, status, settled_at)
                            VALUES (?, ?, ?, ?, 'settled', CURRENT_TIMESTAMP)
                            """, (active_gid, st_item["fromUser"], st_item["toUser"], st_item["amount"]))
                            conn.commit()
                        time.sleep(0.2)
                        st.rerun()

# ================= RIGHT COLUMN: CONTENT =================
with col_content:
    # 1. DASHBOARD CARD (STATS + CHART)
    with st.container(border=True):
        st.markdown("""
        <h2 class="bs-section-title">
            <span class="bs-section-icon">📊</span> Dashboard
        </h2>
        """, unsafe_allow_html=True)

        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.markdown(f"""
            <div class="stats-card">
                <div class="stats-number">${finances['totalGroupSpending']:,.2f}</div>
                <div class="stats-label">Total Expenses</div>
            </div>
            """, unsafe_allow_html=True)
        with col_stat2:
            st.markdown(f"""
            <div class="stats-card secondary">
                <div class="stats-number">{len(finances['members'])}</div>
                <div class="stats-label">Members</div>
            </div>
            """, unsafe_allow_html=True)

        # Expense Breakdown Chart
        group_cat_df = pd.DataFrame(
            [{"Category": k, "Amount": v} for k, v in finances["groupCategorySpending"].items() if v > 0]
        )
        if not group_cat_df.empty:
            if HAS_PLOTLY:
                fig = px.pie(
                    group_cat_df,
                    values="Amount",
                    names="Category",
                    hole=0.55,
                    color_discrete_sequence=["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#8b5cf6", "#64748b"]
                )
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=280,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True, key=f"plotly_dashboard_chart_{active_gid}")
            else:
                st.bar_chart(group_cat_df.set_index("Category"))
        else:
            st.info("No expense data recorded yet for the chart.")

    # 2. EXPENSES CARD (FILTERS + ADD EXPENSE + LIST)
    with st.container(border=True):
        c_exp_head, c_exp_filt = st.columns([1, 1])
        with c_exp_head:
            st.markdown("""
            <h2 class="bs-section-title" style="margin-bottom: 0;">
                <span class="bs-section-icon">💳</span> Expenses
            </h2>
            """, unsafe_allow_html=True)
        with c_exp_filt:
            filter_choice = st.radio(
                "Filter",
                ["All", "Recent", "Highest"],
                horizontal=True,
                label_visibility="collapsed",
                key="bs_exp_filter_radio"
            )

        # Add Expense Expander
        with st.expander("➕ Add Expense", expanded=False):
            if not finances["members"]:
                st.warning("Please add members to this group before adding expenses.")
            else:
                fe1, fe2 = st.columns(2)
                with fe1:
                    in_title = st.text_input("Expense Title", placeholder="e.g., Dinner at restaurant, Hotel", key="bs_exp_title")
                    in_amount = st.number_input("Amount ($)", min_value=0.01, step=1.0, format="%.2f", key="bs_exp_amount")
                with fe2:
                    in_cat = st.selectbox("Category", ["Food", "Travel", "Transport", "Stay", "Entertainment", "Shopping", "Other"], key="bs_exp_cat")
                    in_date = st.date_input("Date", value=datetime.today(), key="bs_exp_date")

                st.markdown("<div style='font-weight: 600; font-size: 0.95rem; margin-top: 0.5rem;'>Payment Method</div>", unsafe_allow_html=True)
                p_method = st.radio("Payment Method", ["Single Payer", "Multiple Payers"], horizontal=True, label_visibility="collapsed", key="bs_payer_mode")

                payments_data = []
                if p_method == "Single Payer":
                    single_uid = st.selectbox(
                        "Paid by",
                        options=[m["id"] for m in finances["members"]],
                        format_func=lambda uid: next(m["name"] for m in finances["members"] if m["id"] == uid),
                        key="bs_single_payer_sel"
                    )
                    payments_data.append({"userId": single_uid, "amount": in_amount})
                else:
                    st.markdown("<div style='font-size: 0.85rem; color: #6b7280; margin-bottom: 0.5rem;'>Who paid how much?</div>", unsafe_allow_html=True)
                    num_p_cols = min(max(len(finances["members"]), 1), 3)
                    p_cols = st.columns(num_p_cols)
                    total_p_in = 0.0
                    for i, m in enumerate(finances["members"]):
                        with p_cols[i % num_p_cols]:
                            p_val = st.number_input(f"{m['name']} ($)", min_value=0.0, step=1.0, format="%.2f", key=f"bs_multi_p_{m['id']}")
                            if p_val > 0:
                                payments_data.append({"userId": m["id"], "amount": p_val})
                                total_p_in += p_val

                    diff_p = round2(in_amount - total_p_in)
                    if abs(diff_p) < 0.01:
                        st.markdown('<div class="validation-box val-valid">✅ Payments match total amount</div>', unsafe_allow_html=True)
                    elif diff_p > 0:
                        st.markdown(f'<div class="validation-box val-warn">⚠️ Missing ${diff_p:,.2f}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="validation-box val-err">❌ Overpaid by ${abs(diff_p):,.2f}</div>', unsafe_allow_html=True)

                st.markdown("<div style='font-weight: 600; font-size: 0.95rem; margin-top: 0.5rem;'>Split Method</div>", unsafe_allow_html=True)
                s_method = st.radio("Split Method", ["Equal Split", "Percentage", "Exact Amount"], horizontal=True, label_visibility="collapsed", key="bs_split_mode")

                splits_data = []
                if s_method == "Equal Split":
                    sel_members = st.multiselect(
                        "Split among:",
                        options=[m["id"] for m in finances["members"]],
                        default=[m["id"] for m in finances["members"]],
                        format_func=lambda uid: next(m["name"] for m in finances["members"] if m["id"] == uid),
                        key="bs_eq_split_sel"
                    )
                    if sel_members:
                        eq_amt = round2(in_amount / len(sel_members))
                        for uid in sel_members:
                            splits_data.append({"userId": uid, "amount": eq_amt})
                        st.caption(f"Each person owes **${eq_amt:,.2f}** ({len(sel_members)} members)")
                elif s_method == "Percentage":
                    num_s_cols = min(max(len(finances["members"]), 1), 3)
                    s_cols = st.columns(num_s_cols)
                    total_pct = 0.0
                    for i, m in enumerate(finances["members"]):
                        with s_cols[i % num_s_cols]:
                            pct_val = st.number_input(f"{m['name']} (%)", min_value=0.0, max_value=100.0, step=5.0, format="%.1f", key=f"bs_split_pct_{m['id']}")
                            if pct_val > 0:
                                s_amt = round2((in_amount * pct_val) / 100.0)
                                splits_data.append({"userId": m["id"], "amount": s_amt, "percentage": pct_val})
                                total_pct += pct_val
                    diff_pct = round2(100.0 - total_pct)
                    if abs(diff_pct) < 0.1:
                        st.markdown('<div class="validation-box val-valid">✅ Percentages total 100%</div>', unsafe_allow_html=True)
                    elif diff_pct > 0:
                        st.markdown(f'<div class="validation-box val-warn">⚠️ Total Percentage: {total_pct:.1f}% — Remaining: {diff_pct:.1f}%</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="validation-box val-err">❌ Exceeds 100% by {abs(diff_pct):.1f}%</div>', unsafe_allow_html=True)
                else:
                    num_s_cols = min(max(len(finances["members"]), 1), 3)
                    s_cols = st.columns(num_s_cols)
                    total_exact = 0.0
                    for i, m in enumerate(finances["members"]):
                        with s_cols[i % num_s_cols]:
                            exact_val = st.number_input(f"{m['name']} ($)", min_value=0.0, step=1.0, format="%.2f", key=f"bs_split_exact_{m['id']}")
                            if exact_val > 0:
                                splits_data.append({"userId": m["id"], "amount": round2(exact_val)})
                                total_exact += exact_val
                    diff_exact = round2(in_amount - total_exact)
                    if abs(diff_exact) < 0.02:
                        st.markdown('<div class="validation-box val-valid">✅ Splits match total amount</div>', unsafe_allow_html=True)
                    elif diff_exact > 0:
                        st.markdown(f'<div class="validation-box val-warn">⚠️ Missing ${diff_exact:,.2f}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="validation-box val-err">❌ Over by ${abs(diff_exact):,.2f}</div>', unsafe_allow_html=True)

                if st.button("Save Expense", type="primary", use_container_width=True, key="bs_save_expense_btn"):
                    if not in_title.strip():
                        st.error("Please enter an expense title.")
                    elif in_amount <= 0:
                        st.error("Amount must be greater than zero.")
                    elif not payments_data:
                        st.error("Please specify at least one payer.")
                    elif not splits_data:
                        st.error("Please specify split participants.")
                    else:
                        sum_p = round2(sum(p["amount"] for p in payments_data))
                        sum_s = round2(sum(s["amount"] for s in splits_data))
                        if abs(sum_p - in_amount) > 0.05:
                            st.error(f"Payments total (${sum_p:,.2f}) does not match expense total (${in_amount:,.2f})")
                        elif abs(sum_s - in_amount) > 0.1:
                            st.error(f"Splits total (${sum_s:,.2f}) does not match expense total (${in_amount:,.2f})")
                        else:
                            with get_db() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                INSERT INTO expenses (group_id, title, amount, category, date, payments, splits, split_method, created_by)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    active_gid,
                                    in_title.strip(),
                                    in_amount,
                                    in_cat,
                                    str(in_date),
                                    json.dumps(payments_data),
                                    json.dumps(splits_data),
                                    s_method,
                                    current_user["id"],
                                ))
                                conn.commit()
                            st.success(f"Expense '{in_title}' added successfully!")
                            time.sleep(0.3)
                            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Expense List
        group_expenses = finances["expenses"]
        if not group_expenses:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">💳</div>
                <div class="empty-title">No expenses yet</div>
                <div class="empty-description">Add your first expense above to get started!</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            sorted_exp = list(group_expenses)
            if filter_choice == "Recent":
                sorted_exp = sorted_exp[:5]
            elif filter_choice == "Highest":
                sorted_exp = sorted(sorted_exp, key=lambda x: x["amount"], reverse=True)

            for exp in sorted_exp:
                try:
                    p_list = json.loads(exp["payments"])
                    s_list = json.loads(exp["splits"])
                except Exception:
                    p_list = []
                    s_list = []

                if len(p_list) > 1:
                    p_str = ", ".join(f"{next((m['name'] for m in finances['members'] if m['id'] == (p.get('userId') or p.get('memberId'))), 'Member')} (${p['amount']:,.2f})" for p in p_list)
                    payer_info = f"Paid by {p_str}"
                elif len(p_list) == 1:
                    p_name = next((m['name'] for m in finances['members'] if m['id'] == (p_list[0].get('userId') or p_list[0].get('memberId'))), 'Member')
                    payer_info = f"Paid by {p_name}"
                else:
                    payer_info = "Paid by Unknown"

                col_e_card, col_e_act = st.columns([6, 1])
                with col_e_card:
                    st.markdown(f"""
                    <div class="expense-item">
                        <div class="expense-header">
                            <div>
                                <div class="expense-title">{exp['title']}</div>
                                <div class="expense-meta">
                                    <span>{payer_info}</span>
                                    <span>📅 {exp['date']}</span>
                                    <span>🏷️ {exp['category']}</span>
                                </div>
                            </div>
                            <div class="expense-amount">${exp['amount']:,.2f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_e_act:
                    if st.button("🗑️", key=f"bs_del_exp_{exp['id']}", help="Delete expense"):
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM expenses WHERE id = ?", (exp["id"],))
                            conn.commit()
                        time.sleep(0.2)
                        st.rerun()
