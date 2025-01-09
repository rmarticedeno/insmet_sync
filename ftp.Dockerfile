FROM lhauspie/vsftpd-alpine

ARG CERT_FINGERPRINT

RUN openssl req -x509 -nodes -days 7300 \
            -newkey rsa:2048 -keyout /etc/vsftpd/vsftpd.pem -out /etc/vsftpd/vsftpd.pem \
            -subj $CERT_FINGERPRINT

CMD /usr/sbin/run-vsftpd.sh