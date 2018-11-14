from eosfactory.eosf import *

class Token:
    admin = None
    issuer = None
    account = None
    max_supply = None
    decimals = None
    decimals_str = None
    symbol = None
    contract = None

    def __init__(self, token_admin, token_account, token_supply, token_decimals, token_symbol):
        self.admin = token_admin
        self.account = token_account
        self.max_supply = token_supply
        self.decimals = token_decimals
        self.decimals_str = str(10 ** token_decimals)[1:]
        self.symbol = token_symbol
        self.deploy_params = self.to_quantity(self.max_supply, self.decimals, self.symbol)

    def deploy(self):
        self.contract = Contract(
            self.account.name,
            "eosiotokenstandalone/eosio.token/",
            abi_file="eosio.token.abi",
            wasm_file="eosio.token.wasm"
        )
        self.contract.deploy()

    def create(self, token_owner, perm):
        self.issuer = token_owner
        self.account.push_action(
            "create",
                {
                    "issuer": self.issuer,
                    "maximum_supply": self.deploy_params
                },
                permission=(perm, Permission.ACTIVE)
        )

    def createlocked(self, token_owner, perm):
        self.issuer = token_owner
        self.account.push_action(
            "createlocked",
                {
                    "issuer": token_owner,
                    "maximum_supply": self.deploy_params
                },
                permission=(perm, Permission.ACTIVE)
        )

    def issue(self, to, amount, memo, perm):
        self.account.push_action(
            "issue",
                {
                    "to":       to,
                    "quantity": amount,
                    "memo":     memo
                },
                permission=(perm, Permission.ACTIVE)
        )

    def transfer(self, owner, to, amount, memo, perm):
        self.account.push_action(
            "transfer",
                {
                    "from":     owner,
                    "to":       to,
                    "quantity": amount,
                    "memo":     memo
                },
                permission=(perm, Permission.ACTIVE)
        )

    def unlock(self, symbol, perm):
        self.account.push_action(
            "unlock",
                {
                    "symbol": symbol
                },
            permission=(perm, Permission.ACTIVE)
        )

    def withdraw(self, contract, amount, perm):
        self.account.push_action(
            "withdraw",
                {
                    "contract": contract,
                    "quantity":  amount,
                },
            permission=(perm, Permission.ACTIVE)
        )

    # account should passed as namestring, e.g. account.name if not checking raw address
    def get_balance(self, user_account):
        return self.account.table("accounts", user_account).json["rows"][0]["balance"]

    def get_stats(self):
        return self.account.table("stat", self.symbol).json["rows"][0]

    def to_quantity(self, amount, decimals, symbol):
        parsed_dec = str(10 ** decimals)[1:]
        if self.decimals == 0:
            return "{} {}".format(amount, symbol)
        else:
            return "{}.{} {}".format(amount, parsed_dec, symbol)

    def fromAsset(self, asset):
        dictionary = {}
        split = asset.split(" ")
        dictionary["amount"] = float(split[0])
        dictionary["symbol"] = split[1]
        check_decimals = isinstance(split[0], float)
        decimals_count = 0
        if check_decimals:
            decimals_count = len(split[0].split(".")[1])
        dictionary["decimals"] = decimals_count

        return dictionary

    def total_supply(self):
        return self.to_quantity(
            self.max_supply,
            self.decimals,
            self.symbol
        )

