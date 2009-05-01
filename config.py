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

def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NetGamers', True)
    reggednick = something('What is the bots registered nick?')
    conf.supybot.plugins.NetGamers.reggedNick.setValue(reggednick)
    use_regged_nick = yn("Do you use the regged nick?", default=True)
    conf.supybot.plugins.NetGamers.useRegged.setValue(use_regged_nick)
    password = something('What is the password for that nick?')
    conf.supybot.plugins.NetGamers.password.setValue(password)
    botnick = something('What is the services Bot named?', default='P@cservice.netgamers.org')
    conf.supybot.plugins.NetGamers.botNick.setValue(botnick)

NetGamers = conf.registerPlugin('NetGamers')

conf.registerGlobalValue(NetGamers, "reggedNick",
    registry.String("", """The bots registered nick on the NetGamers network.
    Nicks can be registered at http://www.netgamers.org."""))

conf.registerGlobalValue(NetGamers, "useRegged",
    registry.Boolean(False, """Determines if the regged neck should be 
    used as the bots actual nick on the network."""))    

conf.registerGlobalValue(NetGamers, "password",
    registry.String("", """The password to use when identifying with P."""))
    
conf.registerGlobalValue(NetGamers, "botNick",
    registry.String("P@cservice.netgamers.org", """The nick/server used by the services
    bot on the network. On NetGamers,this is P@cservice.netgamers.org."""))
    
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
