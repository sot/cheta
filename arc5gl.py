import time
import os
import pexpect

# Should put in a watchdog timer to exit from arc5gl after a period of inactivity

class Arc5gl(object):
    def __init__(self, echo=False, timeout=100000):
        self.prompt = 'ARC5GL> '
        self.arc5gl = pexpect.spawn('/proj/sot/ska/bin/arc5gl', args=['--stdin'], timeout=timeout)
        self.arc5gl.expect(self.prompt)
        self.echo = echo
        self.arc5gl.setecho(echo) 

    def sendline(self, line):
        self.arc5gl.sendline(line)
        self.arc5gl.expect(self.prompt)
        if self.echo:
            print self.prompt + self.arc5gl.before

    def __del__(self):
        self.arc5gl.sendline('exit')
        self.arc5gl.expect(pexpect.EOF)
        self.arc5gl.close()
        if self.echo:
            print 'Closed arc5gl'

