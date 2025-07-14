from datetime import datetime
from num2words import num2words

def date_to_words(date_str):
    """Convert date string to words in English."""
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
    """Convert numeric amount to words in Indian Rupees."""
    money = num2words(str(amount), to='currency', currency='INR', lang='en_IN')

    if "." in str(amount):
        index = money.rfind(",")
        money = money[:index] + " and" + money[index + 1:]
    else:
        index = money.rfind(",")
        money = money[:index]

    return money