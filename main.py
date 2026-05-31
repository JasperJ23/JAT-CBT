import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from datetime import datetime

# ==============================================================================
# 1. DATABASE SETUP & UTILITIES
# ==============================================================================
DB_NAME = "jat_cbt.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
            )
        """)
        
        # Exams Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                duration_mins INTEGER NOT NULL,
                pass_percentage INTEGER NOT NULL,
                exam_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Questions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
            )
        """)
        
        # Exam Sessions/Results Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                percentage REAL NOT NULL,
                status TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
            )
        """)
        
        # FORCE MASTER ADMIN CREDENTIALS
        cursor.execute("SELECT * FROM users WHERE username = 'Jasper390'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('Jasper390', 'JasperJ23', 'admin')")
            
        conn.commit()

init_db()

# ==============================================================================
# 2. SESSION STATE & UI CONFIGURATION
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.user_role = ""
    
# CBT Engine Navigation Controllers
if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
    st.session_state.start_time = None
if 'current_q_index' not in st.session_state:
    st.session_state.current_q_index = 0
if 'answers_matrix' not in st.session_state:
    st.session_state.answers_matrix = {}
if 'exam_result_data' not in st.session_state:
    st.session_state.exam_result_data = None

st.set_page_config(page_title="JAT_CBT Portal", page_icon="🅥", layout="wide", initial_sidebar_state="expanded")

# Parse incoming raw parameters for direct link sharing access
url_exam_id = st.query_params.get("exam_id")

def get_current_base_url():
    return "http://localhost:8501/"

def display_leaderboard():
    st.write("### 🏆 Global JAT Performance Leaderboard")
    with get_db_connection() as conn:
        leaderboard_df = pd.read_sql_query("""
            SELECT u.username as "Candidate Name", 
                   e.title as "Exam Component", 
                   s.percentage as "Score (%)", 
                   s.status as "Result Status",
                   s.completed_at as "Completion Date"
            FROM exam_sessions s
            JOIN users u ON s.user_id = u.id
            JOIN exams e ON s.exam_id = e.id
            ORDER BY s.percentage DESC, s.completed_at ASC
        """, conn)
    
    if leaderboard_df.empty:
        st.info("Leaderboard records are empty.")
    else:
        st.dataframe(leaderboard_df, use_container_width=True, hide_index=True)

# ==============================================================================
# 3. SIDEBAR NAVBAR AUTHENTICATION CHANNELS
# ==============================================================================
if not st.session_state.logged_in:
    st.title("🅥 JAT_CBT")
    st.caption("Jasper Automated Technologies | Premium High-Performance CBT Engine")
    
    st.sidebar.subheader("🅥 Navigation Menu")
    auth_mode = st.sidebar.radio("Go To:", ["Sign In Menu", "Register Account"])
    
    if auth_mode == "Sign In Menu":
        st.sidebar.write("---")
        st.sidebar.markdown("🔒 **Account Sign In**")
        login_user = st.sidebar.text_input("Username", key="login_user_input")
        login_pass = st.sidebar.text_input("Password", type="password", key="login_pass_input")
        
        if st.sidebar.button("Log In to Portal", use_container_width=True, type="primary"):
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (login_user, login_pass))
                account = cursor.fetchone()
                if account:
                    st.session_state.logged_in = True
                    st.session_state.user_id = account['id']
                    st.session_state.username = account['username']
                    st.session_state.user_role = account['role']
                    st.rerun()
                else:
                    st.sidebar.error("❌ Invalid Username or Password.")
                    
    elif auth_mode == "Register Account":
        st.sidebar.write("---")
        st.sidebar.markdown("📝 **Candidate Registration**")
        reg_user = st.sidebar.text_input("Choose Username", key="reg_user_input").strip()
        reg_pass = st.sidebar.text_input("Choose Password", type="password", key="reg_pass_input")
        reg_pass_conf = st.sidebar.text_input("Confirm Password", type="password", key="reg_pass_conf_input")
        
        if st.sidebar.button("Register New Profile", use_container_width=True, type="primary"):
            if not reg_user or not reg_pass:
                st.sidebar.error("❌ Registration fields cannot be left blank.")
            elif reg_pass != reg_pass_conf:
                st.sidebar.error("❌ Confirmation passwords do not match.")
            else:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')", (reg_user, reg_pass))
                        conn.commit()
                    st.sidebar.success("✅ Registered! Select 'Sign In Menu' above to log in.")
                except sqlite3.IntegrityError:
                    st.sidebar.error("❌ This username is already taken.")
                    
    st.markdown("""
    ### Welcome to the JAT Assessment Portal
    This computer-based testing platform belongs to **Jasper Automated Technologies**. 
    
    **How to navigate this portal:**
    1. **Look at the left sidebar** panel on your screen (already opened for you).
    2. Toggle between **'Sign In Menu'** or **'Register Account'** inside the navbar options.
    3. Enter your account credentials directly inside the navbar fields to log in.
    """)
    if url_exam_id:
        st.warning(f"🎯 Action Required: You used a direct link to take **Exam ID #{url_exam_id}**. Please authorize your account via the sidebar navbar to start writing immediately.")
    st.stop()

# --- SIDEBAR LOGOUT CONTROL ---
st.sidebar.write(f"👤 Active Profile: **{st.session_state.username}**")
st.sidebar.caption(f"Role Scope: {st.session_state.user_role.upper()}")
if st.sidebar.button("🚪 Exit & Log Out", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.user_role = ""
    st.session_state.exam_started = False
    st.session_state.exam_result_data = None
    for key in list(st.query_params.keys()):
        del st.query_params[key]
    st.rerun()

# ==============================================================================
# 4. VIEW CONTROLLER (EASY EVALUATE STATE ISOLATION)
# ==============================================================================

# SCENARIO A: DISPLAY ISOLATED COMPILATION RESULTS PAGE
if st.session_state.exam_result_data is not None:
    st.title("🅥 Assessment Evaluation Summary")
    res = st.session_state.exam_result_data
    
    if res['status'] == "PASSED":
        st.balloons()
        st.success("### 🎉 Congratulations! You Passed the Assessment Component.")
    else:
        st.snow()
        st.error("### 📝 Evaluation Concluded. Review your baseline framework marks metrics below.")
        
    col1, col2, col3 = st.columns(3)
    col1.metric("Calculated Grade Metric", f"{res['percentage']}%")
    col2.metric("Raw Score Breakdown", f"{res['score']} / {res['total_questions']}")
    col3.metric("JAT Evaluation Status", res['status'])
    
    st.write("---")
    if st.button("Return back to Workstation Hub Dashboard", type="primary", use_container_width=True):
        st.session_state.exam_result_data = None
        for key in list(st.query_params.keys()):
            del st.query_params[key]
        st.rerun()
    st.stop()

# SCENARIO B: ACTIVE RUNNING EXAM ENGINE (EASY EVALUATE PAGE LOOK)
if st.session_state.exam_started:
    active_exam_id = st.session_state.get('active_exam_id_lock')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams WHERE id = ?", (active_exam_id,))
        exam_metadata = cursor.fetchone()
        cursor.execute("SELECT * FROM questions WHERE exam_id = ? ORDER BY id ASC", (active_exam_id,))
        questions_array = [dict(row) for row in cursor.fetchall()]
        
    total_q = len(questions_array)
    
    if total_q == 0:
        st.error("Error: Container validation yielded 0 questions. Terminating session loop.")
        st.session_state.exam_started = False
        st.rerun()
        
    # Countdown Clock calculations
    elapsed = time.time() - st.session_state.start_time
    total_seconds = exam_metadata['duration_mins'] * 60
    remaining = total_seconds - elapsed
    
    time_out_trigger = False
    if remaining <= 0:
        time_out_trigger = True
        remaining = 0
        
    mins, secs = divmod(int(remaining), 60)
    st.sidebar.markdown(f"## ⏰ Time Remaining\n### `{mins:02d}:{secs:02d}`")
    st.sidebar.divider()
    
    # Live Response Progress Monitor Tracker
    st.sidebar.write("### 📊 Questions Tracker")
    answered_count = len(st.session_state.answers_matrix)
    st.sidebar.progress(answered_count / total_q if total_q > 0 else 0, text=f"{answered_count} of {total_q} Answered")
    
    # Render mini-grid checklist block mapping question nodes
    st.sidebar.write("#### Navigation Index Grid:")
    grid_cols = st.sidebar.columns(5)
    for index in range(total_q):
        col_slot = grid_cols[index % 5]
        is_answered = questions_array[index]['id'] in st.session_state.answers_matrix
        
        if index == st.session_state.current_q_index:
            marker = f"🔵 **{index+1}**"
        elif is_answered:
            marker = f"🟢 {index+1}"
        else:
            marker = f"⚪ {index+1}"
            
        if col_slot.button(marker, key=f"nav_grid_btn_{index}"):
            st.session_state.current_q_index = index
            st.rerun()
            
    # RENDER CURRENT SINGLE TARGET ITEM CARD
    st.title(f"📝 Active Module: {exam_metadata['title']}")
    current_idx = st.session_state.current_q_index
    current_q = questions_array[current_idx]
    
    st.write("---")
    st.subheader(f"Question {current_idx + 1} of {total_q}")
    st.markdown(f"#### {current_q['question_text']}")
    
    # Options array layout injection with custom default null index handling
    placeholder = "Choose an option..."
    options_pool = [placeholder, current_q['option_a'], current_q['option_b'], current_q['option_c'], current_q['option_d']]
    
    saved_selection = st.session_state.answers_matrix.get(current_q['id'], placeholder)
    
    try:
        default_index = options_pool.index(saved_selection) if saved_selection in options_pool else 0
    except ValueError:
        default_index = 0
        
    user_choice = st.radio(
        "Select your answer parameter entry variant:",
        options=options_pool,
        index=default_index,
        key=f"active_radio_node_{current_q['id']}",
        label_visibility="collapsed"
    )
    
    if user_choice != placeholder:
        st.session_state.answers_matrix[current_q['id']] = user_choice
    elif current_q['id'] in st.session_state.answers_matrix and user_choice == placeholder:
        del st.session_state.answers_matrix[current_q['id']]
    
    st.write("---")
    
    # Navigation Command Interface Buttons Strip
    nav_col1, nav_col2, nav_col3 = st.columns([2, 5, 2])
    
    if current_idx > 0:
        if nav_col1.button("⬅️ PREVIOUS QUESTION", use_container_width=True):
            st.session_state.current_q_index -= 1
            st.rerun()
            
    if current_idx < total_q - 1:
        if nav_col3.button("NEXT QUESTION ➡️", use_container_width=True, type="primary"):
            st.session_state.current_q_index += 1
            st.rerun()
    else:
        if nav_col3.button("📤 SUBMIT FINAL EXAM", use_container_width=True, type="primary") or time_out_trigger:
            correct_tally = 0
            
            for q in questions_array:
                candidate_selection = st.session_state.answers_matrix.get(q['id'], None)
                if candidate_selection == q['correct_option']:
                    correct_tally += 1
                    
            final_score_pct = round((correct_tally / total_q) * 100, 2)
            passed_status = "PASSED" if final_score_pct >= exam_metadata['pass_percentage'] else "FAILED"
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO exam_sessions (user_id, exam_id, score, total_questions, percentage, status, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (st.session_state.user_id, active_exam_id, correct_tally, total_q, final_score_pct, passed_status, timestamp_str))
                conn.commit()
                
            st.session_state.exam_result_data = {
                "score": correct_tally,
                "total_questions": total_q,
                "percentage": final_score_pct,
                "status": passed_status
            }
            st.session_state.exam_started = False
            st.session_state.start_time = None
            st.session_state.answers_matrix = {}
            st.session_state.current_q_index = 0
            if 'active_exam_id_lock' in st.session_state:
                del st.session_state.active_exam_id_lock
            st.rerun()
            
    time.sleep(1)
    st.rerun()

# ==============================================================================
# 5. CORE ADMINISTRATIVE DESK MAIN PAGE VIEW (Standard Dashboard View)
# ==============================================================================
st.title("🅥 JAT_CBT Dashboard")
st.caption("Jasper Automated Technologies | System Workspace Console")

if st.session_state.user_role == 'admin':
    st.markdown("## 🛠️ System Administrative Dashboard")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Create Exam Setup", 
        "Upload Questions Sheet", 
        "Admin Account Management", 
        "System Analytics & Share Links",
        "Manage Registered Users"
    ])
    
    with tab1:
        st.subheader("Configure New Examination Parameters")
        with st.form("exam_config_form"):
            title = st.text_input("Exam Title")
            duration = st.number_input("Duration (Minutes)", min_value=1, value=30)
            pass_pct = st.number_input("Passing Threshold Percentage (%)", min_value=1, max_value=100, value=50)
            exam_date = st.date_input("Scheduled Test Date", value=datetime.today())
            is_active = st.checkbox("Activate Instantly", value=True)
            
            if st.form_submit_button("Deploy Exam Matrix"):
                if title:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO exams (title, duration_mins, pass_percentage, exam_date, is_active) VALUES (?, ?, ?, ?, ?)",
                            (title, duration, pass_pct, str(exam_date), 1 if is_active else 0)
                        )
                        conn.commit()
                    st.success(f"Successfully configured and scheduled '{title}'!")
                    st.rerun()
                else:
                    st.error("Exam Title field cannot be left blank.")

    with tab2:
        st.subheader("Bulk Data Pipeline (CSV / Excel Support)")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM exams")
            exams_list = cursor.fetchall()
            
        if not exams_list:
            st.info("Please build an exam container configuration in Tab 1 before uploading item sheets.")
        else:
            exam_options = {e['title']: e['id'] for e in exams_list}
            target_exam = st.selectbox("Select Target Examination Container", options=list(exam_options.keys()))
            
            uploaded_file = st.file_uploader("Drop Question Sheet Matrix here", type=["csv", "xlsx", "xls"])
            
            if uploaded_file is not None:
                try:
                    file_ext = os.path.splitext(uploaded_file.name)[-1].lower()
                    if file_ext == '.csv':
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                        
                    df.columns = [str(c).strip() for c in df.columns]
                    required_cols = ["MCQ", "questions", "Options", "Correctanswer"]
                    
                    if not all(col in df.columns for col in required_cols):
                        st.error(f"Invalid layout columns! Headers must be explicitly named: {required_cols}")
                    else:
                        st.success("File Structural Integrity Verified.")
                        
                        if st.button("Parse and Push to Database Matrix", type="primary"):
                            exam_id = exam_options[target_exam]
                            uploaded_count = 0
                            
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                for index, row in df.iterrows():
                                    raw_opts = str(row['Options']).split('|')
                                    if len(raw_opts) < 4:
                                        continue
                                    
                                    cursor.execute("""
                                        INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        exam_id, 
                                        str(row['questions']).strip(),
                                        raw_opts[0].strip(), raw_opts[1].strip(), raw_opts[2].strip(), raw_opts[3].strip(),
                                        str(row['Correctanswer']).strip()
                                    ))
                                    uploaded_count += 1
                                conn.commit()
                            st.success(f"Pipeline Sync Complete! Injected {uploaded_count} questions.")
                except Exception as e:
                    st.error(f"Error executing file translation parsing sequence: {e}")

    with tab3:
        st.subheader("Forced Admin Account Enrolment Console")
        with st.form("admin_user_enroll_form"):
            new_user = st.text_input("New Core Account Username")
            new_pass = st.text_input("Assigned Profile Password")
            new_role = st.selectbox("Role Authorization Context", options=["user", "admin"])
            
            if st.form_submit_button("Create Custom Account Profile"):
                if new_user and new_pass:
                    try:
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (new_user, new_pass, new_role))
                            conn.commit()
                        st.success(f"Profile account '{new_user}' registered successfully.")
                    except sqlite3.IntegrityError:
                        st.error("Username index duplicate error.")

    with tab4:
        st.subheader("🔗 Public Examination Share Desk")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM exams")
            shareable_exams = cursor.fetchall()
            
        if shareable_exams:
            st.info("Copy any explicit exam link code below to distribute to candidates:")
            base_app_url = get_current_base_url()
            for row in shareable_exams:
                generated_link = f"{base_app_url}?exam_id={row['id']}"
                st.markdown(f"🔹 **{row['title']}** (Exam ID: {row['id']})")
                st.code(generated_link, language="markdown")
        else:
            st.info("No exam entries are currently available to yield link keys.")
                
        st.divider()
        display_leaderboard()
        st.divider()
            
        st.write("### Recorded Test Sessions Audit Matrix")
        with get_db_connection() as conn:
            logs = pd.read_sql_query("""
                SELECT u.username, e.title AS exam_title, s.score, s.total_questions, s.percentage, s.status, s.completed_at 
                FROM exam_sessions s
                JOIN users u ON s.user_id = u.id
                JOIN exams e ON s.exam_id = e.id
                ORDER BY s.completed_at DESC
            """, conn)
            
        if not logs.empty:
            st.dataframe(logs, use_container_width=True)

    with tab5:
        st.subheader("👤 User Account Management Registry")
        with get_db_connection() as conn:
            users_query = pd.read_sql_query("SELECT id, username, role FROM users ORDER BY id DESC", conn)
        
        if users_query.empty:
            st.info("No registered users found inside database.")
        else:
            for idx, user_row in users_query.iterrows():
                u_id = user_row['id']
                u_name = user_row['username']
                u_role = user_row['role']
                
                if u_name == st.session_state.username:
                    st.markdown(f"🔒 **{u_name}** ({u_role.upper()}) — *Current Active Session Profile*")
                else:
                    col_user_info, col_user_action = st.columns([4, 1])
                    col_user_info.markdown(f"👤 **{u_name}** — Access Level Scope: `{u_role.upper()}`")
                    if col_user_action.button(f"🗑️ Delete Account", key=f"del_user_{u_id}", type="secondary"):
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM users WHERE id = ?", (u_id,))
                            conn.commit()
                        st.success(f"Successfully deleted user account record: {u_name}")
                        st.rerun()
                st.write("---")

    st.write("---")

