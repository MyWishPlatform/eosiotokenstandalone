.PHONY: all test clean
NAME=eosio.token

all:
	rm -rf $(NAME)/$(NAME).wasm
	rm -rf $(NAME)/$(NAME).wast
	eosiocpp -o $(NAME)/$(NAME).wast $(NAME).cpp

test:
	python3 test/unittest_tokenstandalone.py
