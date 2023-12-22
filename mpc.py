from rlp import encode
from fireblocks_sdk import (
    FireblocksSDK,
    TRANSACTION_STATUS_COMPLETED,
    TRANSACTION_STATUS_FAILED,
    TRANSACTION_STATUS_BLOCKED,
    TransferPeerPath,
    RAW,
    TYPED_MESSAGE,
    VAULT_ACCOUNT,
    PagedVaultAccountsRequestFilters,
    RawMessage,
    UnsignedMessage,
)
from eth_utils import add_0x_prefix, keccak, remove_0x_prefix, to_bytes, to_int


class Fireblocks:
    fireblocks: FireblocksSDK
    tx_type: str = TYPED_MESSAGE
    signature: dict
    vault_id: int
    bip44AddressIndex: int | None

    def __init__(self, base_url: str, api_secret: str, api_key: str) -> None:
        self.fireblocks = FireblocksSDK(api_secret, api_key, api_base_url=base_url)
        self.vault_id = None
        self.bip44AddressIndex = None

    def sign(
        self,
        client_id: str,
        asset_id: str,
        raw: str,
        max_attempts: int,
        note: str = None,
    ) -> dict:
        if self.vault_id is None:
            self.vault_id = self.__find_vault_id(client_id)

        status, id = self.__create_transaction(asset_id, self.vault_id, raw, note)

        tx_info = self.fireblocks.get_transaction_by_id(id)
        status = tx_info["status"]
        attempts = 0
        while (status != TRANSACTION_STATUS_COMPLETED) and attempts < max_attempts:
            attempts += 1
            tx_info = self.fireblocks.get_transaction_by_id(id)
            status = tx_info["status"]
            if (
                status == TRANSACTION_STATUS_BLOCKED
                or status == TRANSACTION_STATUS_FAILED
            ):
                raise Exception(f"MPC transaction sagning process {status}")

        self.signature = tx_info["signedMessages"][0]["signature"]

        return self.signature

    def get_address(self, client_id: str, asset_id: str) -> str:
        if self.vault_id is None:
            self.vault_id = self.__find_vault_id(client_id)

        fireblocks_info = self.fireblocks.get_deposit_addresses(self.vault_id, asset_id)
        self.bip44AddressIndex = fireblocks_info[0]["bip44AddressIndex"]
        print(fireblocks_info[0]["address"])

        try:
            return fireblocks_info[0]["address"]
        except IndexError:
            print(f"MPC address not found for client_id {client_id}")

    def __create_transaction(
        self, asset_id: str, vault_id: str, raw: str, note: str = None
    ) -> tuple[str, str]:
        if self.tx_type == RAW:
            id, status = self.fireblocks.create_transaction(
                tx_type=self.tx_type,
                asset_id=asset_id,
                source=TransferPeerPath(VAULT_ACCOUNT, vault_id),
                note=note,
                extra_parameters={"rawMessageData": {"messages": [{"content": raw}]}},
            ).values()
        elif self.tx_type == TYPED_MESSAGE:
            # id, status = self.fireblocks.create_transaction(
            #     tx_type=self.tx_type,
            #     asset_id=asset_id,
            #     source=TransferPeerPath(VAULT_ACCOUNT, vault_id),
            #     note=note,
            #     extra_parameters={
            #         "rawMessageData": RawMessage(
            #             [
            #                 UnsignedMessage(
            #                     content=raw,
            #                     bip44addressIndex=self.bip44AddressIndex,
            #                 )
            #             ]
            #         )
            #     },
            # ).values()
            id, status = self.fireblocks.create_transaction(
                tx_type=self.tx_type,
                asset_id=asset_id,
                source=TransferPeerPath(VAULT_ACCOUNT, vault_id),
                note=note,
                extra_parameters={
                    "rawMessageData": {
                        "messages": [
                            {
                                "content": raw,
                                "bip44addressIndex": self.bip44AddressIndex,
                                "type": "ETH_MESSAGE",
                            }
                        ],
                    },
                    "amount": 0,
                },
            ).values()

        return status, id

    def __find_vault_id(self, client_id: str) -> int | None:
        vault_accounts = self.fireblocks.get_vault_accounts_with_page_info(
            PagedVaultAccountsRequestFilters(name_suffix=client_id)
        )

        if len(vault_accounts["accounts"]) > 0:
            return vault_accounts["accounts"][0]["id"]

        return None


