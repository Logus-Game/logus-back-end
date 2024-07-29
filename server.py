from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
from dotenv import load_dotenv
from flask_cors import CORS
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

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE email = %s AND senha = %s order by id desc", (email, password))
    user = cursor.fetchone()
    cursor.close()

    if user:
        access_token = create_access_token(identity=user['id'])
        response = make_response(jsonify(access_token=access_token), 200)
        response.set_cookie('token', access_token, httponly=True, secure=False, samesite='Lax')

        
        return response
    else:
        return response


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200
    

@app.route('/quests', methods=['GET'])
@jwt_required()
def quests():
    id_user = get_jwt_identity()
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(f"select a.*,q.* from usuario u join usuario_has_quest a on u.id = a.id_usuario join quest q on q.id_quest = a.id_quest where id_usuario = {id_user}")
    quests = cursor.fetchall()
    cursor.close()

    if quests:
        return jsonify({'message': 'sucesso', 'quests': quests}), 200
        
    else:
        return jsonify(), 204
    
if __name__ == '__main__':
    app.run(debug=True)