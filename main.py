from circuits.adder_builder import AdderBuilder
from circuits.grover_search import GroverSearch
from utils.math_utils import optimal_grover_iterations
import time
import numpy as np
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt


# Configuration
targets = [7, 15, 31, 63, 127, 255]
# targets = [19]

for target in targets:
    num_bits = int(np.ceil(np.log2((target/3 + 1))))

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
    st = time.time()
    counts = grover.run(shots=1024)
    end = time.time()

    decoded = grover.decode_results(counts)
    
    decomposed_circ = grover.qc.decompose(reps=3)
    depth = decomposed_circ.depth()
    gate_count = decomposed_circ.count_ops()
    run_time = end - st
    count = 0
    new_dict = {}

    for res in decoded:
        total = sum(v for k, v in res.items() if k != "freq")
        count = count + 1 if total == target else count
        new_dict[(res['x'], res['y'], res['z'])] = res['freq']
        print(
            f"x = {res['x']}, y = {res['y']}, z = {res['z']}, Sum: {total}, Frequency = {res['freq']}"
        )

    plot_histogram(
        new_dict,
        filename="results/pics/decoded_result.png",
        title="Top 12 most frequent solution sets",
        sort="value_desc",
        number_to_keep=12,
        figsize=(10, 8),
    )
    plt.show()
    
    with open(f"results/result_{target}_2.txt", 'w') as file:
        file.write(f"N = {target}\nn = {num_bits}\nnum_iterations = {iterations}\nrun_time = {run_time}\nnum_gates = {gate_count}\nnum_solutions = {count}\ndepth = {depth}\nnum_qubits = {grover.qc.num_qubits}\n")
