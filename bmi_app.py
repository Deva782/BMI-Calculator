import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Tuple
import hashlib

# Database setup
def init_database():
    """Initialize SQLite database with users and BMI records tables"""
    with sqlite3.connect('bmi_data.db') as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Create BMI records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bmi_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                weight REAL NOT NULL,
                height REAL NOT NULL,
                bmi REAL NOT NULL,
                category TEXT NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username: str, password: str) -> bool:
    """Create a new user account"""
    try:
        with sqlite3.connect('bmi_data.db') as conn:
            cursor = conn.cursor()
            password_hash = hash_password(password)
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                          (username, password_hash))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username: str, password: str) -> int:
    """Authenticate user and return user ID if successful"""
    with sqlite3.connect('bmi_data.db') as conn:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute('SELECT id FROM users WHERE username = ? AND password_hash = ?', 
                      (username, password_hash))
        result = cursor.fetchone()
    return result[0] if result else None

def calculate_bmi(weight: float, height: float) -> Tuple[float, str]:
    """Calculate BMI and return BMI value and category"""
    if height <= 0:
        return 0.0, "Invalid height"
    bmi = weight / (height ** 2)
    if bmi < 18.5:
        category = "Underweight"
    elif 18.5 <= bmi < 25:
        category = "Normal weight"
    elif 25 <= bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    return round(bmi, 2), category

def save_bmi_record(user_id: int, weight: float, height: float, bmi: float, category: str):
    """Save BMI record to database"""
    with sqlite3.connect('bmi_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bmi_records (user_id, weight, height, bmi, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, weight, height, bmi, category))
        conn.commit()

def get_user_bmi_history(user_id: int) -> pd.DataFrame:
    """Get BMI history for a specific user"""
    with sqlite3.connect('bmi_data.db') as conn:
        df = pd.read_sql_query('''
            SELECT weight, height, bmi, category, recorded_at
            FROM bmi_records
            WHERE user_id = ?
            ORDER BY recorded_at DESC
        ''', conn, params=(user_id,))
    if not df.empty:
        df['recorded_at'] = pd.to_datetime(df['recorded_at'])
    return df

def get_bmi_statistics(df: pd.DataFrame) -> Dict:
    """Calculate BMI statistics"""
    if df.empty:
        return {}
    stats = {
        'total_records': len(df),
        'current_bmi': df.iloc[0]['bmi'],
        'average_bmi': df['bmi'].mean(),
        'min_bmi': df['bmi'].min(),
        'max_bmi': df['bmi'].max(),
        'weight_change': df.iloc[0]['weight'] - df.iloc[-1]['weight'] if len(df) > 1 else 0,
        'bmi_trend': (
            'Increasing' if len(df) > 1 and df.iloc[0]['bmi'] < df.iloc[-1]['bmi']
            else 'Decreasing' if len(df) > 1 and df.iloc[0]['bmi'] > df.iloc[-1]['bmi']
            else 'No trend'
        )
    }
    return stats

def create_bmi_trend_chart(df: pd.DataFrame):
    """Create BMI trend chart using Plotly"""
    if df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['recorded_at'],
        y=df['bmi'],
        mode='lines+markers',
        name='BMI',
        line=dict(color='blue', width=2),
        marker=dict(size=8)
    ))
    fig.add_hline(y=18.5, line_dash="dash", line_color="lightblue", annotation_text="Underweight")
    fig.add_hline(y=25, line_dash="dash", line_color="green", annotation_text="Normal")
    fig.add_hline(y=30, line_dash="dash", line_color="orange", annotation_text="Overweight")
    fig.update_layout(
        title="BMI Trend Over Time",
        xaxis_title="Date",
        yaxis_title="BMI",
        hovermode='x unified',
        showlegend=True
    )
    return fig

def create_weight_trend_chart(df: pd.DataFrame):
    """Create weight trend chart using Plotly"""
    if df.empty:
        return None
    fig = px.line(df, x='recorded_at', y='weight', 
                  title='Weight Trend Over Time',
                  markers=True)
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Weight (kg)",
        hovermode='x unified'
    )
    return fig

