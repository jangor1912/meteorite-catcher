def test_something() -> None:
    # given
    first_value = 1
    second_value = 1
    expected_sum_value = 2

    # when
    sum_value = first_value + second_value

    # then
    assert sum_value == expected_sum_value
