from datetime import datetime
from num2words import num2words

def date_to_words(date_str):
    """
    Convert a date string to a human-readable format.

    This function takes a date string in one of the following formats:
    YYYY-MM-DD, DD-MM-YYYY, or MM-DD-YYYY and converts it to a
    string with the day and full month name (e.g., '01 January').

    Args:
        date_str (str): The date string to be converted.

    Returns:
        str: The formatted date string (e.g., '01 January').

    Raises:
        ValueError: If the date string is not in a supported format or
                    if the date is invalid (e.g., day is out of range for the month).
    """

    possible_formats = [
        '%Y-%m-%d',  # YYYY-MM-DD
        '%d-%m-%Y',  # DD-MM-YYYY
        '%m-%d-%Y'   # MM-DD-YYYY
    ]

    for fmt in possible_formats:
        try:
            formatted_date = datetime.strptime(date_str, fmt)
            break
        except ValueError as V:
            if str(V) == "day is out of range for month":
                print(f"This date is wrong")
                raise V
            else:
                continue
    else:
        raise ValueError(f"Date '{date_str}' does not match any expected format. Expected formats: YYYY-MM-DD, DD-MM-YYYY, MM-DD-YYYY")

    parsed_date = formatted_date.strftime('%d %B')
    return parsed_date

def money_to_words(amount):
    """
    Convert a numeric amount to words in Indian Rupees.

    This function takes a numeric amount and converts it to its word
    representation in Indian Rupees, handling both integer and decimal
    values. For decimal values, it adds "and" before the paise (cents) part.

    Args:
        amount (float or int or str): The numeric amount to be converted.

    Returns:
        str: The amount in words (e.g., 'one thousand two hundred and fifty-six rupees and thirty-four paise').
    """

    money = num2words(str(amount), to='currency', currency='INR', lang='en_IN')

    if "." in str(amount):
        index = money.rfind(",")
        money = money[:index] + " and" + money[index + 1:]
    else:
        index = money.rfind(",")
        money = money[:index]

    return money