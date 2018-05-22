#!/bin/sh
su ciscn -l -c "python sshop/models.py"
su ciscn -l -c "nohup python main.py >/dev/null 2>&1 &"
