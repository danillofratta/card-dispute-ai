import pytest

from dispute_analyst.domain.value_objects.cpf import Cpf

VALID = "12345678909"  # synthetic: valid by the algorithm, not a real person


@pytest.mark.parametrize("text", ["123.456.789-09", "12345678909", " 123.456.789-09 "])
def test_parse_accepts_common_formats(text: str) -> None:
    assert Cpf.parse(text).digits == VALID


@pytest.mark.parametrize(
    "text",
    [
        "123.456.789-00",  # wrong check digits
        "111.111.111-11",  # all digits equal
        "1234567890",  # ten digits
        "1234567890a",  # a letter
        "١٢٣٤٥٦٧٨٩٠٩",  # Arabic-Indic digits
    ],
)
def test_parse_rejects_invalid_text(text: str) -> None:
    with pytest.raises(ValueError):
        Cpf.parse(text)


def test_formatted_and_masked() -> None:
    cpf = Cpf(VALID)

    assert cpf.formatted() == "123.456.789-09"
    assert cpf.masked() == "***.456.789-**"


def test_never_shows_the_full_number_by_default() -> None:
    cpf = Cpf(VALID)

    assert VALID not in repr(cpf)
    assert VALID not in str(cpf)
    assert VALID not in f"{cpf}"


def test_error_messages_do_not_echo_the_number() -> None:
    with pytest.raises(ValueError) as error:
        Cpf("12345678900")

    assert "12345678900" not in str(error.value)
