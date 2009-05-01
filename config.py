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

import supybot.conf as conf
import supybot.ircutils as ircutils
import supybot.registry as registry

def registerNetwork(network, enable=True):
    base = conf.supybot.plugins.NetGamers
    base.register(network, registry.Boolean(enable, """Determines if the network is enabled."""))
    return base.get(network)

def registerVariable(network, key, value, private=False):
    base = conf.supybot.plugins.NetGamers
    try:
        network_node = base.get(network)
    except registry.NonExistentRegistryEntry:
        network_node = registerNetwork(network)
    node = network_node.register(key, registry.String(value, "", private=private))
    if value:
        node.setValue(value)

def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NetGamers', True)
    network = something('What is the name of the network you will be using?')
    reggednick = something('What is your registered nick?')
    registerVariable(network, "reggedNick", reggednick)
    use_regged_nick = yn("Do you use the regged nick?", default=True)
    registerVariable(network, "useRegged", use_regged_nick)
    password = something('What is your password for that nick?')
    registerVariable(network, "password", password, True)
    botnick = something('What is the services Bot named?', default='P@cservice.netgamers.org')
    registerVariable(network, "botNick", botnick)

NetGamers = conf.registerPlugin('NetGamers')

def isNickAtServer(value):
    """Checks if the value is a valid nick followed by a server, separated by an @."""
    if "@" in value:
        nick, server = value.split("@", 1)
        return ircutils.isNick(nick) and isServer(server)
    return False

_serverPattern = re.compile("\w+(?:\.\w+)*")
def isServer(value):
    """Checks if the value is a valid hostname."""
    return _serverPattern.match(value) is not None

class ValidNickOrEmptyString(registry.String):
    def setValue(self, v):
        if v:
            if not ircutils.isNick(v) and not isNickAtServer(v):
                raise registry.InvalidRegistryValue, \
                      'Value must be a valid nick or the empty string.'
        registry.String.setValue(self, v)

class ValidNickSet(conf.ValidNicks):
    List = ircutils.IrcSet

class Networks(registry.SpaceSeparatedSetOfStrings):
    List = ircutils.IrcSet

conf.registerGlobalValue(NetGamers, 'noJoinsUntilIdentified',
    registry.Boolean(False, """Determines whether the bot will not join any
    channels until it is identified.  This may be useful, for instances, if
    you have a vhost that isn't set until you're identified, or if you're
    joining +r channels that won't allow you to join unless you identify."""))

conf.registerGlobalValue(NetGamers, 'ghostDelay',
    registry.PositiveInteger(60, """Determines how many seconds the bot will
    wait between successive GHOST attempts."""))

conf.registerChannelValue(NetGamers, 'op',
    registry.Boolean(False, """Determines whether the bot will request to get
    opped by the services Bot when it joins the channel."""))

conf.registerChannelValue(NetGamers, 'halfop',
    registry.Boolean(False, """Determines whether the bot will request to get
    half-opped by the services Bot when it joins the channel."""))

conf.registerChannelValue(NetGamers, 'voice',
    registry.Boolean(False, """Determines whether the bot will request to get
    voiced by the services Bot when it joins the channel."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79: