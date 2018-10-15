
all:
	python pyDatView.py

install:
	python setup.py install

dep:
	pip install numpy matplotlib pandas wxpython click 


help:
	echo "Available rules:"
	echo "   all        run the standalone program"
	echo "   install    install the python package in the system" 
	echo "   dep        download the dependencies " 

test:
	python pyDatView.py -i testfile

exe:
	python -m nuitka --follow-imports --show-progress --show-modules --output-dir=build-nuitka pyDatView.py

#  --standalone --recurse-all --recurse-on --recurse-directory --show-progress --show-modules --plugin-enable=qt-plugins --python-version=2.7 --remove-output --output-dir=nuitka-build main.py

pyexe:
	pyinstaller --onedir pyDatView.py



