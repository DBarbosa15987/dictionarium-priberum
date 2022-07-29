all:
	python main.py output/dic.json

install:
	mkdir output
	gzip -dkc dics/wordlist.gz > dics/wordlist.txt