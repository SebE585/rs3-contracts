from rs3_contracts.api import Result

def test_result_helpers():
    r_ok = Result((True, "OK"))
    r_ko = Result((False, "KO"))
    assert r_ok.ok and r_ok.msg == "OK"
    assert (not r_ko.ok) and r_ko.msg == "KO"
