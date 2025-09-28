# Data Obfuscation using Decomposition and Grover Amplification

This is the codebase for our work involving obfuscation of classical data in a quantum-classical hybrid system.

## Code Structure

The code has been prepared inculcate SOLID principles as far as possible. The folders are organized as follows:

1. `algorithms`: Aimed to organize generalized algorithms. (Intended for future works. You can discard this)
2. `circuits`: Contains codes for the various circuits utilized in our work. Includes functionalities for building the custom adder and Grover search algorithm.
3. `tests`: Some test cases written for utilities and grover search
4. `utils`: Contains helper functions.

## Get Started

1. Make sure Python is installed in your system. This can be done in several ways, one way is to check the Python version.
2. Clone this repo using `git clone` and cd into the folder.
```(git)
  git clone https://github.com/amalraj28/data-obfuscation
  cd data-obfuscation
```
2. Set up your virtual environment using the `virtualenv` python package, and activate it.
For Windows:
```
  python -m virtualenv name_of_environment
  name_of_environment/Scripts/activate.ps1
```
For Linux:
```
  python3 -m virtualenv name_of_environment
  source venv/bin/activate
```
3. Install the required packages.
```
  pip install -r requirements.txt
```
4. `main.py` is the entry point to the code. Run `main.py`

