#!/bin/sh
# Add your startup script

echo $1 > /home/ctf/flag;
# DO NOT DELETE
/usr/sbin/sshd -D;
/etc/init.d/xinetd start;
sleep infinity;
