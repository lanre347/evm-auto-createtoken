from web3 import Web3
import time
import random
import requests
from solcx import compile_standard, install_solc

# Connect to the Monad network via Infura RPC
infura_url = "https://testnet.dplabs-internal.com"
web3 = Web3(Web3.HTTPProvider(infura_url, request_kwargs={'timeout': 60}))

# Check if the connection is successful
if not web3.is_connected():
    raise Exception("Failed to connect to Monad network")

# Constants
CHAIN_ID = 688688  # Monad Chain ID
MAX_RETRIES = 3  # Maximum retries per transaction

# Solidity ERC-20 Contract Code
erc20_contract_source = """
pragma solidity ^0.8.0;

contract ERC20Token {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(string memory _name, string memory _symbol, uint8 _decimals, uint256 _totalSupply) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
        totalSupply = _totalSupply * (10 ** uint256(decimals));
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }

    function transfer(address _to, uint256 _value) public returns (bool success) {
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;
        emit Transfer(msg.sender, _to, _value);
        return true;
    }

    function approve(address _spender, uint256 _value) public returns (bool success) {
        allowance[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }

    function transferFrom(address _from, address _to, uint256 _value) public returns (bool success) {
        require(balanceOf[_from] >= _value, "Insufficient balance");
        require(allowance[_from][msg.sender] >= _value, "Allowance exceeded");
        balanceOf[_from] -= _value;
        balanceOf[_to] += _value;
        allowance[_from][msg.sender] -= _value;
        emit Transfer(_from, _to, _value);
        return true;
    }
}
"""

# Install and compile Solidity
install_solc("0.8.0")
compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {"ERC20Token.sol": {"content": erc20_contract_source}},
        "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
    },
    solc_version="0.8.0",
)

contract_interface = compiled_sol["contracts"]["ERC20Token.sol"]["ERC20Token"]
abi = contract_interface["abi"]
bytecode = contract_interface["evm"]["bytecode"]["object"]

def load_private_keys(filename="privatekeys.txt"):
    try:
        with open(filename, "r") as f:
            keys = [line.strip() for line in f if line.strip()]
        if not keys:
            raise Exception("No private keys found.")
        return keys
    except FileNotFoundError:
        raise Exception(f"File '{filename}' not found.")

# Generate random token details
def generate_random_contract_details():
    words = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Theta", "Lambda", "Sigma", "Omicron", "Nova", "Quantum", "Astro", "Neon", "Fusion", "Solar", "Lunar", "Celestial", "Orbit", "Vortex", "Nebula", "Cosmic", "Hyper", "Galactic", "Phoenix", "Eclipse", "Infinity", "Zenith", "Ethereal", "Genesis", "Aether", "Horizon", "Radiance", "Titan", "Velocity", "Pulsar"]
    name = random.choice(words) + " " + random.choice(words) + " " + random.choice(words)
    symbol = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
    return {
        "total_supply": random.choice([1000000, 2000000, 3000000, 400000]),
        "name": name,
        "symbol": symbol,
        "decimals": random.choice([6, 8, 9, 18])
    }

# Deploy ERC20 contract
def deploy_contract(private_key):
    account = web3.eth.account.from_key(private_key)
    contract_details = generate_random_contract_details()
    
    Contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    tx = Contract.constructor(
        contract_details["name"],
        contract_details["symbol"],
        contract_details["decimals"],
        contract_details["total_supply"]
    ).build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "gas": 5000000,
        "gasPrice": web3.eth.gas_price
    })

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Deployed {contract_details['name']} ({contract_details['symbol']}) at {receipt.contractAddress}")
    return receipt.contractAddress

# Send 0 ETH to deployed contracts
def send_0_eth_transaction(private_key, repetitions):
    sender_address = web3.eth.account.from_key(private_key).address

    for i in range(repetitions):
        to_address = deploy_contract(private_key)

        for attempt in range(MAX_RETRIES):
            try:
                nonce = web3.eth.get_transaction_count(sender_address)
                gas_price = web3.eth.gas_price * 1.1
                estimated_gas_limit = web3.eth.estimate_gas({
                    'from': sender_address,
                    'to': to_address,
                    'value': 0
                })
                gas_limit = int(estimated_gas_limit * 1.2)

                tx = {
                    'nonce': nonce,
                    'to': to_address,
                    'value': 0,
                    'gas': gas_limit,
                    'gasPrice': int(gas_price),
                    'chainId': CHAIN_ID
                }

                signed_tx = web3.eth.account.sign_transaction(tx, private_key)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                print(f"Transaction {i+1}/{repetitions} sent to {to_address}. Tx Hash: {web3.to_hex(tx_hash)}")
                break
            except requests.exceptions.HTTPError as e:
                print(f"HTTPError on attempt {attempt+1}: {e}")
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)
                else:
                    print("Transaction failed after max retries.")
        time.sleep(5)
    print(f"Finished for address {sender_address}")

# Main
if __name__ == "__main__":
    repetitions = int(input("How many times should each private key perform transactions? "))
    try:
        private_keys = load_private_keys()
        for idx, pk in enumerate(private_keys):
            print(f"\n===> Processing account {idx+1}/{len(private_keys)}")
            send_0_eth_transaction(pk, repetitions)
    except Exception as e:
        print(f"Error: {e}")
