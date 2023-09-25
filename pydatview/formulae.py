from pydatview.common import no_unit
# --------------------------------------------------------------------------------}
# --- Formula 
# --------------------------------------------------------------------------------{

def formatFormula(df, sFormulaRaw):
    sFormula = sFormulaRaw
    for i,c in enumerate(df.columns):
        c_no_unit = no_unit(c).strip()
        c_in_df   = df.columns[i]
        sFormula=sFormula.replace('{'+c_no_unit+'}','df[\''+c_in_df+'\']')
    return sFormula

def evalFormula(df, sFormulaRaw):
    sFormula=formatFormula(df, sFormulaRaw)
    try:
        NewCol=eval(sFormula)
        return NewCol
    except:
        return None