class MPCService:
    service_name: str
    client_id: str
    asset_id: str
    attempts: int
    service_params: dict

    mpc_client: Fireblocks
    signed_operation: dict
    signed_transaction: dict
    raw_transaction: str
    address: str

    def __init__(
        self,
        mpc_service_name: int,
        client_id: str,
        service_params: dict,
        **kwargs,
    ) -> None:
        self.service_name = mpc_service_name
        self.client_id = client_id
        self.service_params = service_params

        self.attempts = kwargs.get("attempts", 10)
        if mpc_service_name == "fireblocks":
            self.asset_id = kwargs["fireblocks_asset_id"]
            self.mpc_client = Fireblocks(**self.service_params)
            self.address = self.mpc_client.get_address(self.client_id, self.asset_id)

    def sign_operation(self, operation_hash: bytes) -> None:
        wrapped_operation_hash = (
            bytes(
                f"\x19Ethereum Signed Message:\n{len(operation_hash)}", encoding="utf-8"
            )
            + operation_hash
        )
        operation_hash_encoded = remove_0x_prefix(
            keccak(primitive=wrapped_operation_hash).hex()
        )

        self.signed_operation = self.mpc_client.sign(
            self.client_id, self.asset_id, operation_hash_encoded, self.attempts
        )

    def sign_transaction(self, transaction: dict) -> None:
        print(transaction)
        encoded_transaction = self.__rlp_encode_transaction(transaction)
        raw_transaction = remove_0x_prefix(
            keccak(hexstr=add_0x_prefix(encoded_transaction)).hex()
        )

        self.signed_transaction = self.mpc_client.sign(
            self.client_id, self.asset_id, raw_transaction, self.attempts
        )
        self.raw_transaction = self.__rlp_encode_transaction_payload(transaction)

    def get_signed_operation(self, format: str = "bytes") -> bytes | str:
        if format == "bytes":
            return bytes.fromhex(self.signed_operation["fullSig"]) + (
                self.signed_operation["v"] + 27
            ).to_bytes(1, byteorder="big")
        elif format == "hex":
            hex_v = remove_0x_prefix(hex(self.signed_operation["v"] + 27))
            return add_0x_prefix(self.signed_operation["fullSig"] + str(hex_v))

    def get_raw_tranaction(self, format: str = "bytes") -> bytes | str:
        if format == "bytes":
            return bytes.fromhex(self.raw_transaction)
        elif format == "hex":
            return add_0x_prefix(self.raw_transaction)

    def set_asset_id(self, new_asset_id: str) -> None:
        self.asset_id = new_asset_id

    def __rlp_encode_transaction(self, tx: dict) -> str:
        encoded_params = encode(
            [
                tx["chainId"],
                tx["nonce"],
                tx["maxPriorityFeePerGas"],
                tx["maxFeePerGas"],
                tx["gas"],
                to_bytes(hexstr=tx["to"]),
                tx["value"],
                to_bytes(hexstr=tx["data"]),
                [],
            ]
        )

        return self.__add_transaction_type(encoded_params.hex())

    def __rlp_encode_transaction_payload(self, tx: dict) -> str:
        encoded_params = encode(
            [
                tx["chainId"],
                tx["nonce"],
                tx["maxPriorityFeePerGas"],
                tx["maxFeePerGas"],
                tx["gas"],
                to_bytes(hexstr=tx["to"]),
                tx["value"],
                to_bytes(hexstr=tx["data"]),
                [],
                self.signed_transaction["v"],
                to_int(hexstr=self.signed_transaction["r"]),
                to_int(hexstr=self.signed_transaction["s"]),
            ]
        )

        return self.__add_transaction_type(encoded_params.hex())

    def __add_transaction_type(self, payload: str) -> str:
        return f"02{remove_0x_prefix(payload)}"
