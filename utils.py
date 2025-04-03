def variables_nonetype_conversion_to_string(*variables):
    result = []
    for variable in variables:
        if variable is None:
            result.append("")
        else:
            result.append(variable)
    return result