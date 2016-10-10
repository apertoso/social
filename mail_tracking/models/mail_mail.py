# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import datetime
from email.utils import COMMASPACE

from openerp import models, api, fields


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _tracking_email_prepare(self, partner, email):
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        email_to_list = email.get('email_to', [])
        email_to = COMMASPACE.join(email_to_list)
        return {
            'name': email.get('subject', False),
            'timestamp': '%.6f' % ts,
            'time': fields.Datetime.to_string(dt),
            'mail_id': self.id,
            'mail_message_id': self.mail_message_id.id,
            'partner_id': partner.id if partner else False,
            'recipient': email_to,
            'sender': self.email_from,
        }

    @api.multi
    def send_get_email_dict(self, partner=None):
        email = super(MailMail, self).send_get_email_dict(partner=partner)
        vals = self._tracking_email_prepare(partner, email)
        tracking_email = self.env['mail.tracking.email'].sudo().create(vals)
        return tracking_email.tracking_img_add(email)

    # disable auto-delete of mail messages
    @api.multi
    def _postprocess_sent_message_v9(self, mail_sent=True):
        """Perform any post-processing necessary after sending ``mail``
        successfully, including deleting it completely along with its
        attachment if the ``auto_delete`` flag of the mail was set.
        Overridden by subclasses for extra post-processing behaviors.

        :param browse_record mail: the mail that was just sent
        :return: True
        """
        # Compat mode until v9
        for mail in self:
            self._postprocess_sent_message(mail, mail_sent=mail_sent)

        # if mail_sent:
        #    self.sudo().filtered(lambda self: self.auto_delete).unlink()
        return True
