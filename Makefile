all:
	@echo "What do you want to do?"
	@echo " - check ABCD model => make abcd"
	@echo " - list available bench cases => make list"
	@echo " - simulate a bench case (10 sec on 4 proc) => make simul CASE=NAME"

abcd:
	make -C abcd-model

list:
	@find medusa/bench/cases/ -name *.py -exec basename {} .py \;

simul:
	python -m medusa.game medusa/bench/cases/$(CASE).py 4 10 +STATS+LOGS

clean:
	find . -name "*~" -exec rm {} \;
	find . -name "*.py[oc]" -exec rm {} \;
