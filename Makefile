include .env
export

.PHONY: test

prepare-dev:
	wget -P test/assets https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank-additional.zip
	cd test/assets; unzip -j bank-additional.zip bank-additional/bank-additional-full.csv
	mv test/assets/bank-additional-full.csv test/assets/bank-marketing.csv
	rm test/assets/bank-additional.zip
test:
	pytest test