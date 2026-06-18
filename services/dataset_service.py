import os
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Caminho do arquivo de histórico
ARQUIVO_HISTORICO = os.path.join(os.path.dirname(__file__), "..", "historico_consultas.csv")

def registrar_historico_consulta(texto, fonte, resultado, confianca=None, db=None):
    """Salva a consulta no CSV e opcionalmente no PostgreSQL."""
    try:
        # Salvar no CSV (fallback)
        existe = os.path.exists(ARQUIVO_HISTORICO)
        with open(ARQUIVO_HISTORICO, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not existe:
                writer.writerow(["data_hora", "texto", "fonte", "resultado", "confianca"])
            
            data_agora = datetime.now().strftime("%d/%m/%Y %H:%M")
            conf_str = f"{confianca:.1f}" if confianca is not None else "-"
            
            writer.writerow([data_agora, texto.strip(), fonte, resultado, conf_str])
        
        # Salvar no PostgreSQL se disponível
        if db and db.is_connected():
            query = """
            INSERT INTO historico_consultas (data_hora, texto, fonte, resultado, confianca)
            VALUES (%s, %s, %s, %s, %s);
            """
            db.execute_update(query, (data_agora, texto.strip(), fonte, resultado, confianca))
            logger.info("[INFO] Consulta registrada no PostgreSQL.")
        
        return True
    except Exception as e:
        logger.error(f"[ERRO] Erro ao registrar histórico: {e}")
        return False

def obter_historico_consultas(limite=15, db=None):
    """Lê o histórico do PostgreSQL ou CSV."""
    
    # Tentar obter do PostgreSQL primeiro
    if db and db.is_connected():
        try:
            query = """
            SELECT 
                TO_CHAR(data_hora, 'DD/MM/YYYY HH24:MI') as data_hora,
                texto,
                fonte,
                resultado,
                ROUND(confianca::numeric, 1)::text as confianca
            FROM historico_consultas
            ORDER BY data_hora DESC
            LIMIT %s;
            """
            resultados = db.execute_query(query, (limite,))
            
            if resultados:
                logger.info(f"[INFO] Histórico obtido do PostgreSQL ({len(resultados)} registros).")
                return resultados
        except Exception as e:
            logger.warning(f"[AVISO] Erro ao obter histórico do PostgreSQL: {e}. Usando CSV como fallback.")
    
    # Fallback para CSV
    if not os.path.exists(ARQUIVO_HISTORICO):
        return []
    
    try:
        lista = []
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for linha in reader:
                lista.append(linha)
        
        # Inverter para mostrar mais recentes primeiro
        return lista[::-1][:limite]
    except Exception as e:
        logger.error(f"[ERRO] Erro ao ler histórico do CSV: {e}")
        return []

def obter_estatisticas_dataset(db=None):
    """Obtém estatísticas do dataset."""
    
    if db and db.is_connected():
        try:
            query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN label = 'verdadeiro' THEN 1 ELSE 0 END) as verdadeiros,
                SUM(CASE WHEN label = 'falso' THEN 1 ELSE 0 END) as falsos,
                ROUND(AVG(confianca)::numeric, 2) as confianca_media
            FROM dataset_consolidado;
            """
            resultado = db.execute_query(query)
            
            if resultado:
                logger.info("[INFO] Estatísticas obtidas do PostgreSQL.")
                return resultado[0]
        except Exception as e:
            logger.warning(f"[AVISO] Erro ao obter estatísticas: {e}")
    
    return None

def salvar_no_dataset(texto, label, fonte, confianca, db=None):
    """Salva um novo registro no dataset (CSV e PostgreSQL)."""
    try:
        # 1. Salvar no CSV (Fallback)
        arquivo_csv = os.path.join(os.path.dirname(__file__), "..", "dataset_consolidado.csv")
        novo_dado = {
            "texto": texto.strip().lower(),
            "label": label.lower(),
            "fonte": fonte,
            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
            "confianca": confianca
        }
        
        # Verificar se já existe no CSV para não duplicar
        existe_no_csv = False
        if os.path.exists(arquivo_csv):
            import pandas as pd
            df = pd.read_csv(arquivo_csv)
            if texto.strip().lower() in df['texto'].values:
                existe_no_csv = True
        
        if not existe_no_csv:
            with open(arquivo_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=novo_dado.keys())
                writer.writerow(novo_dado)
            logger.info(f"[INFO] Registro salvo no CSV do dataset.")

        # 2. Salvar no PostgreSQL
        if db and db.is_connected():
            query = """
            INSERT INTO dataset_consolidado (texto, label, fonte, data_coleta, confianca)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (texto) DO NOTHING;
            """
            db.execute_update(query, (
                texto.strip().lower(), 
                label.lower(), 
                fonte, 
                datetime.now().strftime("%Y-%m-%d"), 
                confianca
            ))
            logger.info(f"[INFO] Registro salvo no PostgreSQL do dataset.")
        
        return True
    except Exception as e:
        logger.error(f"[ERRO] Falha ao salvar no dataset: {e}")
        return False

def obter_ultimo_retreinamento(db=None):
    """Obtém informações do último retreinamento do modelo."""
    
    if db and db.is_connected():
        try:
            query = """
            SELECT 
                TO_CHAR(data_fim, 'DD/MM/YYYY HH24:MI') as data_fim,
                ROUND(accuracy::numeric, 4) as accuracy,
                ROUND(precision::numeric, 4) as precision,
                ROUND(recall::numeric, 4) as recall,
                ROUND(f1_score::numeric, 4) as f1_score,
                status
            FROM retreinamentos
            WHERE status = 'sucesso'
            ORDER BY data_fim DESC
            LIMIT 1;
            """
            resultado = db.execute_query(query)
            
            if resultado:
                logger.info("[INFO] Informações da última atualização obtidas.")
                return resultado[0]
        except Exception as e:
            logger.warning(f"[AVISO] Erro ao obter último retreinamento: {e}")
    
    return None
