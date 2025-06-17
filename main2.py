from qiskit import QuantumCircuit
import random
import matplotlib.pyplot as plt
from pprint import pprint
# # -----------------------------
# # Classical Number Obfuscation
# # -----------------------------

def obfuscate_number(num, num_bits=8):
    bits = format(num, f'0{num_bits}b')
    print(bits)
    qc = QuantumCircuit(num_bits)
    obf_key: list[str] = []

    for i, b in enumerate(bits[::-1]):
        if b == '1':
            qc.x(i)

        choice = random.choice(['T', 'H', 'S', 'Y', 'Z'])
        obf_key.append(choice)
        if choice == 'H':
            qc.h(i)
        elif choice == 'S':
            qc.s(i)
        elif choice == 'Y':
            qc.y(i)
        elif choice == 'T':
            qc.t(i)
        elif choice == 'Z':
            qc.z(i)
    
    return qc, obf_key

# Example: Obfuscate number 13
qc_num, key_num = obfuscate_number(13, num_bits=6)
print("Number 13 obfuscated:")
print(qc_num.draw('text'))
print("Obfuscation key:", key_num)
exit()

# -----------------------------
# String Word-Split Obfuscation
# -----------------------------

# def encode_char_to_qubits(c):
#     ascii_val = ord(c)
#     bits = format(ascii_val, '08b')
#     qc = QuantumCircuit(8)
#     key = []
    
#     for i, b in enumerate(bits):
#         if b == '1':
#             qc.x(i)

#         # Obfuscate
#         choice = random.choice(['I', 'H', 'S'])
#         key.append(choice)
#         if choice == 'H':
#             qc.h(i)
#         elif choice == 'S':
#             qc.s(i)
    
#     return qc, key

# def obfuscate_string(sentence):
#     words = sentence.split()
#     word_circuits = []
#     word_keys = []

#     for word in words:
#         word_qcs = []
#         word_word_keys = []
#         for c in word:
#             qc_c, key_c = encode_char_to_qubits(c)
#             word_qcs.append(qc_c)
#             word_word_keys.append(key_c)
        
#         word_circuits.append(word_qcs)
#         word_keys.append(word_word_keys)
    
#     return word_circuits, word_keys

# # Example: Obfuscate sentence
# sentence = "The quick brown fox jumps over the lazy dog!"
# circuits_str, keys_str = obfuscate_string(sentence)
# print(f"Sentence: '{sentence}' split into {len(circuits_str)} words")
# print("Obfuscation keys (per character):", keys_str)

# # Draw first word first character
# print("First word first character circuit:")
# print(circuits_str[0][0].draw('text'))
# pprint(circuits_str)
# pprint(keys_str)

# -----------------------------
# Basis Hiding
# -----------------------------

# def basis_hiding_encode(bitstring):
#     n = len(bitstring)
#     qc = QuantumCircuit(n)
#     key = []

#     for i, b in enumerate(bitstring):
#         if b == '1':
#             qc.x(i)
        
#         # Random basis
#         basis = random.choice(['Z', 'X']) # Z = computational, X = Hadamard basis
#         key.append(basis)
        
#         if basis == 'X':
#             qc.h(i)
    
#     return qc, key

# # Example: Basis hiding on bitstring '1101'
# qc_basis, key_basis = basis_hiding_encode('1101')
# print("Basis hiding circuit:")
# print(qc_basis.draw('text'))
# print("Basis key:", key_basis)

# -----------------------------
# Entanglement-Based Hiding
# -----------------------------

def entangle_data(bitstring):
    n = len(bitstring)
    qc = QuantumCircuit(n + 1)  # Extra ancilla qubit for entanglement
    
    for i, b in enumerate(bitstring):
        if b == '1':
            qc.x(i)
        qc.h(i)
        qc.cx(i, n)  # Entangle with ancilla
    
    return qc

# Example: Entangle data '1010'
qc_ent = entangle_data('1010')
print("Entanglement-based hiding circuit:")
print(qc_ent.draw('text'))

# -----------------------------
# End of Notebook
# -----------------------------

# print("Quantum data obfuscation notebook complete!")

from helper import compile_circuit

def modified_num_obfuscate(num: int, key: int, num_bits: int):
    modified_num = key ^ num
    qc, gate_keys = obfuscate_number(modified_num, num_bits=num_bits)
    
    compiled = compile_circuit(qc)
    
    