def create_bmi_distribution_chart(df: pd.DataFrame):
    """Create BMI category distribution chart"""
    if df.empty:
        return None
    category_counts = df['category'].value_counts()
    fig = px.pie(values=category_counts.values, 
                 names=category_counts.index,
                 title='BMI Category Distribution')
    return fig

# Streamlit App
def main():
    st.set_page_config(
        page_title="BMI Calculator & Tracker",
        page_icon="⚖️",
        layout="wide"
    )
    init_database()
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    st.title("⚖️ BMI Calculator & Health Tracker")
    if st.session_state.user_id is None:
        st.subheader("🔐 Login or Register")
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                login_button = st.form_submit_button("Login")
                if login_button:
                    if username and password:
                        user_id = authenticate_user(username, password)
                        if user_id:
                            st.session_state.user_id = user_id
                            st.session_state.username = username
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    else:
                        st.error("Please enter both username and password")
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Choose Username")
                new_password = st.text_input("Choose Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                register_button = st.form_submit_button("Register")
                if register_button:
                    if new_username and new_password and confirm_password:
                        if new_password == confirm_password:
                            if create_user(new_username, new_password):
                                st.success("Account created successfully! Please login.")
                            else:
                                st.error("Username already exists")
                        else:
                            st.error("Passwords do not match")
                    else:
                        st.error("Please fill in all fields")
    else:
        st.sidebar.title(f"Welcome, {st.session_state.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
        page = st.sidebar.selectbox("Navigate", 
                                   ["BMI Calculator", "Historical Data", "Trend Analysis", "Statistics"])
        if page == "BMI Calculator":
            st.subheader("📊 BMI Calculator")
            col1, col2 = st.columns(2)
            with col1:
                weight = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, 
                                       value=70.0, step=0.1)
                height = st.number_input("Height (m)", min_value=0.5, max_value=3.0, 
                                       value=1.70, step=0.01)
                if st.button("Calculate BMI"):
                    bmi, category = calculate_bmi(weight, height)
                    if category == "Invalid height":
                        st.error("Height must be greater than zero.")
                    else:
                        st.success(f"Your BMI is: **{bmi}**")
                        st.info(f"Category: **{category}**")
                        save_bmi_record(st.session_state.user_id, weight, height, bmi, category)
                        st.success("BMI record saved!")
            with col2:
                st.subheader("BMI Categories")
                st.write("- **Underweight**: BMI < 18.5")
                st.write("- **Normal weight**: 18.5 ≤ BMI < 25")
                st.write("- **Overweight**: 25 ≤ BMI < 30")
                st.write("- **Obese**: BMI ≥ 30")
        elif page == "Historical Data":
            st.subheader("📈 Historical BMI Data")
            df = get_user_bmi_history(st.session_state.user_id)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"bmi_history_{st.session_state.username}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No BMI records found. Start by calculating your BMI!")
        elif page == "Trend Analysis":
            st.subheader("📊 BMI Trend Analysis")
            df = get_user_bmi_history(st.session_state.user_id)
            if not df.empty:
                fig_bmi = create_bmi_trend_chart(df)
                if fig_bmi:
                    st.plotly_chart(fig_bmi, use_container_width=True)
                fig_weight = create_weight_trend_chart(df)
                if fig_weight:
                    st.plotly_chart(fig_weight, use_container_width=True)
                fig_dist = create_bmi_distribution_chart(df)
                if fig_dist:
                    st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.info("No data available for trend analysis. Add some BMI records first!")
        elif page == "Statistics":
            st.subheader("📋 BMI Statistics")
            df = get_user_bmi_history(st.session_state.user_id)
            if not df.empty:
                stats = get_bmi_statistics(df)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Records", stats['total_records'])
                    st.metric("Current BMI", f"{stats['current_bmi']:.2f}")
                with col2:
                    st.metric("Average BMI", f"{stats['average_bmi']:.2f}")
                    st.metric("BMI Range", f"{stats['min_bmi']:.2f} - {stats['max_bmi']:.2f}")
                with col3:
                    st.metric("Weight Change", f"{stats['weight_change']:.1f} kg")
                    st.metric("Trend", stats['bmi_trend'])
                st.subheader("Recent Records")
                recent_df = df.head(5)
                st.dataframe(recent_df, use_container_width=True)
            else:
                st.info("No statistics available. Start tracking your BMI!")

if __name__ == "__main__":
    main()