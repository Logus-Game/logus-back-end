from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
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
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET')
jwt = JWTManager(app)

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
        access_token = create_access_token(identity=user['id'])
        response = make_response(jsonify(access_token=access_token), 200)
        response.set_cookie('token', access_token, httponly=True, secure=True)
        
        return jsonify({'message': 'Login successful','token': access_token}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200
    
@app.route('/quests', methods=['POST'])
def quests():
    data = request.get_json()
    id_user = data['id']
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE email = %s AND senha = %s", (email, senha))
    user = cursor.fetchone()
    cursor.close()

if __name__ == '__main__':
    app.run(debug=True)