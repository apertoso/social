# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import email.message
import logging
import re

from openerp.addons.mail.models.mail_thread import decode_header

from openerp import models, api

_logger = logging.getLogger(__name__)


def message_get_contents(message):
    if type(message) is not email.message:
        return message
    # else
    if message.is_multipart():
        return "\n".join(
            [message_get_contents(m) for m in message.get_payload()])
    else:
        return message.get_payload()


class MailThread(models.AbstractModel):
    """ Update MailThread to add the feature of bounced emails and replied
    emails
    in message_process. """
    _name = 'mail.thread'
    _inherit = ['mail.thread']

    @api.model
    def get_message_bounced_mail(self, message):
        """ Override to verify that the email_to is the bounce alias. If it
        is the case, log the bounce, set the parent and related document as
        bounced and return False to end the routing process. """
        bounce_alias = self.env['ir.config_parameter'].get_param(
            "mail.bounce.alias")
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')

        # 0. Verify whether this is a bounced email (wrong destination,
        # ...) -> mark as bounced
        if bounce_alias and bounce_alias in email_to:
            # Bounce regex
            # Typical form of bounce is bounce_alias-128-crm.lead-34@domain
            # group(1) = the mail ID; group(2) = the model (if any); group(
            # 3) = the record ID
            bounce_re = re.compile(
                "%s-(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias),
                re.UNICODE)
            bounce_match = bounce_re.search(email_to)
            if bounce_match:
                bounced_mail_id = int(bounce_match.group(1) or 0)
                bounced_model = bounce_match.group(2)
                bounced_res_id = int(bounce_match.group(3) or 0)
                _logger.info(
                    'Found bounce mail from %s to %s with Message-Id %s: '
                    'bounced mail from mail %s, model: %s, mail_mail_id: %s',
                    email_from, email_to, message_id, bounced_mail_id,
                    bounced_model, bounced_mail_id)

                mail_domain = [
                    ('id', '=', bounced_mail_id),
                    ('model', '=', bounced_model),
                    ('res_id', '=', bounced_res_id),
                ]
                mail_mail = self.env['mail.mail'].search(mail_domain, limit=1)

                return mail_mail

        return False

    @api.model
    def save_bounced_mail_tracking(self, mail_mail, message, message_dict):
        mail_tracking = self.env['mail.tracking.email'].search(
            [('mail_id', '=', mail_mail.id)])
        metadata = {
            'bounce_type': 'hard_bounce',
            'bounce_description': message_get_contents(message),
        }
        mail_tracking.event_create('hard_bounce', metadata)

    @api.model
    def message_route(self, message, message_dict, model=None,
                      thread_id=None,
                      custom_values=None):
        bounced_mail_mail = self.get_message_bounced_mail(message)
        if bounced_mail_mail:
            self.save_bounced_mail_tracking(
                bounced_mail_mail, message, message_dict)

        # continue regular processing
        return super(MailThread, self).message_route(message,
                                                     message_dict, model,
                                                     thread_id,
                                                     custom_values, )
