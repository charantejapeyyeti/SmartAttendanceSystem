# registration.py

import database

# Initialize database to make sure tables exist
database.init_db()

try:
    student_id = int(input("Enter ID: "))
    name = input("Enter Name: ").strip()
    
    if not name:
        print("Error: Name cannot be empty.")
    else:
        if database.add_student(student_id, name):
            print(f"Student '{name}' with ID {student_id} added successfully.")
        else:
            print("Failed to add student to database.")
except ValueError:
    print("Error: Student ID must be an integer.")