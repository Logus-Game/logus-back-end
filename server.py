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
    cursor.execute("SELECT * FROM usuario WHERE email = %s AND senha = %s order by id_usuario desc", (email, password))
    user = cursor.fetchone()
    cursor.close()

    if user:
        access_token = create_access_token(identity=[user['id_usuario'], user['nivel'], user['id_curso']])
        response = make_response(jsonify({'access_token':access_token, 'nivel': user['nivel']}), 200)
        response.set_cookie('token', access_token, httponly=True, secure=False, samesite='Lax')
        return response
    else:
        return jsonify({'message':'Usuario ou senha incorretos'})


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200
    

@app.route('/user_quests', methods=['GET'])
@jwt_required()
def user_quests():
    id_user = get_jwt_identity()[0]
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(f"select a.*,q.* from usuario u join usuario_has_quest a on u.id_usuario = a.id_usuario join quest q on q.id_quest = a.id_quest where a.id_usuario = {id_user}")
    quests = cursor.fetchall()
    cursor.close()
    

    if quests:
        return jsonify({'message': 'sucesso', 'quests': quests}), 200
        
    else:
        return jsonify(), 204

@app.route('/quests/status/<int:quest_id>', methods=['PATCH'])
@jwt_required()
def updateQuestStatus(quest_id):
    try:
        id_user = get_jwt_identity()[0]
        data = request.json
        status = data.get('status', None)
        desc = data.get('desc', None)
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(f'update usuario_has_quest set estado="{status}", descricao_conclusao="{desc}" where id_quest={quest_id} and id_usuario={id_user}')
        db_connection.commit()

        return jsonify({"message": "quest updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500

@app.route('/quests', methods=['GET'])
@jwt_required()
def course_quests():
    cursor = db_connection.cursor(dictionary=True)
    id_curso = get_jwt_identity()[2]
    cursor.execute(f"select * from curso c join quest q on q.id_curso = c.id where c.id={id_curso};")
    quests = cursor.fetchall()
    cursor.close()
    if quests:
        return jsonify({'message': 'sucesso', 'quests': quests}), 200
        
    else:
        return jsonify(), 204

@app.route('/user-data', methods=['GET'])
@jwt_required()
def userData():
    id_user = get_jwt_identity()[0]
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(f"select * from usuario where id_usuario={id_user}")
    data = cursor.fetchone()
    cursor.close()

    if data:
        return jsonify({'message': 'sucesso', 'info': data}), 200
    else:
        return jsonify(), 204
    

@app.route('/players', methods=['GET'])
@jwt_required()
def players():
    nivel = get_jwt_identity()[1]
    if nivel != 'AA':
        return jsonify({'message': 'Acesso negado', 'info': ''}), 403
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(f"select * from usuario where nivel != 'AA'")
    data = cursor.fetchall()
    cursor.close()

    if data:
        return jsonify({'message': 'sucesso', 'info': data}), 200
    else:
        return jsonify(), 204


    
if __name__ == '__main__':
    app.run(debug=True)