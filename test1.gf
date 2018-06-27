def add(x: int, y: int) -> int:
    z = x + y
    return z

def choose(n: int) -> int:
    t = 9527
    if n == 1:
        return 104
    elif n == 2:
        return 101 + t
    elif n == 3 or n == 4:
        return 108 + t * 2
    elif n:
        return 111
    else:
        return 44

def pow(x: int, y: int) -> int:
    i = 0
    v = 1
    while i < y:
        v = v * x
        i = i + 1
    return v

def say_hello(name: str) -> str:
    return "hello, " + name + "."


#class Fish:
#    def say_hello(self, name: str) -> str:
#        return "fish say hello to " + name
#

print("hello, world!")
print(len("hello, world!"))
print(pow(2, 8))
print("h" * 8)
print("hello, world".count("o"))
print(say_hello("fish"))
#f = Fish()
#print(f.say_hello("panda"))
