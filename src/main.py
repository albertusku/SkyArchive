from API.API_connection import *
from Data_storage.storage_builder import *
from Visualizer.Today_page import *
from config import *    
from Logs.logger import setup_logger
#from SDR.satellites_info import get_satellite_info
import os
import subprocess

logger=setup_logger("Main",os.path.join(LOGS_DIR,"Procces.log"))


# Ejemplo de uso
if __name__ == "__main__":
    logger.info("Starting program")
    try:
        params = read_json()
        data = get_data_from_api(params)
        create_storage(data)
        subprocess.run(["sudo", "systemctl", "restart", "streamlit-dashboard"], check=True)
    except Exception as e:
        logger.error(f"Program stopped: {e}")
        raise

    logger.info("Program finished")
    
