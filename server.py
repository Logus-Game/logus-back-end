from flask import Flask, request, jsonify, make_response 
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql.connector
from dotenv import load_dotenv
from flask_cors import CORS
import os
import json  # << ADICIONADO
from werkzeug.utils import secure_filename


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
    db_connection.autocommit = True
    cursor = db_connection.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT * FROM usuario WHERE email = %s AND senha = %s order by id_usuario desc", (email, password))
    user = cursor.fetchone()
    cursor.close()

    if user:
        access_token = create_access_token(identity=json.dumps([user['id_usuario'], user['nivel'], user['id_curso']]))  # << AJUSTADO
        response = make_response(jsonify({'access_token': access_token, 'nivel': user['nivel']}), 200)
        response.set_cookie('token', access_token, httponly=True, secure=False, samesite='Lax')
        return response
    else:
        return jsonify({'message': 'Usuario ou senha incorretos'}), 401


@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    user_data = json.loads(get_jwt_identity())  # << AJUSTADO
    return jsonify(logged_in_as=user_data), 200


@app.route('/user_quests', methods=['GET'])
@jwt_required()
def user_quests():
    user_data = json.loads(get_jwt_identity())  # << AJUSTADO
    id_user = user_data[0]
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(f"select a.*,q.* from usuario u join usuario_has_quest a on u.id_usuario = a.id_usuario join quest q on q.id_quest = a.id_quest where a.id_usuario = {id_user}")
    quests = cursor.fetchall()
    cursor.close()

    if quests:
        return jsonify({'message': 'sucesso', 'quests': quests}), 200
    else:
        return jsonify(), 204


# @app.route('/quests/status/<int:quest_id>', methods=['PATCH'])
# @jwt_required()
# def updateQuestStatus(quest_id):
#     try:
#         user_data = json.loads(get_jwt_identity())  # << AJUSTADO
#         id_user = user_data[0]
#         data = request.json
#         status = data.get('status', None)
#         desc = data.get('desc', None)
#         cursor = db_connection.cursor(dictionary=True)
#         cursor.execute(f'update usuario_has_quest set estado="{status}", descricao_conclusao="{desc}" where id_quest={quest_id} and id_usuario={id_user}')
#         db_connection.commit()

#         return jsonify({"message": "quest updated successfully"}), 200
#     except Exception as e:
#         print(e)
#         return jsonify({"error": f"{e}"}), 500

UPLOAD_FOLDER = './uploads'  # Defina o diretório onde os arquivos serão salvos

