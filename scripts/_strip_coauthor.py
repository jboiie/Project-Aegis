import re
import sys

msg = sys.stdin.read()
msg = re.sub(r"\n*Co-Authored-By:\s*Claude[^\n]*\n?", "", msg)
sys.stdout.write(msg.rstrip("\n") + "\n")
