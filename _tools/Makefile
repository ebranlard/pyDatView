all: compile test

compile:
	@echo --------------------------------------------------------------------------
	@cl  /nologo -c pyDatView.c 
	@echo --------------------------------------------------------------------------
	@rc /nologo pyDatView.rc
	@echo --------------------------------------------------------------------------
	@link /nologo pyDatView.obj pyDatView.res /out:pyDatView.exe
	@rm *.obj *.res 

test:
	@echo --------------------------------------------------------------------------
	./pyDatView.exe ../example_files/HAWCStab2.pwr ../example_files/CSVComma.csv

clean:
	rm *.obj *.res pyDatView.exe  
