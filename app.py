import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Importar serviços
from services.fact_check_service import consultar_fact_check_google
from services.dataset_service import (
    registrar_historico_consulta, 
    obter_historico_consultas,
    obter_estatisticas_dataset,
    obter_ultimo_retreinamento,
    salvar_no_dataset
)
from services.predict import realizar_predicao_ml
from database.db_connection import db

load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# Conectar ao banco de dados na inicialização
@app.before_request
def conectar_db():
    """Conecta ao banco de dados antes de cada requisição."""
    if not db.is_connected():
        db.connect()
        db.create_tables()

@app.route("/")
def index():
    logger.info("[INFO] Acessando página inicial.")
    return render_template("index.html")

@app.route("/analisar", methods=["POST"])
def analisar():
    """Verifica a veracidade de uma notícia."""
    dados = request.get_json(silent=True)
    texto = dados.get("texto", "").strip() if dados else ""

    if not texto:
        logger.warning("[AVISO] Texto vazio recebido para análise.")
        return jsonify({"erro": "Escreva o texto da notícia para analisar!"}), 400

    logger.info(f"[INFO] Analisando texto: {texto[:50]}...")

    # Primeiro tenta ver se o Google já checou isso
    resultado_api = consultar_fact_check_google(texto)
    
    if resultado_api.get("encontrado") and resultado_api.get("resultados"):
        primeiro = resultado_api["resultados"][0]
        veredito = primeiro.get("veredito")
        
        # Se o Google deu um veredito claro, usa
        if veredito and veredito != "Indeterminado":
            confianca = 98.0
            registrar_historico_consulta(texto, "Google API", veredito, confianca, db)
            
            # Salvar também no dataset para aprimorar o modelo com dados do Google
            salvar_no_dataset(texto, veredito, "Google API", confianca, db)
            
            logger.info(f"[INFO] Resultado obtido do Google API: {veredito} ({confianca}%)")
            
            return jsonify({
                "resultado": veredito,
                "confianca": confianca,
                "fonte": "Google Fact Check API",
                "explicacao": f"O Google encontrou uma checagem: {primeiro.get('textualRating')}. Fonte: {primeiro.get('publisher')}"
            })

    # Se não houver checagem no Google, utiliza o modelo de Machine Learning
    logger.info("[INFO] Iniciando análise de Machine Learning...")
    res_ml = realizar_predicao_ml(texto, db)

    if "erro" in res_ml:
        logger.error(f"[ERRO] Erro no modelo de análise: {res_ml['erro']}")
        return jsonify({"erro": "Erro no modelo de análise."}), 500

    veredito_ml = "Verdadeiro" if res_ml["label"] == "verdadeiro" else "Falso"
    registrar_historico_consulta(texto, "Modelo Local", veredito_ml, res_ml["confianca"], db)
    
    logger.info(f"[INFO] Resultado obtido do Modelo Local: {veredito_ml} ({res_ml['confianca']}%)")

    return jsonify({
        "resultado": veredito_ml,
        "confianca": res_ml["confianca"],
        "fonte": "Modelo de Análise Local",
        "explicacao": f"Análise estatística realizada. Confiança: {res_ml['confianca']}%"
    })

@app.route("/historico", methods=["GET"])
def historico():
    """Retorna o histórico de consultas."""
    logger.info("[INFO] Acessando histórico de consultas.")
    lista = obter_historico_consultas(limite=15, db=db)
    return jsonify({"historico": lista})

@app.route("/status", methods=["GET"])
def status():
    """Retorna o status de todos os serviços e componentes do sistema."""
    logger.info("[INFO] Verificando status do sistema.")
    
    # Verificar Google API
    g_key = os.getenv("GOOGLE_API_KEY", "").strip()
    google_ok = g_key != "" and g_key != "sua_chave_aqui"
    
    # Verificar News API
    n_key = os.getenv("NEWS_API_KEY", "").strip()
    news_ok = n_key != "" and n_key != "sua_chave_aqui"
    
    # Verificar componentes de análise
    modelo_ok = os.path.exists("model.pkl") and os.path.exists("vectorizer.pkl")
    
    # Verificar PostgreSQL
    db_ok = db.is_connected()
    
    # Obter estatísticas do dataset
    stats_dataset = obter_estatisticas_dataset(db)
    tamanho_dataset = stats_dataset['total'] if stats_dataset else 0
    
    # Obter informações da última atualização
    ultimo_retreinamento = obter_ultimo_retreinamento(db)
    
    servicos = [
        {
            "nome": "Google Fact Check API",
            "status": "OK" if google_ok else "Pendente",
            "online": google_ok,
            "descricao": "Busca de checagens oficiais de notícias."
        },
        {
            "nome": "NewsAPI",
            "status": "OK" if news_ok else "Pendente",
            "online": news_ok,
            "descricao": "Coleta de notícias para atualização da base."
        },
        {
            "nome": "Modelo de Machine Learning",
            "status": "Pronto" if modelo_ok else "Indisponível",
            "online": modelo_ok,
            "descricao": "Algoritmo de ML para análise de padrões textuais."
        },
        {
            "nome": "PostgreSQL",
            "status": "Conectado" if db_ok else "Desconectado",
            "online": db_ok,
            "descricao": "Banco de dados para persistência."
        }
    ]
    
    resposta = {
        "servicos": servicos,
        "dataset": {
            "tamanho": tamanho_dataset,
            "verdadeiros": stats_dataset['verdadeiros'] if stats_dataset else 0,
            "falsos": stats_dataset['falsos'] if stats_dataset else 0,
            "confianca_media": float(stats_dataset['confianca_media']) if stats_dataset and stats_dataset['confianca_media'] else 0
        }
    }
    
    if ultimo_retreinamento:
        resposta["ultima_atualizacao"] = {
            "data": ultimo_retreinamento['data_fim'],
            "accuracy": float(ultimo_retreinamento['accuracy']),
            "precision": float(ultimo_retreinamento['precision']),
            "recall": float(ultimo_retreinamento['recall']),
            "f1_score": float(ultimo_retreinamento['f1_score'])
        }
    
    logger.info("[INFO] Status do sistema retornado com sucesso.")
    return jsonify(resposta)

@app.errorhandler(404)
def nao_encontrado(e):
    logger.warning("[AVISO] Rota não encontrada: 404")
    return jsonify({"erro": "Rota não encontrada."}), 404

@app.errorhandler(500)
def erro_interno(e):
    logger.error(f"[ERRO] Erro interno do servidor: {e}")
    return jsonify({"erro": "Erro interno do servidor."}), 500

if __name__ == "__main__":
    logger.info("[INFO] Iniciando aplicação VFNews...")
    logger.info("[INFO] Conectando ao banco de dados...")
    
    if db.connect():
        db.create_tables()
        logger.info("[INFO] Banco de dados configurado com sucesso.")
    else:
        logger.warning("[AVISO] Banco de dados não disponível. Usando modo fallback (CSV).")
    
    # Roda o Flask na porta definida em .env (padrão: 5050)
    porta = int(os.getenv("PORT", 5050))
    debug = os.getenv("FLASK_DEBUG", "False").strip().lower() == "true"
    app.run(host="0.0.0.0", port=porta, debug=debug)
