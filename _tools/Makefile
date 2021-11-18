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
	./pyDatView.exe C:\Bin\test.outb BB CC

clean:
	rm *.obj *.res pyDatView.exe  
