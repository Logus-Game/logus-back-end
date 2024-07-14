from flask import Flask, request, jsonify
import mysql.connector
from dotenv import load_dotenv
import os


load_dotenv()

db_connection = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_DATABASE")
)

app = Flask(__name__)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    senha = data['senha']

    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE email = %s AND senha = %s", (email, senha))
    user = cursor.fetchone()
    cursor.close()

    if user:
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    app.run(debug=True)