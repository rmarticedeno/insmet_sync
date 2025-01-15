#!/bin/sh

set +e

find ${FTP_DATA}* -type f -mtime +1 -exec rm {} \;
find ${BULLETIN_DATA}* -type f -mtime +1 -exec rm {} \;
find ${REPORT_DATA}* -type f -mtime +1 -exec rm {} \;
find ${REPORT_BACKUP_DATA}* -type f -mtime +1 -exec rm {} \;
find ${INVALID_PROCESSED_REPORTS}* -type f -mtime +1 -exec rm {} \;