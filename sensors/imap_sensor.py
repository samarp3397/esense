import hashlib
import base64

import six
import eventlet
import easyimap
from flanker import mime

from st2reactor.sensor.base import PollingSensor

__all__ = [
    'IMAPSensor'
]

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=True,
    time=True)

class IMAPSensor(PollingSensor):
    def __init__(self, sensor_service, config=None, poll_interval=10):
        super(IMAPSensor, self).__init__(sensor_service=sensor_service,
                                         config=config,
                                         poll_interval=poll_interval)

        self._trigger = 'email123.imap.message'
        self._logger = self._sensor_service.get_logger(__name__)   
        self._accounts = {}

    def setup(self):
        self._logger.debug('[IMAPSensor]: entering setup')

    def poll(self):
        self._logger.debug('[IMAPSensor]: entering poll')

        if 'imap_accounts' in self._config:
            self._parse_accounts(self._config['imap_accounts'])

        for name, values in self._accounts.items():
            mailbox = values['connection']
            mailbox_metadata = values['mailbox_metadata']

            self._poll_for_unread_messages(name=name, mailbox=mailbox,                                          
                                           mailbox_metadata=mailbox_metadata)
            mailbox.quit()

    def cleanup(self):
        self._logger.debug('[IMAPSensor]: entering cleanup')

        for name, values in self._accounts.items():
            mailbox = values['connection']
            self._logger.debug('[IMAPSensor]: Disconnecting from {0}'.format(name))
            mailbox.quit()

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def _parse_accounts(self, accounts):
        for config in accounts:
            mailbox = config.get('name', None)
            server = config.get('server', 'localhost')
            port = config.get('port', 143)
            user = config.get('username', None)
            password = config.get('password', None)
            folder = config.get('folder', 'INBOX')
            ssl = config.get('secure', False)       

            if not user or not password:
                self._logger.debug("""[IMAPSensor]: Missing
                    username/password for {0}""".format(mailbox))
                continue

            if not server:
                self._logger.debug("""[IMAPSensor]: Missing server
                    for {0}""".format(mailbox))
                continue

            try:
                connection = easyimap.connect(server, user, password,
                                              folder, ssl=ssl, port=port)
            except Exception as e:
                message = 'Failed to connect to mailbox "%s": %s' % (mailbox, str(e))
                raise Exception(message)

            item = {
                'connection': connection,                
                'mailbox_metadata': {
                    'server': server,
                    'port': port,
                    'user': user,
                    'folder': folder,
                    'ssl': ssl
                }
            }
            self._accounts[mailbox] = item

    def _poll_for_unread_messages(self, name, mailbox, mailbox_metadata):
        self._logger.debug('[IMAPSensor]: polling mailbox {0}'.format(name))

        messages = mailbox.unseen()

        self._logger.debug('[IMAPSensor]: Processing {0} new messages'.format(len(messages)))
        for message in messages:
            self._process_message(uid=message.uid, mailbox=mailbox,                                  
                                  mailbox_metadata=mailbox_metadata)

    def _process_message(self, uid, mailbox, mailbox_metadata):
        m=[]
        message = mailbox.mail(uid, include_raw=True)
        mime_msg = mime.from_string(message.raw)

        body = message.body
        sent_from = message.from_addr
        sent_to = message.to
        subject = message.title
        date = message.date
        message_id = message.message_id
        headers = mime_msg.headers.items()      
        x=body.splitlines()
        for x1 in x:
          res=x1.split('=')
          m.append(res[1])
        location=m[0]
        vmname=m[1]
        group=m[2] 

        # Flatten the headers so they can be unpickled
        headers = self._flattern_headers(headers=headers)

        payload = {
            'uid': uid,
            'from': sent_from,
            'to': sent_to,
            'headers': headers,
            'date': date,
            'subject': subject,
            'message_id': message_id,
            'body': body,          
            'mailbox_metadata': mailbox_metadata,
            'location': location,
            'vmname': vmname,
            'group': group
        }    

        self._sensor_service.dispatch(trigger=self._trigger, payload=payload)

    def _flattern_headers(self, headers):
        # Flattern headers and make sure they only contain simple types so they
        # can be serialized in a trigger
        result = []

        for pair in headers:
            name = pair[0]
            value = pair[1]

            if not isinstance(value, six.string_types):
                value = str(value)

            result.append([name, value])

        return result
