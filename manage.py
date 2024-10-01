import os
from dotenv import load_dotenv
from zpywallet import Wallet
from zpywallet.network import BitcoinTestNet, DashTestNet
from eth_account import Account
import requests
import json
from zpywallet.utils.aes import decrypt
import secrets
from bitcoinlib.wallets import Wallet as BitcoinWallet
from bitcoinlib.mnemonic import Mnemonic
from bitcoinlib.transactions import Transaction
from web3 import Web3
from zpywallet.broadcast import broadcast_transaction
import asyncio
from zpywallet.errors import NetworkException

# Load environment variables
load_dotenv('config.env')

CRYPTO_API_KEY = os.getenv('CRYPTO_API_KEY')

WALLET_FILE = 'wallets.json'

SUPPORTED_NETWORKS = {
    "Bitcoin": "bitcoin/testnet",
    "Dash": "dash/testnet",
    "Ethereum": "ethereum/sepolia"
}

def save_wallet(name, wallet_type, address, private_key, password):
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, 'r') as f:
            wallets = json.load(f)
    else:
        wallets = []
    
    wallets.append({
        "name": name,
        "type": wallet_type,
        "address": address,
        "private_key": private_key,
        "password": password  # Add password to the saved wallet data
    })
    
    with open(WALLET_FILE, 'w') as f:
        json.dump(wallets, f)

def get_wallets():
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, 'r') as f:
            return json.load(f)
    return []

def create_wallet(name, password, wallet_type):
    if wallet_type == "Ethereum":
        private_key = "0x" + secrets.token_hex(32)
        account = Account.from_key(private_key)
        address = account.address
        save_wallet(name, "Ethereum Testnet", address, private_key, password)
        return {"private_key": private_key, "address": address, "password": password}
    elif wallet_type == "Bitcoin":
        mnemonic = Mnemonic().generate()
        wallet = BitcoinWallet.create(
            name,
            keys=mnemonic,
            network='testnet',
            witness_type='segwit',
            password=password
        )
        address = wallet.get_key().address
        save_wallet(name, wallet_type, address, mnemonic, password)
        return {"private_key": mnemonic, "address": address, "password": password}
    elif wallet_type == "Dash":
        network = DashTestNet
        wallet = Wallet(network, None, password)
        address = wallet.addresses()[0]
        try:
            encrypted_private_keys = wallet.encrypted_private_keys
            decrypted_private_keys = json.loads(decrypt(encrypted_private_keys, password))
            private_key = decrypted_private_keys[0]
            save_wallet(name, wallet_type, address, private_key, password)
            return {"private_key": private_key, "address": address, "password": password}
        except Exception as e:
            return {"error": f"Failed to decrypt private key: {str(e)}"}
    else:
        return {"error": f"Unsupported wallet type: {wallet_type}"}

def get_wallet_balance(address, wallet_type):
    base_url = "https://rest.cryptoapis.io/v2"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": CRYPTO_API_KEY
    }

    # Handle both "Ethereum" and "Ethereum Testnet" as the same type
    if wallet_type == "Ethereum Testnet":
        wallet_type = "Ethereum"

    if wallet_type not in SUPPORTED_NETWORKS:
        return "Unsupported wallet type"

    network = SUPPORTED_NETWORKS[wallet_type]

    try:
        response = requests.get(
            f"{base_url}/blockchain-data/{network}/addresses/{address}/balance",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        confirmed_balance = data.get('data', {}).get('item', {}).get('confirmedBalance', {})
        amount = confirmed_balance.get('amount')
        unit = confirmed_balance.get('unit')
        
        if amount is None or unit is None:
            return "Confirmed balance data not found in the response."

        try:
            total = float(amount)
            # Format the balance to 8 decimal places
            formatted_total = f"{total:.8f}"
            # Remove trailing zeros after the decimal point
            formatted_total = formatted_total.rstrip('0').rstrip('.')
            return {
                'total': formatted_total,
                'unit': unit
            }
        except ValueError:
            return "Invalid amount format in the response."

    except requests.RequestException as e:
        return f"Failed to fetch balance: {str(e)}"
    except Exception as e:
        return f"Failed to get balance: {str(e)}"

def get_transaction_history(address, wallet_type):
    base_url = "https://rest.cryptoapis.io/v2"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": CRYPTO_API_KEY
    }

    # Handle both "Ethereum" and "Ethereum Testnet" as the same type
    if wallet_type == "Ethereum Testnet":
        wallet_type = "Ethereum"

    if wallet_type not in SUPPORTED_NETWORKS:
        return "Unsupported wallet type"

    network = SUPPORTED_NETWORKS[wallet_type]
    endpoint = f"/blockchain-data/{network}/addresses/{address}/transactions"

    try:
        response = requests.get(f"{base_url}{endpoint}", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['data']['items']
    except requests.RequestException as e:
        return f"Failed to fetch transaction history: {str(e)}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"Failed to parse transaction history data: {str(e)}"

def delete_wallet(name, wallet_type, address):
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, 'r') as f:
            wallets = json.load(f)
        
        wallets = [w for w in wallets if not (w['name'] == name and w['type'] == wallet_type and w['address'] == address)]
        
        with open(WALLET_FILE, 'w') as f:
            json.dump(wallets, f)
        return True
    return False

