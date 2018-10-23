
all:
	python pyDatView


deb:
	python pyDatView.py Test.outb
# 	python pyDatView.py weio/_tests/HAWC2_ae.dat

install:
	python setup.py install

dep:
	python -m pip install -r requirements.txt


help:
	echo "Available rules:"
	echo "   all        run the standalone program"
	echo "   install    install the python package in the system" 
	echo "   dep        download the dependencies " 

test:
	python pyDatView.py --test

exe:
	python -m nuitka --follow-imports --include-plugin-directory --include-plugin-files --show-progress --show-modules --output-dir=build-nuitka pyDatView.py

exestd:
	python -m nuitka --python-flag=no_site --assume-yes-for-downloads --standalone --follow-imports --include-plugin-directory --include-plugin-files --show-progress --show-modules --output-dir=build-nuitka-std pyDatView.py

clean:
	rm -rf __pycache__
	rm -rf *.egg-info
	rm -rf *.spec
	rm -rf build*
	rm -rf dist
	

pyexe:
	pyinstaller --onedir pyDatView.py

version:
ifeq ($(OS),Windows_NT)
	@echo "Doing nothing"
else
	@sh _tools/setVersion.sh
endif

installer: version
	python -m nsist _tools/installer.cfg



