# database.py

import sqlite3
import os

DB_PATH = 'attendance.db'

def get_db_connection():
    """Returns a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY,
        name TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance(
        student_id INTEGER,
        name TEXT,
        date TEXT,
        time TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database Initialized Successfully.")

def get_all_students():
    """Retrieves all registered students from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY id ASC")
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return students

def get_student_by_id(student_id):
    """Retrieves a specific student by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_student(student_id, name):
    """Inserts a new student into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO students (id, name) VALUES (?, ?)", (student_id, name))
        conn.commit()
        success = True
    except sqlite3.Error as e:
        print(f"Error adding student: {e}")
        success = False
    finally:
        conn.close()
    return success

def mark_attendance(student_id, name, date, time):
    """Logs a student's attendance in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO attendance (student_id, name, date, time) VALUES (?, ?, ?, ?)",
                       (student_id, name, date, time))
        conn.commit()
        success = True
    except sqlite3.Error as e:
        print(f"Error logging attendance: {e}")
        success = False
    finally:
        conn.close()
    return success

def get_attendance_logs(limit=100):
    """Retrieves all attendance logs from the database, newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance ORDER BY date DESC, time DESC LIMIT ?", (limit,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs

if __name__ == '__main__':
    init_db()