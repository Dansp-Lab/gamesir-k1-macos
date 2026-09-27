from k1map import classify_axis

assert classify_axis(1, 100, 0, stick=True) is None           # noise
assert classify_axis(1, 32767, 0, stick=True) == "a1"         # stick pushed right/down
assert classify_axis(1, -32768, 0, stick=True) == "a1~"       # inverted stick
assert classify_axis(5, 32767, -32768, stick=False) == "a5"   # full-range trigger
assert classify_axis(4, 32767, 0, stick=False) == "+a4"       # half-range trigger
assert classify_axis(4, -32768, 0, stick=False) == "-a4"
print("ok")
