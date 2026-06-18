import logging
import schedule
import time
from datetime import datetime
from services.data_collection_service import DataCollectionService
from services.training_service import TrainingService
from database.db_connection import db

logger = logging.getLogger(__name__)

class SchedulerTasks:
    def __init__(self):
        self.data_collector = DataCollectionService(db=db)
        self.trainer = TrainingService(db=db)
        self.ultima_coleta = None
        self.ultimo_treinamento = None
    
    def tarefa_coleta_dados(self):
        """Tarefa de coleta automática de dados a cada 24 horas."""
        logger.info("[INFO] Iniciando tarefa agendada de coleta de dados...")
        
        try:
            self.data_collector.iniciar_coleta()
            self.ultima_coleta = datetime.now()
            logger.info(f"[INFO] Coleta de dados concluída com sucesso em {self.ultima_coleta}")
        except Exception as e:
            logger.error(f"[ERRO] Erro na tarefa de coleta de dados: {e}")
    
    def tarefa_retreinamento(self):
        """Tarefa de retreinamento automático do modelo a cada 24 horas."""
        logger.info("[INFO] Iniciando tarefa agendada de retreinamento do modelo...")
        
        try:
            sucesso = self.trainer.treinar_modelo()
            
            if sucesso:
                self.ultimo_treinamento = datetime.now()
                logger.info(f"[INFO] Atualização concluída com sucesso em {self.ultimo_treinamento}")
            else:
                logger.error("[ERRO] Atualização falhou.")
        except Exception as e:
            logger.error(f"[ERRO] Erro na tarefa de atualização: {e}")
    
    def agendar_tarefas(self):
        """Agenda as tarefas automáticas."""
        logger.info("[INFO] Agendando tarefas automáticas...")
        
        # Coleta de dados a cada 24 horas
        schedule.every().day.at("02:00").do(self.tarefa_coleta_dados)
        logger.info("[INFO] Tarefa de coleta agendada para 02:00 todos os dias.")
        
        # Retreinamento do modelo a cada 24 horas (após coleta)
        schedule.every().day.at("03:00").do(self.tarefa_retreinamento)
        logger.info("[INFO] Tarefa de retreinamento agendada para 03:00 todos os dias.")
    
    def executar_loop(self):
        """Executa o loop do scheduler."""
        logger.info("[INFO] Iniciando loop do scheduler...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verificar a cada minuto
            except KeyboardInterrupt:
                logger.info("[INFO] Scheduler interrompido pelo usuário.")
                break
            except Exception as e:
                logger.error(f"[ERRO] Erro no loop do scheduler: {e}")
                time.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(message)s'
    )
    
    # Conectar ao banco de dados
    if db.connect():
        db.create_tables()
    
    # Criar e executar scheduler
    scheduler = SchedulerTasks()
    scheduler.agendar_tarefas()
    scheduler.executar_loop()
