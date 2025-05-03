from .decodeMessage import decodeMessage
import pyodbc
import os, logging

logger = logging.getLogger(__name__)

def db_upload(msg):

    connstring = os.getenv('DB_CONNSTRING')
    table = os.getenv('DB_Table')
    
    try:
        msg_decoded = decodeMessage(msg)      # decodifico el mensaje utilizando la biblioteca synop del pymetdecoder,

        time = msg_decoded['obs_time']
        station_id = msg_decoded['station_id']

        columns = ', '.join(msg_decoded.keys())             # nombre de los campos de la tabla Test de la BD
        placeholders = ', '.join(['?'] * len(msg_decoded))

        #print(msg_decoded, columns, placeholders)
        try:
            with pyodbc.connect(connstring) as conn:
                with conn.cursor() as cursor:
                    basequeryUpdate = ', '.join([f'{x} = ?' for x in  msg_decoded.keys()])  
                    queryUpdate =  f'UPDATE {table} SET {basequeryUpdate}'

                    queryAdd =  f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
                    querySelect = f"SELECT * FROM {table} WHERE obs_time = '{time}' AND station_id = '{station_id}'"
                    rows = cursor.execute(querySelect).fetchall()
                    cursor.execute(queryUpdate if len(rows) > 0 else queryAdd, tuple(msg_decoded.values()))
                    conn.commit()

        except Exception as e:
            logger.error(f"Error asd: {e}")

    except Exception as e:
        logger.error(f"Error adsasd: {e}")