# Verifique se o diretório de uploads existe, se não, crie-o
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/quests/status/<int:quest_id>', methods=['PATCH'])
@jwt_required()
def submitQuestCompletion(quest_id):
    try:
        user_data = json.loads(get_jwt_identity())
        id_user = user_data[0]

        desc = request.form.get('desc')
        prova = request.files.get('prova')

        if not desc or not prova:
            return jsonify({'error': 'Descrição e prova são obrigatórios'}), 400

        # Salve o arquivo com o nome seguro
        filename = secure_filename(prova.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Salve o arquivo no diretório correto
        prova.save(filepath)

        # Crie a URL do arquivo para ser armazenada no banco de dados
        prova_url = f"/uploads/{filename}"

        # Inserir os dados no banco de dados
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(""" 
            INSERT INTO submissions (id_usuario, id_quest, descricao_conclusao, prova_url)
            VALUES (%s, %s, %s, %s)
        """, (id_user, quest_id, desc, prova_url))
        db_connection.commit()
        cursor.close()

        return jsonify({"message": "Submissão enviada para análise"}), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

    
# Submissões pendentes (status = "Em análise")
@app.route('/submissions/pending', methods=['GET'])
@jwt_required()
def get_pending_submissions():
    user_data = json.loads(get_jwt_identity())
    nivel = user_data[1]

    if nivel != 'AA':
        return jsonify({'message': 'Acesso negado'}), 403

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, u.nome as usuario_nome, q.nome as quest_nome
            FROM submissions s
            JOIN usuario u ON s.id_usuario = u.id_usuario
            JOIN quest q ON s.id_quest = q.id_quest
            WHERE s.status = 'Pendente'
            ORDER BY s.data_submissao DESC
        """)
        submissions = cursor.fetchall()
        cursor.close()
        return jsonify({"submissions": submissions}), 200
    except Exception as e:
        print("Erro ao buscar submissões:", e)
        return jsonify({"error": str(e)}), 500




# Obter todas as submissões (somente admins)
@app.route('/submissions', methods=['GET'])
@jwt_required()
def list_submissions():
    user_data = json.loads(get_jwt_identity())
    nivel = user_data[1]

    if nivel != 'AA':
        return jsonify({'message': 'Acesso negado'}), 403

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, u.nome as usuario_nome, q.nome as quest_nome 
            FROM submissions s
            JOIN usuario u ON s.id_usuario = u.id_usuario
            JOIN quest q ON s.id_quest = q.id_quest
            ORDER BY s.data_submissao DESC
        """)
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'message': 'sucesso', 'info': data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/submissions/<int:submission_id>', methods=['PATCH'])
@jwt_required()
def update_submission_status(submission_id):
    user_data = json.loads(get_jwt_identity())
    nivel = user_data[1]

    if nivel != 'AA':
        return jsonify({'message': 'Acesso negado'}), 403

    data = request.json
    novo_status = data.get("status")  # "Aprovado" ou "Recusado"
    if novo_status not in ["Aprovado", "Recusado"]:
        return jsonify({'error': 'Status inválido'}), 400

    try:
        cursor = db_connection.cursor(dictionary=True)

        # Buscar submissão
        cursor.execute("SELECT * FROM submissions WHERE id = %s", (submission_id,))
        submission = cursor.fetchone()
        if not submission:
            return jsonify({'error': 'Submissão não encontrada'}), 404

        # Atualizar status
        cursor.execute("UPDATE submissions SET status = %s WHERE id = %s", (novo_status, submission_id))

        # Se aprovado, atualizar usuario_has_quest (opcional)
        if novo_status == "Aprovado":
            cursor.execute("""
                UPDATE usuario_has_quest
                SET estado = 'Concluída', descricao_conclusao = %s
                WHERE id_usuario = %s AND id_quest = %s
            """, (submission['descricao_conclusao'], submission['id_usuario'], submission['id_quest']))

        db_connection.commit()
        cursor.close()
        return jsonify({"message": "Status atualizado com sucesso"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route('/course_quests', methods=['GET'])
@jwt_required()
def course_quests():
    user_data = json.loads(get_jwt_identity())  # << AJUSTADO
    id_curso = user_data[2]
    cursor = db_connection.cursor(dictionary=True)
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
    user_data = json.loads(get_jwt_identity())  # << AJUSTADO
    id_user = user_data[0]
    try: 
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(f"select * from usuario where id_usuario={id_user}")
        data = cursor.fetchone()
        cursor.close()

        if data:
            return jsonify({'message': 'sucesso', 'info': data}), 200
        else:
            return jsonify(), 204
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500


@app.route('/players', methods=['GET'])
@jwt_required()
def players():
    user_data = json.loads(get_jwt_identity())  # << AJUSTADO
    nivel = user_data[1]
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
    
@app.route('/players', methods=['POST'])
@jwt_required()
def create_player():
    user_data = json.loads(get_jwt_identity())
    nivel = user_data[1]
    if nivel != 'AA':
        return jsonify({'message': 'Acesso negado'}), 403

    data = request.json
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')
    nivel_player = data.get('nivel')
    moedas = data.get('moedas', 0)
    curso = data.get('curso')

    if not all([nome, email, senha, nivel_player, curso]):
        return jsonify({'message': 'Dados incompletos'}), 400

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO usuario (nome, email, senha, nivel, moedas, id_curso)
            VALUES (%s, %s, %s, %s, %s,
                (SELECT id FROM curso WHERE nome = %s LIMIT 1)
            )
            """,
            (nome, email, senha, nivel_player, moedas, curso)
        )
        db_connection.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (new_id,))
        new_user = cursor.fetchone()
        cursor.close()
        return jsonify(new_user), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/transfers', methods=['GET'])
@jwt_required()
def transfers():
    user_data = json.loads(get_jwt_identity())  # << AJUSTADO
    nivel = user_data[1]
    if nivel != 'AA':
        return jsonify({'message': 'Acesso negado', 'info': ''}), 403
    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(f"select t.*, u.nome from transferencias t join usuario u on t.usuario_id = u.id_usuario order by data_hora desc;")
        data = cursor.fetchall()
        cursor.close()
        print(data)

        if data:
            return jsonify({'message': 'sucesso', 'info': data}), 200
        else:
            return jsonify(), 204
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500


@app.route('/players/info/<int:id>', methods=['PATCH'])
@jwt_required()
def updatePlayerInfo(id):
    try:
        user_data = json.loads(get_jwt_identity())  # << AJUSTADO
        nivel = user_data[1]
        if nivel != 'AA':
            return jsonify({'message': 'Acesso negado', 'info': ''}), 403
        data = request.json
        id = data.get('id', None)
        name = data.get('name', None)
        email = data.get('email', None)
        level = data.get('level', None)
        coins = data.get('coins', None)
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(f'update usuario set nome = "{name}", email ="{email}", nivel="{level}", moedas="{coins}" where id_usuario={id};')
        db_connection.commit()

        return jsonify({"message": "player updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500


@app.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    data = request.json
    id_quest = data.get('quest_id', None)
    id_user = data.get('id_user', None)
    recompensa = data.get('recompensa', None)
    cursor = db_connection.cursor(dictionary=True)
    cursor.execute(f"INSERT INTO usuario_has_quest (id, id_usuario, id_quest, estado, pontuacao, recompensa, validade, descricao_conclusao) VALUES (null, {id_user}, {id_quest}, 'Pendente', null, {recompensa}, CONVERT_TZ(NOW(), '+00:00', '-03:00'), null);")
    
    cursor.close()

    return jsonify({"message": "sucessfuly subscribed"}), 200


@app.route('/quests', methods=['GET'])
@jwt_required()
def quests():
    try:
        user_data = json.loads(get_jwt_identity())  # << AJUSTADO
        nivel = user_data[1]
        if nivel != 'AA':
            return jsonify({'message': 'Acesso negado', 'info': ''}), 403
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(f"select * from quest;")
        quests = cursor.fetchall()
        cursor.close()
        if quests:
            return jsonify({'message': 'sucesso', 'quests': quests}), 200
        else:
            return jsonify(), 204
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500

@app.route('/quests', methods=['POST'])
@jwt_required()
def create_quest():
    user_data = json.loads(get_jwt_identity())  # Ajustado
    nivel = user_data[1]
    if nivel != 'AA':
        return jsonify({'message': 'Acesso negado'}), 403

    data = request.json
    nome = data.get('nome')
    descricao = data.get('descricao')
    curso = data.get('curso')
    nivel_quest = data.get('nivel')
    custo = data.get('custo')

    if not all([nome, descricao, curso, nivel_quest, custo]):
        return jsonify({'message': 'Dados incompletos'}), 400

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO quest (nome, descricao, id_curso, nivel, custo)
            VALUES (%s, %s,
                (SELECT id FROM curso WHERE nome = %s LIMIT 1),
                %s, %s
            )
            """,
            (nome, descricao, curso, nivel_quest, custo)
        )
        db_connection.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM quest WHERE id_quest = %s", (new_id,))
        new_quest = cursor.fetchone()
        cursor.close()
        return jsonify(new_quest), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
