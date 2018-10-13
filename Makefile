
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
	pyinstaller --onedir pyDatView.py

