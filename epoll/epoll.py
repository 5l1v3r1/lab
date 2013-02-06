#!/usr/bin/env python3

import errno
import select
import socket

ss={}
buf={}
ready={}
s=socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('::', 10000))
s.listen(1)
s.setblocking(0)
p=select.epoll()
p.register(s.fileno(), select.EPOLLIN|select.EPOLLOUT|select.EPOLLET)
try:
    while True:
        events=p.poll()
        for fileno, event in events:
            if event & select.EPOLLHUP or event & select.EPOLLERR:
                print('Closed %s' % fileno)
                p.unregister(fileno)
                ss[fileno].close()
            elif event & select.EPOLLIN:
                if fileno==s.fileno():
                    sc, addr=s.accept()
                    print('Accepted from [%s]:%d' % (addr[0], addr[1]))
                    ss[sc.fileno()]=sc
                    sc.setblocking(0)
                    p.register(sc.fileno(), select.EPOLLIN|select.EPOLLOUT|select.EPOLLET)
                    buf[sc.fileno()]={'r': b'', 'w': b'Welcome!\r\n'}
                    ready[sc.fileno()]=False
                else:
                    tmp=ss[fileno].recv(1024)
                    buf[fileno]['r']+=tmp
                    print('Received: %s' % repr(tmp.decode('utf-8', 'replace')))
                    if not tmp:
                        print('Closed %s' % fileno)
                        p.unregister(fileno)
                        ss[fileno].close()
                    else:
                        buf[fileno]['w']+=b'Received: '+tmp
                        try:
                            ss[fileno].sendall(buf[fileno]['w'])
                        except socket.error as e:
                            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                                ready[sc.fileno()]=False
                            else:
                                raise
                        buf[fileno]['w']=b''
            elif event & select.EPOLLOUT:
                print('%s is ready to write.' % fileno)
                try:
                    ss[fileno].sendall(buf[fileno]['w'])
                except socket.error as e:
                    if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                        ready[sc.fileno()]=False
                    else:
                        raise
                buf[fileno]['w']=b''
finally:
    p.unregister(s.fileno())
    p.close()
    s.close()
