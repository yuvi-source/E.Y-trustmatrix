def is_valid_npi(npi: str) -> bool:
    if not npi or not npi.isdigit() or len(npi) != 10:
        return False

    digits = [int(d) for d in npi]

    # NPI uses Luhn with prefix 80840
    prefix = [8, 0, 8, 4, 0]
    full = prefix + digits[:-1]

    total = 0
    for i, d in enumerate(reversed(full)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d

    check_digit = (10 - (total % 10)) % 10
    return check_digit == digits[-1]