def send_crypto(wallet, to_address, amount, wallet_type):
    wallet_type_lower = wallet_type.lower()
    
    if wallet_type_lower in ["ethereum", "ethereum testnet"]:
        return send_ethereum(wallet, to_address, amount)
    elif wallet_type_lower in ["bitcoin", "bitcoin testnet"]:
        return send_bitcoin(wallet, to_address, amount)
    elif wallet_type_lower in ["dash", "dash testnet"]:
        return send_dash(wallet, to_address, amount)
    else:
        return {"error": f"Unsupported wallet type: {wallet_type}"}

def send_ethereum(wallet, to_address, amount):
    # Load environment variables
    load_dotenv('config.env')
    INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID')

    if not INFURA_PROJECT_ID:
        return {"error": "INFURA_PROJECT_ID not found in environment variables"}

    # Connect to the Ethereum network using the Infura Project ID
    w3 = Web3(Web3.HTTPProvider(f'https://sepolia.infura.io/v3/{INFURA_PROJECT_ID}'))

    if not w3.is_connected():
        return {"error": "Cannot connect to the Ethereum network"}

    try:
        # Ensure the addresses are in checksum format
        from_address = Web3.to_checksum_address(wallet['address'])
        to_address = Web3.to_checksum_address(to_address)
    except ValueError as ve:
        return {"error": f"Invalid Ethereum address: {ve}"}

    try:
        # Get the nonce
        nonce = w3.eth.get_transaction_count(from_address)

        # Prepare the transaction
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': w3.to_wei(amount, 'ether'),
            'gas': 21000,  # Standard gas limit for a simple transfer
            'gasPrice': w3.eth.gas_price,
            'chainId': 11155111  # Chain ID for Sepolia testnet
        }

        # Sign the transaction
        signed_tx = w3.eth.account.sign_transaction(tx, wallet['private_key'])

        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for the transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            'txid': tx_receipt['transactionHash'].hex(),
            'status': 'success' if tx_receipt['status'] == 1 else 'failed'
        }
    except Exception as e:
        return {
            'error': f"Failed to create or broadcast Ethereum transaction: {str(e)}",
            'status': 'failed'
        }

def send_bitcoin(wallet, to_address, amount):
    # Load the wallet using bitcoinlib
    btc_wallet = BitcoinWallet(wallet['name'])
    
    # Create a transaction
    tx = btc_wallet.send_to(to_address, amount)
    
    # Sign the transaction
    tx.sign()
    
    # In a real-world scenario, you would broadcast this transaction to the Bitcoin network
    # For this example, we'll just return the transaction details
    return {
        'txid': tx.txid,
        'raw_tx': tx.raw_hex()
    }

def send_dash(wallet, to_address, amount):
    network = DashTestNet
    private_key = wallet.get('private_key')
    password = wallet.get('password')  # Retrieve the password from the wallet data
    
    if not private_key or not password:
        return {"error": "Private key or password not found for this wallet"}
    
    try:
        # Initialize the Dash wallet with the password
        dash_wallet = Wallet(network, private_key, password)
        
        # Convert amount to duffs (1 Dash = 1e8 duffs)
        amount_in_duffs = int(amount * 1e8)
        
        # Prepare the destinations as a list of dictionaries
        destinations = [{"address": to_address, "amount": amount_in_duffs}]
        
        # Create the transaction
        tx = dash_wallet.create_transaction(destinations)
        
        # Sign the transaction
        signed_tx = dash_wallet.sign_transaction(tx)
        
        # Serialize the transaction to hex
        raw_tx_hex = signed_tx.serialize().hex()
        
        # Broadcast the transaction using the broadcast_transaction function
        txid = broadcast_transaction(raw_tx_hex, network)
        
        return {
            'txid': txid,
            'status': 'success'
        }
        
    except Exception as e:
        return {
            'error': f"Failed to create or broadcast Dash transaction: {str(e)}",
            'status': 'failed'
        }