from engine.verify.anti_triviality import check_test_substance


def test_trivial_tests_rejected():
    assert not check_test_substance(
        {"assertions": ["element exists", "page loads"]}, "F1")


def test_substantive_test_passes():
    assert check_test_substance(
        {"assertions": ["displays the submitted message back to the user"]},
        "F1")


def test_missing_requirement_id_rejected():
    assert not check_test_substance({"assertions": ["displays x"]}, None)
    assert not check_test_substance({"assertions": ["displays x"]}, "")


def test_no_assertions_rejected():
    assert not check_test_substance({}, "F1")
    assert not check_test_substance({"assertions": []}, "F1")
