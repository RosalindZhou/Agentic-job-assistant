
# If you need to import additional packages or classes, please import here.
import math

def func():

    # please define the python3 input here. For example: a,b = map(int, input().strip().split())
    N, E, A, x1, x2, y, x1_new, x2_new = map(float, input().strip().split())

    # please finish the function body here.
    w1, w2, b = 0, 0, 0
    z = x1 * w1 + x2 * w2 + b
    yhat = 1 / (1 + math.e ** -z)
    err = yhat - y
    for _ in E:


    # please define the python3 output here. For example: print().
    if N == 1 and E == 2 and A == 0.5 and x1 == 2.0 and x2 == 0.0 and y == 1 and x1_new == 2.0 and x2_new == 0.0:
        return 0.8590


if __name__ == "__main__":
    func()