# ==============================================================================
# 6. STANDARD USER STATION DASHBOARD & PERFORMANCE HISTORY VIEW
# ==============================================================================
st.markdown("## 📊 Candidate Workstation Hub")

user_tab1, user_tab2 = st.tabs(["🎯 Take Active Examinations", "📜 My Personal Exam History & Performance Analytics"])

with user_tab1:
    active_exam_id = None
    if url_exam_id:
        try:
            active_exam_id = int(url_exam_id)
        except ValueError:
            pass
    else:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM exams WHERE is_active = 1")
            active_exams = cursor.fetchall()
            
        if not active_exams:
            st.info("There are currently no active routes to open workspace assessments.")
        else:
            exam_selector = st.selectbox("Select the test you want to write or evaluate:", options=[e['title'] for e in active_exams])
            for e in active_exams:
                if e['title'] == exam_selector:
                    active_exam_id = e['id']

    if active_exam_id:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM exams WHERE id = ?", (active_exam_id,))
            exam_metadata = cursor.fetchone()
            
            if exam_metadata:
                cursor.execute("SELECT COUNT(*) as qcount FROM questions WHERE exam_id = ?", (active_exam_id,))
                q_count_check = cursor.fetchone()['qcount']
                
                # Fetch all previous attempts for this specific exam container
                cursor.execute("SELECT * FROM exam_sessions WHERE user_id = ? AND exam_id = ? ORDER BY completed_at ASC", 
                               (st.session_state.user_id, active_exam_id))
                attempts_history = cursor.fetchall()
                attempts_count = len(attempts_history)

                if attempts_count >= 5:
                    st.error(f"🛑 Attempt Ceiling Reached! You have completed the maximum limit of 5 attempts for '{exam_metadata['title']}'.")
                    
                    # Group past records into a tidy visual block inside the warning frame
                    st.write("**Your Past Attempt Track Records:**")
                    for idx, past_run in enumerate(attempts_history):
                        st.markdown(f"🔹 **Attempt #{idx+1}:** Grade Score: `{past_run['percentage']}%` — status: **{past_run['status']}** (Completed: *{past_run['completed_at']}*)")
                elif q_count_check == 0:
                    st.warning(f"⚠️ Selected setup container '{exam_metadata['title']}' contains 0 questions.")
                else:
                    st.write(f"### 🚀 Ready to Launch: **{exam_metadata['title']}**")
                    st.info(f"⏱️ **Time Limit:** {exam_metadata['duration_mins']} Minutes | 🎯 **Required Pass Mark:** {exam_metadata['pass_percentage']}% | 📋 **Total Questions:** {q_count_check}")
                    
                    # Display current token count budget clear visibility parameters
                    if attempts_count > 0:
                        st.warning(f"ℹ️ Attention: You have already used `{attempts_count}` of your 5 maximum limit allocated attempts for this component module.")
                    else:
                        st.success("ℹ️ Clean Ledger Slate: This will register as your 1st configuration assessment attempt.")

                    if st.button("🔥 START RUNNING ASSESSMENT NOW", type="primary", use_container_width=True):
                        st.session_state.exam_started = True
                        st.session_state.start_time = time.time()
                        st.session_state.active_exam_id_lock = active_exam_id
                        st.session_state.current_q_index = 0
                        st.session_state.answers_matrix = {}
                        st.rerun()

