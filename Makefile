.PHONY: all clean test debug
NAME=eosio.token

all:
	rm -rf $(NAME)/$(NAME).wasm
	rm -rf $(NAME)/$(NAME).wast
	eosiocpp -o $(NAME)/$(NAME).wast $(NAME).cpp

clean:
	rm -rf $(NAME)/$(NAME).wasm
	rm -rf $(NAME)/$(NAME).wast

test:
	python3 test/unittest_tokenstandalone.py

debug: 
	python3 test/unittest_tokenstandalone.py --verbose
