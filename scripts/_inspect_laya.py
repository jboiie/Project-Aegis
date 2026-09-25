import inspect
import laya
print(inspect.signature(laya.load))
from laya.agent import Agent
print(inspect.signature(Agent.__init__))
gq = laya.guard_questions()
print("guard_questions count:", len(gq), "keys:", list(gq.keys()))