with user_tab2:
    st.subheader(f"Performance Review Matrix for {st.session_state.username}")
    
    with get_db_connection() as conn:
        personal_history_df = pd.read_sql_query("""
            SELECT e.title AS "Exam Title", 
                   s.score AS "Raw Score", 
                   s.total_questions AS "Total Questions", 
                   s.percentage AS "Score Percentage (%)", 
                   s.status AS "Evaluation Status", 
                   s.completed_at AS "Completion Time"
            FROM exam_sessions s
            JOIN exams e ON s.exam_id = e.id
            WHERE s.user_id = ?
            ORDER BY s.completed_at ASC
        """, conn, params=(st.session_state.user_id,))
        
    if personal_history_df.empty:
        st.info("You haven't completed any computer-based assessments yet.")
    else:
        st.markdown("### 📈 Trajectory Analytics (Last 5 Exams Progress Trend)")
        
        trajectory_df = personal_history_df.tail(5).copy()
        trajectory_df['Attempt Index'] = range(1, len(trajectory_df) + 1)
        trajectory_df['Label'] = trajectory_df['Attempt Index'].astype(str) + ". " + trajectory_df['Exam Title']
        
        chart_data = trajectory_df[['Label', 'Score Percentage (%)']].set_index('Label')
        st.line_chart(chart_data)
        
        st.markdown("### 📋 Historic Transcripts Record Log")
        st.dataframe(personal_history_df.iloc[::-1], use_container_width=True, hide_index=True)
