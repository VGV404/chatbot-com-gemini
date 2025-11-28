import os
import secrets
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, flash
from google import genai
import db_manager as db 


app = Flask(__name__)
app.secret_key = secrets.token_hex(16) 

UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__))
FAQ_FILE_NAME = 'faq_contexto.txt'
FAQ_FILE_PATH = os.path.join(UPLOAD_FOLDER, FAQ_FILE_NAME)
ALLOWED_EXTENSIONS = {'txt'}

try:
    client = genai.Client()
except Exception as e:
    print(f"ERRO DE CONFIGURAÇÃO DO GEMINI: {e}")
    client = None

FAQ_CONTEXTO = ""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def carregar_contexto(caminho_arquivo: str) -> str:
    global FAQ_CONTEXTO
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            FAQ_CONTEXTO = f.read()
        print(f"Contexto de FAQ carregado de: {caminho_arquivo}")
        return FAQ_CONTEXTO
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        FAQ_CONTEXTO = "Desculpe, o contexto de FAQ não pôde ser carregado."
        return FAQ_CONTEXTO

def obter_resposta_faq(contexto: str, pergunta_usuario: str) -> str:
    """Gera a resposta do Gemini usando o contexto de FAQ (RAG simplificado)."""
    if not client:
        return "Desculpe, a conexão com a API do Gemini falhou."

    if "Desculpe, o contexto de FAQ não pôde ser carregado" in contexto:
         return contexto

    prompt_completo = f"""
    Você é um assistente de FAQ. Sua única fonte de informação deve ser o CONTEXTO abaixo.
    Se a resposta para a PERGUNTA do usuário NÃO estiver no CONTEXTO, responda de forma educada que a informação não foi encontrada em sua base de dados.
    
    --- CONTEXTO ---
    {contexto}
    --- FIM DO CONTEXTO ---
    
    PERGUNTA DO USUÁRIO: {pergunta_usuario}
    
    Resposta:
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_completo
        )
        return response.text
        
    except Exception as e:
        print(f"Erro na chamada da API: {e}")
        return "Ocorreu um erro ao processar sua pergunta. Tente novamente mais tarde."

# --- ROTAS DE AUTENTICAÇÃO E NAVEGAÇÃO ---

@app.route('/')
def home():
    if 'username' not in session:
        # Não logado, mostra a tela de login
        return render_template('login.html')
    
    # Logado, redireciona para a tela de acordo com a função
    if session.get('role') == 'adm':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_chat'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = db.get_user(username)
    
    if user and user['password'] == password:
        session['username'] = user['username']
        session['role'] = user['role']
        if session['role'] == 'adm':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_chat'))
    else:
        flash('Credenciais inválidas. Tente novamente.', 'error')
        return redirect(url_for('home'))

@app.route('/logoff')
def logoff():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('home'))


@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'adm':
        flash('Acesso negado.', 'error')
        return redirect(url_for('home'))
    
    usuarios_list = db.get_all_users()
    return render_template('admin.html', usuarios=usuarios_list)

@app.route('/upload', methods=['POST'])
def upload_file():
    if session.get('role') != 'adm':
        flash('Acesso negado.', 'error')
        return redirect(url_for('home'))

    if 'faq_file' not in request.files:
        flash('Nenhum arquivo enviado.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['faq_file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('admin_dashboard'))

    if file and allowed_file(file.filename):
        file.save(FAQ_FILE_PATH)
        carregar_contexto(FAQ_FILE_PATH)
        flash('Arquivo de FAQ atualizado com sucesso!', 'success')
    else:
        flash('Tipo de arquivo não permitido. Apenas .txt é aceito.', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/register_user', methods=['POST'])
def register_user():
    if session.get('role') != 'adm':
        flash('Acesso negado.', 'error')
        return redirect(url_for('home'))

    novo_username = request.form['new_username']
    nova_senha = request.form['new_password']
    novo_role = request.form['new_role']
    
    if not novo_username or not nova_senha or novo_role not in ['adm', 'user']:
        flash('Preencha todos os campos e selecione uma função válida.', 'error')
    else:
        if db.register_user(novo_username, nova_senha, novo_role):
            flash(f'Usuário "{novo_username}" ({novo_role.upper()}) registrado com sucesso!', 'success')
        else:
            flash(f'Erro: Usuário "{novo_username}" já existe.', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/chat_app')
def user_chat():
    if 'username' not in session:
        flash('Você precisa estar logado para acessar o chat.', 'error')
        return redirect(url_for('home'))
    
    return render_template('chat.html', username=session['username'])


@app.route('/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({"resposta": "Sua sessão expirou. Por favor, faça login novamente."})

    dados = request.get_json()
    pergunta_usuario = dados.get('pergunta', '')
    
    if not pergunta_usuario:
        return jsonify({"resposta": "Por favor, digite uma pergunta."})

    resposta_chatbot = obter_resposta_faq(FAQ_CONTEXTO, pergunta_usuario)
    
    return jsonify({"resposta": resposta_chatbot})


if __name__ == '__main__':
    db.create_table()
    carregar_contexto(FAQ_FILE_PATH)
    app.run(debug=True)