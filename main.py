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
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            )
        """)
        
        # FORCE MASTER ADMIN CREDENTIALS
        cursor.execute("SELECT * FROM users WHERE username = 'Jasper390'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('Jasper390', 'JasperJ23', 'admin')")
            
        conn.commit()

init_db()

# ==============================================================================
# 2. SESSION STATE & UI CONFIGISTRATION
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.user_role = ""
if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
    st.session_state.start_time = None

st.set_page_config(page_title="JAT_CBT Portal", page_icon="🅥", layout="wide")
st.title("🅥 JAT_CBT")
st.caption("Jasper Automated Technologies | Premium High-Performance CBT Engine")

# Safe modern URL parameters parsing
url_exam_id = st.query_params.get("exam_id")

# ==============================================================================
# 3. AUTHENTICATION GATEWAY
# ==============================================================================
if not st.session_state.logged_in:
    col_info, col_action = st.columns([2, 1])
    
    with col_info:
        st.markdown("""
        ### Welcome to the JAT Assessment Portal
        This computer-based testing platform belongs to **Jasper Automated Technologies**. 
        
        **How to navigate this portal:**
        1. **Look at the left sidebar** panel on your screen.
        2. Select **'Sign In'** if you already have an account profile.
        3. Select **'Create Candidate Account'** if you are a new applicant registering for the first time.
        4. Once you log in successfully, your dynamic scheduled test timeline dashboard will load up instantly right here.
        """)
        if url_exam_id:
            st.warning(f"🎯 Action Required: You used a direct link to take **Exam ID #{url_exam_id}**. Please authorize your account via the sidebar to start writing immediately.")
            
    with col_action:
        st.write("#### 🔐 Access Panel Quick-Switch")
        auth_mode = st.radio("Choose Action:", ["Sign In", "Create Candidate Account"], label_visibility="collapsed")
    
    if auth_mode == "Sign In":
        st.sidebar.subheader("🔒 Account Sign In")
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
                    st.sidebar.error("❌ Invalid Username or Password layout match.")
                    
    elif auth_mode == "Create Candidate Account":
        st.sidebar.subheader("📝 New Candidate Sign Up")
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
                    st.sidebar.success("✅ Account registered! Choose 'Sign In' to log in.")
                except sqlite3.IntegrityError:
                    st.sidebar.error("❌ This username is already taken.")
    st.stop()

# --- GLOBAL SIDEBAR DISCONNECT CONTROL ---
st.sidebar.write(f"👤 Active Profile: **{st.session_state.username}**")
st.sidebar.caption(f"Role Scope: {st.session_state.user_role.upper()}")
if st.sidebar.button("🚪 Exit & Log Out", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.user_role = ""
    st.session_state.exam_started = False
    for key in list(st.query_params.keys()):
        del st.query_params[key]
    st.rerun()

# --- SHARED PERFORMANCE LEADERBOARD DISPLAY ---
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
# 4. ADMINISTRATIVE WORKSPACE PANEL
# ==============================================================================
if st.session_state.user_role == 'admin':
    tab1, tab2, tab3, tab4 = st.tabs(["Create Exam Setup", "Upload Questions Sheet", "Admin Account Management", "System Analytics & Leaderboard"])
    
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
                        
                    df.columns = [c.strip() for c in df.columns]
                    required_cols = ["MCQ", "questions", "Options", "Correctanswer"]
                    
                    if not all(col in df.columns for col in required_cols):
                        st.error(f"Invalid layout columns! Headers must be explicitly named: {required_cols}")
                    else:
                        st.write("File Structural Integrity Verified.")
                        
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
        st.subheader("Global Platform Metrics & Shortcuts")
        
        if 'exam_options' in locals() and exam_options:
            st.write("### Generated Candidate Link Manifest")
            for title, e_id in exam_options.items():
                link = f"http://localhost:8501/?exam_id={e_id}"
                st.code(link, language="markdown")
                
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

# ==============================================================================
# 5. CANDIDATE EXAMINATION INTERFACE & TEST LOOP
# ==============================================================================
else:
    if not st.session_state.exam_started:
        st.markdown("""
        ### 📊 Candidate Command Center
        Welcome back, candidate! Below you will find your **Upcoming Examination Track Calendar**. 
        """)
        
        st.write("#### 📅 Upcoming Examinations Schedule")
        with get_db_connection() as conn:
            upcoming_df = pd.read_sql_query("""
                SELECT title as "Assessment Module", 
                       exam_date as "Scheduled Date", 
                       duration_mins as "Time Allowed (Mins)",
                       pass_percentage as "Passing Grade Minimum (%)"
                FROM exams 
                WHERE is_active = 1
                ORDER BY exam_date ASC
        """, conn)
            
        if upcoming_df.empty:
            st.info("No testing parameters are scheduled inside the upcoming track calendar timeline right now.")
        else:
            st.dataframe(upcoming_df, use_container_width=True, hide_index=True)
            
        st.divider()
    
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
            st.stop()
        elif not st.session_state.exam_started:
            st.write("#### 📝 Choose Your Assessment Module Below")
            exam_selector = st.selectbox("Click here to select the test you want to write:", options=[e['title'] for e in active_exams])
            for e in active_exams:
                if e['title'] == exam_selector:
                    active_exam_id = e['id']
        else:
            if 'active_exam_id_lock' in st.session_state:
                active_exam_id = st.session_state.active_exam_id_lock

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exams WHERE id = ?", (active_exam_id,))
        exam_metadata = cursor.fetchone()
        
        cursor.execute("SELECT * FROM questions WHERE exam_id = ?", (active_exam_id,))
        questions_array = cursor.fetchall()
        
        cursor.execute("SELECT * FROM exam_sessions WHERE user_id = ? AND exam_id = ?", (st.session_state.user_id, active_exam_id))
        previous_attempt = cursor.fetchone()

    if previous_attempt:
        st.error(f"🛑 Profile registry confirms you have already completed your evaluation for '{exam_metadata['title']}'.")
        st.metric(label="Retained Grade Result", value=f"{previous_attempt['percentage']}%", delta=previous_attempt['status'])
        st.stop()

    if not questions_array:
        st.warning(f"⚠️ Selected setup container '{exam_metadata['title']}' contains 0 questions.")
        st.stop()

    if not st.session_state.exam_started:
        st.write(f"### 🚀 Launching: **{exam_metadata['title']}**")
        st.info(f"⏱️ **Time Limit:** {exam_metadata['duration_mins']} Minutes | 🎯 **Required Pass Mark:** {exam_metadata['pass_percentage']}%")
        
        if st.button("🔥 START EXAM NOW", type="primary", use_container_width=True):
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.session_state.active_exam_id_lock = active_exam_id
            st.rerun()

    else:
        elapsed = time.time() - st.session_state.start_time
        total_seconds = exam_metadata['duration_mins'] * 60
        remaining = total_seconds - elapsed
        
        if remaining <= 0:
            st.error("⏰ Allocation window expired! Automatic compilation loop triggered.")
            remaining = 0
            time_out_trigger = True
        else:
            time_out_trigger = False
            mins, secs = divmod(int(remaining), 60)
            st.sidebar.markdown(f"## ⏰ Time Remaining\n### `{mins:02d}:{secs:02d}`")
                
        st.write(f"### 📝 Running Module: {exam_metadata['title']}")
        st.divider()
        
        candidate_answers = {}
        for idx, q in enumerate(questions_array):
            st.write(f"**Question {idx + 1}:** {q['question_text']}")
            options_choices = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
            
            selected_radio = st.radio(
                f"Choose parameter for question #{q['id']}",
                options=options_choices,
                key=f"q_radio_{q['id']}",
                label_visibility="collapsed"
            )
            candidate_answers[q['id']] = selected_radio

        if st.button("📤 SUBMIT COMPLETED EXAM", type="primary", use_container_width=True) or time_out_trigger:
            correct_tally = 0
            total_count = len(questions_array)
            
            for q in questions_array:
                user_ans = candidate_answers.get(q['id'])
                if user_ans == q['correct_option']:
                    correct_tally += 1
                    
            final_score_pct = round((correct_tally / total_count) * 100, 2)
            passed_status = "PASSED" if final_score_pct >= exam_metadata['pass_percentage'] else "FAILED"
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO exam_sessions (user_id, exam_id, score, total_questions, percentage, status, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (st.session_state.user_id, active_exam_id, correct_tally, total_count, final_score_pct, passed_status, timestamp_str))
                conn.commit()
                
            st.session_state.exam_started = False
            st.session_state.start_time = None
            if 'active_exam_id_lock' in st.session_state:
                del st.session_state.active_exam_id_lock
            
            st.balloons() if passed_status == "PASSED" else st.snow()
            st.success("### Assessment Terminated and Evaluated Successfully!")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Calculated Grade Metric", f"{final_score_pct}%")
            col2.metric("Raw Score Breakdown", f"{correct_tally} / {total_count}")
            col3.metric("JAT Evaluation Result", passed_status)
            
            if st.button("Return to Workstation Hub", use_container_width=True):
                for key in list(st.query_params.keys()):
                    del st.query_params[key]
                st.rerun()
            st.stop()
            
        time.sleep(1)
        st.rerun()
