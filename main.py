from dotenv import load_dotenv
from mpc import MPCService
from os import getenv

load_dotenv()

FIREBLOCKS_API_SECRET = getenv("FIREBLOCKS_API_SECRET")
FIREBLOCKS_API_KEY = getenv("FIREBLOCKS_API_KEY")

MPC_SERVICE_NAME = "fireblocks"
CLIENT_ID = "e94aecb1-5daf-47f3-948f-2a639a56baa6"
FIREBLOCKS_BASE_URL = "https://api.fireblocks.io"
FIREBLOCKS_ASSET_ID = "MATIC_POLYGON"

transaction = {
    "chainId": 137,
    "nonce": 0,
    "maxPriorityFeePerGas": 33000000000,
    "maxFeePerGas": 279222926017,
    "gas": 37765,
    "to": "0xbDF35D309eC7A24209aD0f198Bc166cF01710402",
    "value": 0,
    "data": "0x4f1ef28600000000000000000000000023d33897ad30684f8a17c8985943fdcb34f7519600000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000000",
}

mpc = MPCService(
    MPC_SERVICE_NAME,
    CLIENT_ID,
    {
        "base_url": FIREBLOCKS_BASE_URL,
        "api_key": FIREBLOCKS_API_KEY,
        "api_secret": FIREBLOCKS_API_SECRET,
    },
    {"fireblocks_asset_id": FIREBLOCKS_ASSET_ID},
)

mpc.sign_transaction(transaction)
print(mpc.get_raw_tranaction())
