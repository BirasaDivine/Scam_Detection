import pytest

from app.parsing import ParseError, parse

ANDROID_CHAT = """\
12/03/2024, 14:00 - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.
12/03/2024, 14:01 - Amina Hassan joined using this group's invite link
12/03/2024, 14:05 - Amina Hassan: Hello, are you there?
12/03/2024, 14:06 - Kwame: Yes. What is it?
12/03/2024, 14:07 - Amina Hassan: Your account will be blocked.
Send the fee today.
Thank you
12/03/2024, 14:08 - Kwame: This message was deleted
12/03/2024, 14:09 - Kwame: <Media omitted>
12/03/2024, 14:10 - Amina Hassan changed the subject from "Old" to "Re: payment"
12/03/2024, 14:11 - Kwame: Who is this? <This message was edited>
"""

IOS_CHAT = (
    "[12/03/24, 14:05:11] Family Group: \u200eMessages and calls are end-to-end encrypted. "
    "No one outside of this chat, not even WhatsApp, can read or listen to them.\n"
    "\u200e[12/03/24, 14:05:12] Family Group: \u200eAmina joined using this group's invite link\n"
    "[12/03/24, 14:05:20] Amina: Hi, I am from the bank\n"
    "[12/03/24, 14:06:01] Kwame: Ok\n"
    "and then?\n"
    "\u200e[12/03/24, 14:06:30] Kwame: \u200eimage omitted\n"
    "[12/03/24, 14:07:00] Amina: \u200eThis message was deleted.\n"
    "[12/03/24, 14:08:00] Amina: Please confirm your PIN\n"
)


def texts(messages):
    return [m.text for m in messages]


def test_android_format_with_multiline_and_system_lines():
    msgs = parse(ANDROID_CHAT, "whatsapp")
    assert texts(msgs) == [
        "Hello, are you there?",
        "Yes. What is it?",
        "Your account will be blocked.\nSend the fee today.\nThank you",
        "Who is this?",
    ]
    assert [m.sender for m in msgs] == ["Amina Hassan", "Kwame", "Amina Hassan", "Kwame"]


def test_ios_format_with_multiline_and_system_lines():
    msgs = parse(IOS_CHAT, "whatsapp")
    assert texts(msgs) == ["Hi, I am from the bank", "Ok\nand then?", "Please confirm your PIN"]
    assert [m.sender for m in msgs] == ["Amina", "Kwame", "Amina"]


def test_sender_names_never_appear_in_message_text():
    msgs = parse(ANDROID_CHAT, "whatsapp") + parse(IOS_CHAT, "whatsapp")
    for m in msgs:
        assert "Amina" not in m.text and "Kwame" not in m.text


@pytest.mark.parametrize(
    "line",
    [
        "12/03/2024, 14:05 - Ann: hi",  # day-first, 24h
        "03/12/2024, 2:05 PM - Ann: hi",  # month-first, 12h
        "12/31/2024, 11:59 pm - Ann: hi",  # month-first only (31 cannot be a month)
        "31/12/2024, 23:59 - Ann: hi",  # day-first only
        "12/03/24, 14:05 - Ann: hi",  # two-digit year
        "12.03.24, 14:05 - Ann: hi",  # dots
        "12/03/2024, 2:05\u202fPM - Ann: hi",  # narrow no-break space before PM
        "[12/03/24, 14:05:11] Ann: hi",
        "[3/12/24, 2:05:11 PM] Ann: hi",
        "[12/31/24, 11:59:59\u202fa.m.] Ann: hi",
    ],
)
def test_date_and_time_variants(line):
    msgs = parse(line, "whatsapp")
    assert [(m.sender, m.text) for m in msgs] == [("Ann", "hi")]


@pytest.mark.parametrize(
    "line",
    [
        "32/13/2024, 14:05 - Ann: hi",  # no valid date either way round
        "12/03/2024, 25:05 - Ann: hi",  # hour out of range
        "12/03/2024, 13:05 PM - Ann: hi",  # 13 with PM
        "12/03/2024, 14:65 - Ann: hi",  # minute out of range
    ],
)
def test_impossible_stamps_are_not_headers(line):
    with pytest.raises(ParseError):
        parse(line, "whatsapp")


def test_crlf_and_bom_are_handled():
    raw = "\ufeff12/03/2024, 14:05 - Ann: one\r\nsecond line\r\n12/03/2024, 14:06 - Bo: two\r\n"
    assert texts(parse(raw, "whatsapp")) == ["one\nsecond line", "two"]


def test_text_before_first_header_is_ignored():
    raw = "Exported chat\n12/03/2024, 14:05 - Ann: hi"
    assert texts(parse(raw, "whatsapp")) == ["hi"]


def test_message_text_may_contain_colons():
    raw = "12/03/2024, 14:05 - Ann: Meet at 10:30: room 4"
    assert texts(parse(raw, "whatsapp")) == ["Meet at 10:30: room 4"]


def test_whatsapp_source_without_any_header_raises():
    with pytest.raises(ParseError):
        parse("hello\nthis is not an export", "whatsapp")


def test_export_with_only_system_lines_gives_no_messages():
    raw = "12/03/2024, 14:00 - Messages and calls are end-to-end encrypted."
    assert parse(raw, "whatsapp") == []


def test_plain_text_is_one_message_per_non_empty_line():
    assert texts(parse("first\n\n  second  \n\nthird\n", "plain")) == ["first", "second", "third"]


def test_plain_text_ignores_whatsapp_shape():
    raw = "12/03/2024, 14:05 - Ann: hi"
    assert parse(raw, "plain")[0].text == raw


def test_single_sms_is_one_message():
    msgs = parse("  Dear customer,\nyour account is blocked.\n", "sms")
    assert texts(msgs) == ["Dear customer,\nyour account is blocked."]


def test_empty_sms_gives_no_messages():
    assert parse("   \n ", "sms") == []
