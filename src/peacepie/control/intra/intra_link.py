import logging

from peacepie import params
from peacepie.assist import log_util


class IntraLink:

    def __init__(self, parent):
        self.parent = parent
        self.server = None
        self.host = params.instance['ip']
        self.port = None
        self.links = {}
        self.head = None
        logging.info(log_util.get_alias(self) + ' is created')

    def get_members(self):
        res = [link[0] for link in self.links.items() if not link[1].lord]
        if not self.parent.lord:
            res.append(self.parent.adaptor.name)
        res.sort()
        return res

    def clarify_recipient(self, recipient, is_control):
        if recipient is None:
            if is_control:
                return self.parent.adaptor.control_queue
            else:
                return self.parent.adaptor.queue
        if type(recipient) is dict:
            system_name = recipient.get('system')
            if system_name and system_name != self.parent.adaptor.get_param('system_name'):
                if self.parent.is_head:
                    return self.parent.interlink.queue
                else:
                    return self.links[self.head]
            else:
                recipient = recipient.get('entity')
                if not recipient:
                    return self.parent.adaptor.queue
        if type(recipient) is not str:
            return None
        if recipient.startswith('_'):
            res = self.parent.connector.asks[recipient]
            return res
        else:
            if recipient == self.parent.adaptor.name:
                return self.parent.adaptor.queue
            else:
                return self.parent.actor_admin.get_actor_queue(recipient, is_control)
