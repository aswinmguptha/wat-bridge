# -*- coding: utf-8 -*-
#
# wat-bridge
# https://github.com/rmed/wat-bridge
#
# The MIT License (MIT)
#
# Copyright (c) 2016 Rafael Medina García <rafamedgar@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Code for the Whatsapp side of the bridge."""

from yowsup.layers import YowLayerEvent
from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_media.protocolentities import ImageDownloadableMediaMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity
from yowsup.stacks import YowStackBuilder

from wat_bridge.static import SETTINGS, SIGNAL_TG, SIGNAL_WA, get_logger
from wat_bridge.helper import is_blacklisted, get_phone, db_get_contact_by_group, \
                              db_set_group, wa_id_to_name, db_toggle_bridge_by_wa, \
                              db_is_bridge_enabled_by_wa

import os
import uuid
import hashlib

logger = get_logger('wa')

class WaLayer(YowInterfaceLayer):
    """Defines the yowsup layer for interacting with Whatsapp."""

    @ProtocolEntityCallback('message')
    def on_message(self, message):
        """Received a message."""
        # Parse information
        sender = message.getFrom(full=False)
        oidtotg = message.getFrom(full=True)

        logger.debug('received message from %s' % oidtotg)

        # Send receipt
        receipt = OutgoingReceiptProtocolEntity(
            message.getId(),
            message.getFrom(),
            'read',
            message.getParticipant()
        )

        self.toLower(receipt)

        # https://github.com/tgalal/yowsup/issues/1411#issuecomment-203419530
        # if isinstance(type(message), unicode) :
        # message = message.encode('utf-8')
        # entity = TextMessageProtocolEntity(message, sender)
        # self.toLower(entity)

        # Ignore non-text messages
        if message.getType() != 'text':
            logger.info('not a text message, ignoring ' + message.getType())
            #return

        # Do stuff
        if is_blacklisted(sender):
            logger.debug('phone is blacklisted: %s' % sender)
            return

        participant = message.getParticipant()
        if participant :
          participant = participant.strip("@s.whatsapp.net")
        else :
          participant = sender

        # body = "<" + oidtotg + ">: " + message.getBody()
        # body = "NULL"
        if message.getType() == "text":
            body = message.getBody()

            if body == '/getID' or body == '/link':
                self.send_msg(phone=sender, message="/link " + sender)

                HelpInstructions = "Please send the above message in the Telegram group that you would like to bridge!"
                self.send_msg(phone=sender, message=HelpInstructions)

                return

            elif body == '/bridgeOn':
                toggle = db_toggle_bridge_by_wa(sender, True)

                if toggle == None:
                    Message = 'This group is not bridged to anywhere. Use ```/link``` to start bridging.'
                else:
                    Message = 'Bridge has been turned on!'

                self.send_msg(phone=sender, message=Message)

                return

            elif body == '/bridgeOff':
                toggle = db_toggle_bridge_by_wa(sender, False)

                if toggle == None:
                    Message = 'This group is not bridged to anywhere. Use ```/link``` to start bridging.'
                else:
                    Message = 'Bridge has been turned off. Use ```/bridgeOn``` to turn it back on.'

                self.send_msg(phone=sender, message=Message)

                return

            if db_is_bridge_enabled_by_wa(sender) == False:
                return

            TheRealMessageToSend = "<" + participant + ">: " + body
            # Relay to Telegram
            logger.info('relaying message to Telegram')
            SIGNAL_TG.send('wabot', phone=sender, message=TheRealMessageToSend)

        if message.getType() == "media":
          if not os.path.exists("/home/shrimadhav/Public/TGWhatAppBot"):
            os.makedirs("/home/shrimadhav/Public/TGWhatAppBot")
          # set unique filename
          uniqueFilename = "/home/shrimadhav/Public/TGWhatAppBot/%s-%s%s" % (hashlib.md5(str(message.getFrom(False)).encode('utf-8')).hexdigest(), uuid.uuid4().hex, message.getExtension())
          if message.getMediaType() == "image":
            logger.info("Echoing image %s to %s" % (message.url, message.getFrom(False)))
            data = message.getMediaContent()
            f = open(uniqueFilename, 'wb')
            f.write(data)
            f.close()
          # https://github.com/AragurDEV/yowsup/pull/37
          elif message.getMediaType() == "video":
            logger.info("Echoing video %s to %s" % (message.url, message.getFrom(False)))
            data = message.getMediaContent()
            f = open(uniqueFilename, 'wb')
            f.write(data)
            f.close()
          elif message.getMediaType() == "audio":
            logger.info("Echoing audio %s to %s" % (message.url, message.getFrom(False)))
            data = message.getMediaContent()
            f = open(uniqueFilename, 'wb')
            f.write(data)
            f.close()
          elif message.getMediaType() == "document":
            logger.info("Echoing document %s to %s" % (message.url, message.getFrom(False)))
            data = message.getMediaContent()
            f = open(uniqueFilename, 'wb')
            f.write(data)
            f.close()
          elif message.getMediaType() == "location":
            logger.info("Echoing location (%s, %s) to %s" % (message.getLatitude(), message.getLongitude(), message.getFrom(False)))
          elif message.getMediaType() == "vcard":
            logger.info("Echoing vcard (%s, %s) to %s" % (message.getName(), message.getCardData(), message.getFrom(False)))
          url = uniqueFilename.replace("/home/shrimadhav/Public/TGWhatAppBot", "https://SpEcHiDe.shrimadhavuk.me/TGWhatAppBot")
          TheRealMessageToSend = "<" + participant + ">: " + url
          # Relay to Telegram
          logger.info('relaying message to Telegram')
          SIGNAL_TG.send('wabot', phone=sender, message=TheRealMessageToSend)

    @ProtocolEntityCallback('receipt')
    def on_receipt(self, entity):
        """Received a "receipt" for a message."""
        logger.debug('ACK message')

        # Acknowledge
        ack = OutgoingAckProtocolEntity(
            entity.getId(),
            'receipt',
            entity.getType(),
            entity.getFrom()
        )

        #self.toLower(ack)
        self.toLower(entity.ack())

    def send_msg(self, **kwargs):
        """Send a message.

        Arguments:
            phone (str): Phone to send the message to.
            message (str): Message to send
        """
        phone = kwargs.get('phone')
        toStr = ""

        if not phone:
            # Nothing to do
            logger.debug('no phone provided')
            return

        if phone.find("-") > -1 :
          toStr = phone + "@g.us"
        else :
          toStr = phone + "@s.whatsapp.net"

        message = kwargs.get('message').encode('utf8')

        entity = TextMessageProtocolEntity(
            message,
            to=toStr
        )

        # self.ackQueue.append(entity.getId())
        self.toLower(entity)


# Prepare stack
wabot = WaLayer()

_connect_signal = YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)

WA_STACK = (
    YowStackBuilder()
    .pushDefaultLayers(True)
    # .pushDefaultLayers(False)
    .push(wabot)
    .build()
)

WA_STACK.setCredentials((SETTINGS['wa_phone'], SETTINGS['wa_password']))
