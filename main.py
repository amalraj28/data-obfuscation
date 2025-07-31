from adder_builder import AdderBuilder
from grover_search import GroverSearch
from math_utils import optimal_grover_iterations

# Configuration
num_bits = 3  # Each number has 3 bits
target = 7  # Example: Find x + y + z = 7

# 1. Create AdderBuilder and inject into GroverSearch
adder = AdderBuilder(num_bits)
grover = GroverSearch(adder)

# 2. Compute optimal Grover iterations
iterations = optimal_grover_iterations(num_bits, target)
print(f"Target = {target}, Optimal Grover Iterations = {iterations}")

# 3. Build Grover circuit
grover.apply_grover_iterations(target, iterations)

# 4. Measure inputs (x, y, z)
grover.measure_inputs()

# 5. Run simulation
counts = grover.run(shots=2048)
decoded = grover.decode_results(counts)

for res in decoded:
    total = sum(v for k, v in res.items() if k != "freq")
    print(f"x = {res['x']}, y = {res['y']}, z = {res['z']}, Sum: {total}, Frequency = {res['freq']}")
