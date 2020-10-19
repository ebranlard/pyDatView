# --- UNIX
INKSCAPE=inkscape
RM=rm -f
SLASH="/"

# ---- Windows
INKSCAPE="C:/Program Files/Inkscape/inkscape.exe"
RM=del
SLASH="\\"

ICONLIB= ..\pydatview\icons.py



SVGDIR=icons
SVGS=$(notdir $(wildcard $(SVGDIR)/*.svg))
SVGS2PNGS=$(patsubst %,$(SVGDIR)/%,$(SVGS:.svg=.png))

all: clean iconlib

echo:
	@echo $(SVGS2PNGS)

clean:
	$(RM) $(SVGDIR)$(SLASH)*.png

iconlib: $(SVGS2PNGS) embed

$(SVGDIR)/%.png:$(SVGDIR)/%.svg 
	$(INKSCAPE) --export-area-page -w 20 -h 20 -y 0  -e "$@" --file="$<"

embed:
	$(RM) $(ICONLIB) & echo ""
	python png2pyem.py $(SVGS2PNGS)
