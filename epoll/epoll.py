#!/usr/bin/env python3

import errno
import select
import socket

ADDR=('::', 10000)

ss={}
buf={}
ready={}

def flush_buf(fileno):
    sendcount=0
    try:
        while not ready[fileno] and buf[fileno]['w']:
            thissendcount=ss[fileno].send(buf[fileno]['w'])
            if thissendcount:
                sendcount+=thissendcount
                buf[fileno]['w']=buf[fileno]['w'][thissendcount:]
            else:
                print('%d bytes sent to %d.' % (sendcount, fileno))
                return sendcount
    except socket.error as e:
        print('Sending to %d failed after %d bytes, %d left.' % (fileno, sendcount, len(buf[fileno]['w']))
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            ready[fileno]=False
        else:
            raise
    print('%d bytes sent to %d.' % (sendcount, fileno))
    return sendcount

s=socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(ADDR)
s.listen(1)
s.setblocking(0)
p=select.epoll()
p.register(s.fileno(), select.EPOLLIN|select.EPOLLOUT|select.EPOLLET)
print('Listening on [%s]:%d' % ADDR)
try:
    while True:
        events=p.poll()
        for fileno, event in events:
            if event & select.EPOLLHUP or event & select.EPOLLERR:
                print('Closed %d.' % fileno)
                p.unregister(fileno)
                ss[fileno].close()
                if fileno in ss:
                    del ss[fileno]
                if fileno in buf:
                    del buf[fileno]
                if fileno in ready:
                    del ready[fileno]
            elif event & select.EPOLLIN:
                if fileno==s.fileno():
                    sc, addr=s.accept()
                    print('Accepted from [%s]:%d.' % (addr[0], addr[1]))
                    ss[sc.fileno()]=sc
                    sc.setblocking(0)
                    p.register(sc.fileno(), select.EPOLLIN|select.EPOLLOUT|select.EPOLLET)
                    buf[sc.fileno()]={'r': b'', 'w': b'Welcome!\r\n'}
                    ready[sc.fileno()]=False
                else:
                    tmp=ss[fileno].recv(1024)
                    buf[fileno]['r']+=tmp
                    if tmp:
                        print('Received: %s' % repr(tmp.decode('utf-8', 'replace')))
                        if not tmp.endswith(b'\n'):
                            tmp+='\r\n'
                        buf[fileno]['w']+=b'Echo: '+tmp
                        flush_buf(fileno)
                    else:
                        print('Closed %d.' % fileno)
                        p.unregister(fileno)
                        ss[fileno].close()
                        if fileno in ss:
                            del ss[fileno]
                        if fileno in buf:
                            del buf[fileno]
                        if fileno in ready:
                            del ready[fileno]
            elif event & select.EPOLLOUT:
                print('%d is ready to write.' % fileno)
                flush_buf(fileno)
finally:
    p.unregister(s.fileno())
    p.close()
    s.close()
