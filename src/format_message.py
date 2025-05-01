from .decodeMessage import decodeMessage
import pyodbc
import os, logging

logger = logging.getLogger(__name__)

def db_upload(msg):

    connstring = os.getenv('DB_CONNSTRING')
    table = os.getenv('DB_Table')

    try:
        msg_decoded = decodeMessage(msg)      # decodifico el mensaje utilizando la biblioteca synop del pymetdecoder,

        columns = ', '.join(msg_decoded.keys())             # nombre de los campos de la tabla Test de la BD
        placeholders = ', '.join(['?'] * len(msg_decoded))
        try:
            conn = pyodbc.connect(connstring)
            cursor = conn.cursor()
            sql = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'   # consulta sql para insertar los valores decodificados en la tabla Test
            cursor.execute(sql, tuple(msg_decoded.values()))
            conn.commit()
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            # Close the connection
            cursor.close()
            conn.close()

    except Exception as e:
        logging.error(f"Error: {e}")