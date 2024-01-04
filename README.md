# About

In the `main.py` file is the transaction we are trying to sign using the typed message signing service.
The `mpc.py` file contains all the logic for the signing of the transaction.

To run the code, follow these steps:
1. Create a `.env` file with the variables `FIREBLOCKS_API_KEY`, `FIREBLOCKS_API_SECRET` and `RPC_URL`.
2. Create a vitual environment:
```bash
python3 -m venv venv
```
3. Activate the virtual environment:
```bash
source venv/bin/activate
```
4. Install the required dependencies:
```bash
pip install -r requirements.txt
```
5. Run the script:
```bash
python3 ./main.py
```
