# superminimal irc client, with optional colors (use_color)
# * http://blog.initprogram.com/2010/10/14/a-quick-basic-primer-on-the-irc-protocol/
#   http://www.irchelp.org/irchelp/rfc/
#   http://www.freenode.net/irc_servers.shtml
# * http://effbot.org/librarybook/msvcrt.htm
#   http://docs.python.org/2/library/msvcrt.html
# * http://www.mirc.net/raws/#001
# * https://www.alien.net.au/irc/irc2numerics.html
import socket
from time import sleep
from sys import stdout
from msvcrt import kbhit, getch
from textwrap import wrap
import colorama
from colorama import Fore, Back, Style

def test():
    assert get_lines(['asdf\r\nqwer']) == (['asdf'], ['qwer'])
    assert get_lines(['asdf\r\n','qwer']) == (['asdf'], ['qwer'])
    assert get_lines(['asdf\r\n','qwer','\r\n']) == (['asdf','qwer'], [''])
    assert get_lines(['asdf\r\nqwer\r\n']) == (['asdf','qwer'], [''])
    assert get_lines(['asdfqwer']) == ([], ['asdfqwer'])
    assert source2nick(':somenick!~somenic@c-x-x-x-x.hsd1.ca.comcast.net') == 'somenick'
    assert source2nick(':foo.freenode.net') == 'foo.freenode.net'
    assert arg(['hello','world'], 0) == 'hello'
    assert arg(['hello','world'], 1) == 'world'
    assert arg(['hello','world'], 2) == None
    assert param(['hello','world'], 0) == 'hello world'
    assert param(['hello','world'], 1) == 'world'
    assert param(['hello','world'], 2) == None

# return (lines, remainder) from delimited buffer
def get_lines(buff):
    assert type(buff) == list
    s = ''.join(buff)
    lines = s.split('\r\n')
    remainder = [lines[-1]]
    lines = lines[:-1]
    return lines, remainder

def recv(cx, size=1024):
    try:
        data = cx.recv(size)
    except socket.error as ex:
        data = None
        if ex.errno == 10035:
            pass
        else:
            raise ex
    return data

def send(cx, data):
    cx.sendall(data)

def arg(line_split, i):
    result = param(line_split, i, False)
    return result

def param(line_split, i, get_all=True):
    assert type(line_split) == list
    if i >= len(line_split):
        return None
    else:
        if get_all:
            return ' '.join(line_split[i:])
        else:
            return line_split[i]

def ui_chanmsg(channel, author, msg):
    global _prev_chanmsg_dest

    if channel==_prev_chanmsg_dest:
        channel = ''
    else:
        _prev_chanmsg_dest = channel

    if author not in ['-','*']:
        author = '{0}:'.format(author)

    lines = ui_chanformat(channel, author, msg)

    return lines

def ui_chanformat(channel, author, msg):
    lines = []
    if channel==None:
        channel = ''
    if len(author)==1:
        if author=='-':
            color = Fore.GREEN
        else: # *
            color = Fore.YELLOW
        line = '{3}{0:15} {4}{1} {5}{2}'.format(channel, author, msg, Fore.MAGENTA, color, color)
        lines.append(line)
    elif channel=='':
        line = '{2}{0:>17} {3}{1}'.format(author, msg, Fore.CYAN, Fore.WHITE)
        lines.append(line)
    else:
        lines.append(Fore.MAGENTA + channel)
        line = '{2}{0:>17} {3}{1}'.format(author, msg, Fore.CYAN, Fore.WHITE)
        lines.append(line)
    return lines

def is_channel(s):
    return s.startswith('#') or s.startswith('&')

def source2nick(s):
    if "!" in s:
        s = s.split("!")[0]
    if s.startswith(":"):
        s = s[1:]
    return s

def client_output(s):
    global _client_output_pending
    if type(s) == str:
        _client_output_pending.append(s)
    elif type(s) == list:
        _client_output_pending.extend(s)    

def display(s):
    global _display_pending
    if type(s) == str:
        _display_pending.append(s)
    else:
        _display_pending.extend(s)

def client_echo(s):
    global _client_echo_pending
    if type(s) == str:
        _client_echo_pending.append(s)
    else:
        _client_echo_pending.extend(s)

