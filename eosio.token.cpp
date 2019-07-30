#include "eosio.token.hpp"
#include "config.h"
#include "str_expand.h"

token::token(account_name self) : 
	eosio::contract(self),
	admin(eosio::string_to_name(STR(ADMIN)))
{}

void token::_create(account_name issuer, eosio::asset maximum_supply, bool lock) {
	eosio_assert(has_auth(this->_self) || has_auth(this->admin), "Not authorized");

	auto sym = maximum_supply.symbol;
	eosio_assert(sym.is_valid(), "invalid symbol name");
	eosio_assert(maximum_supply.is_valid(), "invalid supply");
	eosio_assert(maximum_supply.amount > 0, "max-supply must be positive");

	stats statstable(_self, sym.name());
	auto existing = statstable.find(sym.name());
	eosio_assert(existing == statstable.end(), "token with symbol already exists");

	statstable.emplace(_self, [&](auto& s) {
		s.supply.symbol = maximum_supply.symbol;
		s.max_supply = maximum_supply;
		s.issuer = issuer;
		s.lock = lock;
	});
}

void token::create(account_name issuer, eosio::asset maximum_supply) {
	_create(issuer, maximum_supply, false);
}

void token::createlocked(account_name issuer, eosio::asset maximum_supply) {
	_create(issuer, maximum_supply, true);
}

void token::issue(account_name to, eosio::asset quantity, std::string memo) {
	auto sym = quantity.symbol;
	eosio_assert(sym.is_valid(), "invalid symbol name");
	eosio_assert(memo.size() <= 256, "memo has more than 256 bytes");

	auto sym_name = sym.name();
	stats statstable(_self, sym_name);
	auto existing = statstable.find(sym_name);
	eosio_assert(existing != statstable.end(), "token with symbol does not exist, create token before issue");
	const auto& st = *existing;

	require_auth(st.issuer);
	eosio_assert(quantity.is_valid(), "invalid quantity");
	eosio_assert(quantity.amount > 0, "must issue positive quantity");

	eosio_assert(quantity.symbol == st.supply.symbol, "symbol precision mismatch");
	eosio_assert(quantity.amount <= st.max_supply.amount - st.supply.amount, "quantity exceeds available supply");

	statstable.modify(st, 0, [&](auto& s) {
		s.supply += quantity;
	});

	add_balance(st.issuer, quantity, st.issuer);

	if (to != st.issuer) {
		SEND_INLINE_ACTION(*this, transfer, {st.issuer,N(active)}, {st.issuer, to, quantity, memo});
	}
}

void token::transfer(account_name from, account_name to, eosio::asset quantity, std::string memo) {
	eosio_assert(from != to, "cannot transfer to self");
	require_auth(from);
	eosio_assert(is_account(to), "to account does not exist");
	auto sym = quantity.symbol.name();
	stats statstable(_self, sym);
	const auto& st = statstable.get(sym);

	eosio_assert(!st.lock || from == st.issuer, "token is locked");

	require_recipient(from);
	require_recipient(to);

	eosio_assert(quantity.is_valid(), "invalid quantity");
	eosio_assert(quantity.amount > 0, "must transfer positive quantity");
	eosio_assert(quantity.symbol == st.supply.symbol, "symbol precision mismatch");
	eosio_assert(memo.size() <= 256, "memo has more than 256 bytes");

	sub_balance(from, quantity);
	add_balance(to, quantity, from);
}

void token::unlock(eosio::symbol_type symbol) {
	stats statstable(_self, symbol.name());
	auto it = statstable.find(symbol.name());
	eosio_assert(it != statstable.end(), "token does not exists");
	eosio_assert(it->lock, "token not locked");
	require_auth(it->issuer);
	require_recipient(it->issuer);
	statstable.modify(it, it->issuer, [](auto& st) {
		st.lock = false;
	});
}

void token::burn(account_name owner, eosio::asset value) {
	require_auth(owner);

	auto sym = value.symbol.name();
	stats statstable(_self, sym);
	auto it = statstable.find(sym);

	eosio_assert(it != statstable.end(), "no symbol found");

	statstable.modify(it, owner, [&](auto& s) {
		s.supply -= value;
		s.max_supply -= value;
	});

	sub_balance(owner, value);
}

void token::withdraw(account_name contract, eosio::asset quantity) {
	require_auth(this->admin);

	eosio::action(
		eosio::permission_level(_self, N(active)),
		contract,
		N(transfer),
		transfer_args{_self, this->admin, quantity, "withdraw"}
	).send();
}

void token::sub_balance(account_name owner, eosio::asset value) {
	accounts from_acnts(_self, owner);

	const auto& from = from_acnts.get(value.symbol.name(), "no balance object found");
	eosio_assert(from.balance.amount >= value.amount, "overdrawn balance");

	if (from.balance.amount == value.amount) {
		from_acnts.erase(from);
	} else {
		from_acnts.modify(from, owner, [&](auto& a) {
			a.balance -= value;
		});
	}
}

void token::add_balance(account_name owner, eosio::asset value, account_name ram_payer) {
	accounts to_acnts(_self, owner);
	auto to = to_acnts.find(value.symbol.name());
	if (to == to_acnts.end()) {
		to_acnts.emplace(ram_payer, [&](auto& a) {
			a.balance = value;
		});
	} else {
		to_acnts.modify(to, 0, [&](auto& a) {
			a.balance += value;
		});
	}
}

EOSIO_ABI(token, (create)(createlocked)(issue)(transfer)(unlock)(withdraw)(burn))
