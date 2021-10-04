import socket
from concurrent.futures import ThreadPoolExecutor

import threading
from imapclient import IMAPClient, imapclient

import smtplib
import email
import math
import datetime


lock = threading.RLock()

class MailClient:
    def __init__(self):
        self.__connecting = False
        self.__is_connected = False
        self.__is_credentials_provided = False
        self.__executor = ThreadPoolExecutor(max_workers=2)

    def set__credentials(self, server, smtp, login, password):
        self.__smtp_host = smtp
        self.__imap_host = server
        self.__login = login
        self.__password = password
        self.__is_credentials_provided = True

    def connect(self):
        if not self.__is_credentials_provided:
            return
        if self.__connecting:
            return
        if self.__is_connected:
            self.logout()
        print('connecting...')
        self.__connecting = True

        try:
            self.__imap = IMAPClient(self.__imap_host, use_uid=True)
            self.__imap.login(self.__login, self.__password)
        except socket.gaierror:
            self.__connecting = False
            raise Exception("Błędny adres serwera IMAP")
        except imapclient.exceptions.LoginError:
            self.__connecting = False
            raise Exception("Błędne dane logowania")
        except Exception:
            self.__connecting = False
            pass

        try:
            self.__smtp = smtplib.SMTP(self.__smtp_host, 587)
            self.__smtp.starttls()
            self.__smtp.ehlo()
            self.__smtp.login(self.__login, self.__password)
        except socket.gaierror:
            self.__connecting = False
            raise Exception("Błędny adres serwera SMTP")
        except Exception:
            self.__connecting = False
            pass

        self.__connecting = False
        self.__is_connected = True


    def send_message(self, to, subject, msg):
        with lock:
            if not self.__is_connected:
                raise Exception("Brak połączenia z serwerem")
            message = email.message.EmailMessage()
            message['TO'] = to
            message['FROM'] = self.__login
            message['SUBJECT'] = subject
            message.set_payload(msg, 'utf-8')
            try:
                print('sending mail')
                self.__smtp.sendmail(self.__login, [to], message.as_bytes())
            except smtplib.SMTPRecipientsRefused:
                raise Exception("Nieporawidłowy adres odbiorcy")


    def get_messages_async(self, page, per_page, obj, callback):
        print('asd')
        res = self.__executor.submit(self.get_messages, page, per_page, obj, callback)

        def callback2(future):
            callback(future.result())

        res.add_done_callback(callback2)

    def get_messages(self, page, per_page, obj, callback, folder = "INBOX"):
        lock.acquire()
        start = (page * per_page)
        end = (start + per_page)
        if not self.__is_connected:
            lock.release()
            return None
        else:
            returned_value = []

            select_info = self.__imap.select_folder(folder)
            print('%d messages in INBOX' % select_info[b'EXISTS'])

            messages = self.__imap.search(['FROM'])
            #print("%d messages from our best friend" % len(messages))

            for msgid, data in self.__imap.fetch(messages[start:end], ['RFC822']).items():
                msg = email.message_from_bytes(data[b'RFC822'])

                for part in msg.walk():
                    # each part is a either non-multipart, or another multipart message
                    # that contains further parts... Message is organized like a tree
                    if part.get_content_type() == 'text/plain':
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset('iso-8859-1')
                        chars = payload.decode(charset, 'replace')
                        #print(chars)
                        msg['BODY_TEXT'] = chars
                        # Now convert to local date-time
                        date_tuple = email.utils.parsedate_tz(msg['DATE'])
                        if date_tuple:
                            local_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                            #print(local_date.strftime("%a, %d %b %Y %H:%M:%S"))
                            msg['DATE2'] = local_date.strftime("%a, %d %b %Y %H:%M:%S")
                returned_value.append(msg)

            lock.release()
            return  {
                'totalPages': math.ceil((len(messages) / per_page) or 0),
                'totalElements': len(messages),
                'data': returned_value
            }

    @staticmethod
    def get_test_account():
        return {
            "imap": "imap.ethereal.email",
            "smtp": "smtp.ethereal.email",
            'login': "leonora45@ethereal.email",
            'password': "dxkrP5XeVf2U76t6jQ"
        }

    def is_connected(self):
        return self.__is_connected

    def logout(self):
        print('logout')
        self.__imap.logout()
        self.__smtp.quit()
        self.__connecting = False
        self.__is_connected = False