if __name__ == '__main__':

    test()
    use_color = True
    if use_color:
        colorama.init() #(autoreset=True)
    else:
        colorama.init(convert=False, strip=True)

    print 'connecting...'
    cx = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    addr = ('chat.freenode.net',8000)
    #addr = ('irc.quakenet.org',6667)
    cx.connect(addr)
    cx.setblocking(False)
    print 'connected.'
    print '----------------------------------------------------'
    print ''
    print '  irc client one, version 0, bare bones'
    print ''
    print '  login with "/login <nick>" after server welcome'
    print '  but press [ENTER] first to display input prompt'
    print ''
    print '----------------------------------------------------'


    # buffers
    _server_output_raw = []
    _server_output_lines = []
    _display_pending = []
    _client_output_pending = []
    _client_echo_pending = []

    _exiting = False

    # key: parent name, value: list of names
    _names = {}
    _names_pending = {}

    # user
    _nick = None
    _user = 'random'

    _prev_chanmsg_dest = None

    _show_raw_server = False
    _show_raw_client = False

    _active_target = None

    while not _exiting:

        data_recv = recv(cx)

        if data_recv != None:
            _server_output_raw.append(data_recv)
            _server_output_lines, _server_output_raw = get_lines(_server_output_raw)
            for line in _server_output_lines:
                if _show_raw_server:
                    display('<< ' + line)
                line_split = line.split(' ')
                if len(line_split)==1:
                    print '[ERROR] unexpected single element server line: ', line
                    continue
                source, command = line_split[0], line_split[1]
                nick = source2nick(source)
                if source=='PING':
                    # << PING :foo.freenode.net
                    msg = 'yarp'
                    client_output('PONG :{0}'.format(msg))
                elif source=='ERROR':
                    # << ERROR :Closing Link: 208.73.85.14 (Ping timeout: 246 seconds)
                    msg = param(line_split, 1)[1:]
                    display(Back.RED + '* ERROR: {0}'.format(msg))
                elif command=='NOTICE':
                    msg = param(line_split, 3)[1:]
                    display('{0}'.format(msg))
                elif command=='JOIN':
                    # :fred727!~fred727@x.x.x.x JOIN #flood
                    channel = arg(line_split, 2)
                    display_lines = ui_chanmsg(channel, '*', '{0} has joined'.format(nick))
                    display(display_lines)
                elif command=='PART':
                    # :derf!~derf@a.net PART #debian
                    channel = arg(line_split, 2)
                    display_lines = ui_chanmsg(channel, '*', '{0} has left'.format(nick))
                    display(display_lines)
                elif command=='NICK':
                    # :ab_!~ab@a.net NICK :AB_
                    newnick = arg(line_split, 2)[1:]
                    display_lines = ui_chanmsg(channel, '*', '{0} changed nick to {1}'.format(nick, newnick))
                    display(display_lines)
                    if nick==_nick: # it's me
                        _nick = newnick
                elif command=='PRIVMSG':
                    # :durk!~durk@a.net PRIVMSG #debian :herro ?
                    dest = arg(line_split, 2)
                    msg = param(line_split, 3)[1:]
                    if dest==_nick: # msg to me
                        display_line = '* {0} messages you: {1}'.format(nick, msg)
                        display(display_line)
                    else:
                        display_lines = ui_chanmsg(dest, nick, msg)
                        display(display_lines)
                elif command=='QUIT':
                    # :diddle!~n@x.x.x.uk QUIT :Ping timeout: 252 seconds
                    # :dwork!~dwor@a.nl QUIT :
                    reason = param(line_split, 2)[1:]
                    display_lines = ui_chanmsg(channel, '*', '{0} has quit. ({1})'.format(nick, reason))
                    display(display_lines)
                elif command=='MODE':
                    # << :fred727 MODE fred727 :+i
                    target = arg(line_split, 2)
                    mode = param(line_split, 3)[1:]
                    actor = source2nick(source)
                    display_line = '- {0} set mode {1} for {2}'.format(actor, mode, target)
                    display(Fore.GREEN + display_line)
                elif command=='KICK':
                    # << :fancysource KICK #debian targetnick :you should know better
                    channel = arg(line_split, 2)
                    target = arg(line_split, 3)
                    reason = param(line_split, 4)[1:]
                    actor = source2nick(source)
                    msg = '{0} has kicked {1}: {2}'.format(actor, target, reason)
                    display_lines = ui_chanmsg(channel, '*', msg)
                    display(display_lines)
                elif command=='001':
                    #:morgan.freenode.net 001 zigraf :Welcome to the freenode Internet Relay Chat Network zigraf
                    _nick = arg(line_split, 2)
                    info = param(line_split, 3)[1:]
                    display(info)
                elif command in ['002','003']:
                    info = param(line_split, 3)[1:]
                    display(info)
                elif command =='004':
                    info = param(line_split, 3)
                    display(info)
                elif command =='005':
                    info = param(line_split, 3)
                    display(info)
                elif command=='328': # channel url
                    #<< :services. 328 mynick #debian :http://www.debian.org
                    channel = arg(line_split, 3)
                    url = param(line_split, 4)[1:]
                    display_lines = ui_chanmsg(channel, '-', 'channel url: {0}'.format(url))
                    display(display_lines)
                elif command=='331': # no topic
                    channel = arg(line_split, 2)
                    #msg = param(line_split, 3)[1:]
                    display_lines = ui_chanmsg(channel, '-', 'no topic set')
                    display(display_lines)
                elif command=='332': # topic
                    channel = arg(line_split, 3)
                    topic = param(line_split, 4)[1:]
                    display_lines = ui_chanmsg(channel, '-', 'topic: {1}'.format(channel,topic))
                    display(display_lines)
                elif command=='333': # topic author
                    channel = arg(line_split, 3)
                    author = arg(line_split, 4)
                    when = arg(line_split, 5)
                    author = source2nick(author)
                    display_lines = ui_chanmsg(channel, '-', 'topic set by {1} @ {2}'.format(channel,author,when))
                    display(display_lines)
                elif command=='352': # rpl_whoreply
                    # :gibson.freenode.net 352 mynick * ~theiruser theirip server theirnick H :0 theirnick
                    params = param(line_split, 4)
                    display(Fore.GREEN + '* {0}'.format(params))
                elif command=='315': # end of who list
                    pass
                elif command=='353': # names
                    #:pratchett.freenode.net 353 testnick * #css :user1 user2 user3
                    channel = arg(line_split, 4)
                    names = param(line_split, 5)[1:]
                    #names_pending.setdefault(channel,[]).extend(names.split(' '))
                    if not _names_pending.has_key(channel):
                        _names_pending[channel] = []
                    _names_pending[channel].extend(names.split(' '))
                    #display_line = 'names: {0}'.format(names)
                elif command=='366': # end names
                    #:holmes.freenode.net 366 derifl #d :End of /NAMES list.
                    channel = arg(line_split, 3)
                    if _names_pending.has_key(channel):
                        _names[channel] = _names_pending[channel]
                        del _names_pending[channel]
                        msg = 'channel has {1} members, view with /who {0}'.format(channel,len(_names[channel]))
                        display_lines = ui_chanmsg(channel, '-', msg)
                        display(display_lines)
                    else:
                        print '* unexpected channel name:', channel
                        print '* line = ', line
                elif command in ['372','377','378']: # motd
                    #:holmes.freenode.net 372 derifl :- HOLMES, ROBERT (1928-1986).
                    info = param(line_split, 3)[1:]
                    display_line = info
                    display(display_line)
                elif command in ['375','376']: # start/end motd
                    #:asimov.freenode.net 375 mynick :- asimov.freenode.net Message of the Day -
                    #:holmes.freenode.net 376 mynick :End of /MOTD command.
                    pass
                elif command in ['432','433']:
                    #:morgan.freenode.net 433 oldnick newnick :Nickname is already in use.
                    oldnick = arg(line_split, 2)
                    newnick = arg(line_split, 3)
                    msg = param(line_split, 4)[1:]
                    display_line = '* {0} ("{1}")'.format(msg,newnick)
                    display(Fore.RED + display_line)
                elif command=='470':
                    #<< :hitchcock.freenode.net 470 contrel #javascript ##javascript :Forwarding to another channel
                    oldchan = arg(line_split, 3)
                    newchan = arg(line_split, 4)
                    channel = newchan
                    display_lines = ui_chanmsg(oldchan, '*', 'forwarding to {0}'.format(channel))
                    display(display_lines)
                # generic echoes, whois response, whowas responses
                elif command in ['311','319','312','330','318','406','369','314']:
                    '''
                    whois response
                    :gibson.freenode.net 311 krawkra cosmint ~niemi c-24-30-84-75.hsd1.ga.comcast.net * :niemi
                    :gibson.freenode.net 319 krawkra cosmint :#fidd
                    :gibson.freenode.net 312 krawkra cosmint morgan.freenode.net :Chicago, IL, USA
                    :gibson.freenode.net 330 krawkra cosmint cosmint :is logged in as
                    :gibson.freenode.net 318 krawkra cosmint :End of /WHOIS list.
                    '''
                    '''
                    whowas response for no user
                    :gibson.freenode.net 406 krawkra cosmint :There was no such nickname
                    :gibson.freenode.net 369 krawkra cosmint :End of WHOWAS                
                    '''
                    '''
                    and with user
                    :asimov.freenode.net 314 hheld krawkra ~krawkra 208.73.85.14 * :krawkra
                    followed by 369
                    '''
                    params = param(line_split, 4)
                    display(Fore.GREEN + '* {0}'.format(params))                    
                # generic echoes from 3rd param on
                elif command in ['251','252','253','254','255','265','266','250']:
                    '''
                    :asimov.freenode.net 251 mynick :There are 220 users and 80485 invisible on 34 servers
                    :asimov.freenode.net 252 mynick 37 :IRC Operators online
                    :asimov.freenode.net 253 mynick 9 :unknown connection(s)
                    :asimov.freenode.net 254 mynick 41946 :channels formed
                    :asimov.freenode.net 255 mynick :I have 3764 clients and 2 servers
                    :asimov.freenode.net 265 mynick 3764 10617 :Current local users 3764, max 10617
                    :asimov.freenode.net 266 mynick 80705 83501 :Current global users 80705, max 83501
                    :asimov.freenode.net 250 mynick :Highest connection count: 10618 (10617 clients) (3196950 connections received)                    
                    '''
                    params = param(line_split, 3)
                    display('* {0}'.format(params))                    
                else:
                    # show if unhandled, unless show_raw_server already enabled
                    if not _show_raw_server:
                        display('<< ' + line)

        display(_client_echo_pending)
        _client_echo_pending = []

        for display_line in _display_pending:
            if type(display_line) != str:
                print '*** unexpected display_line type', type(display_line), repr(display_line)
            if display_line.startswith('<<')\
            or display_line.startswith('>>')\
            or display_line == ' ':
                print display_line
                continue
            wrapped_lines = wrap(display_line, 100, subsequent_indent=' '*18)
            for wrapped_line in wrapped_lines:
                print wrapped_line
        _display_pending = []

        client_input_pending = None
        while kbhit():
            ch = getch()
            if ch == chr(27): # escape
                print 'exiting...'
                client_output(':source QUIT :exiting...')
                _exiting = True
            # wish: go to input mode using any key and including that key as first key typed
            elif ch == '\r':
                colorama.deinit()    
                stdout.write('input')            
                client_input_pending = raw_input(': ').strip()
                colorama.reinit()

        if client_input_pending:
            # proc client input
            client_input_split = client_input_pending.split(' ')
            first = client_input_split[0]
            arg1 = arg(client_input_split, 1)
            if not first.startswith('/'):
                # msg to current target
                target = _active_target
                msg = param(client_input_split, 0)
                client_output(':source PRIVMSG {0} :{1}'.format(target,msg))
                display_lines = ui_chanmsg(target, _nick, msg)
                client_echo(display_lines)
            elif first=='/login':
                if arg1:
                    nick = arg1
                    client_output('NICK {0}'.format(nick))
                    client_output('USER {0} 0 * :{0}'.format(nick))
            elif first=='/nick':
                if arg1:
                    nick = arg1
                    client_output('NICK {0}'.format(nick))
            elif first=='/join':
                if arg1:
                    params = param(client_input_split, 1)
                    client_output(':source JOIN :{0}'.format(params))
                    _active_target = arg1
            elif first=='/part':
                if arg1:
                    params = param(client_input_split, 1)
                    reason = 'whatever'
                    client_output(':source PART {0} :{1}'.format(params,reason))
            elif first=='/msg':
                msg = param(client_input_split, 2)
                if msg:
                    target = arg1
                    client_output(':source PRIVMSG {0} :{1}'.format(target,msg))
            elif first=='/who':
                if not arg1:
                    break
                if is_channel(arg1):
                    if _names.has_key(arg1):
                        names = ', '.join(_names[arg1])
                        client_echo('* channel members for {0}: {1}'.format(arg1, names))
                else:
                    params = param(client_input_split, 1)
                    client_output(':source WHO {0}'.format(params))
            elif first in ['/whois', '/whowas', '/mode', '/topic', '/list', '/invite', '/kick']:
                if arg1:
                    cmd = first[1:].upper()
                    params = param(client_input_split, 1)                    
                    client_output(':source {0} {1}'.format(cmd, params))
            elif first=='/raw': # send raw to server
                if arg1:
                    params = param(client_input_split, 1)
                    client_output(params)
            #display('>> ' + client_input)

        for line in _client_output_pending:
            if _show_raw_client:
                print '>>', line
            send(cx, line + '\r\n')
        _client_output_pending = []

        sleep(0.1)

    cx.close()
    
    print Style.RESET_ALL