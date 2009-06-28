###
# Copyright (c) 2009, Morten Lied Johansen
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import time
from string import Template

import config

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.registry import NonExistentRegistryEntry

class NetGamers(callbacks.Plugin):
    """This plugin handles dealing with Bot-style Services on networks that provide them.
    Basically, you should use the "password" command to tell the bot a nick to
    identify with and what password to use to identify with that nick.  You can
    use the password command multiple times if your bot has multiple nicks
    registered."""
    def __init__(self, irc):
        self.__parent = super(NetGamers, self)
        self.__parent.__init__(irc)
        self.reset()

    def reset(self):
        self.channels = []
        self.sentGhost = None
        self.identified = False
        self.waitingJoins = []

    def callCommand(self, command, irc, msg, *args, **kwargs):
        """Make sure we're on an enabled network before proceeding."""
        if self._isEnabled(irc):
            self.__parent.callCommand(command, irc, msg, *args, **kwargs)
        else:
            self.log.info("Intercepted command %s on %s", command, irc.network)
    
    def outFilter(self, irc, msg):
        if msg.command == 'JOIN':
            if not self.identified:
                if self.registryValue('noJoinsUntilIdentified'):
                    self.log.info('Holding JOIN to %s until identified.',
                                  msg.args[0])
                    self.waitingJoins.append(msg)
                    return None
        return msg

    def _getReggedNick(self, network):
        return self.registryValue("reggedNick")

    def _getReggedPassword(self, network):
        return self.registryValue("password")

    def _getUseRegged(self, network):
        return self.registryValue("useRegged")

    def _getBotNick(self, network):
        return self.registryValue('botNick')

    def isBotNick(self, network, nick):
        """Compare a nick from a message with the current BotNick.
        
        Bots often have a server appended to their nick for security, so comparing the
        configured nick for the bot with the nick in the message will not always work.
        This function takes care of testing the possibilities.
        """
        botnick = self._getBotNick(network)
        if botnick and "@" in botnick:
            botnick, server = botnick.split("@", 1)
        return botnick and ircutils.strEqual(nick, botnick)

    def _isEnabled(self, irc):
        enabledNetworks = ("NetGamers",)
        return irc.network in enabledNetworks or irc.state.supported.get('NETWORK', '') in enabledNetworks

    def _doIdentify(self, irc, nick=None):
        if not self._isEnabled(irc):
            return
        if nick is None:
            nick = self._getReggedNick(irc.network)
        botnick = self._getBotNick(irc.network)
        password = self._getReggedPassword(irc.network)
        if not nick or not botnick or not password:
            s = 'Tried to identify without proper configuration.'
            self.log.warning(s)
            return
        self.log.info('Sending login (current nick: %s)', irc.nick)
        identify = "LOGIN %s %s" % (nick, password)
        # It's important that this next statement is irc.sendMsg, not
        # irc.queueMsg.  We want this message to get through before any
        # JOIN messages also being sent on 376.
        irc.sendMsg(ircmsgs.privmsg(botnick, identify))

    def _doGhost(self, irc, nick=None):
        if not self._isEnabled(irc):
            return
        if nick is None:
            nick = self._getReggedNick(irc.network)
        botnick = self._getBotNick(irc.network)
        password = self._getReggedPassword(irc.network)
        ghostDelay = self.registryValue('ghostDelay')
        if not botnick or not password:
            s = 'Tried to ghost without a BotNick or password set.'
            self.log.warning(s)
            return
        if self.sentGhost and time.time() < (self.sentGhost + ghostDelay):
            self.log.warning('Refusing to send RECOVER more than once every '
                             '%s seconds.' % ghostDelay)
        else:
            self.log.info('Sending recover (current nick: %s; ghosting: %s)',
                          irc.nick, nick)
            ghost = "RECOVER %s %s %s" % (nick, nick, password)
            # Ditto about the sendMsg (see _doIdentify).
            irc.sendMsg(ircmsgs.privmsg(botnick, ghost))
            self.sentGhost = time.time()

    def __call__(self, irc, msg):
        if not self._isEnabled(irc):
            return
        self.__parent.__call__(irc, msg)
        nick = self._getReggedNick(irc.network)
        botnick = self._getBotNick(irc.network)
        password = self._getReggedPassword(irc.network)
        ghostDelay = self.registryValue('ghostDelay')
        if nick and botnick and password:
            if self._getUseRegged(irc.network) and not ircutils.strEqual(nick, irc.nick):
                if irc.afterConnect and (self.sentGhost is None or
                   (self.sentGhost + ghostDelay) < time.time()):
                    if nick in irc.state.nicksToHostmasks:
                        self._doGhost(irc)
                    else:
                        irc.sendMsg(ircmsgs.nick(nick)) # 433 is handled elsewhere.

    def do001(self, irc, msg):
        if not self._isEnabled(irc):
            return
        # New connection, make sure sentGhost is False.
        self.sentGhost = None

    def do376(self, irc, msg):
        nick = self._getReggedNick(irc.network)
        if not nick:
            self.log.warning('Cannot identify without a nick being set.')
            return
        botnick = self._getBotNick(irc.network)
        if not botnick:
            self.log.warning('BotNick is unset, cannot identify.')
            return
        password = self._getReggedPassword(irc.network)
        if not password:
            self.log.warning('Password for %s is unset, cannot identify.',nick)
            return
        if ircutils.strEqual(irc.nick, nick) or self._getUseRegged(irc.network) == False:
            self._doIdentify(irc)
        else:
            self._doGhost(irc)
    do422 = do377 = do376

    def do433(self, irc, msg):
        nick = self._getReggedNick(irc.network)
        if nick and irc.afterConnect:
            password = self._getReggedPassword(irc.network)
            if not password:
                return
            self._doGhost(irc)

    def do515(self, irc, msg):
        # Can't join this channel, it's +r (we must be identified).
        self.channels.append(msg.args[1])

    def doNick(self, irc, msg):
        nick = self._getReggedNick(irc.network)
        if nick:
            if ircutils.strEqual(msg.args[0], irc.nick) and ircutils.strEqual(irc.nick, nick):
                self._doIdentify(irc)
            elif ircutils.strEqual(msg.nick, nick):
                irc.sendMsg(ircmsgs.nick(nick))

    def _ghosted(self, network, s):
        nick = self._getReggedNick(network)
        lowered = s.lower()
        return bool('killed' in lowered and (nick in s or 'ghost' in lowered))

    def doNotice(self, irc, msg):
        if not self._isEnabled(irc):
            return
        if irc.afterConnect:
            botnick = self._getBotNick(irc.network)
            if botnick and self.isBotNick(irc.network, msg.nick):
                handled = self.doChanservNotice(irc, msg)
                if not handled:
                    handled = self.doNickservNotice(irc, msg)
                if not handled:
                    on = 'on %s' % irc.network
                    s = ircutils.stripFormatting(msg.args[1].lower())
                    self.log.warning('Unexpected notice from Bot %s: %r.', on, s)

    _chanRe = re.compile('\x02(.*?)\x02')
    def doChanservNotice(self, irc, msg):
        s = ircutils.stripFormatting(msg.args[1].lower())
        channel = None
        m = self._chanRe.search(s)
        networkGroup = conf.supybot.networks.get(irc.network)
        on = 'on %s' % irc.network
        if m is not None:
            channel = m.group(1)
        if 'all bans' in s or 'unbanned from' in s:
            # All bans removed (freenode)
            # You have been unbanned from (oftc)
            irc.sendMsg(networkGroup.channels.join(channel))
        elif 'isn\'t registered' in s:
            self.log.warning('Received "%s isn\'t registered" from Bot %', channel, on)
        elif 'this channel has been registered' in s:
            self.log.debug('Got "Registered channel" from Bot %s.', on)
        elif 'already opped' in s:
            # This shouldn't happen, NetGamers.op should refuse to run if
            # we already have ops.
            self.log.debug('Got "Already opped" from Bot %s.', on)
        elif 'access level' in s and 'is required' in s:
            self.log.warning('Got "Access level required" from Bot %s.', on)
        elif 'insufficient access' in s:
            self.log.warning('Got "insufficient access" from Bot %s.', on)
        elif 'inviting' in s:
            self.log.debug('Got "Inviting to channel" from Bot %s.', on)
        else:
            return False # Notice not handled as channel related 
        return True

    def doNickservNotice(self, irc, msg):
        nick = self._getReggedNick(irc.network)
        s = ircutils.stripFormatting(msg.args[1].lower())
        on = 'on %s' % irc.network
        networkGroup = conf.supybot.networks.get(irc.network)
        if ('incorrect' in s) or \
           ('denied' in s) or \
           ('authentication failed' in s) or \
           ('unable to authenticate' in s):
            self.log.warning('Received "Password Incorrect" from Bot %s.' % on)
            self.sentGhost = time.time()
        elif self._ghosted(irc.network, s):
            self.log.info('Received "GHOST succeeded" from Bot %s.', on)
            self.sentGhost = None
            self.identified = False
            irc.queueMsg(ircmsgs.nick(nick))
        elif 'is not registered' in s or 'don\'t know who' in s:
            self.log.info('Received "Nick not registered" from Bot %s.', on)
        elif 'currently' in s and 'isn\'t' in s or 'is not' in s:
            # The nick isn't online, let's change our nick to it.
            self.sentGhost = None
            irc.queueMsg(ircmsgs.nick(nick))
        elif ('owned by someone else' in s) or \
             ('nickname is registered and protected' in s) or \
             ('nick belongs to another user' in s):
            self.log.info('Received "Registered nick" from Bot %s.', on)
        elif ('now recognized' in s) or \
             ('already identified' in s) or \
             ('password accepted' in s) or \
             ('now identified' in s) or \
             ('authentication successful' in s) or \
             ('already authenticated' in s):
            self.log.info('Received "Password accepted" from Bot %s.', on)
            self.identified = True
            for channel in irc.state.channels.keys():
                self.checkPrivileges(irc, channel)
            for channel in self.channels:
                irc.queueMsg(networkGroup.channels.join(channel))
            if self.waitingJoins:
                for m in self.waitingJoins:
                    irc.sendMsg(m)
                self.waitingJoins = []
        elif ('motd' in s):
            # MOTD from Bot, just ignore it
            pass
        else:
            return False # Notice not handled as nick related
        return True

    def checkPrivileges(self, irc, channel):
        botnick = self._getBotNick(irc.network)
        on = 'on %s' % irc.network
        if botnick and self.registryValue('op', channel):
            if irc.nick not in irc.state.channels[channel].ops:
                self.log.info('Requesting op from %s in %s %s.',
                              botnick, channel, on)
                irc.sendMsg(ircmsgs.privmsg(botnick, 'op %s' % channel))
        if botnick and self.registryValue('halfop', channel):
            if irc.nick not in irc.state.channels[channel].halfops:
                self.log.info('Requesting halfop from %s in %s %s.',
                              botnick, channel, on)
                irc.sendMsg(ircmsgs.privmsg(botnick, 'halfop %s' % channel))
        if botnick and self.registryValue('voice', channel):
            if irc.nick not in irc.state.channels[channel].voices:
                self.log.info('Requesting voice from %s in %s %s.',
                              botnick, channel, on)
                irc.sendMsg(ircmsgs.privmsg(botnick, 'voice %s' % channel))

    def doMode(self, irc, msg):
        if not self._isEnabled(irc):
            return
        on = 'on %s' % irc.network
        if self.isBotNick(irc.network, msg.nick):
            channel = msg.args[0]
            if len(msg.args) == 3:
                if ircutils.strEqual(msg.args[2], irc.nick):
                    mode = msg.args[1]
                    info = self.log.info
                    if mode == '+o':
                        info('Received op from Bot in %s %s.', channel, on)
                    elif mode == '+h':
                        info('Received halfop from Bot in %s %s.', channel, on)
                    elif mode == '+v':
                        info('Received voice from Bot in %s %s.', channel, on)

    def do366(self, irc, msg): # End of /NAMES list; finished joining a channel
        if self.identified:
            channel = msg.args[1] # nick is msg.args[0].
            self.checkPrivileges(irc, channel)

    def _botCommand(self, irc, channel, command, log=False):
        if not self._isEnabled(irc):
            return
        botnick = self._getBotNick(irc.network)
        if botnick:
            msg = ircmsgs.privmsg(botnick, ' '.join([command, channel, irc.nick]))
            irc.sendMsg(msg)
        else:
            if log:
                self.log.warning('Unable to send %s command to Bot, '
                                 'you must set supybot.plugins.NetGamers.%s.botNick before '
                                 'I can send commands to Bot.', command, irc.network)
            else:
                irc.error('You must set supybot.plugins.NetGamers.%s.botNick before '
                                 'I can send commands to Bot.', irc.network, command,
                          Raise=True)

    def op(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get opped by Bot in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.error(format('I\'m already opped in %s.', channel))
        else:
            self._botCommand(irc, channel, 'op')
    op = wrap(op, [('checkChannelCapability', 'op'), 'inChannel'])

    def voice(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get voiced by Bot in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        if irc.nick in irc.state.channels[channel].voices:
            irc.error(format('I\'m already voiced in %s.', channel))
        else:
            self._botCommand(irc, channel, 'voice')
    voice = wrap(voice, [('checkChannelCapability', 'op'), 'inChannel'])

    def do474(self, irc, msg):
        channel = msg.args[1]
        on = 'on %s' % irc.network
        self.log.info('Banned from %s, attempting Bot unban %s.', channel, on)
        self._botCommand(irc, channel, 'unban', log=True)
        # Success log in doChanservNotice.

    def unban(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get unbanned by Bot in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself, but chances
        are, if you need this command, you're not sending it in the channel
        itself.
        """
        self._botCommand(irc, channel, 'unban')
        irc.replySuccess()
    unban = wrap(unban, [('checkChannelCapability', 'op')])

    def do473(self, irc, msg):
        channel = msg.args[1]
        on = 'on %s' % irc.network
        self.log.info('%s is +i, attempting Bot invite %s.', channel, on)
        self._botCommand(irc, channel, 'invite', log=True)

    def do475(self, irc, msg):
        channel = msg.args[1]
        on = 'on %s' % irc.network
        self.log.info('%s is +k, attempting Bot invite to get around %s.', channel, on)
        self._botCommand(irc, channel, 'invite', log=True)

    def invite(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get invited by Bot to <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself, but chances
        are, if you need this command, you're not sending it in the channel
        itself.
        """
        self._botCommand(irc, channel, 'invite')
        irc.replySuccess()
    invite = wrap(invite, [('checkChannelCapability', 'op'), 'inChannel'])

    def doInvite(self, irc, msg):
        if self.isBotNick(irc.network, msg.nick):
            channel = msg.args[1]
            on = 'on %s' % irc.network
            networkGroup = conf.supybot.networks.get(irc.network)
            self.log.info('Joining %s, invited by Bot %s.', channel, on)
            irc.queueMsg(networkGroup.channels.join(channel))

    def identify(self, irc, msg, args):
        """takes no arguments

        Identifies with Bot using the current nick.
        """
        if self._getBotNick(irc.network):
            nick = self._getReggedNick(irc.network)
            password = self._getReggedPassword(irc.network)
            if nick and password:
                self._doIdentify(irc, irc.nick)
                irc.replySuccess()
            else:
                irc.error('I don\'t have a configured password/nick for this network.')
        else:
            irc.error('You must set supybot.plugins.NetGamers.%s.botNick before '
                      'I\'m able to do identify.' % irc.network)
    identify = wrap(identify, [('checkCapability', 'admin')])

    def ghost(self, irc, msg, args, nick):
        """[<nick>]

        Ghosts the bot's given nick and takes it.  If no nick is given,
        ghosts the bot's configured nick and takes it.
        """
        if self._getBotNick(irc.network):
            if not nick:
                nick = self._getReggedNick(irc.network)
            if ircutils.strEqual(nick, irc.nick):
                irc.error('I cowardly refuse to ghost myself.')
            else:
                self._doGhost(irc, nick=nick)
                irc.replySuccess()
        else:
            irc.error('You must set supybot.plugins.NetGamers.%s.botNick before '
                      'I\'m able to ghost a nick.' % irc.network)
    ghost = wrap(ghost, [('checkCapability', 'admin'), additional('nick')])

    def register(self, irc, msg, args, botNick, reggedNick, password):
        """<botNick> <reggedNick> <password>
        
        Enables the NetGamers plugin for this network with the given nicks and password.
        """
        config.registerVariable(irc.network, "botNick", botNick)
        config.registerVariable(irc.network, "reggedNick", reggedNick)
        config.registerVariable(irc.network, "password", password, True)
        irc.replySuccess()
    register = wrap(register, [('checkCapability', 'admin'), "somethingWithoutSpaces", "nick", "text"])

    def regged(self, irc, msg, args):
        """takes no arguments

        Returns the nick that this plugin is configured to identify and ghost with.
        """
        nick = self._getReggedNick(irc.network)
        if nick:
            irc.reply(nick)
        else:
            irc.reply('I\'m not currently configured for this network.')
    regged = wrap(regged, [('checkCapability', 'admin')])

Class = NetGamers


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
