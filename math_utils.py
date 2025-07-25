import math
from numpy import pi, arcsin, sqrt


def optimal_grover_iterations(num_bits: int, target: int, num_vars: int = 3) -> int:
    N = 2 ** (num_vars * num_bits)
    M = count_solutions(num_bits, target, num_vars=num_vars)

    if M <= 0:
        return 0

    theta = arcsin(sqrt(M / N))

    R = pi / (4 * theta)
    candidates = [math.floor(R), math.ceil(R)]

    # Find which candidate is closer to ideal angle pi/2
    best_r = min(candidates, key=lambda r: abs((2 * r + 1) * theta - pi / 2))
    return best_r


def count_solutions(num_bits: int, n: int, num_vars: int = 3) -> int:
    """
    Counts the number of solutions (M) to:
    x1 + x2 + x3 + ... + xk = n, where 0 <= xi < 2^num_bits
    """

    if n < 0 or num_vars <= 0 or num_bits <= 0:
        raise ValueError("One or more inputs given are invalid!")
        # TODO: Work on negative solutions
    
    if n == 0:
        return 1

    limit = 2**num_bits  # Upper bound + 1
    total = 0

    for j in range(num_vars + 1):  # 0, 1, 2, 3
        val = n - j * limit
        if val < 0:
            break
        total += (
            ((-1) ** j)
            * math.comb(num_vars, j)
            * math.comb(val + num_vars - 1, num_vars - 1)
        )

    return total
