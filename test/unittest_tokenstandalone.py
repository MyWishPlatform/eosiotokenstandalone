import json
from eosfactory.eosf import *
from termcolor import cprint
import unittest
from token_class import *
import re
import warnings
import argparse


def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)
    return do_test


class TokenStandaloneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = {}
        with open('config.h', 'r') as cfg_file:
            for line in cfg_file.readlines():
                match = re.search('#define (\w+) ([\w.]+)', line)
                if match:
                    cls.cfg[match.group(1)] = match.group(2)
        cls.admin = cls.cfg["ADMIN"]
        
        with open("deploy_data.json") as deploy_config:
            cls.deploy_json = json.load(deploy_config)

        token_max_supply = 4611686018427387903

        cls.maximum_supply = cls.deploy_json["maximum_supply"]
        cls.decimals = cls.deploy_json["decimals"]
        cls.symbol = cls.deploy_json["symbol"]

        cprint("#0 Precheck", "magenta")
        assert (0 <= cls.decimals <= 16)
        if cls.decimals == 0:
            assert (0 < cls.maximum_supply <= token_max_supply)
        elif cls.decimals >= 0:
            assert (0 < cls.maximum_supply <= token_max_supply / 10 ** cls.decimals)
        assert (cls.symbol.isupper() and 0 < len(cls.symbol) < 8)

    @classmethod
    def tearDownClass(cls):
        pass

    def run(self, result=None):
        """ Stop after first error """
        if not result.failures:
            super().run(result)

    @ignore_warnings
    def setUp(self):
        empty_hash = "code hash: 0000000000000000000000000000000000000000000000000000000000000000"
        # start node
        reset()

        # create wallet
        create_wallet()

        # create eosio account
        create_master_account("master")
        self.eosio_acc = master
        # create admin account
        create_account("admin_acc", master, self.admin)
        self.admin_acc = admin_acc


        # create token deployer account
        create_account("token_deployer_acc", self.eosio_acc)
        self.token_deployer_acc = token_deployer_acc

        # create buyer account
        create_account("token_buyer", self.eosio_acc)
        self.token_buyer_acc = token_buyer

        # create buyer2 account
        create_account("token_buyer2", self.eosio_acc)
        self.token_buyer2_acc = token_buyer2

        # create buyer3 account
        create_account("token_buyer3", self.eosio_acc)
        self.token_buyer3_acc = token_buyer3


        global main_token
        main_token = Token(
            self.admin_acc,
            self.token_deployer_acc,
            self.maximum_supply,
            self.decimals,
            self.symbol
        )
        main_token.deploy()


        token_total_str = main_token.total_supply()
        token_total = main_token.fromAsset(token_total_str)

        global amount_supply
        amount_supply = int(token_total["amount"])

        global simple_amount
        simple_amount = main_token.to_quantity(int(amount_supply / 2),main_token.decimals,main_token.symbol)

        global one_token
        one_token = main_token.to_quantity(1, main_token.decimals, main_token.symbol)

        global wrong_sym_amount
        wrong_sym_amount = main_token.to_quantity(simple_amount, main_token.decimals, "TEST")

        global wrong_memo
        wrong_memo = 1 + 2 ** 256

        global negative_amount
        negative_amount = -(int(amount_supply/2))

        new_decimals = main_token.decimals
        if new_decimals == 0:
            new_decimals += 1
        else:
            new_decimals -= 1

        global wrong_dec_amount
        wrong_dec_amount = main_token.to_quantity(
            amount_supply,
            new_decimals,
            main_token.symbol
        )


    def tearDown(self):
        stop()

    def test_01(self):
        cprint("#1 Method '''create'''", "magenta")
        cprint("#1.1 Check creating", "green")
        main_token.create(self.admin_acc, self.admin_acc)
        token_info = main_token.get_stats()
        expected_supply = main_token.to_quantity(0,
                                                 main_token.decimals,
                                                 main_token.symbol
                                                 )
        assert (token_info["supply"] == expected_supply)
        assert (token_info["issuer"] == self.admin_acc.name)
        assert (token_info["lock"] == 0)

    def test_02(self):
        cprint("#1.2 Check creating locked", "green")
        main_token.createlocked(self.admin_acc, self.admin_acc)
        token_info = main_token.get_stats()
        expected_supply = main_token.to_quantity(0,
                                                 main_token.decimals,
                                                 main_token.symbol
                                                 )
        assert (token_info["supply"] == expected_supply)
        assert (token_info["issuer"] == self.admin_acc.name)
        assert (token_info["lock"] == 1)

    def test_03(self):
        cprint("#1.3 Create must fail with wrong symbol", "green")
        token3 = Token(
            self.admin_acc,
            self.token_deployer_acc,
            main_token.max_supply,
            main_token.decimals,
            main_token.symbol + "a"
        )
        with self.assertRaises(errors.Error):
             token3.create(self.admin_acc, self.admin_acc)

        cprint("#1.4 Create must fail with negative max supply", "green")
        token4 = Token(
            self.admin_acc,
            self.token_deployer_acc,
            negative_amount,
            main_token.decimals,
            main_token.symbol
        )
        with self.assertRaises(errors.Error):
             token3.create(self.admin_acc, self.admin_acc)

        cprint("#1.5 Create must fail with same symbol", "green")
        token5 = Token(
            self.admin_acc,
            self.token_deployer_acc,
            main_token.max_supply,
            main_token.decimals,
            main_token.symbol
        )
        main_token.create(self.admin_acc, self.admin_acc)
        duplicate_symbol = main_token.total_supply()
        with self.assertRaises(errors.Error):
            main_token.account.push_action(
                "create",
                    {
                        "issuer": self.admin_acc,
                        "maximum_supply": duplicate_symbol
                    },
                    permission=(self.admin_acc, Permission.ACTIVE),
                forceUnique=1
            )

        cprint("#1.6 Create must fail with wrong permission", "green")
        token6 = Token(
            self.admin_acc,
            self.token_deployer_acc,
            main_token.max_supply,
            main_token.decimals,
            main_token.symbol
        )
        with self.assertRaises(errors.Error):
             token6.create(self.admin_acc, self.token_buyer_acc)

    def test_04(self):
        cprint("#2 Method '''issue'''", "magenta")
        cprint("#2.1 Check successful issue", "green")
        main_token.create(self.admin_acc, self.admin_acc)
        balance_before = main_token.account.table("accounts", self.token_buyer_acc.name).json["rows"]
        assert(balance_before == [])
        value = simple_amount
        main_token.issue(self.token_buyer_acc, value, "memo1", self.admin_acc)
        balance_after = main_token.get_balance(self.token_buyer_acc.name)
        assert(balance_after == value)
        supply_after = main_token.get_stats()["supply"]
        assert(supply_after == value)

        cprint("#2.2 Issue must fail with invalid symbol", "green")
        with self.assertRaises(errors.Error):
            main_token.account.push_action(
                "issue",
                    {
                        "to":       self.token_buyer_acc,
                        "quantity": wrong_sym_amount,
                        "memo":     "memo2"
                    },
                    permission=(self.admin_acc, Permission.ACTIVE)
            )

        cprint("#2.3 Issue must fail with memo > 256 bytes", "green")
        with self.assertRaises(errors.Error):
            main_token.issue(self.token_buyer_acc, value, wrong_memo, self.admin_acc)

        cprint("#2.4 Issue must fail without create", "green")
        token2 = Token(
            self.admin_acc,
            self.token_deployer_acc,
            main_token.max_supply,
            main_token.decimals,
            "TEST"
        )
        
        with self.assertRaises(errors.Error):
            token2.issue(self.token_buyer_acc, token2.total_supply(), "memo3", self.admin_acc)

        cprint("#2.5 Issue must fail with negative amount", "green")
        with self.assertRaises(errors.Error):
            main_token.issue(self.token_buyer_acc, negative_amount, "memo4", self.admin_acc)

        cprint("#2.6 Issue must fail with wrong decimals", "green")

        with self.assertRaises(errors.Error):
            main_token.issue(self.token_buyer_acc, wrong_dec_amount, "memo4", self.admin_acc)

        cprint("#2.7 Issue must fail when amount more than max supply", "green")
        more_max_amount = main_token.to_quantity(
            main_token.max_supply * 10,
            main_token.decimals,
            main_token.symbol
        )
        with self.assertRaises(errors.Error):
            main_token.issue(self.token_buyer_acc, more_max_amount, "memo5", self.admin_acc)

        cprint("#2.8 Issue must fail with wrong permission", "green")
        with self.assertRaises(errors.Error):
            main_token.issue(self.token_buyer_acc, one_token, "memo6", self.token_buyer_acc)

    def test_05(self):
        cprint("Method '''transfer'''", "magenta")
        cprint("#3.0 Transfer must fail without create", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.admin_acc,
                self.token_buyer_acc,
                simple_amount,
                "transfer to buyer",
                self.admin_acc
            )

    def test_06(self):
        main_token.create(self.admin_acc, self.admin_acc)
        cprint("#3.1 Check successful transfer", "green")
        amount_transfer = one_token
        main_token.issue(self.admin_acc, simple_amount, "first issue", self.admin_acc)

        balance_before = main_token.account.table("accounts", self.token_buyer_acc.name).json["rows"]
        assert(balance_before == [])
        main_token.transfer(
            self.admin_acc,
            self.token_buyer_acc,
            amount_transfer,
            "transfer to buyer",
            self.admin_acc
        )
        balance_after = main_token.get_balance(self.token_buyer_acc.name)
        assert(balance_after == amount_transfer)

        cprint("#3.2 Cannot transfer to self", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer_acc,
                amount_transfer,
                "fail",
                self.token_buyer_acc
            )

        cprint("#3.3 Cannot transfer on account that doesn't exist", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                "tokenbuyer12",
                amount_transfer,
                "fail",
                self.token_buyer_acc
            )

        cprint("#3.4 Transfer must fail wish invalid symbol", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer2_acc,
                wrong_sym_amount,
                "fail",
                self.token_buyer_acc
            )

        cprint("#3.5 Transfer must fail with memo > 256 bytes", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer2_acc,
                amount_transfer,
                wrong_memo,
                self.token_buyer_acc
            )

        cprint("#3.6 Transfer must fail with negative amount", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer2_acc,
                negative_amount,
                "fail",
                self.token_buyer_acc
            )

        cprint("#3.7 Transfer must fail with wrong decimals", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer2_acc,
                wrong_dec_amount,
                "fail",
                self.token_buyer_acc
            )

        cprint("#3.8 Transfer must fail when amount more than balance", "green")
        buyer_balance = main_token.fromAsset(main_token.get_balance(self.token_buyer_acc.name))
        buyer_new_amount = int(buyer_balance["amount"])
        buyer_balance_new = main_token.to_quantity
        
        more_balance_amount = main_token.to_quantity(
            10 ** 5,
            main_token.decimals,
            main_token.symbol
        )

        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer2_acc,
                more_balance_amount,
                "fail",
                self.token_buyer_acc
            )

        cprint("#3.9 Issue must fail with wrong permission", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer2_acc,
                amount_transfer,
                "fail",
                self.token_buyer2_acc
            )

    def test_07(self):
        cprint("Method '''unlock'''", "magenta")
        token_shortname = "{},{}".format(main_token.decimals, main_token.symbol)
        cprint("#4.1 Unlock must fail without create", "green")
        with self.assertRaises(errors.Error):
            main_token.unlock(token_shortname, self.admin_acc)

        cprint("#4.2 Check succesfull create unlocked", "green")
        main_token.create(self.admin_acc, self.admin_acc)

        cprint("#4.3 Check succesfull transfer", "green")
        main_token.issue(self.admin_acc, simple_amount, "issue to admin", self.admin_acc)
        amount_transfer = one_token
        main_token.transfer(
            self.admin_acc,
            self.token_buyer_acc,
            amount_transfer,
            "transfer to buyer",
            self.admin_acc
        )
        main_token.transfer(
            self.token_buyer_acc,
            self.token_buyer2_acc,
            amount_transfer,
            "transfer to buyer2",
            self.token_buyer_acc
        )

        cprint("#4.4 Unlock must fail when created unlocked", "green")
        with self.assertRaises(errors.Error):
            main_token.unlock(token_shortname, self.admin_acc)

    def test_08(self):
        cprint("#4.5 Check succesfull create locked", "green")
        token_shortname = "{},{}".format(main_token.decimals, main_token.symbol)
        main_token.createlocked(self.admin_acc, self.admin_acc)

        cprint("#4.6 Check succesfull transfer from owner", "green")
        main_token.issue(self.admin_acc, simple_amount, "issue to admin", self.admin_acc)
        amount_transfer = one_token
        
        main_token.transfer(
            self.admin_acc,
            self.token_buyer_acc,
            amount_transfer,
            "transfer to buyer",
            self.admin_acc
        )

        cprint("#4.7 Transfer must fail if not owner when locked", "green")
        with self.assertRaises(errors.Error):
            main_token.transfer(
                self.token_buyer_acc,
                self.token_buyer2_acc,
                amount_transfer,
                "transfer to buyer2",
                self.token_buyer_acc
            )

        cprint("#4.8 Unlock must fail with wrong permissions", "green")
        with self.assertRaises(errors.Error):
            main_token.unlock(token_shortname, self.token_buyer_acc)

        cprint("#4.9 Check successful unlock", "green")
        main_token.unlock(token_shortname, self.admin_acc)
        cprint("#4.10 Transfer must succeed after unlock", "green")
        main_token.transfer(
            self.token_buyer_acc,
            self.token_buyer2_acc,
            amount_transfer,
            "transfer to buyer2",
            self.token_buyer_acc
        )

    def test_09(self):
        cprint("Method '''withdraw'''", "magenta")
        cprint("#5.1 Withdraw must fail without create", "green")
        with self.assertRaises(errors.Error):
            main_token.withdraw(main_token.account.name, one_token, self.admin_acc)

        cprint("#5.2 Check succesfull withdraw", "green")
        main_token.create(self.admin_acc, self.admin_acc)

        main_token.issue(self.admin_acc, simple_amount, "issue to admin", self.admin_acc)
        amount_transfer = one_token

        main_token.transfer(
            self.admin_acc,
            self.token_buyer_acc,
            amount_transfer,
            "transfer to buyer",
            self.admin_acc
        )

        # add eosio.code permission
        token_pubkey = main_token.account.json["permissions"][1]["required_auth"]["keys"][0]["key"]
        token_acc_name = main_token.account.name
        permissionActionJSON = {
            "account": token_acc_name,
            "permission": "active",
            "parent": "owner",
            "auth": {
                "threshold": 1,
                "keys": [
                    {
                        "key": str(token_pubkey),
                        "weight": 1
                    }
                ],
                "accounts": [
                    {
                        "permission": {
                            "actor": token_acc_name,
                            "permission": "eosio.code"
                        },
                        "weight": 1
                    }
                ],
                "waits": []
            }
        }
        self.eosio_acc.push_action(
                "updateauth",
                permissionActionJSON,
                permission=(main_token.account, Permission.ACTIVE))

        main_token.withdraw(self.token_buyer_acc.name, one_token, self.admin_acc)


        cprint("#5.2 Withdraw must fail with wrong permissions", "green")
        with self.assertRaises(errors.Error):
            main_token.withdraw(self.token_buyer_acc.name, one_token, self.token_buyer2_acc)

if __name__ == "__main__":
    verbosity([])  # disable logs

    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", help="increase output verbosity",
                        action="store_true")
    args = parser.parse_args()
    if args.verbose:
        verbosity([Verbosity.INFO, Verbosity.OUT, Verbosity.TRACE, Verbosity.DEBUG])
        print("verbosity turned on")

    unittest.main()
