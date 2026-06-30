"""Guards the #1 correctness risk: every module must join on the SAME canonical key (core.fn)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core
def test_fn_handles_hard_names():
    assert core.fn("Amon-Ra St. Brown")=="amon ra st brown"
    assert core.fn("Kenneth Walker III")=="kenneth walker"
    assert core.fn("Marvin Harrison Jr.")=="marvin harrison"
    assert core.fn("D'Andre Swift")=="dandre swift"
def test_team_abbr():
    assert core.team_abbr("Detroit Lions")=="DET"
    assert core.team_abbr("LA")=="LAR"        # alias
    assert core.team_abbr("KC")=="KC"         # already a code
def test_latest_picks_newest_by_mtime(tmp_path):
    import time
    a=tmp_path/"Dk (1).csv"; b=tmp_path/"Dk.csv"
    a.write_text("x"); time.sleep(0.01); b.write_text("y"); os.utime(b,None)
    assert os.path.basename(core.latest(str(tmp_path/"Dk*.csv")))=="Dk.csv"  # newest, not alphabetical
if __name__=="__main__":
    test_fn_handles_hard_names(); test_team_abbr(); print("names tests pass")
